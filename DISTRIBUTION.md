# UE Asset Path Finder - 快速开始

## 📥 安装和运行

### 方式一：直接运行（推荐）
1. 打开 `dist` 文件夹
2. 双击 `UEAssetPathFinder.exe` 即可运行
3. 无需安装任何依赖

### 方式二：开发者模式
```powershell
# 进入项目目录
cd D:\UEProject\UEASSESTFINDER

# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 运行应用（GUI模式）
python main.py

# 或者运行 CLI 模式
python main.py -cli
```

## 🎮 使用示例

### 示例 1：拖拽资产分析
```
1. 启动 UEAssetPathFinder.exe
2. 打开 Windows 文件资源管理器
3. 找到 UE 项目的 Content 文件夹
4. 拖拽一个 .uasset 文件到应用窗口
5. 查看分析结果
```

### 示例 2：浏览并选择资产
```
1. 点击 "📁 浏览文件" 按钮
2. 导航到 Content 文件夹
3. 选择要分析的资产
4. 应用自动分析并显示结果
```

### 示例 3：批量扫描目录
```
1. 点击 "📂 浏览目录" 按钮
2. 选择包含资产的目录
3. 应用列出所有找到的 UE 资产
```

## 📊 输出示例

```
═══════════════════════════════════════════════════════════════
         📍 UE Asset Analysis - Character_BP.uasset
═══════════════════════════════════════════════════════════════

📍 UE内路径:
    /Game/Characters/Character_BP

📄 基本信息:
    文件名: Character_BP.uasset
    文件大小: 2.45 MB
    资产类型: Blueprint Class

🎮 引擎信息:
    虚幻引擎版本: UE 5.2+
    版本代码: 1041
    魔数: 0x9E2A83C1

📁 关联文件:
    - Character_BP.uexp
    - Character_BP.ubulk

🔗 导入/引用 (前20条):
    1. /Script/Engine.Actor
    2. /Script/Engine.Character
    3. /Game/Meshes/SK_Character
    ... 更多导入信息
```

## 🔍 常见问题

### Q: 提示 "无法识别的资产文件"
**A:** 确保：
- 文件是有效的 UE 资产（.uasset）
- 文件未被损坏
- 文件来自受支持的 UE 版本

### Q: 拖拽不工作
**A:** 
- 尝试重新启动应用程序
- 确保使用了最新的 EXE 版本
- 检查 Windows 是否为最新版本

### Q: 路径显示不正确
**A:**
- 确认资产确实在 Content 文件夹中
- 检查文件路径中是否有特殊字符
- 尝试使用 "浏览文件" 功能

## 📦 文件结构

```
dist/
└── UEAssetPathFinder.exe    (单个可执行文件)

项目源代码/
├── main.py                   (入口点)
├── gui_dnd.py               (GUI 和拖拽功能)
├── ue_parser.py             (资产解析器)
├── asset_finder.py          (路径转换工具)
├── config.py                (配置管理)
└── ...其他文件
```

## 🚀 性能说明

- **启动时间**: < 2秒
- **资产分析速度**: < 100ms（大多数资产）
- **内存占用**: ~50MB
- **界面响应**: 流畅

## ✅ 测试清单

- [x] GUI 正常启动
- [x] 拖拽功能正常工作
- [x] 资产分析准确
- [x] 版本识别正确
- [x] 路径转换准确
- [x] 复制功能正常
- [x] 文件浏览器集成正常

## 🔄 版本历史

### v1.0 (Current Release)
- 完整的资产分析功能
- 改进的版本和类型检测
- 美化的 Material Design 界面
- 拖拽支持
- 单文件可执行程序

---

**需要帮助？** 检查项目中的 `README.md` 或 `QUICKSTART.md` 了解更多详情。
