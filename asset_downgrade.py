"""Force older UE version metadata into loose, editor-format asset copies."""

import os
import shutil
import struct
import tempfile
from collections import Counter
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Iterable

from ue_parser import UEAssetParser


DEFAULT_TARGET = "UE 5.5"
_TARGETS = {"UE 5.5": (5, 1013), "UE 5.3": (3, 1009), "UE 5.1": (1, 1008)}
TARGET_VERSIONS = tuple(_TARGETS)
PACKAGE_EXTENSIONS = (".uasset", ".umap")
_SIDECAR_EXTENSIONS = (".uexp", ".ubulk", ".uptnl", ".m.ubulk")

# FPackageFileSummary and FObjectExport format milestones in ObjectVersion.h.
_SOFT_OBJECT_PATH_LIST = 1008
_DATA_RESOURCES = 1009
_SCRIPT_SERIALIZATION_OFFSET = 1010
_PROPERTY_TAG_EXTENSIONS = 1011
_COMPLETE_PROPERTY_TYPE_NAME = 1012
_METADATA_OFFSET = 1014
_VERSE_CELLS = 1015
_PACKAGE_SAVED_HASH = 1016
_IMPORT_TYPE_HIERARCHIES = 1018
_COMPATIBLE_CHANGELISTS = {5: 37670630, 3: 27405482, 1: 23058290}
_SIMPLE_PROPERTIES = {
    "BoolProperty", "DoubleProperty", "FloatProperty", "IntProperty", "Int8Property",
    "Int16Property", "Int64Property", "UInt16Property", "UInt32Property", "UInt64Property",
    "NameProperty", "StrProperty", "ObjectProperty", "ClassProperty", "SoftObjectProperty",
    "SoftClassProperty",
}

# UE 5.5.4 / 5.3.2 editor registrations and stock packages, plus UE 5.1.1
# editor registrations. An unknown limit leaves that GUID and version intact.
# GUIDs are four uint32s in Unreal's byte order.
_CUSTOM_VERSION_LIMITS = {
    (0x12F88B9F, 0x88754AFC, 0xA67CD90C, 0x383ABD29): (49, 47, 45),  # Rendering
    (0x23AFE18E, 0x4CE14E58, 0x8D61C252, 0xB953BEB7): (11, 11, None),  # Landscape
    (0x35F94A83, 0xE258406C, 0xA31809F5, 0x9610247C): (41, 41, 41),  # Chaos
    (0x59DA5D52, 0x12324948, 0xB8785978, 0x70B8E98B): (8, 8, 8),  # PrivateFrosty
    (0x5B4C06B7, 0x24634AF8, 0x805BBF70, 0xCDF5D0DD): (13, 10, 10),  # FortniteSeason
    (0x601D1886, 0xAC644F84, 0xAA16D3DE, 0x0DEAC7D6): (170, 111, 80),  # FortniteMain
    (0x697DD581, 0xE64F41AB, 0xAA4A51EC, 0xBEB7B628): (119, 118, 88),  # UE5-Main
    (0x78F01B33, 0xEBEA4F98, 0xB9B484EA, 0xCCB95AA2): (20, 20, 20),  # Physics
    (0x8DBC2C5B, 0x54A743E0, 0xA768FCBB, 0x7DA29060): (8, 2, None),  # FortniteValkyrie
    (0x92738C43, 0x29884D9C, 0x9A3D9BBE, 0x6EFF9FC0): (1, 1, None),  # Interchange
    (0x9C54D522, 0xA8264FBE, 0x94210746, 0x61B482D0): (44, 44, 44),  # Release
    (0x9DFFBCD6, 0x494F0158, 0xE2211282, 0x3C92A888): (10, 10, 10),  # Enterprise
    (0xD89B5E42, 0x24BD4D46, 0x8412ACA8, 0xDF641779): (51, 47, 41),  # UE5-Release
    (0xE7086368, 0x6B234C58, 0x84391B70, 0x16265E91): (15, 11, 4),  # FortniteRelease
}
_LIMIT_COLUMN = {5: 0, 3: 1, 1: 2}


@dataclass(frozen=True)
class DowngradeResult:
    source: Path
    relative_path: Path
    output: Path | None
    source_version: str
    detail: str
    status: str

    @property
    def output_root(self) -> Path | None:
        if self.output is not None:
            return self.output.parents[len(self.relative_path.parts) - 1]
        return None


class _PackageSummaryReader:
    def __init__(self, stream: BinaryIO, file_size: int):
        self.stream = stream
        self.limit = min(file_size, 16 * 1024 * 1024)

    def tell(self) -> int:
        return self.stream.tell()

    def take(self, size: int) -> bytes:
        if size < 0 or self.tell() + size > self.limit:
            raise ValueError("UE 包头截断或字段长度无效。")
        data = self.stream.read(size)
        if len(data) != size:
            raise ValueError("UE 包头截断。")
        return data

    def int32(self) -> int:
        return struct.unpack("<i", self.take(4))[0]

    def array(self, element_size: int) -> bytes:
        return self.take(self.int32() * element_size)

    def string(self) -> None:
        size = self.int32()
        self.take(size if size >= 0 else -2 * size)


@dataclass(frozen=True)
class _Patch:
    summary: bytes
    source_version: str
    detail: str
    export_offset: int
    export_count: int
    export_edits: tuple["_ExportEdit | None", ...] = ()
    has_unconverted_properties: bool = False


@dataclass(frozen=True)
class _ExportEdit:
    serial_offset: int
    start: int
    end: int
    old_size: int
    properties: bytes

    @property
    def shrinkage(self) -> int:
        return self.end - self.start - len(self.properties)


def _read_names(stream: BinaryIO, offset: int, count: int, limit: int) -> list[str]:
    stream.seek(offset)
    reader = _PackageSummaryReader(stream, limit)
    if count > (reader.limit - offset) // 8:
        raise ValueError("UE 名称表数量无效。")
    names = []
    for _ in range(count):
        size = reader.int32()
        raw = reader.take(size if size >= 0 else -2 * size)
        names.append(raw.decode("utf-16-le" if size < 0 else "latin-1").rstrip("\0"))
        reader.take(4)  # Serialized name hashes.
    return names


def _fname(reader: _PackageSummaryReader, names: list[str]) -> tuple[bytes, str]:
    raw = reader.take(8)
    index, number = struct.unpack("<2i", raw)
    if not 0 <= index < len(names) or number < 0:
        raise ValueError("UE 属性名无效。")
    return raw, names[index] if not number else f"{names[index]}_{number - 1}"


def _legacy_properties(data: bytes, names: list[str], version: int) -> bytes:
    """Translate root control and simple UE 5.4+ tags, preserving property values."""
    reader = _PackageSummaryReader(BytesIO(data), len(data))
    if reader.take(1) != b"\0":
        raise ValueError("资产使用属性覆盖扩展。")
    result = bytearray()
    while reader.tell() < len(data):
        name_raw, name = _fname(reader, names)
        result.extend(name_raw)
        if name == "None":
            if reader.tell() != len(data):
                raise ValueError("属性结束位置无效。")
            return bytes(result)
        if version < _COMPLETE_PROPERTY_TYPE_NAME:
            raise ValueError("未识别的属性标签布局。")

        type_raw, prop_type = _fname(reader, names)
        remaining = reader.int32()
        if not 0 <= remaining <= 16:
            raise ValueError("属性类型参数无效。")
        params = []
        while remaining:
            raw, param = _fname(reader, names)
            children = reader.int32()
            if len(params) >= 16 or not 0 <= children <= 16:
                raise ValueError("属性类型参数无效。")
            params.append((raw, param, children))
            remaining += children - 1

        size, flags = struct.unpack("<iB", reader.take(5))
        if flags & ~0x1B:
            raise ValueError("资产使用目标版本无法读取的属性扩展。")
        array_index = reader.take(4) if flags & 1 else bytes(4)
        has_guid = bool(flags & 2)
        property_guid = reader.take(16) if has_guid else b""
        if prop_type in _SIMPLE_PROPERTIES and not params:
            extra = bytes((bool(flags & 0x10),)) if prop_type == "BoolProperty" else b""
        elif prop_type == "StructProperty" and flags & 8 and len(params) == 2 and (
            params[0][1:] == ("Guid", 1) and params[1][1:] == ("/Script/CoreUObject", 0)
        ):
            extra = params[0][0] + bytes(16)
        else:
            raise ValueError(f"未适配 {prop_type} 属性布局。")
        result.extend(type_raw + struct.pack("<i", size) + array_index + extra)
        result.extend(bytes((has_guid,)) + property_guid + reader.take(size))
    raise ValueError("UE 属性数据缺少结束标记。")


def _plan_export_edits(
    stream: BinaryIO, file_size: int, header_size: int, export_offset: int, export_count: int,
    name_offset: int, name_count: int, ue5: int,
) -> tuple[tuple[_ExportEdit | None, ...], str]:
    names = _read_names(stream, name_offset, name_count, export_offset)
    edits = []
    first_error = ""
    for index in range(export_count):
        stream.seek(export_offset + index * 112)
        entry = stream.read(112)
        if len(entry) != 112:
            raise ValueError("UE 导出表截断。")
        serial_size, serial_offset = struct.unpack_from("<2q", entry, 28)
        start, end = struct.unpack_from("<2q", entry, 96)
        if start == end == 0:
            edits.append(None)
            continue
        if not 0 <= start < end <= serial_size or serial_offset < header_size:
            raise ValueError("UE 导出属性位置无效。")
        if serial_offset + serial_size > file_size or end - start > 16 * 1024 * 1024:
            edits.append(None)
            first_error = first_error or "属性位于独立导出数据中或超过处理范围"
            continue
        stream.seek(serial_offset + start)
        try:
            properties = _legacy_properties(stream.read(end - start), names, ue5)
            if len(properties) > end - start:
                raise ValueError("旧版标签超出原属性空间。")
            edits.append(_ExportEdit(
                serial_offset, serial_offset + start, serial_offset + end, serial_size, properties,
            ))
        except ValueError as exc:
            edits.append(None)
            first_error = first_error or str(exc).rstrip("。")
    return tuple(edits), first_error


def _plan_patch(stream: BinaryIO, file_size: int, target: str) -> _Patch:
    """Repack only the summary and version-dependent export map metadata."""
    minor, ue5_limit = _TARGETS[target]
    reader = _PackageSummaryReader(stream, file_size)
    magic, legacy, ue3, ue4, ue5, licensee = struct.unpack("<I5i", reader.take(24))
    if magic != UEAssetParser.UASSET_MAGIC:
        raise ValueError("文件不是标准小端 UE 二进制包。")
    if legacy not in (-8, -9) or ue4 != 522 or not 1000 <= ue5 <= _IMPORT_TYPE_HIERARCHIES:
        raise ValueError("仅支持已识别格式的有版本 UE5 资产包。")
    if licensee:
        raise ValueError("该资产使用定制引擎的包版本。")

    if ue5 >= _PACKAGE_SAVED_HASH:
        original_guid = reader.take(20)[:16]
        header_size = reader.int32()
    custom_versions = reader.array(20)
    if ue5 < _PACKAGE_SAVED_HASH:
        header_size = reader.int32()
    custom_end = reader.tell()
    if not custom_end < header_size <= file_size:
        raise ValueError("UE 包头大小无效。")
    reader.limit = min(reader.limit, header_size)
    reader.string()  # Package name
    flags = struct.unpack("<I", reader.take(4))[0]
    if flags & (0x00000200 | 0x00002000 | 0x80000000):
        raise ValueError("仅支持带版本属性的未烘焙编辑器资产。")

    name_count, name_offset = struct.unpack("<2i", reader.take(8))
    if name_count <= 0 or not reader.tell() < name_offset <= reader.limit:
        raise ValueError("UE 名称表位置或数量无效。")
    reader.limit = name_offset
    if ue5 >= _SOFT_OBJECT_PATH_LIST:
        reader.take(8)
    reader.string()  # Localization ID
    reader.take(8)  # Gatherable text count and offset
    export_count, export_offset, import_count, import_offset = struct.unpack("<4i", reader.take(16))

    removed_start = reader.tell()
    if ue5 >= _VERSE_CELLS:
        cell_exports, _, cell_imports, _ = struct.unpack("<4i", reader.take(16))
        if cell_exports or cell_imports:
            raise ValueError("资产使用目标版本不支持的 Verse 单元。")
    if ue5 >= _METADATA_OFFSET:
        reader.take(4)
    removed_end = reader.tell()
    reader.take(20)  # Depends, soft package references, searchable names and thumbnails

    guid_start = reader.tell()
    if ue5 >= _IMPORT_TYPE_HIERARCHIES:
        reader.take(8)
    if ue5 >= _PACKAGE_SAVED_HASH:
        guid_replacement = original_guid
    else:
        guid_replacement = reader.take(16)
    guid_end = reader.tell()
    reader.take(16)  # Persistent GUID
    reader.array(8)  # Generations

    engine_start = reader.tell()
    engine_records = []
    source_version = f"包版本 {ue5}"
    for index in range(2):
        start = reader.tell()
        major, saved_minor, patch, _ = struct.unpack("<3HI", reader.take(10))
        reader.string()
        end = reader.tell()
        if index == 0 and major:
            source_version = f"UE {major}.{saved_minor}.{patch}"
        engine_records.append((start, end, (major, saved_minor) > (5, minor)))
    engine_end = reader.tell()

    reader.take(4)  # Compression flags
    if reader.int32():
        raise ValueError("资产使用不支持的整包压缩。")
    reader.take(4)  # Package source
    additional_packages = reader.int32()
    if not 0 <= additional_packages <= (reader.limit - reader.tell()) // 4:
        raise ValueError("UE 包头中的附加包列表无效。")
    for _ in range(additional_packages):
        reader.string()
    reader.take(16)  # Asset registry, bulk data and world tile offsets
    reader.array(4)  # Chunk IDs
    reader.take(8)  # Preload dependencies
    if ue5 >= 1001:
        reader.take(4)  # Names referenced from export data count
    if ue5 >= 1002:
        reader.take(8)  # Payload TOC offset
    resources_start = reader.tell()
    if ue5 >= _DATA_RESOURCES:
        reader.take(4)
    summary_end = reader.tell()

    has_script_offsets = ue5 >= _SCRIPT_SERIALIZATION_OFFSET
    export_record_size = 112 if has_script_offsets else 96
    if ue5 < 1006:
        export_record_size -= 4
    if ue5 < 1005:
        export_record_size += 16
    if ue5 < 1003:
        export_record_size -= 4
    import_record_size = 40 if ue5 >= 1003 else 36
    for count, offset, record_size in (
        (export_count, export_offset, export_record_size),
        (import_count, import_offset, import_record_size),
    ):
        if count < 0 or (count and not name_offset <= offset <= header_size - count * record_size):
            raise ValueError("UE 导入或导出表位置无效。")

    clamped_versions = bytearray()
    clamped_count = 0
    for *key, version in struct.iter_unpack("<4Ii", custom_versions):
        limits = _CUSTOM_VERSION_LIMITS.get(tuple(key))
        limit = limits[_LIMIT_COLUMN[minor]] if limits else None
        value = min(version, limit) if limit is not None else version
        clamped_count += value != version
        clamped_versions.extend(struct.pack("<4Ii", *key, value))

    new_ue5 = min(ue5, ue5_limit)
    if legacy == -8 and new_ue5 == ue5 and not clamped_count and not any(
        change for _, _, change in engine_records
    ):
        return _Patch(b"", source_version, "已识别的版本字段符合目标范围。", 0, 0)

    stream.seek(0)
    original = stream.read(summary_end)
    if len(original) != summary_end:
        raise ValueError("UE 包头在读取期间发生变化。")
    summary = bytearray(struct.pack("<I5ii", magic, -8, ue3, ue4, new_ue5, licensee, len(custom_versions) // 20))
    summary.extend(clamped_versions)
    summary.extend(struct.pack("<i", header_size))
    summary.extend(original[custom_end:removed_start])
    summary.extend(original[removed_end:guid_start])
    summary.extend(guid_replacement)
    summary.extend(original[guid_end:engine_start])
    for start, end, change in engine_records:
        if change:
            label = f"++UE5+Release-5.{minor}".encode("ascii") + b"\0"
            if end - start < 14 + len(label):
                label = b""
            changelist = _COMPATIBLE_CHANGELISTS[minor]
            summary.extend(struct.pack("<3HIi", 5, minor, 0, changelist, len(label)) + label)
        else:
            summary.extend(original[start:end])
    tail_end = resources_start if new_ue5 < _DATA_RESOURCES else summary_end
    summary.extend(original[engine_end:tail_end])
    if len(summary) > summary_end:
        raise ValueError("降级后的摘要超出原有空间。")

    # Leave the file size and absolute locations of tables and payloads intact.
    summary.extend(bytes(summary_end - len(summary)))
    compact_export_map = has_script_offsets and new_ue5 < _SCRIPT_SERIALIZATION_OFFSET
    export_edits = ()
    unconverted_properties = ""
    detail = f"包版本 {ue5} → {new_ue5}，下调 {clamped_count} 个已知自定义版本"
    if compact_export_map and ue5 >= _PROPERTY_TAG_EXTENSIONS and export_count:
        export_edits, unconverted_properties = _plan_export_edits(
            stream, file_size, header_size, export_offset, export_count, name_offset, name_count, ue5,
        )
        if unconverted_properties:
            detail = f"部分属性仍为新版（{unconverted_properties}）。{detail}"
    return _Patch(
        bytes(summary), source_version, detail, export_offset, export_count if compact_export_map else 0, export_edits,
        bool(unconverted_properties),
    )


def _write_package(stream: BinaryIO, output: BinaryIO, patch: _Patch) -> None:
    stream.seek(0)
    shutil.copyfileobj(stream, output, length=1024 * 1024)
    if patch.summary:
        output.seek(0)
        output.write(patch.summary)
    if patch.export_count:
        stream.seek(patch.export_offset)
        output.seek(patch.export_offset)
        for index in range(patch.export_count):
            entry = stream.read(112)
            if len(entry) != 112:
                raise ValueError("UE 导出表截断。")
            edit = patch.export_edits[index] if patch.export_edits else None
            if edit:
                entry = bytearray(entry)
                struct.pack_into(
                    "<2q", entry, 28, edit.old_size - edit.shrinkage, edit.serial_offset + edit.shrinkage,
                )
            output.write(entry[:96])
        # The next package section still starts at its original offset.
        remaining = 16 * patch.export_count
        while remaining:
            chunk = min(remaining, 1024 * 1024)
            output.write(bytes(chunk))
            remaining -= chunk
    for edit in patch.export_edits:
        if edit is None:
            continue
        # Right-align the smaller export so native data after the tags stays at its original offset.
        output.seek(edit.serial_offset)
        output.write(bytes(edit.shrinkage))
        stream.seek(edit.serial_offset)
        remaining = edit.start - edit.serial_offset
        while remaining:
            chunk = stream.read(min(remaining, 1024 * 1024))
            if not chunk:
                raise ValueError("UE 导出数据截断。")
            output.write(chunk)
            remaining -= len(chunk)
        output.write(edit.properties)


def _collect_sources(
    sources: Iterable[str | Path], destination: Path,
) -> tuple[dict[Path, Path], list[DowngradeResult]]:
    roots = list(dict.fromkeys(Path(source).resolve() for source in sources))
    folders = sorted((root for root in roots if root.is_dir()), key=lambda path: len(path.parts))
    files = {}
    results = []
    for folder in folders:
        scan_errors = []
        found = False
        for current, subdirs, names in os.walk(folder, onerror=scan_errors.append):
            directory = Path(current)
            # A chosen output directory below the input is outside the source asset tree.
            subdirs[:] = sorted(name for name in subdirs if directory / name != destination)
            for name in sorted(names):
                path = directory / name
                if path.suffix.lower() in PACKAGE_EXTENSIONS:
                    relative = Path(folder.name) / path.relative_to(folder)
                    files.setdefault(path, relative)
                    found = True
        for error in scan_errors:
            source = Path(error.filename) if error.filename else folder
            results.append(DowngradeResult(source, Path(folder.name), None, "—", str(error), "失败"))
        if not found and not scan_errors:
            results.append(DowngradeResult(
                folder, Path(folder.name), None, "—", "文件夹中没有 .uasset 或 .umap 文件。", "失败",
            ))
    for path in roots:
        if path not in folders:
            files.setdefault(path, Path(path.name))
    return files, results


def downgrade_assets(
    sources: Iterable[str | Path], destination: str | Path, target: str = DEFAULT_TARGET,
) -> list[DowngradeResult]:
    """Export individually selected assets and recursively discovered folder assets."""
    if target not in _TARGETS:
        raise ValueError(f"未知目标版本 {target}")
    root = Path(destination).resolve()
    paths, results = _collect_sources(sources, root)
    stems = Counter(str(relative.with_suffix("")).casefold() for relative in paths.values())
    result_dir = None
    for source, relative in paths.items():
        written = []
        source_version = "—"
        try:
            if source.suffix.lower() not in PACKAGE_EXTENSIONS:
                raise ValueError("请选择 .uasset 或 .umap 文件。")
            if stems[str(relative.with_suffix("")).casefold()] > 1:
                raise ValueError("所选资产在输出中路径冲突，请分开导出。")
            with source.open("rb") as stream:
                stream.seek(0, 2)
                file_size = stream.tell()
                stream.seek(0)
                patch = _plan_patch(stream, file_size, target)
                source_version = patch.source_version
                if result_dir is None:
                    result_dir = Path(tempfile.mkdtemp(prefix=f"UE5.{_TARGETS[target][0]}_", dir=root))
                path = result_dir / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                for extension in _SIDECAR_EXTENSIONS:
                    sidecar = source.with_suffix(extension)
                    if sidecar.is_file():
                        copy = path.with_suffix(extension)
                        with sidecar.open("rb") as side_input, copy.open("xb") as side_output:
                            written.append(copy)
                            shutil.copyfileobj(side_input, side_output, length=1024 * 1024)
                with path.open("xb") as output:
                    written.append(path)
                    _write_package(stream, output, patch)
            status = "已改写" if patch.summary else "已复制"
            if patch.has_unconverted_properties:
                status = "属性未完全适配"
            results.append(DowngradeResult(source, relative, path, source_version, patch.detail, status))
        except (OSError, ValueError) as exc:
            for path in written:
                path.unlink(missing_ok=True)
            results.append(DowngradeResult(source, relative, None, source_version, str(exc), "失败"))
    if result_dir is not None:
        for current, subdirs, names in os.walk(result_dir, topdown=False):
            directory = Path(current)
            if not names and not any((directory / name).exists() for name in subdirs):
                directory.rmdir()
    return results
