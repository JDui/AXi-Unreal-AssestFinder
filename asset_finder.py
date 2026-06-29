"""
UE资产路径转换工具
用于将文件系统路径转换为UE Content文件夹中的真实路径
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, List


class UEAssetFinder:
    """虚幻引擎资产路径查找器"""
    
    # 常见UE资产文件扩展名及其对应的内容类型
    ASSET_TYPES = {
        '.uasset': '资产文件',
        '.umap': '关卡/地图',
        '.png': '贴图',
        '.tga': '贴图',
        '.jpg': '贴图',
        '.jpeg': '贴图',
        '.fbx': '骨骼网格体',
        '.usmf': '骨骼网格体',
        '.uexp': '资产导出',
        '.ubulk': '资产数据',
        '.upk': '包文件',
        '.umac': '宏资产',
    }
    
    # UE Content文件夹的默认子目录
    CONTENT_DIRECTORIES = [
        'Characters',    # 角色
        'Meshes',        # 网格
        'Materials',     # 材质
        'Textures',      # 贴图
        'Effects',       # 特效
        'Animations',    # 动画
        'Sounds',        # 音频
        'Blueprints',    # 蓝图
        'Maps',          # 地图
        'Widgets',       # UI控件
        'DataTables',    # 数据表格
        'Particles',     # 粒子
        'Levels',        # 关卡
    ]
    
    def __init__(self, project_path: Optional[str] = None):
        """
        初始化资产查找器
        
        Args:
            project_path: UE项目根目录路径（可选）
        """
        self.project_path = project_path
        self.content_path = None
        
        if project_path:
            self.content_path = os.path.join(project_path, 'Content')
    
    def get_asset_type(self, file_path: str) -> str:
        """
        获取资产类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            资产类型描述
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        return self.ASSET_TYPES.get(ext, '未知类型')
    
    def path_to_ue_content_path(self, file_path: str) -> Optional[Dict[str, str]]:
        """
        将文件路径转换为UE Content路径
        
        Args:
            file_path: 原始文件路径
            
        Returns:
            包含转换结果的字典，如果无法转换则返回None
        """
        # 规范化路径
        file_path = os.path.normpath(file_path)
        
        # 获取文件名和扩展名
        file_name = os.path.basename(file_path)
        _, ext = os.path.splitext(file_name)
        asset_type = self.get_asset_type(file_path)
        
        # 尝试智能识别应该放在哪个目录
        suggested_dir = self._suggest_content_directory(file_name, ext)
        
        # 构建UE路径
        ue_path = f"/Game/{suggested_dir}/{file_name}"
        
        return {
            'original_path': file_path,
            'file_name': file_name,
            'file_extension': ext,
            'asset_type': asset_type,
            'suggested_directory': suggested_dir,
            'ue_content_path': ue_path,
            'relative_content_path': f"Content/{suggested_dir}/{file_name}"
        }
    
    def _suggest_content_directory(self, file_name: str, extension: str) -> str:
        """
        根据文件名和扩展名建议应该放在哪个Content子目录
        
        Args:
            file_name: 文件名
            extension: 文件扩展名
            
        Returns:
            建议的目录名
        """
        file_name_lower = file_name.lower()
        
        # 根据扩展名分类
        if extension.lower() in ['.png', '.tga', '.jpg', '.jpeg']:
            return 'Textures'
        elif extension.lower() in ['.fbx', '.usmf']:
            return 'Meshes'
        elif extension.lower() == '.umap':
            return 'Maps'
        elif 'material' in file_name_lower or extension.lower() == '.umat':
            return 'Materials'
        elif 'character' in file_name_lower or 'char' in file_name_lower:
            return 'Characters'
        elif 'particle' in file_name_lower or extension.lower() == '.umpc':
            return 'Particles'
        elif 'animation' in file_name_lower or 'anim' in file_name_lower or extension.lower() == '.uanim':
            return 'Animations'
        elif 'sound' in file_name_lower or 'audio' in file_name_lower or extension.lower() in ['.wav', '.mp3']:
            return 'Sounds'
        elif 'blueprint' in file_name_lower or 'bp_' in file_name_lower or extension.lower() == '.ublueprint':
            return 'Blueprints'
        elif 'widget' in file_name_lower or 'ui' in file_name_lower:
            return 'Widgets'
        elif 'effect' in file_name_lower or 'vfx' in file_name_lower:
            return 'Effects'
        else:
            # 默认放在根Content目录
            return ''
    
    def batch_convert_paths(self, file_paths: List[str]) -> List[Dict[str, str]]:
        """
        批量转换多个文件路径
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            转换结果列表
        """
        results = []
        for file_path in file_paths:
            result = self.path_to_ue_content_path(file_path)
            if result:
                results.append(result)
        return results
    
    def find_assets_in_directory(self, directory: str) -> List[Dict[str, str]]:
        """
        查找目录中的所有UE资产文件
        
        Args:
            directory: 目录路径
            
        Returns:
            找到的资产信息列表
        """
        results = []
        if not os.path.isdir(directory):
            return results
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file)
                
                if ext.lower() in self.ASSET_TYPES:
                    result = self.path_to_ue_content_path(file_path)
                    if result:
                        results.append(result)
        
        return results
