"""
UE资产文件解析器
用于读取和分析虚幻引擎资产文件（.uasset、.umap 等）
"""

import os
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class UEAssetInfo:
    """UE资产信息"""
    file_path: str
    file_name: str
    file_size: int
    magic: int
    version: int
    ue_version: str
    asset_type: str
    asset_name: str
    related_files: List[str]
    imports: List[str]
    exports: List[str]
    properties: Dict[str, Any]
    raw_data: bytes = None


class UEAssetParser:
    """虚幻引擎资产文件解析器"""

    UASSET_MAGIC = 0x9E2A83C1

    UE_VERSION_MAP = {
        1: "UE 4.0 - 4.3",
        2: "UE 4.4 - 4.6",
        3: "UE 4.7 - 4.8",
        4: "UE 4.9 - 4.10",
        5: "UE 4.11 - 4.12",
        6: "UE 4.13 - 4.14",
        7: "UE 4.15 - 4.16",
        8: "UE 4.17 - 4.18",
        9: "UE 4.19 - 4.20",
        10: "UE 4.21 - 4.23",
        11: "UE 4.24 - 4.25",
        12: "UE 4.26 - 4.27",
        13: "UE 5.0 - 5.1",
        14: "UE 5.2+",
    }

    ASSET_TYPE_TRANSLATIONS = {
        "MapBuildDataRegistry": "地图构建数据注册表",
        "World": "关卡地图",
        "LevelSequence": "序列器",
        "MovieSceneSequence": "电影场景序列",
        "MaterialInstance": "材质实例",
        "Material": "材质",
        "Texture": "纹理",
        "Texture2D": "纹理",
        "TextureCube": "纹理立方体",
        "StaticMesh": "静态网格体",
        "SkeletalMesh": "骨架网格体",
        "Blueprint": "蓝图",
        "BlueprintGeneratedClass": "蓝图生成类",
        "AnimBlueprint": "动画蓝图",
        "AnimSequence": "动画序列",
        "WidgetBlueprint": "控件蓝图",
        "NiagaraSystem": "Niagara系统",
        "ParticleSystem": "粒子系统",
        "SoundWave": "声波",
        "DataTable": "数据表",
        "CurveTable": "曲线表",
        "Skeleton": "骨架",
        "Font": "字体",
        "UBulk": "批量数据",
        "UExp": "导出数据",
        "Asset": "资产",
        "Unknown": "未知",
    }

    def parse_file(self, file_path: str) -> Optional[UEAssetInfo]:
        """解析 UE 资产文件"""
        if not os.path.isfile(file_path):
            return None

        try:
            file_data = Path(file_path).read_bytes()
        except Exception as exc:
            print(f"读取文件失败: {exc}")
            return None

        if len(file_data) < 4:
            return None

        magic = struct.unpack('<I', file_data[0:4])[0]
        if magic != self.UASSET_MAGIC:
            return None

        try:
            info = UEAssetInfo(
                file_path=file_path,
                file_name=os.path.basename(file_path),
                file_size=os.path.getsize(file_path),
                magic=magic,
                version=0,
                ue_version="未知",
                asset_type="未知",
                asset_name="",
                related_files=[],
                imports=[],
                exports=[],
                properties={},
                raw_data=file_data,
            )

            version_info = self._parse_version_info(file_data)
            info.version = version_info.get("package_version", 0) or 0
            info.ue_version = self._format_ue_version_label(version_info, file_data)
            info.properties.update({
                "legacy_version": version_info.get("legacy_version"),
                "file_version_ue4": version_info.get("file_version_ue4"),
                "file_version_ue5": version_info.get("file_version_ue5"),
            })

            self._analyze_asset(info, file_data)
            self._find_related_files(file_path, info)
            return info

        except Exception as exc:
            print(f"解析文件时出错: {exc}")
            return None

    def _analyze_asset(self, info: UEAssetInfo, file_data: bytes) -> None:
        """分析资产内容"""
        file_name_lower = info.file_name.lower()

        if file_name_lower.endswith('.umap'):
            info.asset_type = self._extract_feature_text(file_data, info.file_path)
        elif file_name_lower.endswith('.uasset'):
            info.asset_type = self._extract_feature_text(file_data, info.file_path)
        elif file_name_lower.endswith('.ubulk'):
            info.asset_type = 'UBulk'
        elif file_name_lower.endswith('.uexp'):
            info.asset_type = 'UExp'

        info.asset_name = Path(info.file_name).stem

        info.properties.update({
            'file_size': f"{info.file_size / 1024:.2f} KB",
            'magic_number': hex(info.magic),
            'version': info.version,
        })

    def _detect_asset_type(self, file_data: bytes, file_path: Optional[str] = None) -> str:
        """从文件数据中检测资产类型（保留但不再默认使用）"""
        inferred = self._infer_asset_type_from_tokens(file_data, file_path)
        if inferred:
            return inferred

        if len(file_data) > 1024 * 1024:
            return 'Asset'

        return 'Unknown'

    def _read_int32(self, data: bytes, offset: int) -> Optional[int]:
        if offset + 4 > len(data):
            return None
        return struct.unpack('<i', data[offset:offset + 4])[0]

    def _read_uint32(self, data: bytes, offset: int) -> Optional[int]:
        if offset + 4 > len(data):
            return None
        return struct.unpack('<I', data[offset:offset + 4])[0]

    def _parse_version_info(self, file_data: bytes) -> Dict[str, Any]:
        version_info: Dict[str, Any] = {
            "legacy_version": None,
            "legacy_raw": None,
            "legacy_key": None,
            "file_version_ue4": 0,
            "file_version_ue5": 0,
            "package_version": 0,
        }

        legacy_version = self._read_int32(file_data, 4)
        if legacy_version is None:
            return version_info

        version_info["legacy_version"] = legacy_version

        if legacy_version >= 0:
            legacy_raw = self._read_uint32(file_data, 4) or 0
            legacy_key = (legacy_raw >> 16) & 0xFFFF
            version_info["legacy_raw"] = legacy_raw
            version_info["legacy_key"] = legacy_key
            version_info["package_version"] = legacy_raw
            return version_info

        candidates = [
            (12, self._read_int32(file_data, 12)),
            (16, self._read_int32(file_data, 16)),
            (20, self._read_int32(file_data, 20)),
            (24, self._read_int32(file_data, 24)),
        ]
        plausible = [(off, val) for off, val in candidates if val is not None and 0 < val < 10000]
        if plausible:
            version_info["file_version_ue4"] = plausible[0][1]
            if len(plausible) > 1:
                version_info["file_version_ue5"] = plausible[1][1]

        if version_info["file_version_ue5"] > 0:
            version_info["package_version"] = version_info["file_version_ue5"]
        elif version_info["file_version_ue4"] > 0:
            version_info["package_version"] = version_info["file_version_ue4"]

        return version_info

    def _extract_engine_version(self, file_data: bytes) -> Optional[str]:
        """从文件数据中提取引擎版本信息"""
        try:
            header = file_data[:min(len(file_data), 262144)]
            text = header.decode('latin1', errors='ignore')

            patterns = [
                r"\+\+UE(?P<major>[45])\+Release-(?P<ver>\d+\.\d+(?:\.\d+)?)",
                r"UE(?P<major>[45])\s*(?P<ver>\d+\.\d+(?:\.\d+)?)",
                r"UE(?P<major>[45])\.(?P<ver>\d+\.\d+(?:\.\d+)?)",
                r"EngineVersion\D+(?P<ver>\d+\.\d+(?:\.\d+)?)",
            ]

            for pattern in patterns:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    return f"UE {match.group('ver')}"

            if "UE5" in text:
                return "UE 5.x"
            if "UE4" in text:
                return "UE 4.x"
        except Exception:
            return None

        return None

    def _format_ue_version_label(self, version_info: Dict[str, Any], file_data: bytes) -> str:
        text_version = self._extract_engine_version(file_data)
        if text_version:
            return text_version

        ue5 = version_info.get("file_version_ue5", 0) or 0
        ue4 = version_info.get("file_version_ue4", 0) or 0
        if ue5 > 0:
            return f"UE5 (Package {ue5})"
        if ue4 > 0:
            return f"UE4 (Package {ue4})"

        legacy_key = version_info.get("legacy_key")
        if legacy_key in self.UE_VERSION_MAP:
            return self.UE_VERSION_MAP[legacy_key]

        return "未知"

    def _format_asset_type_display(self, asset_type: str) -> str:
        base = asset_type or "Unknown"
        zh = self.ASSET_TYPE_TRANSLATIONS.get(base)
        if zh:
            return f"{zh}({base})"
        return base

    def _extract_feature_text(self, file_data: bytes, file_path: Optional[str] = None) -> str:
        data = file_data[:min(len(file_data), 1048576)]
        tokens = self._collect_tokens(file_data)
        if not tokens:
            return "Unknown"

        candidates: Dict[str, int] = {}

        # 添加脚本类名
        try:
            text = data.decode('latin1', errors='ignore')
            for match in re.finditer(r"Class'/Script/([A-Za-z0-9_]+)/([A-Za-z0-9_]+)'", text):
                candidates[match.group(2)] = candidates.get(match.group(2), 0) + 3
            for match in re.finditer(r"/Script/([A-Za-z0-9_]+)/([A-Za-z0-9_]+)", text):
                candidates[match.group(2)] = candidates.get(match.group(2), 0) + 2
        except Exception:
            pass

        # 从可读字符串中筛选候选特征（只保留标识符风格文本）
        identifier_pattern = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,40}$")
        for token in tokens:
            if not identifier_pattern.match(token):
                continue
            if token.isupper() and len(token) <= 4:
                continue
            if len(set(token)) == 1:
                continue
            if token.lower() in {"none", "engine", "script", "game", "transient"}:
                continue
            weight = 1
            if token[0].isupper():
                weight += 1
            if token.startswith("MaterialExpression"):
                weight += 3
            if token.endswith("Sequence") or token.endswith("Blueprint"):
                weight += 2
            candidates[token] = candidates.get(token, 0) + weight

        # 按出现频率做一次加权
        for token in list(candidates.keys()):
            try:
                token_bytes = token.encode("ascii", errors="ignore")
                if token_bytes:
                    candidates[token] += min(data.count(token_bytes), 10)
            except Exception:
                pass

        # 路径信息辅助
        if file_path:
            name_upper = Path(file_path).stem.upper()
            for prefix in ("SM_", "SK_", "MI_", "M_", "MAT_", "T_", "TEX_", "BP_", "B_", "LS_", "SEQ_"):
                if name_upper.startswith(prefix):
                    candidates[prefix.rstrip("_")] = candidates.get(prefix.rstrip("_"), 0) + 4

        sorted_tokens = sorted(candidates.items(), key=lambda x: (-x[1], x[0]))
        top = [token for token, _ in sorted_tokens[:6]]
        if top:
            return ", ".join(top)
        if file_path:
            return Path(file_path).stem
        return "Unknown"

    def _extract_ascii_strings(self, data: bytes, min_len: int = 4, max_len: int = 80) -> List[str]:
        results: List[str] = []
        current = bytearray()
        for b in data:
            if 32 <= b <= 126:
                current.append(b)
                continue
            if min_len <= len(current) <= max_len:
                results.append(current.decode('ascii', errors='ignore'))
            current = bytearray()
        if min_len <= len(current) <= max_len:
            results.append(current.decode('ascii', errors='ignore'))
        return results

    def _collect_tokens(self, file_data: bytes) -> set[str]:
        data = file_data[:min(len(file_data), 524288)]
        tokens: set[str] = set()

        # 提取可读字符串（名称表/路径/类名）
        for value in self._extract_ascii_strings(data):
            tokens.add(value)

        # 提取脚本类名
        try:
            text = data.decode('latin1', errors='ignore')
            for match in re.finditer(r"Class'/Script/([A-Za-z0-9_]+)/([A-Za-z0-9_]+)'", text):
                tokens.add(match.group(2))
            for match in re.finditer(r"/Script/([A-Za-z0-9_]+)/([A-Za-z0-9_]+)", text):
                tokens.add(match.group(2))
        except Exception:
            pass

        return tokens

    def _infer_asset_type_from_tokens(self, file_data: bytes, file_path: Optional[str] = None) -> Optional[str]:
        data = file_data[:min(len(file_data), 1048576)]
        tokens = self._collect_tokens(file_data)
        if not tokens:
            return None

        def has_any(values: set[str]) -> bool:
            return any(value in tokens for value in values)

        name_upper = ""
        path_lower = ""
        if file_path:
            path_lower = file_path.replace("\\", "/").lower()
            name_upper = Path(file_path).stem.upper()

        # .umap：关卡地图
        if path_lower.endswith(".umap"):
            return "World"

        counts = {
            "MapBuildDataRegistry": data.count(b"MapBuildDataRegistry"),
            "World": data.count(b"World"),
            "Level": data.count(b"Level"),
            "MaterialInstance": data.count(b"MaterialInstance"),
            "Material": data.count(b"Material"),
            "MaterialExpression": data.count(b"MaterialExpression"),
            "MaterialFunction": data.count(b"MaterialFunction"),
            "Texture2D": data.count(b"Texture2D"),
            "TextureCube": data.count(b"TextureCube"),
            "Texture": data.count(b"Texture"),
            "StaticMesh": data.count(b"StaticMesh"),
            "SkeletalMesh": data.count(b"SkeletalMesh"),
            "AnimSequence": data.count(b"AnimSequence"),
            "AnimBlueprint": data.count(b"AnimBlueprint"),
            "BlueprintGeneratedClass": data.count(b"BlueprintGeneratedClass"),
            "Blueprint": data.count(b"Blueprint"),
            "NiagaraSystem": data.count(b"NiagaraSystem"),
            "ParticleSystem": data.count(b"ParticleSystem"),
            "SoundWave": data.count(b"SoundWave"),
            "DataTable": data.count(b"DataTable"),
            "CurveTable": data.count(b"CurveTable"),
            "Font": data.count(b"Font"),
            "LevelSequence": data.count(b"LevelSequence"),
            "MovieSceneSequence": data.count(b"MovieSceneSequence"),
        }

        # 强特征（脚本类 / 关键类名）
        if "MapBuildDataRegistry" in tokens or counts["MapBuildDataRegistry"] > 0 or (path_lower and "builtdata" in path_lower):
            return "MapBuildDataRegistry"

        if has_any({"LevelSequence", "MovieSceneSequence"}):
            return "LevelSequence"

        if counts["MaterialExpression"] >= 2:
            return "MaterialInstance"

        scores: Dict[str, float] = {
            "World": (1 if has_any({"World", "Level"}) else 0) * 8,
            "MapBuildDataRegistry": counts["World"] * 1 + counts["Level"] * 1,
            "MaterialInstance": counts["MaterialInstance"] * 8 + counts["Material"] * 4 + counts["MaterialFunction"] * 3 + counts["MaterialExpression"] * 2,
            "Texture": counts["Texture2D"] * 8 + counts["TextureCube"] * 6 + counts["Texture"] * 3,
            "StaticMesh": counts["StaticMesh"] * 8,
            "SkeletalMesh": counts["SkeletalMesh"] * 8,
            "AnimSequence": counts["AnimSequence"] * 7,
            "AnimBlueprint": counts["AnimBlueprint"] * 8,
            "BlueprintGeneratedClass": counts["BlueprintGeneratedClass"] * 8 + counts["Blueprint"] * 2,
            "NiagaraSystem": counts["NiagaraSystem"] * 8 + counts["ParticleSystem"] * 6,
            "SoundWave": counts["SoundWave"] * 8,
            "DataTable": counts["DataTable"] * 8,
            "CurveTable": counts["CurveTable"] * 8,
            "Font": counts["Font"] * 8,
            "LevelSequence": counts["LevelSequence"] * 8 + counts["MovieSceneSequence"] * 6,
        }

        # 路径与命名规则加权
        if path_lower:
            if "/maps/" in path_lower:
                scores["World"] += 12
            if "/staticmeshes/" in path_lower:
                scores["StaticMesh"] += 12
            if "/skeletalmeshes/" in path_lower:
                scores["SkeletalMesh"] += 12
            if "/textures/" in path_lower:
                scores["Texture"] += 10
            if "/material/" in path_lower or "/materials/" in path_lower:
                scores["MaterialInstance"] += 10
            if "/blueprints/" in path_lower:
                scores["BlueprintGeneratedClass"] += 10
            if "/sequences/" in path_lower or "/cinematics/" in path_lower:
                scores["LevelSequence"] += 10

        if name_upper.startswith("SM_"):
            scores["StaticMesh"] += 10
        if name_upper.startswith(("SK_", "SKEL_")):
            scores["SkeletalMesh"] += 10
        if name_upper.startswith(("T_", "TEX_")):
            scores["Texture"] += 10
        if name_upper.startswith(("MI_", "M_", "MAT_")):
            scores["MaterialInstance"] += 8
        if name_upper.startswith(("BP_", "B_")):
            scores["BlueprintGeneratedClass"] += 8
        if name_upper.startswith(("LS_", "SEQ_")):
            scores["LevelSequence"] += 8

        best = max(scores.items(), key=lambda x: x[1])
        if best[1] <= 0:
            return None

        return best[0]

    def _find_related_files(self, file_path: str, info: UEAssetInfo) -> None:
        """查找关联文件"""
        file_dir = os.path.dirname(file_path)
        file_stem = Path(file_path).stem

        try:
            for item in os.listdir(file_dir):
                item_path = os.path.join(file_dir, item)
                if os.path.isfile(item_path):
                    item_stem = Path(item).stem
                    if item_stem == file_stem and item != Path(file_path).name:
                        info.related_files.append(item)
        except Exception:
            pass

    def extract_import_references(self, info: UEAssetInfo) -> List[str]:
        """从资产中提取导入/引用信息"""
        imports: List[str] = []

        if info.raw_data:
            prefixes = [b'/Game/', b'/Engine/', b'/Script/']

            for prefix in prefixes:
                data = info.raw_data
                index = 0
                while True:
                    index = data.find(prefix, index)
                    if index == -1:
                        break

                    end = index
                    while end < len(data) and data[end] != 0:
                        end += 1

                    try:
                        path = data[index:end].decode('utf-8', errors='ignore')
                        if path not in imports and len(path) > len(prefix):
                            imports.append(path)
                    except Exception:
                        pass

                    index += 1

        return imports

    def get_asset_summary(self, info: UEAssetInfo) -> Dict[str, Any]:
        """获取资产摘要"""
        return {
            '文件名': info.file_name,
            '资产名': info.asset_name,
            '资产类型': info.asset_type,
            '文件大小': info.properties.get('file_size', 'N/A'),
            'UE版本': info.ue_version,
            '关联文件数': len(info.related_files),
            '关联文件': info.related_files,
        }


class UEPathExtractor:
    """从 UE 资产中提取路径信息"""

    @staticmethod
    def extract_asset_path(file_path: str) -> Optional[str]:
        """尝试从 uasset 中提取其在 UE 中的路径"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4096)

            if len(header) > 200:
                for i in range(100, len(header) - 20):
                    if header[i:i + 5] == b'/Game':
                        end = i
                        while end < len(header) and header[end] != 0:
                            end += 1
                        try:
                            path = header[i:end].decode('utf-8', errors='ignore')
                            if len(path) > 5 and '/' in path:
                                return path
                        except Exception:
                            pass
        except Exception:
            pass

        return None
