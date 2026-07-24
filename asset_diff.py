"""UE asset folder comparison and difference-package export."""

from __future__ import annotations

import json
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Optional


UE_ASSET_EXTENSIONS = frozenset({".uasset", ".umap", ".uexp", ".ubulk"})
_COPY_BUFFER_SIZE = 1024 * 1024


@dataclass(frozen=True)
class DiffEntry:
    """One changed relative file path."""

    relative_path: str
    status: str
    old_size: Optional[int]
    new_size: Optional[int]
    reason: str


@dataclass(frozen=True)
class ComparisonResult:
    """Complete comparison result for two folder snapshots."""

    old_root: str
    new_root: str
    old_game_prefix: str
    new_game_prefix: str
    entries: tuple[DiffEntry, ...]
    old_file_count: int
    new_file_count: int
    unchanged_count: int
    elapsed_seconds: float

    @property
    def added_count(self) -> int:
        return sum(entry.status == "added" for entry in self.entries)

    @property
    def modified_count(self) -> int:
        return sum(entry.status == "modified" for entry in self.entries)

    @property
    def deleted_count(self) -> int:
        return sum(entry.status == "deleted" for entry in self.entries)

    @property
    def size_changed_count(self) -> int:
        return sum(entry.reason == "size_changed" for entry in self.entries)

    @property
    def content_changed_count(self) -> int:
        return sum(entry.reason == "content_changed" for entry in self.entries)


@dataclass(frozen=True)
class _ContentScope:
    scan_root: Path
    game_prefix: str


def _find_nested_content_root(selected_root: Path) -> Optional[Path]:
    """Find the nearest descendant Content directory using breadth-first search."""

    ignored_names = {
        ".git",
        "binaries",
        "deriveddatacache",
        "intermediate",
        "node_modules",
        "saved",
    }
    pending = [selected_root]
    while pending:
        next_level: list[Path] = []
        matches: list[Path] = []
        for directory in pending:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    name = entry.name.casefold()
                    path = Path(entry.path)
                    if name == "content":
                        matches.append(path)
                    elif name not in ignored_names:
                        next_level.append(path)
        if matches:
            matches.sort(key=lambda path: str(path).casefold())
            if len(matches) > 1:
                listed = "\n".join(str(path) for path in matches[:8])
                raise ValueError(
                    "同一层级发现多个 Content 文件夹，请拖入更精确的 Old / New 上层目录:\n"
                    f"{listed}"
                )
            return matches[0]
        pending = next_level

    return None


def _resolve_content_scope(selected_root: Path) -> Optional[_ContentScope]:
    """Resolve a real Content mapping, or None for a detached asset folder."""

    for candidate in (selected_root, *selected_root.parents):
        if candidate.name.casefold() == "content":
            relative = selected_root.relative_to(candidate)
            prefix = "" if str(relative) == "." else relative.as_posix()
            return _ContentScope(selected_root, prefix)

    content_root = _find_nested_content_root(selected_root)
    if content_root is None:
        return None
    return _ContentScope(content_root, "")


def _collect_files(
    scan_root: Path,
    game_prefix: str,
    extensions: frozenset[str],
) -> dict[str, tuple[str, Path, int]]:
    files: dict[str, tuple[str, Path, int]] = {}
    for current_root, dir_names, file_names in os.walk(scan_root):
        dir_names.sort(key=str.casefold)
        for file_name in sorted(file_names, key=str.casefold):
            path = Path(current_root) / file_name
            if path.suffix.lower() not in extensions:
                continue
            local_path = path.relative_to(scan_root)
            relative_path = (
                (PurePosixPath(game_prefix) / PurePosixPath(local_path.as_posix())).as_posix()
                if game_prefix
                else local_path.as_posix()
            )
            key = relative_path.casefold()
            if key in files:
                raise ValueError(f"检测到仅大小写不同的重复路径: {relative_path}")
            files[key] = (relative_path, path, path.stat().st_size)
    return files


def _files_equal(left: Path, right: Path) -> bool:
    with left.open("rb", buffering=0) as left_file, right.open("rb", buffering=0) as right_file:
        while True:
            left_data = left_file.read(_COPY_BUFFER_SIZE)
            right_data = right_file.read(_COPY_BUFFER_SIZE)
            if left_data != right_data:
                return False
            if not left_data:
                return True


def compare_asset_folders(
    old_root: os.PathLike[str] | str,
    new_root: os.PathLike[str] | str,
    *,
    extensions: Iterable[str] = UE_ASSET_EXTENSIONS,
    workers: Optional[int] = None,
) -> ComparisonResult:
    """Compare UE asset files by relative path and exact bytes."""

    started_at = time.perf_counter()
    old_path = Path(old_root).expanduser().resolve()
    new_path = Path(new_root).expanduser().resolve()
    if not old_path.is_dir():
        raise ValueError(f"Old 文件夹不存在: {old_path}")
    if not new_path.is_dir():
        raise ValueError(f"New 文件夹不存在: {new_path}")
    if old_path == new_path:
        raise ValueError("Old 与 New 不能是同一文件夹")

    old_scope = _resolve_content_scope(old_path)
    new_scope = _resolve_content_scope(new_path)
    if old_scope is None and new_scope is None:
        raise ValueError(
            "Old 与 New 均未找到 Content 路径，无法确定资产对应的 /Game 起点"
        )
    if old_scope is None:
        old_scope = _ContentScope(old_path, new_scope.game_prefix)
    if new_scope is None:
        new_scope = _ContentScope(new_path, old_scope.game_prefix)

    normalized_extensions = frozenset(
        extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        for extension in extensions
    )
    old_files = _collect_files(
        old_scope.scan_root,
        old_scope.game_prefix,
        normalized_extensions,
    )
    new_files = _collect_files(
        new_scope.scan_root,
        new_scope.game_prefix,
        normalized_extensions,
    )
    all_keys = sorted(old_files.keys() | new_files.keys())

    entries: list[DiffEntry] = []
    same_size_pairs: list[tuple[str, tuple[str, Path, int], tuple[str, Path, int]]] = []
    unchanged_count = 0

    for key in all_keys:
        old_item = old_files.get(key)
        new_item = new_files.get(key)
        if old_item is None:
            relative_path, _, new_size = new_item
            entries.append(DiffEntry(relative_path, "added", None, new_size, "added"))
        elif new_item is None:
            relative_path, _, old_size = old_item
            entries.append(DiffEntry(relative_path, "deleted", old_size, None, "deleted"))
        elif old_item[2] != new_item[2]:
            entries.append(
                DiffEntry(
                    new_item[0],
                    "modified",
                    old_item[2],
                    new_item[2],
                    "size_changed",
                )
            )
        else:
            same_size_pairs.append((key, old_item, new_item))

    def compare_pair(
        pair: tuple[str, tuple[str, Path, int], tuple[str, Path, int]]
    ) -> tuple[str, bool]:
        key, old_item, new_item = pair
        return key, _files_equal(old_item[1], new_item[1])

    max_workers = workers or min(8, max(1, os.cpu_count() or 1))
    if same_size_pairs:
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ue-diff") as executor:
            pair_results = dict(executor.map(compare_pair, same_size_pairs))
        for key, old_item, new_item in same_size_pairs:
            if pair_results[key]:
                unchanged_count += 1
            else:
                entries.append(
                    DiffEntry(
                        new_item[0],
                        "modified",
                        old_item[2],
                        new_item[2],
                        "content_changed",
                    )
                )

    status_order = {"added": 0, "modified": 1, "deleted": 2}
    entries.sort(key=lambda entry: (status_order[entry.status], entry.relative_path.casefold()))
    return ComparisonResult(
        old_root=str(old_scope.scan_root),
        new_root=str(new_scope.scan_root),
        old_game_prefix=old_scope.game_prefix,
        new_game_prefix=new_scope.game_prefix,
        entries=tuple(entries),
        old_file_count=len(old_files),
        new_file_count=len(new_files),
        unchanged_count=unchanged_count,
        elapsed_seconds=time.perf_counter() - started_at,
    )


def export_difference_package(
    result: ComparisonResult,
    destination: os.PathLike[str] | str,
    *,
    selected_paths: Optional[Iterable[str]] = None,
) -> Path:
    """Export selected added/modified files and a deletion-aware JSON manifest."""

    destination_path = Path(destination).expanduser().resolve()
    if destination_path.exists() and any(destination_path.iterdir()):
        raise ValueError(f"导出目录必须为空: {destination_path}")
    destination_path.mkdir(parents=True, exist_ok=True)

    selected_keys = (
        None
        if selected_paths is None
        else {str(path).replace("\\", "/").casefold() for path in selected_paths}
    )
    selected_entries = [
        entry
        for entry in result.entries
        if selected_keys is None or entry.relative_path.casefold() in selected_keys
    ]
    if not selected_entries:
        raise ValueError("未选择任何差异文件")

    new_root = Path(result.new_root).resolve()
    files_root = destination_path / "Content"
    copied_count = 0
    copied_bytes = 0
    for entry in selected_entries:
        if entry.status == "deleted":
            continue
        game_path = PurePosixPath(entry.relative_path)
        prefix_parts = (
            PurePosixPath(result.new_game_prefix).parts
            if result.new_game_prefix
            else ()
        )
        game_parts = game_path.parts
        if tuple(part.casefold() for part in game_parts[: len(prefix_parts)]) != tuple(
            part.casefold() for part in prefix_parts
        ):
            raise ValueError(
                f"差异路径不属于 New 的 /Game 计算范围: {entry.relative_path}"
            )
        local_parts = game_parts[len(prefix_parts) :]
        source = new_root.joinpath(*local_parts).resolve()
        try:
            source.relative_to(new_root)
        except ValueError as exc:
            raise ValueError(f"非法相对路径: {entry.relative_path}") from exc
        if not source.is_file():
            raise FileNotFoundError(f"New 文件夹中缺少差异文件: {entry.relative_path}")
        target = files_root / Path(entry.relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied_count += 1
        copied_bytes += source.stat().st_size

    def manifest_entry(entry: DiffEntry) -> dict:
        item = asdict(entry)
        content_path = (Path("Content") / Path(entry.relative_path)).as_posix()
        game_relative = Path(entry.relative_path).with_suffix("").as_posix()
        item["content_path"] = content_path
        item["game_path"] = f"/Game/{game_relative}"
        return item

    manifest = {
        "format": "axi-ue-asset-diff",
        "version": 1,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "old_folder": Path(result.old_root).name,
        "new_folder": Path(result.new_root).name,
        "selected_count": len(selected_entries),
        "copied_count": copied_count,
        "copied_bytes": copied_bytes,
        "deleted_paths": [
            (Path("Content") / Path(entry.relative_path)).as_posix()
            for entry in selected_entries
            if entry.status == "deleted"
        ],
        "deleted_game_paths": [
            f"/Game/{Path(entry.relative_path).with_suffix('').as_posix()}"
            for entry in selected_entries
            if entry.status == "deleted"
        ],
        "entries": [manifest_entry(entry) for entry in selected_entries],
    }
    manifest_path = destination_path / "diff_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destination_path
