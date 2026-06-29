"""
UE资产分析工具 - GUI界面
使用tkinter提供图形用户界面，支持拖拽文件和UE资产分析
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
from pathlib import Path
from asset_finder import UEAssetFinder
from ue_parser import UEAssetParser, UEPathExtractor
from typing import Optional, List

# 尝试导入 Windows 拖拽支持
try:
    from win_dnd import enable_dnd_for_widget
    HAS_WIN_DND = True
except ImportError:
    HAS_WIN_DND = False

# 拖拽功能在 Windows 上可能不稳定，所以我们禁用它
HAS_DND = False


class UEAssetFinderGUI:
    """UE资产查找工具的GUI应用"""
    
    def __init__(self, root: tk.Tk):
        """初始化GUI应用"""
        self.root = root
        self.root.title("UE资产分析工具")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)
        
        # 初始化工具
        self.finder = UEAssetFinder()
        self.parser = UEAssetParser()
        
        # 设置样式
        self.setup_styles()
        
        # 创建界面
        self.create_ui()
        
        # 居中窗口
        self.center_window()
    
    def setup_styles(self):
        """配置样式"""
        style = ttk.Style()
        style.theme_use('clam')
    
    def create_ui(self):
        """创建用户界面"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 标题
        ttk.Label(
            main_frame,
            text="UE资产分析工具",
            font=('Arial', 16, 'bold')
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # 拖拽区域提示
        drop_frame = tk.Frame(
            main_frame,
            bg='#c8e6c9',
            highlightbackground='#2e7d32',
            highlightthickness=2,
            height=60
        )
        drop_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=0, pady=(10, 15), ipady=15)
        drop_frame.columnconfigure(0, weight=1)
        
        drop_text = tk.Label(
            drop_frame,
            text="📁 拖拽UE资产文件到这里或点击下方浏览按钮\n支持 .uasset、.umap、.uexp、.ubulk 等文件",
            bg='#c8e6c9',
            fg='#1b5e20',
            font=('Arial', 10)
        )
        drop_text.pack(expand=True, fill=tk.BOTH)
        
        # 注册拖拽事件
        if HAS_WIN_DND:
            try:
                enable_dnd_for_widget(drop_frame, self.on_drop_asset)
                enable_dnd_for_widget(drop_text, self.on_drop_asset)
                drop_text.config(text="📁 拖拽UE资产文件到这里\n支持 .uasset、.umap、.uexp、.ubulk 等文件")
            except Exception as e:
                print(f"⚠ 拖拽功能初始化失败: {e}")
        
        # 也为主窗口注册拖拽
        if HAS_WIN_DND:
            try:
                enable_dnd_for_widget(self.root, self.on_drop_asset)
            except:
                pass
        
        # 文件选择框
        file_frame = ttk.LabelFrame(main_frame, text="或点击浏览选择文件", padding="10")
        file_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        file_frame.columnconfigure(1, weight=1)
        
        self.asset_file_var = tk.StringVar()
        entry = ttk.Entry(file_frame, textvariable=self.asset_file_var)
        entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        
        ttk.Button(
            file_frame,
            text="浏览",
            command=self.browse_asset
        ).grid(row=0, column=2, padx=(0, 5))
        
        ttk.Button(
            file_frame,
            text="分析",
            command=self.analyze_asset
        ).grid(row=0, column=3)
        
        # 结果显示
        result_frame = ttk.LabelFrame(main_frame, text="分析结果", padding="10")
        result_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            height=25,
            font=('Courier', 10),
            wrap=tk.WORD
        )
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN
        ).grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def browse_asset(self):
        """浏览选择资产文件"""
        file = filedialog.askopenfilename(
            title="选择UE资产文件",
            filetypes=[
                ("UE资产文件", "*.uasset *.umap *.uexp *.ubulk"),
                ("所有文件", "*.*")
            ]
        )
        if file:
            self.asset_file_var.set(file)
            self.analyze_asset()
    
    def on_drop_asset(self, event):
        """处理拖拽资产文件"""
        try:
            data = event.data
            
            # 处理文件路径（可能被花括号包围）
            if data.startswith('{') and data.endswith('}'):
                data = data[1:-1]
            
            # 处理多个文件的情况
            files = []
            if '} {' in data:
                files = [f.strip('{}') for f in data.split('} {')]
            else:
                files = [data]
            
            # 取第一个文件
            file_path = files[0].strip()
            
            # Windows 路径转换
            if '\\' in file_path:
                file_path = file_path.replace('\\', '/')
            
            # 验证文件是否存在
            if os.path.isfile(file_path):
                self.asset_file_var.set(file_path)
                self.analyze_asset()
            else:
                self.result_text.delete('1.0', tk.END)
                self.result_text.insert('1.0', f"❌ 文件不存在: {file_path}")
                self.status_var.set("✗ 文件不存在")
        except Exception as e:
            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', f"❌ 拖拽处理出错:\n{str(e)}")
            self.status_var.set("✗ 拖拽失败")
    
    def analyze_asset(self):
        """分析UE资产文件"""
        file_path = self.asset_file_var.get().strip()
        
        if not file_path:
            messagebox.showwarning("警告", "请选择文件")
            return
        
        if not os.path.isfile(file_path):
            messagebox.showwarning("警告", "文件不存在: " + file_path)
            return
        
        self.result_text.delete('1.0', tk.END)
        self.status_var.set("分析中...")
        self.root.update()
        
        try:
            # 解析文件
            info = self.parser.parse_file(file_path)
            
            if not info:
                output = f"❌ 无法识别此文件为UE资产文件\n文件: {file_path}"
            else:
                # 提取导入信息
                imports = self.parser.extract_import_references(info)
                
                # 构建输出
                output = f"""╔════════════════════════════════════════════════════════════╗
║                   UE资产文件分析结果
╚════════════════════════════════════════════════════════════╝

📄 基本信息
  文件名: {info.file_name}
  文件大小: {info.properties.get('file_size', 'N/A')}
  资产类型: {info.asset_type}
  
🎮 引擎信息
  UE版本: {info.ue_version}
  版本号: {hex(info.version)}
  魔数: {hex(info.magic)}

📁 关联文件
"""
                if info.related_files:
                    for i, rf in enumerate(info.related_files, 1):
                        output += f"  {i}. {rf}\n"
                else:
                    output += "  (未找到关联文件)\n"
                
                output += f"\n🔗 导入/引用 (前20个)\n"
                if imports:
                    for i, imp in enumerate(imports[:20], 1):
                        output += f"  {i}. {imp}\n"
                else:
                    output += "  (无法提取导入信息)\n"
                
                # 尝试提取UE中的路径
                ue_path = UEPathExtractor.extract_asset_path(file_path)
                if ue_path:
                    output += f"\n📍 UE内路径\n  {ue_path}\n"
            
            self.result_text.insert('1.0', output)
            self.status_var.set("✓ 分析完成")
        
        except Exception as e:
            error_msg = f"❌ 错误: {str(e)}\n\n详情:\n{repr(e)}"
            self.result_text.insert('1.0', error_msg)
            self.status_var.set("✗ 分析失败")
    
    def center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f'+{x}+{y}')


def launch_gui():
    """启动GUI应用"""
    root = tk.Tk()
    app = UEAssetFinderGUI(root)
    root.mainloop()


if __name__ == '__main__':
    launch_gui()
