import struct
import tempfile
import unittest
from pathlib import Path

from asset_downgrade import downgrade_assets


def _string(text):
    return struct.pack("<i", len(text) + 1) + text.encode("ascii") + b"\0"


def _package(package_flags=0, property_flags=0):
    name_offset, export_offset, serial_offset = 512, 600, 900
    saved_version = struct.pack("<3HI", 5, 8, 2, 51000000) + _string("++UE5+Release-5.8")
    release_stream = (0xD89B5E42, 0x24BD4D46, 0x8412ACA8, 0xDF641779)
    summary = struct.pack("<I5i", 0x9E2A83C1, -9, 864, 522, 1018, 0)
    summary += b"H" * 20 + struct.pack("<2i", serial_offset, 2)
    summary += struct.pack("<4Ii4Ii", *release_stream, 68, 1, 2, 3, 4, 99)
    summary += _string("/Game/Test") + struct.pack("<5i", package_flags, 3, name_offset, 0, 0)
    summary += _string("Test") + struct.pack("<6i", 0, 0, 1, export_offset, 0, 0)
    summary += bytes(20 + 20 + 8 + 16 + 4)  # New sections, offsets, persistent GUID, generations.
    summary += saved_version * 2
    summary += bytes(16 + 16 + 4 + 8 + 4 + 8 + 4)  # Remaining package summary fields.
    names = b"".join(_string(name) + bytes(4) for name in ("None", "TestProperty", "IntProperty"))
    tags = b"\0" + struct.pack("<2i3iiB", 1, 0, 2, 0, 0, 4, property_flags)
    tags += struct.pack("<i2i", 42, 0, 0)
    prefix, suffix = b"prefix", b"native data"
    serial = prefix + tags + suffix
    entry = bytearray(112)
    struct.pack_into("<2q", entry, 28, len(serial), serial_offset)
    struct.pack_into("<2q", entry, 96, len(prefix), len(prefix) + len(tags))
    data = summary.ljust(name_offset, b"\0") + names
    data = data.ljust(export_offset, b"\0") + entry
    data = data.ljust(serial_offset, b"\0") + serial
    return data, export_offset, serial_offset


class AssetDowngradeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.source = self.base / "Test.umap"

    def test_default_target_rewrites_summary_and_preserves_original_and_sidecar(self):
        package, _, serial_offset = _package()
        self.source.write_bytes(package)
        self.source.with_suffix(".ubulk").write_bytes(b"bulk")
        result, = downgrade_assets([self.source], self.base)
        self.assertIsNotNone(result.output, result.detail)
        copy = result.output.read_bytes()
        self.assertEqual(result.output.name, self.source.name)
        self.assertEqual(result.source_version, "UE 5.8.2")
        self.assertEqual(struct.unpack_from("<5i", copy, 4), (-8, 864, 522, 1013, 0))
        self.assertEqual(struct.unpack_from("<i", copy, 44)[0], 51)
        self.assertEqual(struct.unpack_from("<i", copy, 64)[0], 99)
        self.assertIn(b"++UE5+Release-5.5", copy)
        self.assertEqual(copy[serial_offset:], package[serial_offset:])
        self.assertEqual(self.source.read_bytes(), package)
        self.assertEqual(result.output.with_suffix(".ubulk").read_bytes(), b"bulk")

    def test_older_targets_compact_export_map_and_translate_property_tags(self):
        package, export_offset, serial_offset = _package()
        self.source.write_bytes(package)
        for target, version, release in (("UE 5.3", 1009, 47), ("UE 5.1", 1008, 41)):
            with self.subTest(target=target):
                result, = downgrade_assets([self.source], self.base, target)
                self.assertIsNotNone(result.output, result.detail)
                copy = result.output.read_bytes()
                self.assertEqual(len(copy), len(package))
                self.assertEqual(struct.unpack_from("<i", copy, 16)[0], version)
                self.assertEqual(struct.unpack_from("<i", copy, 44)[0], release)
                self.assertEqual(copy[export_offset + 96:export_offset + 112], bytes(16))
                size, offset = struct.unpack_from("<2q", copy, export_offset + 28)
                self.assertEqual(offset, serial_offset + 1)
                self.assertEqual(offset + size, len(copy))
                expected = b"prefix" + struct.pack("<6iB3i", 1, 0, 2, 0, 4, 0, 0, 42, 0, 0)
                self.assertEqual(copy[offset:], expected + b"native data")

    def test_already_compatible_package_is_copied_without_rewriting(self):
        self.source.write_bytes(_package()[0])
        converted, = downgrade_assets([self.source], self.base, "UE 5.3")
        self.assertIsNotNone(converted.output, converted.detail)
        compatible, = downgrade_assets([converted.output], self.base)
        self.assertIsNotNone(compatible.output, compatible.detail)
        self.assertEqual(compatible.output.read_bytes(), converted.output.read_bytes())
        self.assertEqual(compatible.status, "已复制")

    def test_marks_copies_with_unhandled_property_layouts(self):
        self.source.write_bytes(_package(property_flags=4)[0])
        result, = downgrade_assets([self.source], self.base, "UE 5.3")
        self.assertIsNotNone(result.output, result.detail)
        self.assertEqual(result.status, "属性未完全适配")

    def test_folder_keeps_nested_paths_and_copies_sidecars(self):
        folder = self.base / "Content"
        package = _package()[0]
        for subfolder in ("Maps", "Nested/Maps"):
            path = folder / subfolder / "Shared.umap"
            path.parent.mkdir(parents=True)
            path.write_bytes(package)
            path.with_suffix(".uexp").write_bytes(subfolder.encode("ascii"))
        (folder / "note.txt").write_text("ignore")
        output_parent = self.base / "Exports"
        output_parent.mkdir()

        results = downgrade_assets([folder, folder / "Maps/Shared.umap"], output_parent, "UE 5.3")

        self.assertEqual(len(results), 2)
        for result in results:
            self.assertIsNotNone(result.output, result.detail)
            self.assertEqual(result.output.relative_to(result.output_root), result.source.relative_to(self.base))
            self.assertEqual(result.source.read_bytes(), package)
            self.assertEqual(
                result.output.with_suffix(".uexp").read_bytes(), result.source.with_suffix(".uexp").read_bytes(),
            )
        self.assertFalse((results[0].output_root / "Content/note.txt").exists())

    def test_empty_folder_reports_failure_without_creating_output(self):
        source = self.base / "Empty"
        source.mkdir()
        result, = downgrade_assets([source], self.base)
        self.assertEqual(result.status, "失败")
        self.assertEqual(list(self.base.iterdir()), [source])

    def test_rejects_cooked_and_truncated_inputs_without_output(self):
        other = self.base / "Cooked.uasset"
        other.write_bytes(_package(package_flags=0x200)[0])
        self.source.write_bytes(_package()[0][:64])
        results = downgrade_assets([self.source, other], self.base)
        self.assertEqual([result.status for result in results], ["失败", "失败"])
        self.assertEqual(set(self.base.iterdir()), {self.source, other})


if __name__ == "__main__":
    unittest.main()
