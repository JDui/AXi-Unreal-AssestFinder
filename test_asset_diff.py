import json
import os
import tempfile
import unittest
from pathlib import Path

from asset_diff import compare_asset_folders, export_difference_package


class AssetDiffTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.old = self.root / "old" / "Content"
        self.new = self.root / "new" / "Content"
        self.old.mkdir(parents=True)
        self.new.mkdir(parents=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def write(root: Path, relative_path: str, data: bytes):
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def test_compare_added_modified_deleted_and_unchanged(self):
        self.write(self.old, "Maps/Same.umap", b"same")
        self.write(self.new, "Maps/Same.umap", b"same")
        self.write(self.old, "Props/Changed.uasset", b"old!")
        self.write(self.new, "Props/Changed.uasset", b"new!")
        self.write(self.old, "Props/Removed.uexp", b"removed")
        self.write(self.new, "Props/Added.ubulk", b"added")
        self.write(self.old, "Ignored.txt", b"old")
        self.write(self.new, "Ignored.txt", b"new")

        result = compare_asset_folders(self.old, self.new, workers=2)

        self.assertEqual(result.unchanged_count, 1)
        self.assertEqual(result.size_changed_count, 0)
        self.assertEqual(result.content_changed_count, 1)
        self.assertEqual(
            [(entry.status, entry.relative_path) for entry in result.entries],
            [
                ("added", "Props/Added.ubulk"),
                ("modified", "Props/Changed.uasset"),
                ("deleted", "Props/Removed.uexp"),
            ],
        )

    def test_export_selected_and_manifest_deleted_paths(self):
        self.write(self.old, "A.uasset", b"old")
        self.write(self.new, "A.uasset", b"new")
        self.write(self.new, "B.uexp", b"added")
        self.write(self.old, "C.umap", b"deleted")
        result = compare_asset_folders(self.old, self.new)
        package = self.root / "package"

        export_difference_package(
            result,
            package,
            selected_paths={"A.uasset", "C.umap"},
        )

        self.assertEqual((package / "Content" / "A.uasset").read_bytes(), b"new")
        self.assertFalse((package / "Content" / "B.uexp").exists())
        manifest = json.loads((package / "diff_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["selected_count"], 2)
        self.assertEqual(manifest["copied_count"], 1)
        self.assertEqual(manifest["deleted_paths"], ["Content/C.umap"])
        self.assertEqual(manifest["deleted_game_paths"], ["/Game/C"])
        manifest_by_path = {
            entry["relative_path"]: entry for entry in manifest["entries"]
        }
        self.assertEqual(manifest_by_path["A.uasset"]["content_path"], "Content/A.uasset")
        self.assertEqual(manifest_by_path["A.uasset"]["game_path"], "/Game/A")
        self.assertEqual(manifest_by_path["A.uasset"]["reason"], "content_changed")
        self.assertNotIn("old_root", manifest)
        self.assertNotIn("new_root", manifest)

    def test_project_roots_export_from_content_without_duplicate_content(self):
        old_project = self.root / "OldProject"
        new_project = self.root / "NewProject"
        self.write(old_project, "Content/Characters/Hero.uasset", b"old")
        self.write(new_project, "Content/Characters/Hero.uasset", b"new")
        self.write(new_project, "Plugins/Example/Content/Ignored.uasset", b"plugin")

        result = compare_asset_folders(old_project, new_project)
        package = self.root / "project-package"
        export_difference_package(result, package)

        self.assertEqual(
            [(entry.status, entry.relative_path) for entry in result.entries],
            [("modified", "Characters/Hero.uasset")],
        )
        self.assertEqual(
            (package / "Content" / "Characters" / "Hero.uasset").read_bytes(),
            b"new",
        )
        self.assertFalse((package / "Content" / "Content").exists())
        self.assertFalse((package / "Content" / "Plugins").exists())

    def test_content_subfolders_keep_path_from_game_root(self):
        old_content = self.root / "OldProject" / "Content"
        new_content = self.root / "NewProject" / "Content"
        self.write(old_content, "Characters/Hero.uasset", b"old")
        self.write(new_content, "Characters/Hero.uasset", b"new")

        result = compare_asset_folders(
            old_content / "Characters",
            new_content / "Characters",
        )

        self.assertEqual(result.entries[0].relative_path, "Characters/Hero.uasset")
        self.assertEqual(Path(result.old_root), (old_content / "Characters").resolve())
        self.assertEqual(Path(result.new_root), (new_content / "Characters").resolve())
        self.assertEqual(result.old_game_prefix, "Characters")
        self.assertEqual(result.new_game_prefix, "Characters")

    def test_recursively_finds_content_below_arbitrary_drop_root(self):
        old_drop = self.root / "OldDelivery"
        new_drop = self.root / "NewDelivery"
        old_nested = old_drop / "Build" / "Windows" / "DemoProject"
        new_nested = new_drop / "Archive" / "DemoProject"
        self.write(old_nested, "Content/Maps/Main.umap", b"old")
        self.write(new_nested, "Content/Maps/Main.umap", b"new")
        self.write(old_drop, "OutsideContent.uasset", b"ignored-old")
        self.write(new_drop, "OutsideContent.uasset", b"ignored-new")

        result = compare_asset_folders(old_drop, new_drop)

        self.assertEqual(
            [(entry.status, entry.relative_path) for entry in result.entries],
            [("modified", "Maps/Main.umap")],
        )
        self.assertEqual(Path(result.old_root).name, "Content")
        self.assertEqual(Path(result.new_root).name, "Content")

    def test_rejects_when_neither_side_has_content_mapping(self):
        old_drop = self.root / "NoContentOld"
        new_drop = self.root / "NoContentNew"
        self.write(old_drop, "A.uasset", b"old")
        self.write(new_drop, "A.uasset", b"new")

        with self.assertRaisesRegex(ValueError, "均未找到 Content"):
            compare_asset_folders(old_drop, new_drop)

    def test_detached_new_folder_inherits_old_game_prefix(self):
        old_content = self.root / "Project" / "Content"
        old_selected = old_content / "Characters" / "YanHe" / "YH_001_10TH"
        new_selected = self.root / "Downloaded" / "YH_001_10TH"
        self.write(old_selected, "Rig/Hero.uasset", b"old")
        self.write(new_selected, "Rig/Hero.uasset", b"new")

        result = compare_asset_folders(old_selected, new_selected)
        package = self.root / "detached-package"
        export_difference_package(result, package)

        expected_game_path = "Characters/YanHe/YH_001_10TH/Rig/Hero.uasset"
        self.assertEqual(result.entries[0].relative_path, expected_game_path)
        self.assertEqual(result.new_game_prefix, "Characters/YanHe/YH_001_10TH")
        self.assertEqual(
            (
                package
                / "Content"
                / "Characters"
                / "YanHe"
                / "YH_001_10TH"
                / "Rig"
                / "Hero.uasset"
            ).read_bytes(),
            b"new",
        )

    def test_reject_same_folder(self):
        with self.assertRaisesRegex(ValueError, "不能是同一文件夹"):
            compare_asset_folders(self.old, self.old)

    def test_ignores_file_modification_time_when_bytes_match(self):
        self.write(self.old, "Same.uasset", b"identical bytes")
        self.write(self.new, "Same.uasset", b"identical bytes")
        os.utime(self.old / "Same.uasset", (1_600_000_000, 1_600_000_000))
        os.utime(self.new / "Same.uasset", (1_700_000_000, 1_700_000_000))

        result = compare_asset_folders(self.old, self.new)

        self.assertEqual(result.entries, ())
        self.assertEqual(result.unchanged_count, 1)

    def test_reports_size_and_same_size_content_reasons_separately(self):
        self.write(self.old, "Size.uasset", b"old")
        self.write(self.new, "Size.uasset", b"new-longer")
        self.write(self.old, "Content.uasset", b"aaaa")
        self.write(self.new, "Content.uasset", b"bbbb")

        result = compare_asset_folders(self.old, self.new)
        reasons = {entry.relative_path: entry.reason for entry in result.entries}

        self.assertEqual(reasons["Size.uasset"], "size_changed")
        self.assertEqual(reasons["Content.uasset"], "content_changed")
        self.assertEqual(result.size_changed_count, 1)
        self.assertEqual(result.content_changed_count, 1)


if __name__ == "__main__":
    unittest.main()
