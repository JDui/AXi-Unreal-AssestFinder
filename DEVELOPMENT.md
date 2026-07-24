# 开发说明

## 环境

- Python 3.10+
- Windows 10/11（拖放与打包验证）
- Rust stable（仅用于可选性能原型）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 模块

```text
main.py                         GUI / CLI 入口
gui_dnd.py                      当前 GUI、拖放、分析、修复、比对、导出
asset_diff.py                   目录扫描、字节比对、差异包导出
ue_parser.py                    UE 资产头、版本、引用与路径解析
asset_finder.py                 文件系统路径到 UE Content 路径的转换
config.py                       版本与 UI 默认值
test_parser.py                  解析器冒烟测试
test_asset_diff.py              差异功能单元测试
rust_diff_probe/                可选 Rust 性能原型
benchmarks/benchmark_diff.py    Python / Rust 对比基准
```

只维护 `gui_dnd.py` 这一套 GUI。Windows 原生拖放回退已内置其中，不依赖
额外的 `win_dnd` 模块。

## 核心流程

资产分析：

1. `UEAssetParser` 校验包头并提取版本、类型、关联文件。
2. `UEPathExtractor` 扫描可见路径与引用字符串。
3. GUI 将结果按目录层级展示。

目录修复：

1. 扫描资产并确认统一的旧 `/Game/.../` 前缀。
2. 默认复制目录；原位模式需明确确认。
3. 仅替换已识别前缀，并处理不等长字符串。

更新比对：

1. 按相对路径扫描 Old / New 支持文件。
2. 同路径文件先比较大小，再分块比较完整字节。
3. 导出新增、修改文件；删除项写入 `diff_manifest.json`。

## 测试

```powershell
python -m unittest -v test_asset_diff.py
python test_parser.py
python -m compileall -q main.py gui_dnd.py asset_diff.py ue_parser.py asset_finder.py config.py
cargo test --manifest-path rust_diff_probe\Cargo.toml
```

GUI 变更还需手工验证：启动、拖入文件和目录、目录修复安全确认、差异筛选、
导出清单及文件定位。

## 构建

```powershell
pyinstaller --clean --noconfirm build_exe.spec
```

输出：`dist\UEAssetPathFinder\UEAssetPathFinder.exe`

`build/`、`dist/`、`release/`、`__pycache__/` 和
`rust_diff_probe/target/` 都是可重建产物，不入库。

## 发布

1. 更新 `config.py`、`README.md`、`RELEASE_NOTES.md`。
2. 执行全部自动测试和 GUI 冒烟测试。
3. 重新构建 `dist\UEAssetPathFinder`。
4. 压缩为 `UEAssetPathFinder-vX.Y.Z-win64.zip`。
5. 创建 Git tag，并将压缩包上传至 GitHub Release。
