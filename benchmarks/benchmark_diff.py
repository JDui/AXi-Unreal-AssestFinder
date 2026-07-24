"""Repeatable Python/Rust UE asset diff benchmark."""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from asset_diff import compare_asset_folders


def create_fixture(root: Path, file_count: int, file_size_mb: int) -> tuple[Path, Path]:
    old_root = root / "old"
    new_root = root / "new"
    old_content = old_root / "Content"
    new_content = new_root / "Content"
    old_content.mkdir(parents=True)
    new_content.mkdir(parents=True)
    randomizer = random.Random(20260724)
    block_size = file_size_mb * 1024 * 1024
    for index in range(file_count):
        relative_path = Path(f"Group{index % 8}") / f"Asset_{index:04d}.uasset"
        old_path = old_content / relative_path
        new_path = new_content / relative_path
        old_path.parent.mkdir(parents=True, exist_ok=True)
        new_path.parent.mkdir(parents=True, exist_ok=True)
        data = randomizer.randbytes(block_size)
        old_path.write_bytes(data)
        new_path.write_bytes(data)
    changed_path = new_content / "Group0" / "Asset_0000.uasset"
    changed = bytearray(changed_path.read_bytes())
    changed[-1] ^= 0xFF
    changed_path.write_bytes(changed)
    (new_content / "Added.uasset").write_bytes(b"added")
    (old_content / "Deleted.uasset").write_bytes(b"deleted")
    return old_root, new_root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rust-bin", type=Path, required=True)
    parser.add_argument("--files", type=int, default=64)
    parser.add_argument("--size-mb", type=int, default=2)
    parser.add_argument("--runs", type=int, default=5)
    arguments = parser.parse_args()

    timings = {"python": [], "rust": []}
    with tempfile.TemporaryDirectory(prefix="ue-diff-bench-") as temp:
        old_root, new_root = create_fixture(Path(temp), arguments.files, arguments.size_mb)
        for index in range(arguments.runs):
            order = ("python", "rust") if index % 2 == 0 else ("rust", "python")
            for implementation in order:
                started_at = time.perf_counter()
                if implementation == "python":
                    result = compare_asset_folders(old_root, new_root)
                    assert (result.added_count, result.modified_count, result.deleted_count) == (1, 1, 1)
                else:
                    completed = subprocess.run(
                        [str(arguments.rust_bin), str(old_root), str(new_root)],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    rust_result = json.loads(completed.stdout)
                    assert (
                        rust_result["added"],
                        rust_result["modified"],
                        rust_result["deleted"],
                    ) == (1, 1, 1)
                timings[implementation].append(time.perf_counter() - started_at)

    for implementation, samples in timings.items():
        samples.sort()
        median = samples[len(samples) // 2]
        print(f"{implementation}: median={median:.4f}s samples={samples}")
    speedup = timings["python"][len(timings["python"]) // 2] / timings["rust"][len(timings["rust"]) // 2]
    print(f"rust_speedup={speedup:.2f}x")


if __name__ == "__main__":
    main()
