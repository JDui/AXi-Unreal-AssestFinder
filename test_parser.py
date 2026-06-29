#!/usr/bin/env python3
"""Smoke test for the UE asset parser."""

from ue_parser import UEAssetParser


def main():
    parser = UEAssetParser()
    info = parser.parse_file("test_asset.uasset")

    if info:
        print("[OK] UE asset parsed")
        print(f"file: {info.file_name}")
        print(f"type: {info.asset_type}")
        print(f"version: {info.ue_version}")
        print(f"size: {info.properties.get('file_size', 'N/A')}")
        print(f"related files: {len(info.related_files)}")
        return

    print("[WARN] asset could not be parsed")


if __name__ == "__main__":
    main()
