"""
UE资产路径查找工具 - GUI界面
使用tkinter提供图形用户界面，支持拖拽文件和UE资产分析
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
from pathlib import Path
from asset_finder import UEAssetFinder
from ue_parser import UEAssetParser, UEPathExtractor
from typing import Optional, List

# 尝试导入tkinterdnd2用于拖拽功能
try:
    from tkinterdnd2 import DND_FILES, DND_TEXT, DND_URI
    HAS_DND = True
except ImportError:
    HAS_DND = False


class UEAssetFinderGUI:
    """UE资产查找工具的GUI应用"""
    
    def __init__(self, root: tk.Tk):
        """初始化GUI应用"""
        self.root = root
        self.root.title("UE资产路径查找工具")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # 初始化资产查找器和解析器
        self.finder = UEAssetFinder()
        self.parser = UEAssetParser()
        
        # 设置样式
        self.setup_styles()
        
        # 创建标签页
        self.create_notebook()
        
        # 设置窗口图标和居中
        self.center_window()
    
    def setup_styles(self):
        """配置样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置颜色
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Info.TLabel', font=('Arial', 10))
        style.configure('Result.TFrame', relief='sunken', borderwidth=1)
        style.configure('DragDrop.TFrame', relief='dashed', borderwidth=2, background='#f0f0f0')
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Subtitle.TLabel', font=('Arial', 10), foreground='gray')
    
    def create_notebook(self):
        """创建标签页界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建笔记本（标签页）
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 创建标签页
        self.create_asset_analyzer_tab(notebook)
        self.create_path_converter_tab(notebook)
    
    def create_notebook(self):
        """创建标签页界面"""
        # 创建笔记本（标签页）
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建标签页
        self.create_asset_analyzer_tab(notebook)
        self.create_path_converter_tab(notebook)
    
    def create_asset_analyzer_tab(self, notebook):
        """创建资产分析标签页"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="UE资产分析")
        
        # 配置grid权重
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        
        # 标题
        title = ttk.Label(frame, text="UE资产分析工具", style='Title.TLabel')
        title.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        subtitle = ttk.Label(
            frame,
            text="拖拽或选择 .uasset 或 .umap 文件进行分析",
            style='Subtitle.TLabel'
        )
        subtitle.grid(row=1, column=0, sticky=tk.W, pady=(0, 15))
        
        # 拖拽区域
        self.create_asset_drop_zone(frame)
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(frame, text="文件选择", padding="10")
        file_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="文件路径:").grid(row=0, column=0, sticky=tk.W)
        
        self.asset_file_var = tk.StringVar()
        self.asset_file_entry = ttk.Entry(file_frame, textvariable=self.asset_file_var)
        self.asset_file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        
        ttk.Button(
            file_frame,
            text="浏览...",
            command=self.browse_asset_file
        ).grid(row=0, column=2, padx=(0, 5))
        
        ttk.Button(
            file_frame,
            text="分析",
            command=self.analyze_asset_file
        ).grid(row=0, column=3)
        
        # 结果显示区域
        result_frame = ttk.LabelFrame(frame, text="分析结果", padding="10")
        result_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        # 创建文本显示区域
        self.asset_result_text = scrolledtext.ScrolledText(
            result_frame,
            height=20,
            font=('Courier', 9),
            wrap=tk.WORD
        )
        self.asset_result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 底部按钮
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(
            button_frame,
            text="清空",
            command=lambda: self.asset_result_text.delete('1.0', tk.END)
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        # 状态栏
        self.asset_status_var = tk.StringVar(value="就绪")
        ttk.Label(
            frame,
            textvariable=self.asset_status_var,
            relief=tk.SUNKEN,
            font=('Arial', 9)
        ).grid(row=6, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def create_asset_drop_zone(self, parent):
        """创建资产拖拽区域"""
        drop_frame = tk.Frame(
            parent,
            bg='#e8f4f8',
            bd=2,
            relief='dashed',
            highlightthickness=1,
            highlightbackground='#4a90e2'
        )
        drop_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 15), ipady=30)
        drop_frame.columnconfigure(0, weight=1)
        
        # 拖拽提示文本
        drop_label = tk.Label(
            drop_frame,
            text="📁 拖拽 UE 资产文件到这里分析",
            bg='#e8f4f8',
            fg='#1a5490',
            font=('Arial', 12, 'bold')
        )
        drop_label.pack(side=tk.TOP, expand=True, fill=tk.BOTH)
        
        sub_label = tk.Label(
            drop_frame,
            text='支持 .uasset, .umap, .uexp 等文件',
            bg='#e8f4f8',
            fg='#4a90e2',
            font=('Arial', 9)
        )
        sub_label.pack(side=tk.TOP)
        
        # 注册拖拽事件
        if HAS_DND:
            try:
                from tkinterdnd2 import DND_FILES
                drop_frame.drop_target_register(DND_FILES)
                drop_frame.dnd_bind('<<Drop>>', self.on_drop_asset_file)
                drop_label.drop_target_register(DND_FILES)
                drop_label.dnd_bind('<<Drop>>', self.on_drop_asset_file)
                sub_label.drop_target_register(DND_FILES)
                sub_label.dnd_bind('<<Drop>>', self.on_drop_asset_file)
            except Exception as e:
                print(f"拖拽功能配置出错: {e}")
    
    def create_path_converter_tab(self, notebook):
        """创建路径转换标签页"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="路径转换")
        
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(3, weight=1)
        
        # ===== 标题 =====
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        title_label = ttk.Label(
            title_frame,
            text="UE资产路径查找工具",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = ttk.Label(
            title_frame,
            text="将文件系统路径转换为UE Content路径",
            font=('Arial', 10),
            foreground='gray'
        )
        subtitle_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # ===== 拖拽区域 =====
        if HAS_DND:
            self.create_drop_zone(main_frame)
        
        # ===== 单个文件转换区域 =====
        single_frame = ttk.LabelFrame(main_frame, text="单个文件转换", padding="10")
        single_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        single_frame.columnconfigure(1, weight=1)
        
        ttk.Label(single_frame, text="文件路径:").grid(row=0, column=0, sticky=tk.W)
        
        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(single_frame, textvariable=self.file_path_var)
        self.file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        self.file_entry.bind('<Return>', lambda e: self.convert_single_file())
        
        self.browse_button = ttk.Button(
            single_frame,
            text="浏览...",
            command=self.browse_file
        )
        self.browse_button.grid(row=0, column=2, padx=(0, 5))
        
        self.convert_button = ttk.Button(
            single_frame,
            text="转换",
            command=self.convert_single_file
        )
        self.convert_button.grid(row=0, column=3)
        
        # ===== 批量转换区域 =====
        batch_frame = ttk.LabelFrame(main_frame, text="批量转换", padding="10")
        batch_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        batch_frame.columnconfigure(1, weight=1)
        
        ttk.Label(batch_frame, text="目录路径:").grid(row=0, column=0, sticky=tk.W)
        
        self.dir_path_var = tk.StringVar()
        self.dir_entry = ttk.Entry(batch_frame, textvariable=self.dir_path_var)
        self.dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        
        self.browse_dir_button = ttk.Button(
            batch_frame,
            text="浏览...",
            command=self.browse_directory
        )
        self.browse_dir_button.grid(row=0, column=2, padx=(0, 5))
        
        self.search_button = ttk.Button(
            batch_frame,
            text="搜索资产",
            command=self.search_assets_in_directory
        )
        self.search_button.grid(row=0, column=3)
        
        # ===== 结果显示区域 =====
        result_frame = ttk.LabelFrame(main_frame, text="转换结果", padding="10")
        result_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        # 创建树形视图显示结果
        self.create_result_treeview(result_frame)
        
        # ===== 底部按钮 =====
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, sticky=(tk.W, tk.E))
        
        self.clear_button = ttk.Button(
            button_frame,
            text="清空结果",
            command=self.clear_results
        )
        self.clear_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.copy_button = ttk.Button(
            button_frame,
            text="复制UE路径",
            command=self.copy_to_clipboard
        )
        self.copy_button.pack(side=tk.LEFT)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            font=('Arial', 9)
        )
        self.status_bar.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def create_result_treeview(self, parent: ttk.Frame):
        """创建结果树形视图"""
        # 创建树形视图
        columns = ('文件名', '资产类型', '建议目录', 'UE路径')
        self.result_tree = ttk.Treeview(
            parent,
            columns=columns,
            height=15,
            show='headings'
        )
        
        # 定义列
        self.result_tree.heading('#0', text='#')
        self.result_tree.column('#0', width=30)
        
        self.result_tree.heading('文件名', text='文件名')
        self.result_tree.column('文件名', width=200)
        
        self.result_tree.heading('资产类型', text='资产类型')
        self.result_tree.column('资产类型', width=100)
        
        self.result_tree.heading('建议目录', text='建议目录')
        self.result_tree.column('建议目录', width=120)
        
        self.result_tree.heading('UE路径', text='UE Content路径')
        self.result_tree.column('UE路径', width=300)
        
        # 添加滚动条
        vsb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.result_tree.yview)
        hsb = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.result_tree.xview)
        self.result_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # 布局
        self.result_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        # 绑定双击事件显示详细信息
        self.result_tree.bind('<Double-1>', self.on_item_double_click)
    
    def browse_file(self):
        """浏览选择单个文件"""
        file_path = filedialog.askopenfilename(
            title="选择文件",
            initialdir=os.path.expanduser("~")
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.convert_single_file()
    
    def browse_directory(self):
        """浏览选择目录"""
        dir_path = filedialog.askdirectory(
            title="选择目录",
            initialdir=os.path.expanduser("~")
        )
        if dir_path:
            self.dir_path_var.set(dir_path)
            self.search_assets_in_directory()
    
    def convert_single_file(self):
        """转换单个文件"""
        file_path = self.file_path_var.get().strip()
        
        if not file_path:
            messagebox.showwarning("警告", "请输入或选择文件路径")
            return
        
        if not os.path.isfile(file_path):
            messagebox.showerror("错误", f"文件不存在:\n{file_path}")
            return
        
        try:
            # 清空之前的结果
            self.clear_results()
            
            # 转换路径
            result = self.finder.path_to_ue_content_path(file_path)
            
            if result:
                # 添加到树形视图
                self.result_tree.insert(
                    '',
                    'end',
                    text='1',
                    values=(
                        result['file_name'],
                        result['asset_type'],
                        result['suggested_directory'],
                        result['ue_content_path']
                    )
                )
                
                self.status_var.set("✓ 转换成功")
            else:
                messagebox.showerror("错误", "无法转换该文件")
                self.status_var.set("✗ 转换失败")
        
        except Exception as e:
            messagebox.showerror("错误", f"转换过程中出错:\n{str(e)}")
            self.status_var.set("✗ 出错")
    
    def search_assets_in_directory(self):
        """搜索目录中的资产"""
        dir_path = self.dir_path_var.get().strip()
        
        if not dir_path:
            messagebox.showwarning("警告", "请输入或选择目录路径")
            return
        
        if not os.path.isdir(dir_path):
            messagebox.showerror("错误", f"目录不存在:\n{dir_path}")
            return
        
        try:
            # 清空之前的结果
            self.clear_results()
            
            self.status_var.set("搜索中...")
            self.root.update()
            
            # 搜索资产
            results = self.finder.find_assets_in_directory(dir_path)
            
            if not results:
                messagebox.showinfo("信息", "在该目录中未找到UE资产文件")
                self.status_var.set("就绪")
                return
            
            # 按类型分组排序
            results_by_type = {}
            for result in results:
                asset_type = result['asset_type']
                if asset_type not in results_by_type:
                    results_by_type[asset_type] = []
                results_by_type[asset_type].append(result)
            
            # 添加到树形视图
            row_num = 1
            for asset_type in sorted(results_by_type.keys()):
                items = results_by_type[asset_type]
                
                # 添加类型标题
                type_item = self.result_tree.insert(
                    '',
                    'end',
                    text=f'类型',
                    values=(f'【{asset_type}】', f'({len(items)}个)', '', ''),
                    tags=('type_header',)
                )
                
                # 添加该类型的项目
                for i, result in enumerate(items, 1):
                    self.result_tree.insert(
                        type_item,
                        'end',
                        text=f'{i}',
                        values=(
                            result['file_name'],
                            result['asset_type'],
                            result['suggested_directory'],
                            result['ue_content_path']
                        )
                    )
                    row_num += 1
            
            self.status_var.set(f"✓ 找到 {len(results)} 个资产")
        
        except Exception as e:
            messagebox.showerror("错误", f"搜索过程中出错:\n{str(e)}")
            self.status_var.set("✗ 出错")
    
    def on_item_double_click(self, event):
        """树形视图双击事件 - 显示详细信息"""
        item = self.result_tree.selection()[0]
        values = self.result_tree.item(item, 'values')
        
        if values:
            detail_text = f"""
文件名: {values[0]}
资产类型: {values[1]}
建议目录: {values[2]}
UE Content路径: {values[3]}

按Ctrl+C复制UE路径，或使用"复制UE路径"按钮
            """
            messagebox.showinfo("资产详情", detail_text.strip())
    
    def copy_to_clipboard(self):
        """复制选中项的UE路径到剪贴板"""
        selected = self.result_tree.selection()
        
        if not selected:
            messagebox.showwarning("警告", "请选择要复制的项目")
            return
        
        # 收集选中项的UE路径
        paths = []
        for item in selected:
            values = self.result_tree.item(item, 'values')
            if values and len(values) >= 4:
                paths.append(values[3])
        
        if paths:
            # 复制到剪贴板
            clipboard_text = '\n'.join(paths)
            self.root.clipboard_clear()
            self.root.clipboard_append(clipboard_text)
            self.root.update()
            
            messagebox.showinfo("成功", f"已复制 {len(paths)} 个UE路径到剪贴板")
        else:
            messagebox.showwarning("警告", "选中的项目无有效数据")
    
    def clear_results(self):
        """清空结果"""
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.status_var.set("就绪")
    
    def on_drop_file(self, event):
        """处理拖拽文件事件"""
        try:
            # 解析拖拽的数据
            data = event.data
            
            # 处理Windows文件路径格式
            # Windows下拖拽的格式可能是 {C:/path/to/file} 或 C:/path/to/file
            if data.startswith('{') and data.endswith('}'):
                data = data[1:-1]
            
            # 如果包含多个文件，使用空格或大括号分割
            files = []
            if '} {' in data:
                files = [f.strip('{}').replace('\\', '/') for f in data.split('} {')]
            else:
                files = [data.replace('\\', '/')]
            
            # 处理拖拽的文件
            for file_path in files:
                file_path = file_path.strip()
                if not file_path:
                    continue
                
                # 标准化路径
                file_path = os.path.normpath(file_path)
                
                if os.path.isfile(file_path):
                    # 拖拽的是文件，进行单文件转换
                    self.file_path_var.set(file_path)
                    self.convert_single_file()
                    break  # 只处理第一个文件
                elif os.path.isdir(file_path):
                    # 拖拽的是目录，进行批量搜索
                    self.dir_path_var.set(file_path)
                    self.search_assets_in_directory()
                    break  # 只处理第一个目录
            
            if not files or not files[0].strip():
                messagebox.showwarning("警告", "无法识别拖拽的文件")
        
        except Exception as e:
            messagebox.showerror("错误", f"处理拖拽文件时出错:\n{str(e)}")
            self.status_var.set("✗ 拖拽处理失败")
    
    def center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')


def launch_gui():
    """启动GUI应用"""
    root = tk.Tk()
    app = UEAssetFinderGUI(root)
    root.mainloop()


if __name__ == '__main__':
    launch_gui()
