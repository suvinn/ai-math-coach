"""
원본 페이지 PNG에서 보기(선택지) 이미지 영역을 크롭해서 저장하는 스크립트.
rebuild_options.py 실행 결과(merged_problems_fixed.csv)의 `image_regions` 컬럼을 사용한다.

전제: JSON bbox 좌표계 == PNG 픽셀 좌표계 (1:1). 001610 샘플로 확인됨
      (bbox 최대값들이 PNG 실제 크기(470x559)와 거의 일치).
      혹시 일부 페이지에서 안 맞으면 --scale 옵션으로 보정 가능.

사용법:
    python crop_option_images.py \
        --csv merged_problems_fixed.csv \
        --png-dir data/raw/TS_06.중학교_2학년_01.객관식 \
        --out-dir data/assets/option_images

출력:
    {out-dir}/{source_data_name}/{class_name}_{idx}.png  (문제별 폴더에 영역별 이미지)
    {out-dir}/manifest.csv  -> problem_assets 테이블에 그대로 적재 가능한 매니페스트
        (source_data_name, class_name, file_path, bbox_x1, bbox_y1, bbox_x2, bbox_y2)
"""

import argparse
import ast
import json
import csv
from pathlib import Path

import pandas as pd
from PIL import Image

PADDING = 4  # 잘릴 때 글자가 너무 딱 붙지 않게 여백(px)


def find_png(png_dir: Path, source_data_name: str):
    # 보통 png-dir 바로 아래 있지만, 혹시 하위 폴더로 나뉘어 있을 수도 있으니 재귀 검색
    direct = png_dir / f"{source_data_name}.png"
    if direct.exists():
        return direct
    matches = list(png_dir.rglob(f"{source_data_name}.png"))
    return matches[0] if matches else None


def crop_and_save(img: Image.Image, bbox, out_path: Path, scale: float = 1.0):
    x1, y1, x2, y2 = bbox
    x1, y1, x2, y2 = x1 * scale, y1 * scale, x2 * scale, y2 * scale
    w, h = img.size
    x1 = max(0, x1 - PADDING)
    y1 = max(0, y1 - PADDING)
    x2 = min(w, x2 + PADDING)
    y2 = min(h, y2 + PADDING)
    if x2 <= x1 or y2 <= y1:
        return False
    cropped = img.crop((x1, y1, x2, y2))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(out_path)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--png-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--scale", type=float, default=1.0, help="JSON bbox -> PNG 픽셀 환산 배율 (기본 1:1)")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    png_dir = Path(args.png_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = df[df["option_type"] == "mixed_with_image"]
    print(f"이미지 크롭 대상: {len(targets)}개")

    manifest_rows = []
    n_ok, n_missing_png, n_no_regions, n_crop_fail = 0, 0, 0, 0

    for _, row in targets.iterrows():
        name = row["source_data_name"]
        regions_raw = row.get("image_regions")
        if pd.isna(regions_raw) or not str(regions_raw).strip():
            n_no_regions += 1
            continue

        try:
            regions = json.loads(regions_raw)
        except (json.JSONDecodeError, TypeError):
            try:
                regions = ast.literal_eval(regions_raw)
            except Exception:
                n_no_regions += 1
                continue

        png_path = find_png(png_dir, name)
        if png_path is None:
            n_missing_png += 1
            continue

        img = Image.open(png_path).convert("RGB")

        for i, region in enumerate(regions):
            bbox = region.get("bbox")
            class_name = region.get("class_name", "region")
            if not bbox:
                continue
            safe_class = class_name.replace("(", "_").replace(")", "")
            out_path = out_dir / name / f"{safe_class}_{i}.png"
            ok = crop_and_save(img, bbox, out_path, scale=args.scale)
            if ok:
                n_ok += 1
                manifest_rows.append({
                    "source_data_name": name,
                    "class_name": class_name,
                    "file_path": str(out_path),
                    "bbox_x1": bbox[0], "bbox_y1": bbox[1],
                    "bbox_x2": bbox[2], "bbox_y2": bbox[3],
                })
            else:
                n_crop_fail += 1

    manifest_path = out_dir / "manifest.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "source_data_name", "class_name", "file_path",
            "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2",
        ])
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"크롭 성공: {n_ok}")
    print(f"원본 PNG 못 찾음: {n_missing_png}")
    print(f"image_regions 비어있음/파싱 실패: {n_no_regions}")
    print(f"크롭 실패(bbox 이상): {n_crop_fail}")
    print(f"매니페스트 저장: {manifest_path}")


if __name__ == "__main__":
    main()