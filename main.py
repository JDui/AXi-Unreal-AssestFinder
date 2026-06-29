"""
UE资产路径查找工具 - 主程序
提供命令行和GUI界面来转换UE资产文件路径
"""

import sys
import os
from pathlib import Path
from asset_finder import UEAssetFinder
from gui_dnd import launch_gui
import json


def print_separator(title: str = ""):
    """打印分隔线"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'-'*60}\n")


def interactive_mode():
    """交互模式"""
    print_separator("UE资产路径查找工具")
    print("欢迎使用UE资产路径查找工具！\n")
    
    # 获取项目路径（可选）
    project_path = input("请输入UE项目路径 (按Enter跳过): ").strip()
    if not project_path or not os.path.isdir(project_path):
        project_path = None
    
    finder = UEAssetFinder(project_path)
    
    while True:
        print("\n请选择操作:")
        print("1. 转换单个文件路径")
        print("2. 批量转换文件路径")
        print("3. 搜索目录中的资产")
        print("4. 退出")
        
        choice = input("\n请输入选项 (1-4): ").strip()
        
        if choice == '1':
            single_file_convert(finder)
        elif choice == '2':
            batch_file_convert(finder)
        elif choice == '3':
            search_directory(finder)
        elif choice == '4':
            print("\n谢谢使用！再见！")
            break
        else:
            print("无效选项，请重新选择")


def single_file_convert(finder: UEAssetFinder):
    """转换单个文件"""
    print_separator("转换单个文件路径")
    
    file_path = input("请输入文件完整路径: ").strip()
    
    if not os.path.isfile(file_path):
        print(f"错误: 文件不存在 - {file_path}")
        return
    
    result = finder.path_to_ue_content_path(file_path)
    
    if result:
        print("\n转换结果:")
        print(f"  原始路径:        {result['original_path']}")
        print(f"  文件名:          {result['file_name']}")
        print(f"  资产类型:        {result['asset_type']}")
        print(f"  建议目录:        {result['suggested_directory']}")
        print(f"  UE Content路径:  {result['ue_content_path']}")
        print(f"  相对路径:        {result['relative_content_path']}")


def batch_file_convert(finder: UEAssetFinder):
    """批量转换文件"""
    print_separator("批量转换文件路径")
    
    print("请输入文件路径 (每行一个，输入'done'结束):")
    file_paths = []
    
    while True:
        path = input("> ").strip()
        if path.lower() == 'done':
            break
        if path and os.path.isfile(path):
            file_paths.append(path)
        else:
            print(f"警告: 文件不存在或路径无效 - {path}")
    
    if not file_paths:
        print("未输入任何有效文件")
        return
    
    results = finder.batch_convert_paths(file_paths)
    
    print(f"\n共转换 {len(results)} 个文件:\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['file_name']}")
        print(f"   UE路径: {result['ue_content_path']}")
        print()


def search_directory(finder: UEAssetFinder):
    """搜索目录中的资产"""
    print_separator("搜索目录中的资产")
    
    directory = input("请输入目录路径: ").strip()
    
    if not os.path.isdir(directory):
        print(f"错误: 目录不存在 - {directory}")
        return
    
    print("正在搜索资产...")
    results = finder.find_assets_in_directory(directory)
    
    if not results:
        print("未找到任何UE资产文件")
        return
    
    print(f"\n找到 {len(results)} 个资产文件:\n")
    
    # 按类型分组显示
    by_type = {}
    for result in results:
        asset_type = result['asset_type']
        if asset_type not in by_type:
            by_type[asset_type] = []
        by_type[asset_type].append(result)
    
    for asset_type, items in sorted(by_type.items()):
        print(f"\n【{asset_type}】({len(items)}个)")
        for item in items:
            print(f"  {item['file_name']}")
            print(f"    → {item['ue_content_path']}")


def quick_convert_mode():
    """快速转换模式 - 从命令行参数读取路径"""
    if len(sys.argv) < 2:
        launch_gui()
        return
    
    finder = UEAssetFinder()
    found_any = False
    
    for file_path in sys.argv[1:]:
        # 跳过所有选项参数
        if file_path in ['-h', '--help', '-gui', '--gui', '-cli', '--cli']:
            continue
        
        if os.path.isfile(file_path):
            result = finder.path_to_ue_content_path(file_path)
            if result:
                print(json.dumps(result, ensure_ascii=False, indent=2))
                found_any = True
        elif os.path.isdir(file_path):
            results = finder.find_assets_in_directory(file_path)
            for result in results:
                print(json.dumps(result, ensure_ascii=False, indent=2))
                found_any = True
        else:
            print(f"错误: 路径不存在 - {file_path}", file=sys.stderr)
    
    # 如果没有找到任何有效的路径，显示帮助
    if not found_any and len(sys.argv) > 1:
        print("未处理任何有效的文件或目录", file=sys.stderr)


def main():
    """主函数"""
    try:
        # 检查命令行参数
        if len(sys.argv) > 1:
            if sys.argv[1] in ['-h', '--help']:
                print_help()
            elif sys.argv[1] in ['-gui', '--gui']:
                # 启动GUI模式
                launch_gui()
            elif sys.argv[1] in ['-cli', '--cli']:
                # 启动CLI交互模式
                interactive_mode()
            else:
                # 快速转换模式
                quick_convert_mode()
        else:
            # 默认启动GUI模式
            launch_gui()
    except KeyboardInterrupt:
        print("\n\n程序已中止")
        sys.exit(0)
    except Exception as e:
        print(f"发生错误: {e}", file=sys.stderr)
        sys.exit(1)


def print_help():
    """打印帮助信息"""
    help_text = """
UE资产路径查找工具

使用方法:
  python main.py              启动GUI模式
  python main.py -gui         启动GUI模式
  python main.py -cli         启动交互式命令行模式
  python main.py <file>       快速转换单个文件
  python main.py <dir>        快速转换目录中的资产
  python main.py -h/--help    显示此帮助信息

示例:
  python main.py
  python main.py "path/to/file.fbx"
  python main.py "path/to/directory"
    """
    print(help_text)


if __name__ == '__main__':
    main()
