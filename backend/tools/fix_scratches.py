#!/usr/bin/env python3
"""
修复数据集中 scraches/scratches 类别拼写错误

问题：
    Roboflow raw Dataset 中 class 5 = "scraches"（拼写错误）, class 6 = "scratches"（正确拼写）
    两者实际指向同一种缺陷类型（scratches/划痕），需要合并。

修复内容：
    1. 将所有标注中 class_id=5 改为 6（合并 scraches → scratches）
    2. 重新编号：class 6 -> class 5（移除空位）
    3. 更新 data.yaml（nc: 7 -> nc: 6，移除 scraches）

使用方式：
    python backend/tools/fix_scratches.py datasets/ssdd
"""

import os
import sys
from pathlib import Path


def fix_scratches_labels(dataset_dir: str) -> dict:
    """
    修复标注文件中的 scraches/scratches 问题

    步骤：
        1. 将所有 class_id=5 替换为 class_id=6（合并 scraches → scratches）
        2. 将所有 class_id=6 降为 class_id=5（移除空位）
    """
    stats = {
        "files_scanned": 0,
        "files_changed": 0,
        "scraches_fixed": 0,   # class 5 → 6 的数量
        "scratches_renumbered": 0,  # class 6 → 5 的数量
    }

    labels_dir = Path(dataset_dir) / "labels"
    if not labels_dir.exists():
        print(f"[错误] 标注目录不存在: {labels_dir}")
        return stats

    for txt_file in sorted(labels_dir.rglob("*.txt")):
        stats["files_scanned"] += 1
        content = txt_file.read_text(encoding="utf-8").strip()

        if not content:
            continue

        new_lines = []
        file_changed = False

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) != 5:
                new_lines.append(line)
                continue

            try:
                class_id = int(parts[0])
            except ValueError:
                new_lines.append(line)
                continue

            # 步骤1：scraches (5) 合并到 scratches (6)
            if class_id == 5:
                parts[0] = "6"
                class_id = 6  # 更新以触发后续的 if
                stats["scraches_fixed"] += 1
                file_changed = True
            # 步骤2：scratches (6) 降为 5（填补空位）
            # 注意：必须是独立 if（不能 elif），因为步骤1的 scraches 已变为 6
            if class_id == 6:
                parts[0] = "5"
                stats["scratches_renumbered"] += 1
                file_changed = True

            new_lines.append(" ".join(parts))

        if file_changed:
            txt_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            stats["files_changed"] += 1

    return stats


def fix_data_yaml(dataset_dir: str):
    """更新 data.yaml：nc 7→6，移除 scraches"""
    yaml_path = Path(dataset_dir) / "data.yaml"
    if not yaml_path.exists():
        print(f"[警告] data.yaml 不存在: {yaml_path}")
        return

    content = yaml_path.read_text(encoding="utf-8")
    new_lines = []
    in_names = False
    class_idx = 0

    for line in content.split("\n"):
        stripped = line.strip()

        if stripped.startswith("nc:"):
            new_lines.append("nc: 6")
            continue

        if stripped.startswith("names:"):
            in_names = True
            new_lines.append(line)
            continue

        if in_names and stripped:
            if stripped[0].isdigit():
                parts = stripped.split(":", 1)
                old_id = int(parts[0].strip())
                name = parts[1].strip() if len(parts) > 1 else ""

                if name == "scraches":
                    # 跳过 scraches
                    continue
                elif old_id == 6:
                    # scratches 从 6 降为 5
                    new_lines.append(f"  {class_idx}: scratches")
                    class_idx += 1
                else:
                    new_lines.append(f"  {class_idx}: {name}")
                    class_idx += 1
                continue
            else:
                in_names = False
                new_lines.append(line)
                continue

        new_lines.append(line)

    yaml_path.write_text("\n".join(new_lines), encoding="utf-8")
    print(f"  data.yaml 已更新: nc=6, names=[crazing,inclusion,patches,pitted,rolled,scratches]")


def main():
    if len(sys.argv) < 2:
        print("用法: python backend/tools/fix_scratches.py <数据集目录>")
        print("示例: python backend/tools/fix_scratches.py datasets/ssdd")
        sys.exit(1)

    dataset_dir = sys.argv[1]
    if not os.path.isdir(dataset_dir):
        print(f"[错误] 目录不存在: {dataset_dir}")
        sys.exit(1)

    print("=" * 70)
    print(f"  修复 scraches → scratches: {dataset_dir}")
    print("=" * 70)

    stats = fix_scratches_labels(dataset_dir)
    print(f"\n  扫描文件: {stats['files_scanned']}")
    print(f"  修改文件: {stats['files_changed']}")
    print(f"  scraches(5→6): {stats['scraches_fixed']} 个")
    print(f"  scratches(6→5): {stats['scratches_renumbered']} 个")

    fix_data_yaml(dataset_dir)

    print("\n" + "=" * 70)
    print("  修复完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
