# Implementation Notes

## 模块

- `main.py`：入口。默认启动 GUI；`-cli` 进入交互 CLI；传入文件或目录时执行快速转换。
- `gui_dnd.py`：主 GUI。包含资产分析、目录修复、拖拽、状态栏、进度条和 Matrix 风格动画。
- `ue_parser.py`：UE 资产解析。负责魔数校验、版本字段读取、特征文本提取、关联文件扫描和引用提取。
- `asset_finder.py`：普通文件路径到 UE Content 路径的映射与分类建议。
- `win_dnd.py` / `win_dnd_advanced.py`：Windows 拖拽辅助实现。

## 资产分析流程

1. GUI 或 CLI 接收资产文件路径。
2. `UEAssetParser.parse_file` 读取二进制内容。
3. 校验 UE 包魔数 `0x9E2A83C1`。
4. 解析 UE4 / UE5 版本字段。
5. 从二进制字符串中提取资产类型、UE 内路径、导入引用。
6. 扫描同名 `.uexp` / `.ubulk` 等关联文件。
7. GUI 将结果写入终端风文本面板。

## 目录修复流程

1. 用户拖入或选择资产文件夹。
2. GUI 收集 `.uasset` / `.umap` 文件。
3. 根据文件夹路径推导期望 `/Game/.../` 前缀。
4. 每个资产尝试提取当前 UE 路径。
5. 若全部路径一致，启用目录变更控件。
6. 用户输入新目录名。
7. 新旧目录名前缀长度必须一致。
8. 副本模式复制目录后修改副本；原位模式直接重命名目录。
9. 在目标文件中按字节替换旧前缀。

## UI 实现

`v1.1.0` 的 UI 美化集中在 `gui_dnd.py`：

- `_init_theme` 定义深色矩阵配色。
- `setup_styles` 统一 ttk 控件样式。
- `create_ui` 增加顶部扫描条。
- `_animate_matrix_strip` 使用 `root.after` 刷新扫描字符。
- `_animate_drop_pulse` 处理拖拽区和状态栏霓虹边框。

业务函数未改动：

- `analyze_asset`
- `validate_folder`
- `execute_relocate`
- `on_drop_asset`
- `on_drop_folder`
- `_replace_prefix_in_file`

## 打包

`build_exe.spec` 收集 `tkinterdnd2` 数据文件，并隐藏导入 Windows 拖拽依赖。

```powershell
pyinstaller --clean --noconfirm build_exe.spec
```

输出目录：

```text
dist\UEAssetPathFinder\
```
