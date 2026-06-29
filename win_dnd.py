"""
Windows 拖拽支持 - 使用 Win32 API 实现
"""

import ctypes
from ctypes import wintypes, windll
import threading

# Windows API 常量
WM_DROPFILES = 0x233
WM_DESTROY = 2

# Tcl 命令
class TclDropTarget:
    """使用 Tcl 的拖拽目标"""
    
    def __init__(self, widget, callback):
        self.widget = widget
        self.callback = callback
        self.hwnd = widget.winfo_id()
        self.tcl = widget.tk
        
    def register(self):
        """注册拖拽"""
        try:
            # 获取 Tcl 解释器
            tcl_code = f"""
            package require Tkdnd
            dnd register {self.widget} *
            {self.widget} configure -dropcommand [list {self.callback_name} %D]
            """
            self.tcl.eval(tcl_code)
            return True
        except:
            return False
    
    def callback_name(self):
        """回调函数名"""
        return "_dnd_callback"


def enable_dnd_for_widget(widget, on_drop_callback):
    """为 widget 启用拖拽"""
    try:
        # 尝试使用 Tcl/Tk 的 dnd 命令
        tcl = widget.tk
        
        # 生成唯一的回调命令
        callback_id = f"_dnd_{id(widget)}"
        
        # 注册 Tcl 回调函数
        def tcl_callback(*args):
            if args:
                # 处理拖拽的文件
                data = args[0] if args else ""
                class Event:
                    pass
                event = Event()
                event.data = data
                on_drop_callback(event)
        
        # 创建 Tcl 命令
        tcl.createcommand(callback_id, tcl_callback)
        
        # 注册拖拽 - 使用 Tcl 的 dnd 包
        try:
            tcl.eval('package require Tkdnd')
            tcl.eval(f'''
                dnd register {widget} *
                bind {widget} <<Drop:files>> {{
                    {callback_id} %D
                }}
            ''')
            print("✓ 拖拽功能已启用 (Tcl/Tk DND)")
            return True
        except:
            # 如果 Tkdnd 不可用，尝试其他方法
            return False
            
    except Exception as e:
        print(f"⚠ 拖拽初始化失败: {e}")
        return False
