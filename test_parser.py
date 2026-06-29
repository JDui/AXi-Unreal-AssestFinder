#!/usr/bin/env python3
"""测试UE资产解析器"""

from ue_parser import UEAssetParser

parser = UEAssetParser()
info = parser.parse_file('test_asset.uasset')

if info:
    print("✓ UE资产解析成功")
    print(f"文件: {info.file_name}")
    print(f"类型: {info.asset_type}")
    print(f"版本: {info.ue_version}")
    print(f"文件大小: {info.properties.get('file_size', 'N/A')}")
    print(f"关联文件数: {len(info.related_files)}")
else:
    print("✗ 无法解析文件")
