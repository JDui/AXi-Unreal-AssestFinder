# UE Asset Path Finder

一个用于查找虚幻引擎(UE)资产文件真实路径的工具。

## 功能

- **UE资产分析**: 读取和分析 .uasset、.umap 等UE资产文件
  - 识别资产属于的UE版本
  - 显示资产文件大小和类型
  - 提取关联文件列表
  - 解析导入/引用信息
- **路径转换**: 将文件系统路径转换为UE Content路径
- **批量转换**: 同时处理多个文件
- **目录扫描**: 搜索指定目录中的所有UE资产
- **拖拽分析**: 直接拖拽资产文件进行分析
- **智能分类**: 根据文件类型自动分类

## 支持的资产类型

- **贴图**: .png, .tga, .jpg, .jpeg
- **网格**: .fbx, .usmf
- **关卡**: .umap
- **材质**: .umat, 包含"material"的文件
- **角色**: 包含"character"或"char"的文件
- **动画**: 包含"animation"或"anim"的文件
- **粒子**: .umpc, 包含"particle"的文件
- **音频**: .wav, .mp3, 包含"sound"或"audio"的文件
- **蓝图**: .ublueprint, 包含"blueprint"或"bp_"的文件

## 快速开始

### GUI模式（推荐）
```bash
python main.py
```

### 命令行模式
```bash
python main.py -cli              # 交互式命令行模式
python main.py "path/to/file.fbx"    # 快速转换单个文件
python main.py "path/to/directory"   # 快速转换目录
```

## 使用示例

### GUI模式（推荐）

启动应用：
```bash
python main.py
```

**资产分析标签页：**
- 拖拽UE资产文件到拖拽区进行分析
- 或点击"浏览"按钮选择文件
- 查看详细的分析结果，包括：
  - UE版本信息
  - 文件大小和类型
  - 关联文件列表
  - 导入/引用信息
  - 资产在UE中的路径（如果可解析）

**路径转换标签页：**
- 单文件转换：输入文件路径，自动转换为UE Content路径
- 批量转换：输入目录，搜索所有UE资产并转换路径
- 结果按资产类型分组显示
- 一键复制UE路径到剪贴板

### 命令行模式

**交互式命令行：**
```bash
python main.py -cli
```

菜单选项：
1. 转换单个文件路径
2. 批量转换文件路径
3. 搜索目录中的资产
4. 退出

**快速转换：**
```bash
python main.py "C:\Assets\character_model.fbx"
```

输出格式（JSON）：
```json
{
  "original_path": "C:\\Assets\\character_model.fbx",
  "file_name": "character_model.fbx",
  "file_extension": ".fbx",
  "asset_type": "骨骼网格体",
  "suggested_directory": "Characters",
  "ue_content_path": "/Game/Characters/character_model.fbx",
  "relative_content_path": "Content/Characters/character_model.fbx"
}
```

## 项目结构

```
├── main.py              # 主程序入口和交互逻辑
├── asset_finder.py      # 资产路径转换核心逻辑
├── config.py            # 配置文件
├── requirements.txt     # Python依赖
├── README.md           # 本文件
└── .github/
    └── copilot-instructions.md  # 项目文档
```

## 系统要求

- Python 3.7 或更高版本
- Windows/Mac/Linux

## 安装与运行

1. 克隆或下载项目
2. 进入项目目录
3. 安装依赖（如果需要）：
   ```bash
   pip install -r requirements.txt
   ```
4. 运行主程序：
   ```bash
   python main.py
   ```

## 文件位置与路径含义

### UE资产分析
当您分析UE资产文件时，将看到：

- **UE版本**: 该资产文件属于的虚幻引擎版本
- **文件信息**: 文件大小、魔数等技术信息
- **资产类型**: 识别的资产类型（网格、贴图、蓝图等）
- **关联文件**: 与该资产相关的其他文件（.ubulk、.uexp等）
- **导入引用**: 该资产引用的其他资产路径
- **UE内路径**: 资产在虚幻引擎项目中的位置

### 路径转换
- **原始路径**: 您选择或拖拽的文件在计算机文件系统中的完整路径
- **相对路径**: 该文件在UE项目Content文件夹中的相对路径
- **UE Content路径**: 虚幻引擎识别的标准格式路径（/Game/...）

## 工作原理

UEAssetFinder 类通过以下方式转换路径：

1. **文件分析**: 分析文件扩展名和文件名
2. **类型识别**: 根据扩展名和命名规则识别资产类型
3. **目录建议**: 根据资产类型建议放置在Content文件夹的哪个子目录
4. **路径构建**: 生成标准的UE Content路径格式 (/Game/DirectoryName/FileName)

## 常见用途

- **资产导入前验证**: 确认资产应该放在哪个目录
- **资产管理**: 快速定位资产在项目中的位置
- **批量资产处理**: 同时处理多个资产的路径转换
- **项目结构规范**: 帮助遵循UE项目的标准结构
- **快速拖拽查询**: 拖拽文件立即查看其UE路径信息

## 注意事项

- 工具无需连接到实际的UE项目即可工作
- 文件不需要真实存在，仅根据路径和扩展名进行转换
- 建议的目录遵循虚幻引擎的标准最佳实践
- 您可以根据项目需求自定义目录名称
