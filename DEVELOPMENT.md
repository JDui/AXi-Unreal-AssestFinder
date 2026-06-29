# Development

本文件记录 AXi Unreal Asset Finder 的开发、测试、构建和发布流程。

## 环境

- Python 3.12 推荐，3.10+ 理论可运行。
- Windows 10/11 推荐，用于拖拽和 PyInstaller 打包验证。
- 主要依赖：`tkinterdnd2`、`pywin32`、`pyinstaller`。

初始化：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
```

## 运行

GUI：

```powershell
python main.py
```

CLI：

```powershell
python main.py -cli
python main.py "D:\Project\Content\Asset.uasset"
```

## 测试

基础解析测试：

```powershell
python test_parser.py
```

语法检查：

```powershell
python -m compileall main.py gui_dnd.py ue_parser.py asset_finder.py config.py
```

构建前至少验证：

- GUI 可启动。
- 拖拽区可接收文件。
- `test_asset.uasset` 可被解析。
- 目录修复按钮默认禁用，校验通过后才启用。
- 目录修复模式药丸滑块可在副本粘贴和原位更改之间切换。
- 目录修复拖入文件夹和检测路径时会显示代码流扫过动画。
- 检测结果双击异常行可定位到实际文件。
- 分析结果选中文本使用亮绿底和深色字反转显示。
- 引用文件按目录层级输出脑图风格结构。
- 新旧目录名长度不一致时会弹出二次确认。
- 切换到“原位更改模式”时会提示不可逆风险。
- 执行目录变更前会提示目录外引用丢失风险。

## UI 约束

当前 UI 位于 `gui_dnd.py`。

- 不在 UI 美化中改动解析、重命名、复制、拖拽处理等业务函数。
- 视觉状态可以变更颜色、字体、边框、动画，不改变控件命令绑定。
- 动画使用 `root.after`，不要阻塞 Tk 主线程。
- 长耗时逻辑仍需保持进度条和状态栏反馈。

## 构建

使用 PyInstaller：

```powershell
pyinstaller --clean --noconfirm build_exe.spec
```

输出目录：

```text
dist\UEAssetPathFinder\
```

发行压缩包建议命名：

```text
release\UEAssetPathFinder-v1.2.1-win64.zip
```

## 发布

1. 更新 `README.md`、`DEVELOPMENT.md`、`RELEASE_NOTES.md`。
2. 运行测试和语法检查。
3. 重新构建 `dist\UEAssetPathFinder`。
4. 压缩 `dist\UEAssetPathFinder` 到 `release\UEAssetPathFinder-vX.Y.Z-win64.zip`。
5. 提交源码变更。
6. 推送 `main`。
7. 创建 Git tag，例如 `v1.2.1`。
8. 在 GitHub Release 上传压缩包。

## Git

生成物不入库：

- `.venv/`
- `__pycache__/`
- `build/`
- `dist/`
- `release/`

Release 附件由 GitHub Release 保存。
