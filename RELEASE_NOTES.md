# Release Notes

## v1.1.0 - Matrix UI Refresh

发布日期：2026-06-29

### 新增

- 深色矩阵风格界面。
- 顶部扫描条动画。
- 拖拽区域霓虹边框脉冲。
- 终端风结果面板、输入框和状态栏。
- `DEVELOPMENT.md` 开发、测试、构建、发布流程文档。

### 改进

- 重写 `README.md`，补充安装、运行、构建、限制和目录修复说明。
- 重写 `IMPLEMENTATION.md`，记录核心模块和业务流程。
- 更新 ttk 按钮、标签页、表格、进度条和输入控件样式。

### 保持不变

- 资产解析逻辑不变。
- 拖拽处理逻辑不变。
- 目录校验和目录变更逻辑不变。
- PyInstaller 打包入口不变。

### 构建产物

- `UEAssetPathFinder-v1.1.0-win64.zip`

## v1.0.0 - Initial Release

- UE 资产文件分析。
- UE 内路径提取。
- 引用和关联文件显示。
- GUI 拖拽支持。
- 目录修复辅助。
- Windows PyInstaller 打包。
