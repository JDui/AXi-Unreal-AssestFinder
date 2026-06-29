"""
Windows 文件拖拽 - 使用 Shell COM 接口实现
"""

import os
import sys
import threading
import time
from pathlib import Path

def create_dnd_handler(root_window, on_drop_callback):
    """创建一个 Windows 级别的拖拽处理器"""
    
    try:
        import win32api
        import win32con
        import win32gui
        from ctypes import wintypes, windll, c_char_p
        
        hwnd = root_window.winfo_id()
        
        # 声明 DragAcceptFiles 函数
        DragAcceptFiles = windll.shell32.DragAcceptFiles
        DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
        
        # 启用拖拽
        DragAcceptFiles(hwnd, True)
        
        # 拦截 WM_DROPFILES 消息
        original_wnd_proc = None
        
        def handle_drop(hwnd, msg, wparam, lparam):
            """处理拖拽文件消息"""
            if msg == 0x233:  # WM_DROPFILES
                # 获取文件数量
                from ctypes import windll, wintypes, pointer, create_unicode_buffer
                
                DragQueryFileW = windll.shell32.DragQueryFileW
                DragFinish = windll.shell32.DragFinish
                
                # 获取拖拽数据
                hdrop = wparam
                
                # 获取文件数
                num_files = DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
                files = []
                
                for i in range(num_files):
                    # 获取文件名长度
                    length = DragQueryFileW(hdrop, i, None, 0) + 1
                    filename = create_unicode_buffer(length)
                    DragQueryFileW(hdrop, i, filename, length)
                    files.append(filename.value)
                
                DragFinish(hdrop)
                
                # 触发回调
                if files:
                    class Event:
                        def __init__(self, data):
                            self.data = data
                    
                    event = Event(files[0])
                    on_drop_callback(event)
                
                return 0
            
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
        
        print("✓ Windows 拖拽支持已初始化")
        return True
        
    except ImportError:
        print("⚠ Win32 API 不可用，拖拽功能将不可用")
        return False
    except Exception as e:
        print(f"⚠ 拖拽初始化失败: {e}")
        return False
