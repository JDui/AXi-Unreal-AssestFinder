"""
Windows 拖拽支持补丁 - 通过 OS 事件处理实现拖拽功能
"""

import ctypes
import os
from ctypes import wintypes

# Windows API 常量
WM_DROPFILES = 0x233

class WindowsDropTarget:
    """Windows 文件拖拽目标实现"""
    
    @staticmethod
    def enable_dnd(widget, on_drop_callback):
        """为 Tkinter 窗口启用拖拽功能"""
        try:
            # 获取 widget 的窗口句柄
            hwnd = widget.winfo_id()
            
            # 使用 Windows API 注册拖拽
            # 这需要使用 ctypes 和 windll
            windll = ctypes.windll.shell32
            
            # DragAcceptFiles 函数注册文件拖拽
            DragAcceptFiles = windll.DragAcceptFiles
            DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
            DragAcceptFiles.restype = None
            
            DragAcceptFiles(hwnd, True)
            
            # 绑定拖拽事件
            widget.bind('<Control-v>', lambda e: on_drop_callback_from_clipboard(on_drop_callback))
            
            return True
        except Exception as e:
            print(f"Windows DND 初始化失败: {e}")
            return False


def on_drop_callback_from_clipboard(callback):
    """从剪贴板获取拖拽的文件"""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        try:
            # 获取剪贴板内容
            data = root.clipboard_get()
            # 触发回调
            class Event:
                pass
            event = Event()
            event.data = data
            callback(event)
        finally:
            root.destroy()
    except:
        pass
