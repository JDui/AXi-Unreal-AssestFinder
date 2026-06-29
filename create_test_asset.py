import struct

# 创建一个简单的模拟UE资产文件用于测试
magic = 0x9E2A83C1  # UE资产魔数
version = 0x000C0001  # UE 4.27版本
custom_version = 0

# 创建二进制数据
data = struct.pack('<I', magic)  # 魔数
data += struct.pack('<I', version)  # 版本
data += struct.pack('<I', custom_version)  # 自定义版本

# 添加一些示例数据和路径引用
data += b'\x00' * 100  # 填充

# 添加一些资产路径用于演示
data += b'/Game/Blueprints/ExampleBP\x00'
data += b'/Game/Materials/BaseMaterial\x00'
data += b'/Engine/EngineMaterials/DefaultMaterial\x00'

# 添加更多填充
data += b'\x00' * 200

# 写入文件
with open('test_asset.uasset', 'wb') as f:
    f.write(data)

print(f"✓ 创建测试资产文件: test_asset.uasset ({len(data)} 字节)")
