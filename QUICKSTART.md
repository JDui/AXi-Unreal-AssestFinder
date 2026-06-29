# 🎮 UE Asset Path Finder - 快速开始指南

## ⚡ 30秒快速上手

### 启动应用

#### 方式 1：直接启动（推荐）
```
双击运行: dist/UEAssetPathFinder.exe
```

#### 方式 2：使用启动脚本
```powershell
# Windows 批处理
run.bat

# PowerShell
.\run.ps1
```

#### 方式 3：开发者模式（需要 Python）
```bash
# 进入项目目录
cd UEASSESTFINDER

# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 启动应用
python main.py
```

## 🎯 三种使用方式

### 方式 1：拖拽分析（推荐）⭐

**最快的方法！**

```
1. 打开应用窗口
2. 打开文件资源管理器，找到 UE Content 中的 .uasset 文件
3. 拖拽文件到应用窗口
4. 查看分析结果
5. 点击 "✓ 复制路径" 复制 UE 内路径

完成！✓
```

### 方式 2：浏览文件

```
1. 点击 "📁 浏览文件" 按钮
2. 在文件浏览对话框中选择资产文件
3. 点击打开
4. 查看分析结果
5. 点击 "✓ 复制路径" 复制 UE 内路径

完成！✓
```

### 方式 3：扫描目录

```
1. 点击 "📂 浏览目录" 按钮
2. 在文件浏览对话框中选择包含资产的目录
3. 点击打开
4. 应用自动扫描并列出所有 UE 资产
5. 查看资产列表

完成！✓
```

## 📊 输出说明

分析资产时，您会看到：

| 部分 | 说明 | 例子 |
|------|------|------|
| 📍 **UE内路径** | 资产在 UE Content 中的路径 | `/Game/Characters/MyCharacter_BP` |
| 📄 **基本信息** | 文件名、大小、资产类型 | `Blueprint Class, 2.45 MB` |
| 🎮 **引擎信息** | UE 版本、版本代码、魔数 | `UE 5.2+, 1041, 0x9E2A83C1` |
| 📁 **关联文件** | 同名的二进制文件 | `.uexp, .ubulk` |
| 🔗 **导入/引用** | 资产引用的其他资产（前20条） | `/Script/Engine.Character` |

## 🎨 界面元素

```
┌─────────────────────────────────────────────────────┐
│  UE Asset Path Finder                           [_][□][×] │
├─────────────────────────────────────────────────────┤
│                                                       │
│  拖拽资产到此，或使用下面的按钮                       │
│                                                       │
│  [🔍 分析资产]  [📁 浏览文件]  [📂 浏览目录]         │
│                                                       │
│  ╔═══════════════════════════════════════════════╗  │
│  ║ 分析结果将显示在这里                          ║  │
│  ║ ...                                           ║  │
│  ╚═══════════════════════════════════════════════╝  │
│                                                       │
│  [✓ 复制路径]                                       │
│                                                       │
│  准备就绪                                              │
└─────────────────────────────────────────────────────┘
```

## 💡 使用技巧

### 快速复制路径
```
1. 分析完资产后
2. 点击 "✓ 复制路径" 按钮
3. 打开 UE Editor 的搜索框 (Ctrl+F)
4. 粘贴路径进行搜索
5. 快速定位资产
```

### 批量查看资产
```
1. 点击 "📂 浏览目录" 按钮
2. 选择包含多个资产的目录
3. 应用自动列出所有资产
4. 快速了解目录结构
```

### 检查资产版本
```
1. 拖拽资产分析
2. 查看 "🎮 引擎信息" 部分
3. 立即看到 UE 版本 (UE 4.x 或 UE 5.x)
4. 检查兼容性
```

## ⚙️ 功能按钮详解

| 按钮 | 功能 | 快捷说明 |
|-----|------|---------|
| 🔍 分析资产 | 打开文件浏览器选择资产 | 同「浏览文件」 |
| 📁 浏览文件 | 选择单个资产文件进行分析 | 支持 .uasset, .umap 等 |
| 📂 浏览目录 | 扫描目录中的所有资产 | 自动列出全部资产 |
| ✓ 复制路径 | 将 UE 内路径复制到剪贴板 | 可直接粘贴使用 |
| 🔎 搜索 | 在结果中搜索关键词 | 快速查找信息 |

## 🔍 实际示例

### 例 1：查找 Character 资产路径

```
操作步骤：
1. 打开应用
2. 拖拽 Character_BP.uasset 到窗口
3. 查看结果

输出：
📍 UE内路径: /Game/Characters/Character_BP
📄 基本信息: Blueprint Class, 2.45 MB
🎮 引擎信息: UE 5.2+

复制 UE 内路径后，在 UE Editor 中搜索即可定位！✓
```

### 例 2：检查资产版本兼容性

```
操作步骤：
1. 拖拽资产文件
2. 查看 "🎮 引擎信息" 部分

输出：
虚幻引擎版本: UE 4.27
版本代码: 504

→ 这个资产是 UE 4 版本的，如果项目是 UE 5，需要迁移！
```

### 例 3：批量查看资产信息

```
操作步骤：
1. 点击 "📂 浏览目录"
2. 选择 Content/Characters 目录
3. 应用自动扫描

输出：
Character_BP.uasset
SK_Character_01.uasset
SK_Character_02.uasset
Mat_Character_Skin.uasset
...

→ 快速了解目录中的所有资产！
```

## 🐛 常见问题排查

### Q: 应用无法启动
**A:** 
- 确保 Windows 7+ 系统
- 尝试以管理员身份运行
- 检查磁盘空间充足

### Q: 拖拽功能无效
**A:**
- 确保文件是有效的 UE 资产 (.uasset 或 .umap)
- 先点击应用窗口获得焦点
- 使用「浏览文件」按钮作为替代

### Q: 路径显示不正确
**A:**
- 确保资产在 Content 文件夹中
- 检查文件是否损坏
- 尝试在 UE Editor 中打开验证

### Q: 版本识别错误
**A:**
- 可能是特殊的 UE 版本
- 查看「版本代码」自行判断
- 确认文件来自标准 UE 版本

## 📚 了解更多

需要详细说明？查看项目文档：

- **[README.md](README.md)** - 项目完整介绍
- **[FEATURES.md](FEATURES.md)** - 功能详解
- **[DISTRIBUTION.md](DISTRIBUTION.md)** - 分发指南
- **[COMPLETION_REPORT.md](COMPLETION_REPORT.md)** - 技术报告

## ✨ 就这么简单！

```
拖拽文件 → 自动分析 → 一键复制 → UE Editor 中使用

完成！✓
```

---

**立即开始：** 运行 `dist/UEAssetPathFinder.exe` 或 `run.bat` 🚀
2. 选择要分析的UE资产文件
3. 自动分析并显示结果

#### 查看分析结果
分析结果包含以下部分：
```
【基本信息】
- 文件名: character.uasset
- 文件大小: 2048.50 KB
- 资产类型: 蓝图

【引擎信息】
- UE版本: UE 4.27
- 版本号: 0x1f1
- 魔数: 0x9e2a83c1

【关联文件】
- character.uexp
- character.ubulk

【导入引用】
- /Game/Materials/CharacterMaterial
- /Game/Meshes/BaseMesh
- /Engine/EngineMaterials/DefaultMaterial

【UE内路径】
- /Game/Characters/Character_BP
```

### 标签页2: 路径转换

#### 单文件转换
1. 选择"路径转换"标签页
2. 在"单个文件转换"区域输入或浏览选择文件
3. 点击"转换"按钮
4. 在树形视图中查看结果
5. 选中项目后点击"复制路径"复制到剪贴板

#### 批量转换
1. 在"批量转换"区域选择一个包含资产的目录
2. 点击"搜索"按钮
3. 工具会搜索该目录下所有UE资产
4. 结果按资产类型自动分组显示
5. 可选中多个项目后批量复制

## 🔧 运行模式

### 1. GUI模式（默认，推荐）
```bash
python main.py
```
优点：
- 图形界面直观
- 支持拖拽
- 实时反馈
- 易于批量操作

### 2. CLI交互模式
```bash
python main.py -cli
```
菜单选项：
```
1. 转换单个文件路径
2. 批量转换文件路径
3. 搜索目录中的资产
4. 退出
```

### 3. 快速转换模式
```bash
# 快速转换单个文件
python main.py "D:\Assets\character.fbx"

# 快速搜索目录
python main.py "D:\Assets"
```
输出：JSON格式的转换结果

## 📋 支持的文件类型

### 资产分析支持
- `.uasset` - 虚幻资产主文件
- `.umap` - 虚幻地图/关卡文件
- `.uexp` - 资产导出数据
- `.ubulk` - 资产数据块

### 路径转换支持
- **贴图**: .png, .tga, .jpg, .jpeg
- **网格**: .fbx, .usmf
- **蓝图**: 包含"blueprint"或"bp_"的文件
- **材质**: 包含"material"的文件
- **动画**: 包含"animation"或"anim"的文件
- **音效**: .wav, .mp3
- **粒子**: .umpc, 包含"particle"的文件
- **其他**: 自动分类

## 🎓 示例工作流

### 示例1: 分析现有资产

```
步骤1: 启动工具
       python main.py

步骤2: 选择"资产分析"标签页

步骤3: 拖拽 "E:\UEProject\Content\Characters\BP_Hero.uasset" 文件

步骤4: 等待分析完成，查看：
       - UE版本: UE 4.27
       - 资产类型: 蓝图
       - 关联文件: BP_Hero.uexp, BP_Hero.ubulk
       - 导入引用: 
         * /Game/Materials/M_CharacterBody
         * /Game/Meshes/SK_CharacterSkeleton
```

### 示例2: 转换导入资产

```
步骤1: 启动工具

步骤2: 选择"路径转换"标签页

步骤3: 在"单个文件转换"中选择：
       "D:\NewAssets\my_texture.png"

步骤4: 点击"转换"，查看结果：
       - 文件名: my_texture.png
       - 资产类型: 贴图
       - 推荐目录: Textures
       - UE路径: /Game/Textures/my_texture.png

步骤5: 点击"复制路径"

步骤6: 在虚幻编辑器中粘贴该路径进行导入
```

### 示例3: 批量处理资产库

```
步骤1: 启动工具

步骤2: 选择"路径转换"标签页

步骤3: 在"批量转换"中选择目录：
       "D:\GameAssets"

步骤4: 点击"搜索"，工具会找到并分类：
       【贴图文件】(12个)
       ├─ diffuse_01.png → /Game/Textures/diffuse_01.png
       ├─ diffuse_02.png → /Game/Textures/diffuse_02.png
       └─ ...
       
       【网格文件】(5个)
       ├─ character.fbx → /Game/Characters/character.fbx
       └─ ...
       
       【蓝图文件】(3个)
       ├─ BP_Enemy.uasset → /Game/Blueprints/BP_Enemy.uasset
       └─ ...

步骤5: 全选所有"蓝图文件"，点击"复制路径"

步骤6: 在虚幻编辑器中使用这些路径
```

## ⚙️ 高级配置

### 修改默认搜索目录

编辑 `config.py`:
```python
DEFAULT_SEARCH_PATHS = [
    "D:\\MyAssets",
    "E:\\GameContent"
]
```

### 修改默认项目路径

编辑 `config.py`:
```python
DEFAULT_PROJECT_PATH = "D:\\MyUEProject"
```

## 🐛 常见问题

### Q1: 拖拽功能不工作？
A: 确保已安装 tkinterdnd2:
```bash
pip install tkinterdnd2
```
如果问题持续，使用"浏览"按钮替代。

### Q2: 无法识别某个资产文件？
A: 可能原因：
- 文件不是有效的UE资产文件
- 文件损坏或不完整
- 使用了非标准格式

尝试用虚幻编辑器检查该文件的有效性。

### Q3: 版本识别不准确？
A: 某些特殊编译的虚幻版本可能无法精确识别。
可以通过文件的版本号和文件大小来手动判断。

### Q4: 如何处理非常大的资产文件？
A: 对于超过1GB的文件：
- 使用CLI模式可能更快
- 确保系统有足够的可用内存
- 分割大型资产后再处理

## 📞 获取帮助

查看详细文档：
- `README.md` - 功能概览
- `ASSET_ANALYSIS.md` - 资产分析详解
- `FEATURES.md` - 完整功能说明

## 📝 版本信息

- **工具版本**: 1.0
- **Python要求**: 3.7+
- **支持UE版本**: 4.0 - 5.2+
- **最后更新**: 2026年1月29日

---

**提示**: 建议首先运行 `python main.py` 启动GUI，然后拖拽测试资产文件 `test_asset.uasset` 来体验功能！
