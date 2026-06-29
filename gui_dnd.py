"""
UE 资产分析工具 - 支持拖拽的 GUI 界面
"""

import math
import os
import random
import re
import shutil
import stat
import subprocess
import ctypes
import time
from ctypes import wintypes
import platform
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from tkinter import font as tkfont
from typing import Optional, List

from asset_finder import UEAssetFinder
from ue_parser import UEAssetParser, UEPathExtractor


def _patch_tkdnd_loader():
    try:
        import tkinterdnd2
        from tkinterdnd2 import TkinterDnD as _tkdnd

        def _detect_platform_rep():
            system = platform.system()
            if system == "Windows":
                machine = os.environ.get("PROCESSOR_ARCHITECTURE", platform.machine())
            else:
                machine = platform.machine()

            if system == "Darwin" and machine == "arm64":
                return "osx-arm64"
            if system == "Darwin" and machine == "x86_64":
                return "osx-x64"
            if system == "Linux" and machine == "aarch64":
                return "linux-arm64"
            if system == "Linux" and machine == "x86_64":
                return "linux-x64"
            if system == "Windows" and machine == "ARM64":
                return "win-arm64"
            if system == "Windows" and machine == "AMD64":
                return "win-x64"
            if system == "Windows" and machine == "x86":
                return "win-x86"
            return None

        def _custom_require(tkroot):
            rep = _detect_platform_rep()
            if not rep:
                raise RuntimeError("Plaform not supported.")

            candidates = []
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                candidates.append(Path(meipass) / "tkinterdnd2" / "tkdnd" / rep)
            candidates.append(Path(tkinterdnd2.__file__).parent / "tkdnd" / rep)

            module_path = None
            for candidate in candidates:
                if candidate.is_dir():
                    module_path = candidate
                    break

            if module_path:
                tkroot.tk.call("lappend", "auto_path", str(module_path))

            _tkdnd.TkdndVersion = tkroot.tk.call("package", "require", "tkdnd")
            return _tkdnd.TkdndVersion

        _tkdnd._require = _custom_require
    except Exception:
        pass


# 导入拖拽功能（可选）
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
    _patch_tkdnd_loader()
except ImportError:
    HAS_DND = False


class UEAssetFinderGUI:
    """UE 资产分析工具的 GUI 应用"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AXi UE Asset Finder")
        self.root.geometry("1000x720")
        self.root.minsize(900, 620)
        self.root.resizable(True, True)

        self._init_theme()
        self._apply_window_icon()

        # 初始化工具
        self.finder = UEAssetFinder()
        self.parser = UEAssetParser()
        self.relocate_ready = False
        self.relocate_files: List[str] = []
        self.relocate_rel_parts: List[str] = []
        self.relocate_folder_path = ""
        self.relocate_old_prefix = ""
        self._win_dnd_enabled = False
        self._old_wndproc = None
        self._new_wndproc = None
        self._call_wndproc = None
        self._drop_hover = False
        self._folder_drop_hover = False
        self._analysis_active = False
        self._active_tab = "analyze"
        self._tab_buttons = {}
        self._panel_frames = []

        # 设置样式并创建界面
        self.setup_styles()
        self.create_ui()
        self.center_window()
        self._start_drop_pulse()
        if not HAS_DND:
            self.root.after(120, self._late_enable_win_drop)

    def _init_theme(self):
        self.colors = {
            "bg": "#020403",
            "panel": "#07100b",
            "panel_high": "#0d1c13",
            "panel_line": "#19492f",
            "terminal": "#010503",
            "terminal_line": "#123523",
            "text": "#d7ffe5",
            "text_muted": "#73d58f",
            "accent": "#00ff66",
            "accent_soft": "#75ffa5",
            "accent_dim": "#00a84a",
            "cyan": "#00d9ff",
            "success": "#2cff8a",
            "warning": "#f4ff70",
            "error": "#ff4f6d",
            "selection_bg": "#9dffb8",
            "selection_fg": "#001f0b",
        }
        self.root.configure(bg=self.colors["bg"])
        self.root.option_add("*selectBackground", self.colors["selection_bg"])
        self.root.option_add("*selectForeground", self.colors["selection_fg"])
        self.root.option_add("*inactiveselectBackground", self.colors["accent_dim"])

        available = set(tkfont.families(self.root))

        def pick_font(names, size, weight="normal"):
            for name in names:
                if name in available:
                    return (name, size, weight)
            return ("Segoe UI", size, weight)

        self.fonts = {
            "title": pick_font(["Cascadia Code SemiBold", "Cascadia Code", "Consolas", "Microsoft YaHei"], 18, "bold"),
            "subtitle": pick_font(["Cascadia Code", "Consolas", "Microsoft YaHei"], 10),
            "body": pick_font(["Microsoft YaHei", "Cascadia Code", "Segoe UI"], 10),
            "body_bold": pick_font(["Microsoft YaHei UI", "Cascadia Code SemiBold", "Consolas"], 11, "bold"),
            "mono": pick_font(["Cascadia Code", "Consolas", "Courier New"], 10),
            "mono_bold": pick_font(["Cascadia Code SemiBold", "Cascadia Code", "Consolas"], 10, "bold"),
            "button": pick_font(["Cascadia Code SemiBold", "Cascadia Code", "Consolas", "Microsoft YaHei"], 10, "bold"),
            "status": pick_font(["Cascadia Code", "Consolas", "Microsoft YaHei"], 9),
        }

    def _apply_window_icon(self):
        try:
            icon_path = Path(__file__).parent / "assets" / "app_icon.png"
            if icon_path.exists():
                self.app_icon = tk.PhotoImage(file=str(icon_path))
            else:
                self.app_icon = self._build_app_icon(64)
            header_scale = max(1, math.ceil(max(self.app_icon.width(), self.app_icon.height()) / 48))
            self.header_icon = self.app_icon.subsample(header_scale, header_scale)
            self.root.iconphoto(True, self.app_icon)
        except Exception:
            self.app_icon = None
            self.header_icon = None

    def _build_app_icon(self, size: int) -> tk.PhotoImage:
        img = tk.PhotoImage(width=size, height=size)
        bg = self.colors["panel"]
        accent = self.colors["accent"]
        accent_dim = self.colors["accent_dim"]
        border = self.colors["panel_line"]

        for y in range(size):
            img.put("{" + " ".join([bg] * size) + "}", to=(0, y))

        for x in range(size):
            img.put(border, (x, 0))
            img.put(border, (x, size - 1))
        for y in range(size):
            img.put(border, (0, y))
            img.put(border, (size - 1, y))

        y_top = int(size * 0.22)
        y_bot = int(size * 0.78)
        x_left = int(size * 0.26)
        x_right = int(size * 0.74)
        arm = int(size * 0.12)
        thickness = 2

        for y in range(y_top, y_bot):
            for t in range(thickness):
                img.put(accent, (x_left + t, y))
                img.put(accent, (x_right - t, y))

        for x in range(x_left, x_left + arm):
            for t in range(thickness):
                img.put(accent, (x, y_top + t))
                img.put(accent, (x, y_bot - t))

        for x in range(x_right - arm, x_right):
            for t in range(thickness):
                img.put(accent, (x, y_top + t))
                img.put(accent, (x, y_bot - t))

        x_start = int(size * 0.44)
        x_end = int(size * 0.56)
        for i in range(y_top + 2, y_bot - 2):
            x = int(x_start + (x_end - x_start) * (i - (y_top + 2)) / (y_bot - y_top - 4))
            img.put(accent_dim, (x, i))
            img.put(accent_dim, (x + 1, i))
        return img

    def _hex_to_rgb(self, color: str):
        return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))

    def _blend_color(self, c1: str, c2: str, t: float) -> str:
        r1, g1, b1 = self._hex_to_rgb(c1)
        r2, g2, b2 = self._hex_to_rgb(c2)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background=self.colors["bg"])
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text"], font=self.fonts["body"])
        style.configure("Title.TLabel", background=self.colors["panel_high"], foreground=self.colors["accent"], font=self.fonts["title"])
        style.configure("Subtitle.TLabel", background=self.colors["panel_high"], foreground=self.colors["text_muted"], font=self.fonts["subtitle"])
        style.configure("TLabelFrame", background=self.colors["bg"], foreground=self.colors["accent"], borderwidth=1, relief=tk.FLAT)
        style.configure("TLabelFrame.Label", background=self.colors["bg"], foreground=self.colors["accent"], font=self.fonts["body_bold"])
        style.configure("TSeparator", background=self.colors["panel_line"])
        style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=self.colors["panel"],
            foreground=self.colors["text_muted"],
            padding=(16, 7),
            font=self.fonts["body_bold"],
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.colors["panel_high"]), ("active", self.colors["panel_high"])],
            foreground=[("selected", self.colors["accent"]), ("active", self.colors["accent_soft"])],
        )
        style.configure(
            "Treeview",
            background=self.colors["panel"],
            fieldbackground=self.colors["panel"],
            foreground=self.colors["text"],
            font=self.fonts["body"],
            rowheight=24,
            borderwidth=0,
        )
        style.map(
            "Treeview",
            background=[("selected", self.colors["selection_bg"])],
            foreground=[("selected", self.colors["selection_fg"])],
        )
        style.configure(
            "Treeview.Heading",
            background=self.colors["panel_high"],
            foreground=self.colors["accent_soft"],
            font=self.fonts["body_bold"],
            relief=tk.FLAT,
        )
        style.map("Treeview.Heading", background=[("active", self.colors["panel_high"])])
        style.configure("TRadiobutton", background=self.colors["panel"], foreground=self.colors["text"], font=self.fonts["body"])
        style.map("TRadiobutton", foreground=[("active", self.colors["accent_soft"])])
        style.configure(
            "TCombobox",
            fieldbackground=self.colors["terminal"],
            background=self.colors["panel_high"],
            foreground=self.colors["text"],
            arrowcolor=self.colors["accent"],
            bordercolor=self.colors["panel_line"],
            lightcolor=self.colors["panel_line"],
            darkcolor=self.colors["panel_line"],
            selectbackground=self.colors["selection_bg"],
            selectforeground=self.colors["selection_fg"],
            disabledbackground=self.colors["terminal"],
            disabledforeground=self.colors["text_muted"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.colors["terminal"]), ("disabled", self.colors["panel"])],
            foreground=[("readonly", self.colors["text"]), ("disabled", self.colors["text_muted"])],
            selectbackground=[("readonly", self.colors["selection_bg"])],
            selectforeground=[("readonly", self.colors["selection_fg"])],
        )

        style.configure(
            "Primary.TButton",
            font=self.fonts["button"],
            background=self.colors["accent"],
            foreground=self.colors["terminal"],
            padding=(16, 7),
            borderwidth=0,
            focusthickness=1,
            focuscolor=self.colors["accent_soft"],
        )
        style.map(
            "Primary.TButton",
            background=[("active", self.colors["accent_soft"]), ("pressed", self.colors["accent_dim"])],
            foreground=[("active", self.colors["terminal"])],
        )

        style.configure(
            "Ghost.TButton",
            font=self.fonts["button"],
            background=self.colors["panel_high"],
            foreground=self.colors["accent_soft"],
            padding=(14, 7),
            borderwidth=0,
            focusthickness=1,
            focuscolor=self.colors["panel_line"],
        )
        style.map(
            "Ghost.TButton",
            background=[("active", self.colors["terminal_line"]), ("pressed", self.colors["panel_line"])],
            foreground=[("active", self.colors["accent"])],
        )

        style.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor=self.colors["terminal"],
            background=self.colors["accent"],
            bordercolor=self.colors["panel_line"],
            lightcolor=self.colors["accent_soft"],
            darkcolor=self.colors["accent_dim"],
            thickness=6,
        )

    def create_ui(self):
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        header = tk.Frame(
            main_frame,
            bg=self.colors["panel_high"],
            highlightbackground=self.colors["panel_line"],
            highlightthickness=1,
        )
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8), ipady=6)
        header.columnconfigure(1, weight=1)

        if self.header_icon:
            icon_label = tk.Label(header, image=self.header_icon, bg=self.colors["panel_high"])
            icon_label.grid(row=0, column=0, rowspan=2, padx=(0, 12))

        ttk.Label(header, text="UE 资产分析工具 // AXi PATHFINDER", style="Title.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(header, text="MATRIX ROUTE SCANNER / 拖拽 UE 资源文件或文件夹进行分析与修复", style="Subtitle.TLabel").grid(row=1, column=1, sticky="w", pady=(2, 0))

        self.matrix_strip = tk.Canvas(
            main_frame,
            height=28,
            bg=self.colors["terminal"],
            highlightthickness=1,
            highlightbackground=self.colors["panel_line"],
            bd=0,
        )
        self.matrix_strip.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self._matrix_items = []

        self.tab_bar = tk.Frame(main_frame, bg=self.colors["bg"])
        self.tab_bar.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        self.tab_bar.columnconfigure(2, weight=1)

        self._create_tab_button("analyze", "ASSET ANALYZE", "资产分析", 0)
        self._create_tab_button("relocate", "PATH REPAIR", "目录修复", 1)

        self.content_frame = tk.Frame(
            main_frame,
            bg=self.colors["bg"],
            highlightbackground=self.colors["panel_line"],
            highlightthickness=1,
        )
        self.content_frame.grid(row=3, column=0, sticky="nsew")
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1)

        self.tab_analyze = tk.Frame(self.content_frame, bg=self.colors["bg"])
        self.tab_relocate = tk.Frame(self.content_frame, bg=self.colors["bg"])
        for tab in (self.tab_analyze, self.tab_relocate):
            tab.grid(row=0, column=0, sticky="nsew")

        self.analysis_flow = tk.Canvas(
            self.content_frame,
            bg=self.colors["terminal"],
            highlightthickness=1,
            highlightbackground=self.colors["accent_dim"],
            bd=0,
        )
        self._analysis_flow_items = []
        self._analysis_flow_step = 0

        self._build_analyze_tab(self.tab_analyze)
        self._build_relocate_tab(self.tab_relocate)
        self._select_tab("analyze")

        self.status_var = tk.StringVar(value="就绪")
        self.status_frame = tk.Frame(main_frame, bg=self.colors["terminal"], highlightbackground=self.colors["panel_line"], highlightthickness=1)
        self.status_frame.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        self.status_frame.columnconfigure(0, weight=1)

        self.status_label = tk.Label(
            self.status_frame,
            textvariable=self.status_var,
            bg=self.colors["terminal"],
            fg=self.colors["text_muted"],
            font=self.fonts["status"],
            anchor="w",
        )
        self.status_label.pack(fill=tk.X, padx=10, pady=5)

    def _create_tab_button(self, key: str, label: str, sublabel: str, column: int):
        canvas = tk.Canvas(
            self.tab_bar,
            width=180,
            height=46,
            bg=self.colors["bg"],
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        canvas.grid(row=0, column=column, sticky="w", padx=(0, 8))
        canvas.bind("<Button-1>", lambda _event, tab=key: self._select_tab(tab))
        canvas.bind("<Enter>", lambda _event, tab=key: self._draw_tab_button(tab, hover=True))
        canvas.bind("<Leave>", lambda _event, tab=key: self._draw_tab_button(tab, hover=False))
        self._tab_buttons[key] = {"canvas": canvas, "label": label, "sublabel": sublabel, "hover": False}
        self._draw_tab_button(key)

    def _draw_tab_button(self, key: str, hover: Optional[bool] = None):
        tab = self._tab_buttons[key]
        canvas: tk.Canvas = tab["canvas"]
        if hover is not None:
            tab["hover"] = hover

        selected = key == self._active_tab
        canvas.delete("all")

        width = int(canvas["width"])
        height = int(canvas["height"])
        y0 = 2 if selected else 9
        y1 = height - 2 if selected else height - 8
        fill = self.colors["panel_high"] if selected else self.colors["terminal"]
        outline = self.colors["accent_soft"] if selected else self.colors["panel_line"]
        if tab["hover"] and not selected:
            outline = self.colors["accent_dim"]
            fill = self.colors["panel"]

        points = [
            1, y0 + 8,
            10, y0,
            width - 12, y0,
            width - 1, y0 + 10,
            width - 1, y1,
            1, y1,
        ]
        canvas.create_polygon(points, fill=fill, outline=outline, width=2 if selected else 1)
        canvas.create_line(12, y1 - 4, width - 12, y1 - 4, fill=self.colors["accent"] if selected else self.colors["terminal_line"])
        if selected:
            canvas.create_rectangle(12, y0 + 6, width - 12, y0 + 9, outline="", fill=self.colors["accent_dim"])
            text_color = self.colors["accent_soft"]
            sub_color = self.colors["text"]
            font = self.fonts["mono_bold"]
        else:
            text_color = self.colors["text_muted"]
            sub_color = self.colors["accent_dim"]
            font = self.fonts["mono"]

        canvas.create_text(16, y0 + 13, text=tab["label"], anchor="w", fill=text_color, font=font)
        canvas.create_text(16, y0 + 29, text=tab["sublabel"], anchor="w", fill=sub_color, font=self.fonts["status"])

    def _select_tab(self, key: str):
        self._active_tab = key
        if key == "analyze":
            self.tab_analyze.tkraise()
        else:
            self.tab_relocate.tkraise()
        for tab_key in self._tab_buttons:
            self._draw_tab_button(tab_key)

    def _make_action_button(self, parent, text: str, command, primary: bool = False, width: int = 10):
        bg = self.colors["accent"] if primary else self.colors["panel_high"]
        fg = self.colors["selection_fg"] if primary else self.colors["accent_soft"]
        active_bg = self.colors["accent_soft"] if primary else self.colors["terminal_line"]
        active_fg = self.colors["selection_fg"] if primary else self.colors["accent"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=active_fg,
            disabledforeground=self.colors["text_muted"],
            font=self.fonts["button"],
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=5,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=self.colors["accent_dim"] if primary else self.colors["panel_line"],
            highlightcolor=self.colors["accent_soft"],
        )

    def _build_analyze_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(3, weight=1)

        drop_container = tk.Frame(parent, bg=self.colors["bg"])
        drop_container.grid(row=0, column=0, sticky="ew", pady=(2, 8))
        drop_container.columnconfigure(0, weight=1)

        self.drop_frame = tk.Frame(
            drop_container,
            bg=self.colors["terminal"],
            highlightbackground=self.colors["panel_line"],
            highlightthickness=1,
        )
        self.drop_frame.grid(row=0, column=0, sticky="ew", ipady=10)
        self.drop_frame.columnconfigure(0, weight=1)

        self.drop_title = tk.Label(
            self.drop_frame,
            text="将 UE 资产文件拖到此处",
            bg=self.colors["terminal"],
            fg=self.colors["accent_soft"],
            font=self.fonts["body_bold"],
        )
        self.drop_title.pack(anchor="center", pady=(6, 2))

        self.drop_subtitle = tk.Label(
            self.drop_frame,
            text="支持 .uasset / .umap / .uexp / .ubulk",
            bg=self.colors["terminal"],
            fg=self.colors["text_muted"],
            font=self.fonts["body"],
        )
        self.drop_subtitle.pack(anchor="center", pady=(0, 6))

        self.drop_frame.bind("<Enter>", self._on_drop_enter)
        self.drop_frame.bind("<Leave>", self._on_drop_leave)
        self.drop_title.bind("<Enter>", self._on_drop_enter)
        self.drop_title.bind("<Leave>", self._on_drop_leave)
        self.drop_subtitle.bind("<Enter>", self._on_drop_enter)
        self.drop_subtitle.bind("<Leave>", self._on_drop_leave)

        if HAS_DND:
            try:
                self.drop_frame.drop_target_register(DND_FILES)
                self.drop_frame.dnd_bind("<<Drop>>", self.on_drop_asset)
                self.drop_title.drop_target_register(DND_FILES)
                self.drop_title.dnd_bind("<<Drop>>", self.on_drop_asset)
                self.drop_subtitle.drop_target_register(DND_FILES)
                self.drop_subtitle.dnd_bind("<<Drop>>", self.on_drop_asset)
            except Exception:
                pass
        else:
            self.drop_subtitle.configure(text="拖拽需要安装 tkinterdnd2，当前可使用下方浏览按钮")

        file_section, file_frame = self._create_section(parent, "文件选择", icon_kind="file")
        file_section.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        file_section.columnconfigure(0, weight=1)

        file_inner = tk.Frame(file_frame, bg=self.colors["panel"])
        file_inner.pack(fill=tk.X, padx=10, pady=8)
        file_inner.columnconfigure(1, weight=1)

        self.asset_file_var = tk.StringVar()
        entry = tk.Entry(
            file_inner,
            textvariable=self.asset_file_var,
            font=self.fonts["mono"],
            bg=self.colors["terminal"],
            fg=self.colors["text"],
            insertbackground=self.colors["accent"],
            relief=tk.FLAT,
            bd=1,
            highlightthickness=1,
            highlightbackground=self.colors["terminal_line"],
            highlightcolor=self.colors["accent"],
            selectbackground=self.colors["selection_bg"],
            selectforeground=self.colors["selection_fg"],
            disabledbackground=self.colors["terminal"],
            disabledforeground=self.colors["text_muted"],
        )
        entry.grid(row=0, column=1, sticky="ew", padx=(8, 8), pady=2)

        self._make_action_button(file_inner, "浏览文件", self.browse_asset, width=10).grid(row=0, column=2, padx=(0, 6))
        self._make_action_button(file_inner, "开始分析", self.analyze_asset, primary=True, width=10).grid(row=0, column=3)

        self.progress = ttk.Progressbar(parent, mode="indeterminate", style="Accent.Horizontal.TProgressbar")
        self.progress.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        self.progress.grid_remove()

        result_section, result_frame = self._create_section(parent, "分析结果", icon_kind="result")
        result_section.grid(row=3, column=0, sticky="nsew")
        result_section.columnconfigure(0, weight=1)
        result_section.rowconfigure(1, weight=1)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            height=20,
            font=self.fonts["mono"],
            wrap=tk.WORD,
            bg=self.colors["terminal"],
            fg=self.colors["text"],
            insertbackground=self.colors["accent"],
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["terminal_line"],
            highlightcolor=self.colors["accent"],
            selectbackground=self.colors["selection_bg"],
            selectforeground=self.colors["selection_fg"],
            padx=10,
            pady=8,
        )
        self.result_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self._setup_text_tags()
        self.result_text.configure(state=tk.DISABLED)

    def _build_relocate_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)

        drop_container = tk.Frame(parent, bg=self.colors["bg"])
        drop_container.grid(row=0, column=0, sticky="ew", pady=(2, 8))
        drop_container.columnconfigure(0, weight=1)

        self.folder_drop_frame = tk.Frame(
            drop_container,
            bg=self.colors["terminal"],
            highlightbackground=self.colors["panel_line"],
            highlightthickness=1,
        )
        self.folder_drop_frame.grid(row=0, column=0, sticky="ew", ipady=10)
        self.folder_drop_frame.columnconfigure(0, weight=1)

        self.folder_drop_title = tk.Label(
            self.folder_drop_frame,
            text="将 UE 资产文件夹拖到此处",
            bg=self.colors["terminal"],
            fg=self.colors["accent_soft"],
            font=self.fonts["body_bold"],
        )
        self.folder_drop_title.pack(anchor="center", pady=(6, 2))

        self.folder_drop_subtitle = tk.Label(
            self.folder_drop_frame,
            text="用于校验相对路径并一键变更目录名",
            bg=self.colors["terminal"],
            fg=self.colors["text_muted"],
            font=self.fonts["body"],
        )
        self.folder_drop_subtitle.pack(anchor="center", pady=(0, 6))

        self.folder_drop_frame.bind("<Enter>", self._on_folder_drop_enter)
        self.folder_drop_frame.bind("<Leave>", self._on_folder_drop_leave)
        self.folder_drop_title.bind("<Enter>", self._on_folder_drop_enter)
        self.folder_drop_title.bind("<Leave>", self._on_folder_drop_leave)
        self.folder_drop_subtitle.bind("<Enter>", self._on_folder_drop_enter)
        self.folder_drop_subtitle.bind("<Leave>", self._on_folder_drop_leave)

        if HAS_DND:
            try:
                self.folder_drop_frame.drop_target_register(DND_FILES)
                self.folder_drop_frame.dnd_bind("<<Drop>>", self.on_drop_folder)
                self.folder_drop_title.drop_target_register(DND_FILES)
                self.folder_drop_title.dnd_bind("<<Drop>>", self.on_drop_folder)
                self.folder_drop_subtitle.drop_target_register(DND_FILES)
                self.folder_drop_subtitle.dnd_bind("<<Drop>>", self.on_drop_folder)
            except Exception:
                pass
        else:
            self.folder_drop_subtitle.configure(text="拖拽需要安装 tkinterdnd2，当前可使用下方浏览按钮")

        folder_section, folder_frame = self._create_section(parent, "文件夹选择", icon_kind="folder")
        folder_section.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        folder_section.columnconfigure(0, weight=1)

        folder_inner = tk.Frame(folder_frame, bg=self.colors["panel"])
        folder_inner.pack(fill=tk.X, padx=10, pady=8)
        folder_inner.columnconfigure(1, weight=1)

        self.folder_path_var = tk.StringVar()
        entry = tk.Entry(
            folder_inner,
            textvariable=self.folder_path_var,
            font=self.fonts["mono"],
            bg=self.colors["terminal"],
            fg=self.colors["text"],
            insertbackground=self.colors["accent"],
            relief=tk.FLAT,
            bd=1,
            highlightthickness=1,
            highlightbackground=self.colors["terminal_line"],
            highlightcolor=self.colors["accent"],
            selectbackground=self.colors["selection_bg"],
            selectforeground=self.colors["selection_fg"],
            disabledbackground=self.colors["terminal"],
            disabledforeground=self.colors["text_muted"],
        )
        entry.grid(row=0, column=1, sticky="ew", padx=(8, 8), pady=2)

        self._make_action_button(folder_inner, "浏览文件夹", self.browse_folder, width=10).grid(row=0, column=2, padx=(0, 6))
        self._make_action_button(folder_inner, "检测路径", self.validate_folder, primary=True, width=10).grid(row=0, column=3)

        self.folder_hint_var = tk.StringVar(value="等待检测")
        self.folder_hint_label = tk.Label(
            folder_inner,
            textvariable=self.folder_hint_var,
            bg=self.colors["panel"],
            fg=self.colors["text_muted"],
            font=self.fonts["status"],
            anchor="w",
        )
        self.folder_hint_label.grid(row=1, column=1, columnspan=3, sticky="w", padx=(8, 0), pady=(4, 0))

        result_section, result_frame = self._create_section(parent, "检测结果", icon_kind="result")
        result_section.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
        result_section.columnconfigure(0, weight=1)
        result_section.rowconfigure(1, weight=1)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        self.relocate_tree = ttk.Treeview(
            result_frame,
            columns=("file", "ue_path", "issue"),
            show="headings",
            selectmode="browse",
        )
        self.relocate_tree.heading("file", text="文件")
        self.relocate_tree.heading("ue_path", text="UE 路径")
        self.relocate_tree.heading("issue", text="问题")
        self.relocate_tree.column("file", width=420, anchor="w")
        self.relocate_tree.column("ue_path", width=260, anchor="w")
        self.relocate_tree.column("issue", width=180, anchor="w")
        self.relocate_tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        self.relocate_tree.tag_configure("error", foreground=self.colors["error"])
        self.relocate_tree.tag_configure("ok", foreground=self.colors["success"])

        tree_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=self.relocate_tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns", pady=10, padx=(0, 10))
        self.relocate_tree.configure(yscrollcommand=tree_scroll.set)
        self.relocate_tree.bind("<Double-1>", self._on_relocate_item_double_click)

        rename_section, rename_frame = self._create_section(parent, "目录变更", icon_kind="edit")
        rename_section.grid(row=3, column=0, sticky="ew", pady=(0, 6))
        rename_section.columnconfigure(0, weight=1)

        rename_inner = tk.Frame(rename_frame, bg=self.colors["panel"])
        rename_inner.pack(fill=tk.X, padx=10, pady=8)
        rename_inner.columnconfigure(1, weight=1)

        tk.Label(
            rename_inner,
            text="新目录名",
            bg=self.colors["panel"],
            fg=self.colors["text_muted"],
            font=self.fonts["body"],
        ).grid(row=0, column=0, sticky="w")

        self.relocate_name_var = tk.StringVar()
        self.relocate_name_entry = tk.Entry(
            rename_inner,
            textvariable=self.relocate_name_var,
            font=self.fonts["mono"],
            bg=self.colors["terminal"],
            fg=self.colors["text"],
            insertbackground=self.colors["accent"],
            relief=tk.FLAT,
            bd=1,
            highlightthickness=1,
            highlightbackground=self.colors["terminal_line"],
            highlightcolor=self.colors["accent"],
            selectbackground=self.colors["selection_bg"],
            selectforeground=self.colors["selection_fg"],
        )
        self.relocate_name_entry.grid(row=0, column=1, sticky="ew", padx=(8, 8), pady=2)

        self.relocate_execute_btn = self._make_action_button(
            rename_inner,
            "执行变更",
            self.execute_relocate,
            primary=True,
            width=10,
        )
        self.relocate_execute_btn.grid(row=0, column=2, padx=(0, 6))

        self.relocate_mode_var = tk.StringVar(value="副本粘贴模式")
        self.relocate_mode_combo = ttk.Combobox(
            rename_inner,
            textvariable=self.relocate_mode_var,
            values=["副本粘贴模式", "原位更改模式"],
            state="readonly",
            width=16,
            takefocus=True,
        )
        self.relocate_mode_combo.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0))
        self.relocate_mode_combo.bind("<Button-1>", lambda _event: self.relocate_mode_combo.focus_set())

        self.relocate_tip_label = tk.Label(
            rename_inner,
            text="提示：为保证安全，当前仅支持新旧目录名长度一致。",
            bg=self.colors["panel"],
            fg=self.colors["text_muted"],
            font=self.fonts["status"],
        )
        self.relocate_tip_label.grid(row=2, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=(4, 0))

        self._toggle_relocate_controls(False)

    def _create_section(self, parent, title: str, icon_kind: str = "file"):
        section = tk.Frame(parent, bg=self.colors["bg"])
        header = self._make_section_label(section, title, icon_kind=icon_kind)
        header.pack(anchor="w", padx=2, pady=(0, 6))

        card = tk.Frame(
            section,
            bg=self.colors["panel"],
            highlightbackground=self.colors["panel_line"],
            highlightthickness=2,
        )
        self._panel_frames.append(card)
        card.pack(fill=tk.BOTH, expand=True)
        return section, card

    def _setup_text_tags(self):
        self.result_text.tag_configure("header", foreground=self.colors["accent_dim"], font=self.fonts["mono_bold"])
        self.result_text.tag_configure("divider", foreground=self.colors["panel_line"])
        self.result_text.tag_configure("section", foreground=self.colors["accent"], font=self.fonts["mono_bold"])
        self.result_text.tag_configure("label", foreground=self.colors["text_muted"])
        self.result_text.tag_configure("value", foreground=self.colors["text"])
        self.result_text.tag_configure("path", foreground=self.colors["accent_dim"])
        self.result_text.tag_configure("bullet", foreground=self.colors["accent_dim"])
        self.result_text.tag_configure("error", foreground=self.colors["error"], font=self.fonts["mono_bold"])
        self.result_text.tag_configure("success", foreground=self.colors["success"], font=self.fonts["mono_bold"])

    def _append_text(self, text: str, tag: Optional[str] = None):
        self.result_text.configure(state=tk.NORMAL)
        if tag:
            self.result_text.insert(tk.END, text, tag)
        else:
            self.result_text.insert(tk.END, text)
        self.result_text.configure(state=tk.DISABLED)

    def _map_ue_path(self, path: str) -> str:
        if not path:
            return path
        if path == "/Game":
            return "/Content"
        if path.startswith("/Game/"):
            return "/Content/" + path[len("/Game/"):]
        return path

    def _format_reference(self, ref: str) -> tuple[str, str]:
        mapped = self._map_ue_path(ref)
        tail = mapped.rsplit("/", 1)[-1]
        name = tail.split(".")[-1] if "." in tail else tail
        if not name:
            name = mapped
        return name, mapped

    def _make_section_label(self, parent, text: str, icon_kind: str = "file") -> tk.Frame:
        label_frame = tk.Frame(parent, bg=self.colors["bg"])
        icon = tk.Canvas(label_frame, width=14, height=14, bg=self.colors["bg"], highlightthickness=0)
        if icon_kind == "result":
            icon.create_oval(1, 1, 13, 13, outline=self.colors["accent"], width=2)
            icon.create_line(4, 7, 10, 7, fill=self.colors["accent"], width=2)
        elif icon_kind == "folder":
            icon.create_rectangle(1, 5, 13, 12, outline=self.colors["accent"], width=2)
            icon.create_line(3, 4, 7, 4, fill=self.colors["accent"], width=2)
            icon.create_line(3, 3, 3, 5, fill=self.colors["accent"], width=2)
            icon.create_line(7, 3, 7, 5, fill=self.colors["accent"], width=2)
        elif icon_kind == "edit":
            icon.create_line(3, 11, 11, 3, fill=self.colors["accent"], width=2)
            icon.create_line(2, 12, 4, 10, fill=self.colors["accent"], width=2)
        else:
            icon.create_rectangle(2, 2, 12, 12, outline=self.colors["accent"], width=2)
            icon.create_line(4, 5, 10, 5, fill=self.colors["accent"], width=2)
            icon.create_line(4, 8, 10, 8, fill=self.colors["accent"], width=2)
        icon.pack(side="left", padx=(0, 6))

        label = tk.Label(
            label_frame,
            text=f"[ {text} ]",
            bg=self.colors["bg"],
            fg=self.colors["accent"],
            font=self.fonts["body_bold"],
        )
        label.pack(side="left")
        return label_frame

    def _on_drop_enter(self, _event):
        self._drop_hover = True
        self.drop_frame.configure(bg=self.colors["panel_high"], highlightbackground=self.colors["accent_soft"])
        self.drop_title.configure(bg=self.colors["panel_high"])
        self.drop_subtitle.configure(bg=self.colors["panel_high"])

    def _on_drop_leave(self, _event):
        self._drop_hover = False
        self.drop_frame.configure(bg=self.colors["terminal"], highlightbackground=self.colors["panel_line"])
        self.drop_title.configure(bg=self.colors["terminal"])
        self.drop_subtitle.configure(bg=self.colors["terminal"])

    def _on_folder_drop_enter(self, _event):
        self._folder_drop_hover = True
        self.folder_drop_frame.configure(bg=self.colors["panel_high"], highlightbackground=self.colors["accent_soft"])
        self.folder_drop_title.configure(bg=self.colors["panel_high"])
        self.folder_drop_subtitle.configure(bg=self.colors["panel_high"])

    def _on_folder_drop_leave(self, _event):
        self._folder_drop_hover = False
        self.folder_drop_frame.configure(bg=self.colors["terminal"], highlightbackground=self.colors["panel_line"])
        self.folder_drop_title.configure(bg=self.colors["terminal"])
        self.folder_drop_subtitle.configure(bg=self.colors["terminal"])

    def _start_drop_pulse(self):
        self._pulse_step = 0.0
        self._matrix_step = 0
        self._animate_drop_pulse()
        self._animate_matrix_strip()

    def _animate_drop_pulse(self):
        t = (math.sin(self._pulse_step) + 1.0) / 2.0
        border = self._blend_color(self.colors["panel_line"], self.colors["accent_soft"], t * 0.8)
        title_color = self._blend_color(self.colors["accent_dim"], self.colors["accent_soft"], t)
        bg = self._blend_color(self.colors["terminal"], self.colors["panel_high"], t * 0.35)
        for frame, title, subtitle, hovering in (
            (getattr(self, "drop_frame", None), getattr(self, "drop_title", None), getattr(self, "drop_subtitle", None), self._drop_hover),
            (getattr(self, "folder_drop_frame", None), getattr(self, "folder_drop_title", None), getattr(self, "folder_drop_subtitle", None), self._folder_drop_hover),
        ):
            frame_bg = self.colors["panel_high"] if hovering else bg
            frame_border = self.colors["accent_soft"] if hovering else border
            if frame:
                frame.configure(bg=frame_bg, highlightbackground=frame_border)
            if title:
                title.configure(bg=frame_bg, fg=self.colors["accent_soft"] if hovering else title_color)
            if subtitle:
                subtitle.configure(bg=frame_bg)
        if getattr(self, "status_frame", None):
            self.status_frame.configure(highlightbackground=border)
        for panel in getattr(self, "_panel_frames", []):
            panel.configure(highlightbackground=self._blend_color(self.colors["panel_line"], self.colors["accent_dim"], t * 0.5))
        self._pulse_step += 0.08
        self.root.after(50, self._animate_drop_pulse)

    def _animate_matrix_strip(self):
        strip = getattr(self, "matrix_strip", None)
        if not strip:
            return

        width = max(strip.winfo_width(), 1)
        height = max(strip.winfo_height(), 28)
        columns = max(width // 18, 24)
        glyphs = "01<>[]{}#$:/\\"

        if len(self._matrix_items) != columns:
            strip.delete("all")
            self._matrix_items = []
            for i in range(columns):
                x = 8 + i * 18
                y = 7 + (i % 3) * 7
                item = strip.create_text(
                    x,
                    y,
                    text=random.choice(glyphs),
                    anchor="nw",
                    fill=self.colors["accent_dim"],
                    font=self.fonts["mono"],
                )
                self._matrix_items.append(item)
            strip.create_line(0, height - 2, width, height - 2, fill=self.colors["accent_dim"])

        for i, item in enumerate(self._matrix_items):
            if (i + self._matrix_step) % 3 == 0:
                strip.itemconfigure(item, text=random.choice(glyphs), fill=self.colors["accent_soft"])
            else:
                strip.itemconfigure(item, text=random.choice(glyphs), fill=self.colors["accent_dim"])

        scan_x = (self._matrix_step * 14) % max(width, 1)
        strip.delete("scan")
        strip.create_rectangle(
            scan_x,
            1,
            min(scan_x + 70, width),
            height - 3,
            outline="",
            fill=self.colors["terminal_line"],
            tags="scan",
        )
        strip.tag_lower("scan")
        self._matrix_step += 1
        self.root.after(90, self._animate_matrix_strip)

    def _start_analysis_flow(self):
        self._analysis_active = True
        self._analysis_flow_step = 0
        self.analysis_flow.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.analysis_flow.tk.call("raise", self.analysis_flow._w)
        self._animate_analysis_flow()

    def _stop_analysis_flow(self):
        self._analysis_active = False
        self.analysis_flow.delete("all")
        self.analysis_flow.place_forget()

    def _animate_analysis_flow(self):
        if not self._analysis_active:
            return

        canvas = self.analysis_flow
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 1)
        glyphs = "01:/\\[]{}<>#$UEASSETFINDER"
        col_width = 18
        columns = max(width // col_width, 20)

        canvas.delete("all")
        canvas.create_rectangle(0, 0, width, height, outline="", fill=self.colors["terminal"])
        scan_y = (self._analysis_flow_step * 18) % max(height, 1)
        canvas.create_rectangle(0, scan_y, width, min(scan_y + 80, height), outline="", fill=self.colors["terminal_line"])
        canvas.create_text(
            22,
            18,
            text="ANALYZING PACKAGE STREAM...",
            anchor="w",
            fill=self.colors["accent_soft"],
            font=self.fonts["mono_bold"],
        )
        for col in range(columns):
            x = col * col_width + 8
            offset = (self._analysis_flow_step * (col % 5 + 1) * 7 + col * 13) % max(height, 1)
            for row in range(-2, max(height // 16, 1) + 2):
                y = row * 16 + offset - 80
                if y < 38 or y > height:
                    continue
                color = self.colors["accent_soft"] if row % 5 == 0 else self.colors["accent_dim"]
                canvas.create_text(
                    x,
                    y,
                    text=random.choice(glyphs),
                    anchor="nw",
                    fill=color,
                    font=self.fonts["mono"],
                )
        self._analysis_flow_step += 1
        self.root.after(45, self._animate_analysis_flow)

    def _hold_analysis_animation(self, started_at: float, min_seconds: float = 0.5):
        while time.perf_counter() - started_at < min_seconds:
            self.root.update()
            time.sleep(0.02)

    def _set_status(self, text: str, kind: str = "normal"):
        self.status_var.set(text)
        color = self.colors["text_muted"]
        if kind == "success":
            color = self.colors["success"]
        elif kind == "warning":
            color = self.colors["warning"]
        elif kind == "error":
            color = self.colors["error"]
        self.status_label.configure(fg=color)

    def _set_busy(self, busy: bool, message: Optional[str] = None):
        if busy:
            if message:
                self._set_status(message)
            self.progress.grid()
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.grid_remove()

    def _parse_drop_files(self, data: str) -> List[str]:
        if not data:
            return []
        if data.startswith("{") and data.endswith("}"):
            if "} {" in data:
                files = [chunk.strip("{}") for chunk in data.split("} {")]
            else:
                files = [data.strip("{}")]
        else:
            files = [data]
        return [f.strip().strip('"') for f in files if f.strip()]

    def _late_enable_win_drop(self):
        if self._win_dnd_enabled:
            return
        enabled = self._enable_win_drop()
        self._win_dnd_enabled = enabled
        if enabled:
            self.drop_subtitle.configure(text="支持拖拽文件/文件夹到窗口任意区域")
            self.folder_drop_subtitle.configure(text="支持拖拽文件夹到窗口任意区域")

    def _enable_win_drop(self) -> bool:
        if os.name != "nt":
            return False
        try:
            hwnd = self.root.winfo_id()
            ctypes.windll.shell32.DragAcceptFiles(hwnd, True)

            GWL_WNDPROC = -4
            WM_DROPFILES = 0x233
            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32

            if hasattr(wintypes, "LONG_PTR"):
                long_ptr = wintypes.LONG_PTR
            else:
                long_ptr = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long

            WNDPROC_TYPE = ctypes.WINFUNCTYPE(wintypes.LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
            user32.SetWindowLongPtrW.restype = long_ptr
            user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, long_ptr]
            user32.CallWindowProcW.restype = wintypes.LRESULT
            user32.CallWindowProcW.argtypes = [long_ptr, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

            def wndproc(hwnd_, msg, wparam, lparam):
                if msg == WM_DROPFILES:
                    files = self._query_drop_files(wparam)
                    if files:
                        self._handle_drop_files(files)
                    shell32.DragFinish(wparam)
                    return 0
                return user32.CallWindowProcW(self._old_wndproc, hwnd_, msg, wparam, lparam)

            self._new_wndproc = WNDPROC_TYPE(wndproc)
            self._old_wndproc = user32.SetWindowLongPtrW(hwnd, GWL_WNDPROC, self._new_wndproc)
            if not self._old_wndproc:
                return False
            return True
        except Exception:
            return False

    def _query_drop_files(self, hdrop) -> List[str]:
        files: List[str] = []
        try:
            DragQueryFileW = ctypes.windll.shell32.DragQueryFileW
            DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
            DragQueryFileW.restype = wintypes.UINT
            count = DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
            for i in range(count):
                length = DragQueryFileW(hdrop, i, None, 0) + 1
                buffer = ctypes.create_unicode_buffer(length)
                DragQueryFileW(hdrop, i, buffer, length)
                files.append(buffer.value)
        except Exception:
            return []
        return files

    def _handle_drop_files(self, files: List[str]):
        if not files:
            return
        path = files[0]
        if os.path.isdir(path):
            self.folder_path_var.set(path)
            self._select_tab("relocate")
            self.validate_folder()
            return
        if os.path.isfile(path):
            ext = Path(path).suffix.lower()
            if ext in {".uasset", ".umap", ".uexp", ".ubulk"}:
                self.asset_file_var.set(path)
                self._select_tab("analyze")
                self.analyze_asset()
            else:
                self.asset_file_var.set(path)
                self._select_tab("analyze")
                self.analyze_asset()

    def _toggle_relocate_controls(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.relocate_name_entry.configure(state=state)
        self.relocate_mode_combo.configure(state="readonly")
        self.relocate_execute_btn.configure(state="normal" if enabled else "disabled")

    def _set_folder_hint(self, text: str, kind: str = "normal"):
        self.folder_hint_var.set(text)
        color = self.colors["text_muted"]
        if kind == "success":
            color = self.colors["success"]
        elif kind == "warning":
            color = self.colors["warning"]
        elif kind == "error":
            color = self.colors["error"]
        self.folder_hint_label.configure(fg=color)

    def browse_asset(self):
        """浏览选择资产文件"""
        file_path = filedialog.askopenfilename(
            title="选择 UE 资产文件",
            filetypes=[
                ("UE 资产文件", "*.uasset *.umap *.uexp *.ubulk"),
                ("所有文件", "*.*"),
            ],
        )
        if file_path:
            self.asset_file_var.set(file_path)
            self.analyze_asset()

    def on_drop_asset(self, event):
        """处理拖拽资产文件"""
        try:
            files = self._parse_drop_files(event.data)
            if not files:
                return
            file_path = files[0].strip()

            if os.path.isfile(file_path):
                self.asset_file_var.set(file_path)
                self.analyze_asset()
            else:
                self.result_text.configure(state=tk.NORMAL)
                self.result_text.delete("1.0", tk.END)
                self.result_text.insert("1.0", f"✗ 文件不存在: {file_path}")
                self.result_text.configure(state=tk.DISABLED)
                self._set_status("文件不存在", "warning")
        except Exception as exc:
            self.result_text.configure(state=tk.NORMAL)
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert("1.0", f"✗ 拖拽处理出错:\n{exc}")
            self.result_text.configure(state=tk.DISABLED)
            self._set_status("拖拽失败", "error")

    def browse_folder(self):
        """浏览选择资产文件夹"""
        folder_path = filedialog.askdirectory(title="选择 UE 资产文件夹")
        if folder_path:
            self.folder_path_var.set(folder_path)
            self.validate_folder()

    def on_drop_folder(self, event):
        """处理拖拽资产文件夹"""
        try:
            files = self._parse_drop_files(event.data)
            if not files:
                return
            path = files[0].strip()
            folder_path = path
            if os.path.isfile(path):
                folder_path = os.path.dirname(path)

            if os.path.isdir(folder_path):
                self.folder_path_var.set(folder_path)
                self.validate_folder()
            else:
                self._set_folder_hint("文件夹不存在", "warning")
        except Exception as exc:
            self._set_folder_hint("拖拽失败", "error")
            messagebox.showerror("错误", f"拖拽处理出错:\n{exc}")

    def _collect_asset_files(self, folder_path: str, include_sidecars: bool = False) -> List[str]:
        exts = {".uasset", ".umap"}
        if include_sidecars:
            exts.update({".uexp", ".ubulk"})
        assets: List[str] = []
        for root, _, files in os.walk(folder_path):
            for name in files:
                if Path(name).suffix.lower() in exts:
                    assets.append(os.path.join(root, name))
        return assets

    def _scan_game_paths(self, file_path: str, expected_prefix: str) -> Optional[str]:
        try:
            with open(file_path, "rb") as f:
                data = f.read(512 * 1024)
        except Exception:
            return None

        best = None
        for match in re.finditer(b"/Game", data):
            start = match.start()
            end = start
            while end < len(data) and data[end] != 0:
                end += 1
            if end - start < 6:
                continue
            try:
                text = data[start:end].decode("utf-8", errors="ignore")
            except Exception:
                continue
            if text.startswith(expected_prefix):
                return text
            if not best and text.startswith("/Game/"):
                best = text
        return best

    def _get_expected_prefix(self, folder_path: str) -> tuple[List[str], str]:
        parts = Path(folder_path).parts
        rel_parts: Optional[List[str]] = None
        for idx, part in enumerate(parts):
            if part.lower() == "content":
                rel_parts = list(parts[idx + 1:])
        if not rel_parts:
            rel_parts = [Path(folder_path).name]
        expected = "/Game/" + "/".join(rel_parts).replace("\\", "/")
        if not expected.endswith("/"):
            expected += "/"
        return rel_parts, expected

    def validate_folder(self):
        """校验文件夹下资产的相对路径"""
        folder_path = self.folder_path_var.get().strip()
        if not folder_path:
            messagebox.showwarning("提示", "请先选择文件夹")
            return
        if not os.path.isdir(folder_path):
            messagebox.showwarning("提示", "文件夹不存在: " + folder_path)
            return

        self.relocate_tree.delete(*self.relocate_tree.get_children())
        self.relocate_ready = False
        self._toggle_relocate_controls(False)
        self._set_folder_hint("正在检测...", "normal")
        self._set_status("正在检测目录...", "normal")

        asset_files = self._collect_asset_files(folder_path)
        if not asset_files:
            self._set_folder_hint("未发现 UE 资产文件", "warning")
            self._set_status("未发现资产", "warning")
            return

        rel_parts, expected_prefix = self._get_expected_prefix(folder_path)
        self.relocate_rel_parts = rel_parts
        self.relocate_folder_path = folder_path
        self.relocate_old_prefix = expected_prefix
        self.relocate_files = asset_files

        errors = 0
        for file_path in asset_files:
            ue_path = UEPathExtractor.extract_asset_path(file_path)
            fallback_path = None
            if not ue_path or not ue_path.startswith(expected_prefix):
                fallback_path = self._scan_game_paths(file_path, expected_prefix)
                if fallback_path and fallback_path.startswith(expected_prefix):
                    continue
                if not ue_path:
                    issue = "未识别 UE 路径"
                elif not ue_path.startswith("/Game/"):
                    issue = "非 /Game 路径"
                else:
                    issue = "路径不在所选目录"
            else:
                continue

            errors += 1
            display_base = ue_path or fallback_path
            display_ue = self._map_ue_path(display_base) if display_base else "(未找到)"
            rel_display = os.path.relpath(file_path, folder_path)
            self.relocate_tree.insert(
                "",
                "end",
                iid=file_path,
                values=(rel_display, display_ue, issue),
                tags=("error",),
            )

        if errors == 0:
            old_name = rel_parts[-1]
            self.relocate_name_var.set(old_name)
            self.relocate_ready = True
            self._toggle_relocate_controls(True)
            self._set_folder_hint(f"目录变更就位：{len(asset_files)} 个资产路径一致", "success")
            self._set_status("目录校验通过", "success")
        else:
            self._set_folder_hint(f"发现 {errors} 个路径异常文件（双击可定位）", "error")
            self._set_status("目录校验失败", "warning")

    def _build_new_prefix(self, new_name: str) -> str:
        if len(self.relocate_rel_parts) > 1:
            base = "/Game/" + "/".join(self.relocate_rel_parts[:-1])
            return f"{base}/{new_name}/"
        return f"/Game/{new_name}/"

    def _replace_prefix_in_file(self, file_path: str, old_bytes: bytes, new_bytes: bytes) -> int:
        data = Path(file_path).read_bytes()
        count = data.count(old_bytes)
        if count == 0:
            return 0
        if len(old_bytes) != len(new_bytes):
            raise ValueError("prefix length mismatch")
        new_data = data.replace(old_bytes, new_bytes)
        if new_data != data:
            self._ensure_writable(file_path)
            Path(file_path).write_bytes(new_data)
        return count

    def _ensure_writable(self, file_path: str):
        try:
            mode = os.stat(file_path).st_mode
            if not (mode & stat.S_IWRITE):
                os.chmod(file_path, mode | stat.S_IWRITE)
        except Exception:
            pass

    def execute_relocate(self):
        """执行目录名变更"""
        if not self.relocate_ready:
            messagebox.showwarning("提示", "请先检测路径并确保无异常")
            return

        new_name = self.relocate_name_var.get().strip()
        if not new_name:
            messagebox.showwarning("提示", "请输入新的目录名")
            return

        invalid_chars = set('<>:"/\\|?*')
        if any(ch in invalid_chars for ch in new_name):
            messagebox.showwarning("提示", "目录名包含非法字符")
            return

        old_name = self.relocate_rel_parts[-1]
        if new_name == old_name:
            messagebox.showinfo("提示", "新目录名与旧目录名相同，无需变更")
            return

        old_prefix = self.relocate_old_prefix
        new_prefix = self._build_new_prefix(new_name)
        if len(old_prefix) != len(new_prefix):
            messagebox.showwarning("提示", "新旧目录名长度不同，为避免破坏资产，需保持长度一致")
            return

        mode_label = self.relocate_mode_var.get()
        mode = "copy" if mode_label == "副本粘贴模式" else "inplace"
        src_folder = self.relocate_folder_path
        dest_folder = os.path.join(os.path.dirname(src_folder), new_name)

        try:
            if mode == "copy":
                if os.path.exists(dest_folder):
                    overwrite = messagebox.askyesno("提示", "目标文件夹已存在，是否删除后重新创建？")
                    if not overwrite:
                        return
                    shutil.rmtree(dest_folder)
                shutil.copytree(src_folder, dest_folder)
            else:
                if os.path.exists(dest_folder):
                    messagebox.showwarning("提示", "目标文件夹已存在，请更换名称")
                    return
                os.rename(src_folder, dest_folder)
        except Exception as exc:
            messagebox.showerror("错误", f"文件夹操作失败:\n{exc}")
            self._set_status("目录变更失败", "error")
            return

        target_files = self._collect_asset_files(dest_folder, include_sidecars=True)
        old_bytes = old_prefix.encode("utf-8")
        new_bytes = new_prefix.encode("utf-8")
        modified_files = 0
        total_hits = 0

        try:
            for file_path in target_files:
                count = self._replace_prefix_in_file(file_path, old_bytes, new_bytes)
                if count > 0:
                    modified_files += 1
                    total_hits += count
        except Exception as exc:
            messagebox.showerror("错误", f"更新资产路径失败:\n{exc}")
            self._set_status("资产更新失败", "error")
            return

        self.folder_path_var.set(dest_folder)
        self.relocate_ready = False
        self._toggle_relocate_controls(False)
        self._set_folder_hint(f"变更完成：修改 {modified_files} 个文件，共 {total_hits} 处", "success")
        self._set_status("目录变更完成", "success")

    def _on_relocate_item_double_click(self, _event):
        item = self.relocate_tree.focus()
        if not item:
            return
        if os.path.exists(item):
            self._reveal_in_explorer(item)

    def _reveal_in_explorer(self, file_path: str):
        try:
            target = os.path.abspath(file_path).replace("/", "\\")
            subprocess.run(["explorer", f'/select,"{target}"'], check=False)
        except Exception:
            try:
                os.startfile(os.path.dirname(file_path))
            except Exception:
                pass

    def analyze_asset(self):
        """分析 UE 资产文件"""
        file_path = self.asset_file_var.get().strip()
        if not file_path:
            messagebox.showwarning("提示", "请先选择文件")
            return
        if not os.path.isfile(file_path):
            messagebox.showwarning("提示", "文件不存在: " + file_path)
            return

        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.configure(state=tk.DISABLED)
        self._set_busy(True, "正在分析...")
        analysis_started = time.perf_counter()
        self._start_analysis_flow()
        self.root.update_idletasks()

        try:
            info = self.parser.parse_file(file_path)
            self._hold_analysis_animation(analysis_started)
            self._stop_analysis_flow()
            if not info:
                self._append_text("✗ 无法识别该文件为 UE 资产文件\n", "error")
                self._append_text(f"文件: {file_path}\n", "label")
                self._set_status("分析失败", "error")
            else:
                ue_path = UEPathExtractor.extract_asset_path(file_path)
                display_path = self._map_ue_path(ue_path) if ue_path else "(未找到)"
                imports = self.parser.extract_import_references(info)
                references = []
                seen = set()
                for ref in imports:
                    name, mapped = self._format_reference(ref)
                    if mapped in seen:
                        continue
                    seen.add(mapped)
                    references.append((name, mapped))

                self._append_text("UE 资产分析结果\n", "header")
                self._append_text("────────────────────────────────────────────────────────────\n", "divider")

                self._append_text("\nUE 内路径\n", "section")
                self._append_text("  ", None)
                self._append_text(f"{display_path}\n", "path")

                self._append_text("\n基本信息\n", "section")
                self._append_text("  文件名: ", "label")
                self._append_text(f"{info.file_name}\n", "value")
                self._append_text("  文件大小: ", "label")
                self._append_text(f"{info.properties.get('file_size', 'N/A')}\n", "value")
                self._append_text("  特征文本: ", "label")
                self._append_text(f"{info.asset_type}\n", "value")

                self._append_text("\n引擎信息\n", "section")
                self._append_text("  UE 版本: ", "label")
                self._append_text(f"{info.ue_version}\n", "value")
                self._append_text("  版本号: ", "label")
                self._append_text(f"{hex(info.version)}\n", "value")

                self._append_text("\n关联文件\n", "section")
                if info.related_files:
                    for i, rf in enumerate(info.related_files, 1):
                        self._append_text("  - ", "bullet")
                        self._append_text(f"{rf}\n", "value")
                else:
                    self._append_text("  (未找到关联文件)\n", "label")

                self._append_text(f"\n引用文件（共 {len(references)} 项）\n", "section")
                if references:
                    for name, path in references:
                        self._append_text("  - ", "bullet")
                        self._append_text(f"{name}  ", "value")
                        self._append_text(f"{path}\n", "path")
                else:
                    self._append_text("  (未发现引用)\n", "label")

                self._set_status("分析完成", "success")

            self.result_text.see("1.0")
        except Exception as exc:
            self._hold_analysis_animation(analysis_started)
            self._stop_analysis_flow()
            error_msg = f"✗ 错误: {exc}\n\n详情:\n{repr(exc)}"
            self._append_text(error_msg, "error")
            self._set_status("分析失败", "error")
        finally:
            if self._analysis_active:
                self._stop_analysis_flow()
            self._set_busy(False)

    def center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")


def launch_gui():
    """启动 GUI 应用"""
    if HAS_DND:
        try:
            root = TkinterDnD.Tk()
        except Exception:
            root = tk.Tk()
    else:
        root = tk.Tk()
    app = UEAssetFinderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
