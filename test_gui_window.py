import tkinter as tk
import unittest

from asset_downgrade import DEFAULT_TARGET, TARGET_VERSIONS
from gui_dnd import UEAssetFinderGUI, _taskbar_extended_style, _window_drag_offset


class TaskbarWindowStyleTests(unittest.TestCase):
    def test_taskbar_style_adds_appwindow_and_removes_toolwindow(self):
        ws_ex_toolwindow = 0x00000080
        ws_ex_appwindow = 0x00040000
        unrelated_style = 0x00000100

        style = _taskbar_extended_style(ws_ex_toolwindow | unrelated_style)

        self.assertEqual(style & ws_ex_toolwindow, 0)
        self.assertEqual(style & ws_ex_appwindow, ws_ex_appwindow)
        self.assertEqual(style & unrelated_style, unrelated_style)

    def test_drag_offset_uses_screen_coordinates_not_child_widget_coordinates(self):
        offset = _window_drag_offset(
            pointer_x=540,
            pointer_y=330,
            window_x=400,
            window_y=250,
        )

        self.assertEqual(offset, (140, 80))
        self.assertEqual((541 - offset[0], 331 - offset[1]), (401, 251))


class DowngradeVersionPickerTests(unittest.TestCase):
    def test_popdown_loads_versions_with_the_configured_font(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")
        self.addCleanup(root.destroy)
        root.withdraw()
        app = UEAssetFinderGUI(root)

        combo = str(app.downgrade_combo)
        root.tk.call("ttk::combobox::ConfigureListbox", combo)
        popdown = root.tk.call("ttk::combobox::PopdownWindow", combo)
        self.assertEqual(root.tk.call(f"{popdown}.f.l", "get", 0, "end"), TARGET_VERSIONS)
        self.assertEqual(app.downgrade_target.get(), DEFAULT_TARGET)


if __name__ == "__main__":
    unittest.main()
