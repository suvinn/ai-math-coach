"""
원본 JSON(class_name 기반) -> question_with_options / question_image_bbox 재생성 백필 스크립트

사용법:
    python rebuild_options.py --json-dir /path/to/raw_jsons --csv merged_problems.csv --out merged_problems_fixed.csv

동작:
    1. raw_dir 안의 {source_data_name}.json 을 읽는다.
    2. class_name 이 "문항(텍스트|이미지)", "정답(텍스트|이미지)", "오답(텍스트|이미지)" 인
       모든 class_info_list 항목을 모은다. (해설은 제외 — 보기에 해당 안 함)
    3. bbox 의 y좌표(상단 기준) -> x좌표 순으로 정렬해 text_description 을 이어붙인다.
    4. question_image_bbox 는 위 항목들 bbox 의 합집합(min/max)으로 재계산한다.
    5. "(이미지)" 접미사가 붙은 class_name 이 하나라도 있으면 option_type = "mixed_with_image",
       전부 "(텍스트)"면 option_type = "text" 로 표시한다.
    6. 정답(텍스트/이미지) 항목만 따로 모아 recovered_answer 를 만들고,
       기존 answer 컬럼과 일치하는지 검증해 answer_match 플래그를 남긴다(검수 우선순위용).
    7. 기존에 question_with_options 가 이미 차 있던 행(23%)은 건드리지 않는다.
"""

import argparse
import json
import re
from pathlib import Path

import pandas as pd

OPTION_CLASS_PREFIXES = ("문항", "정답", "오답")
ANSWER_CLASS_PREFIX = "정답"


def load_problem_json(json_path: Path) -> dict:
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def split_bundled_choices(item):
    """
    '① $-6ab$ ② $6ab$ ④ $6a^2b$ ⑤ ...' 처럼 한 bbox/text 안에 여러 번호가 뭉쳐
    들어온 경우(오답 클래스에서 흔함), 번호 경계로 쪼개 별도 항목 리스트로 반환.
    번호가 2개 미만이면 원본 그대로 1개짜리 리스트 반환.
    같은 bbox를 그대로 공유시켜 정렬 시 같은 줄(원래 위치)로 취급되게 한다.
    """
    text = item["text"]
    positions = [i for i, ch in enumerate(text) if ch in CIRCLED_DIGITS]
    if len(positions) < 2:
        return [item]

    pieces = []
    for k, start in enumerate(positions):
        end = positions[k + 1] if k + 1 < len(positions) else len(text)
        piece_text = text[start:end].strip()
        if piece_text:
            pieces.append({**item, "text": piece_text})
    return pieces


def normalize_bbox(type_value):
    """
    Type_value 형태:
      - 표준: [[x1, y1, x2, y2]]               (가장 흔함)
      - 다각형 점들: [[x1,y1],[x2,y2],[x3,y3],...]  (드물게 등장)
      - 빈 리스트 / 길이가 안 맞는 경우 등 -> None

    어떤 형태든 [x1, y1, x2, y2] (min/max) 로 통일해서 반환. 파싱 불가하면 None.
    """
    if not type_value or not isinstance(type_value, list):
        return None

    first = type_value[0]

    # case 1: 표준 형태 [[x1,y1,x2,y2]]
    if isinstance(first, (list, tuple)) and len(first) == 4 and all(
        isinstance(v, (int, float)) for v in first
    ):
        x1, y1, x2, y2 = first
        return [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]

    # case 2: 다각형 점들의 리스트 [[x,y],[x,y],...]
    if isinstance(first, (list, tuple)) and len(first) == 2:
        xs, ys = [], []
        for p in type_value:
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                xs.append(p[0])
                ys.append(p[1])
        if xs and ys:
            return [min(xs), min(ys), max(xs), max(ys)]

    # case 3: 평탄화된 숫자 나열 [x1,y1,x2,y2] (리스트 안 리스트가 아닌 경우)
    if all(isinstance(v, (int, float)) for v in type_value):
        if len(type_value) == 4:
            x1, y1, x2, y2 = type_value
            return [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]
        if len(type_value) >= 4 and len(type_value) % 2 == 0:
            xs = type_value[0::2]
            ys = type_value[1::2]
            return [min(xs), min(ys), max(xs), max(ys)]

    return None


def extract_items(problem_json: dict):
    """class_info_list 의 모든 항목을 (class_name, bbox, text) 플랫 리스트로 변환."""
    items = []
    for block in problem_json.get("learning_data_info", []):
        class_name = block.get("class_name", "")
        for info in block.get("class_info_list", []):
            bbox_raw = info.get("Type_value", [])
            bbox = normalize_bbox(bbox_raw)
            text = info.get("text_description", "") or ""
            items.append({
                "class_name": class_name,
                "bbox": bbox,  # None일 수 있음 -> 정렬 시 폴백 처리
                "text": text.strip(),
            })
    return items


def is_option_related(class_name: str) -> bool:
    return any(class_name.startswith(p) for p in OPTION_CLASS_PREFIXES)


def is_image_class(class_name: str) -> bool:
    return "이미지" in class_name


def is_answer_class(class_name: str) -> bool:
    return class_name.startswith(ANSWER_CLASS_PREFIX)


CIRCLED_DIGITS = "①②③④⑤⑥⑦⑧⑨⑩"


def parse_choice_number(text: str):
    """텍스트 맨 앞쪽에서 ①~⑩ 번호를 찾아 1~10 정수로 반환. 없으면 None."""
    for ch in text[:3]:
        if ch in CIRCLED_DIGITS:
            return CIRCLED_DIGITS.index(ch) + 1
    return None


def sort_key(item, y_tol=8.0):
    """
    1순위: 문항(질문 stem)은 항상 맨 앞.
    2순위: ①~⑩ 번호가 파싱되면 그 숫자로 정렬 (그래프/도형 등 2차원 배치에서도
           정답 항목이 제 위치(번호)에 정확히 끼워 들어가게 함).
    3순위: 번호가 없으면 bbox y->x 순서로 폴백.
    """
    is_stem = item["class_name"].startswith("문항")
    choice_num = None if is_stem else parse_choice_number(item["text"])

    bbox = item.get("bbox")
    if bbox is None:
        x1, y_bucket = 0, 0  # bbox 파싱 실패 시 정렬 안정성을 위한 폴백값(맨 앞쪽 취급)
    else:
        x1, y1 = bbox[0], bbox[1]
        y_bucket = round(y1 / y_tol)

    group = 0 if is_stem else (1 if choice_num is not None else 2)
    return (group, choice_num if choice_num is not None else 0, y_bucket, x1)


def rebuild_one(problem_json: dict):
    items = extract_items(problem_json)
    raw_option_items = [it for it in items if is_option_related(it["class_name"]) and it["text"]]

    option_items = []
    for it in raw_option_items:
        if it["class_name"].startswith("문항"):
            option_items.append(it)  # 질문 본문은 분리하지 않음
        else:
            option_items.extend(split_bundled_choices(it))

    if not option_items:
        return None  # 복구 불가 (원본에도 없음) -> 사람 검수 필요

    option_items.sort(key=sort_key)

    merged_text = " ".join(it["text"] for it in option_items)

    bboxed_items = [it for it in option_items if it.get("bbox") is not None]
    if bboxed_items:
        xs1 = [it["bbox"][0] for it in bboxed_items]
        ys1 = [it["bbox"][1] for it in bboxed_items]
        xs2 = [it["bbox"][2] for it in bboxed_items]
        ys2 = [it["bbox"][3] for it in bboxed_items]
        merged_bbox = [min(xs1), min(ys1), max(xs2), max(ys2)]
    else:
        merged_bbox = None

    has_image_class = any(is_image_class(it["class_name"]) for it in option_items)
    option_type = "mixed_with_image" if has_image_class else "text"

    answer_items = [it for it in option_items if is_answer_class(it["class_name"])]
    recovered_answer = " ".join(it["text"] for it in answer_items) if answer_items else None

    image_regions = [
        {"class_name": it["class_name"], "bbox": it["bbox"]}
        for it in option_items if is_image_class(it["class_name"])
    ]

    return {
        "question_with_options": merged_text,
        "question_image_bbox": json.dumps([merged_bbox] if merged_bbox else [], ensure_ascii=False),
        "option_type": option_type,
        "recovered_answer": recovered_answer,
        "image_regions": json.dumps(image_regions, ensure_ascii=False) if image_regions else None,
    }


def normalize_answer(s):
    if s is None:
        return ""
    s = str(s)
    s = re.sub(r"\s+", "", s)
    return s


def answer_matches(existing_answer_raw, recovered_answer_raw):
    """
    기존 answer 컬럼이 '② ... | ②' 처럼 '|'로 여러 조각이 들어있는 경우가 있어
    단순 substring 비교로는 거짓 불일치가 많이 난다.
    '|' 기준으로 조각을 나눠 각 조각이 recovered_answer 안에 들어있는지로 판단.
    """
    if not existing_answer_raw:
        return False
    recovered_norm = normalize_answer(recovered_answer_raw)
    if not recovered_norm:
        return False

    fragments = [normalize_answer(f) for f in str(existing_answer_raw).split("|")]
    fragments = [f for f in fragments if f]
    if not fragments:
        return False

    return all(frag in recovered_norm for frag in fragments)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-dir", required=True, help="원본 per-문제 JSON들이 있는 디렉토리 (재귀 검색)")
    parser.add_argument("--csv", required=True, help="기존 merged_problems.csv 경로")
    parser.add_argument("--out", required=True, help="결과 저장 경로")
    args = parser.parse_args()

    json_dir = Path(args.json_dir)
    json_index = {p.stem: p for p in json_dir.rglob("*.json")}
    print(f"원본 JSON 파일 {len(json_index)}개 인덱싱 완료")

    df = pd.read_csv(args.csv)
    for col in ["option_type", "extraction_status", "recovered_answer", "answer_match", "image_regions"]:
        if col not in df.columns:
            df[col] = None

    def is_blank(x):
        return pd.isna(x) or str(x).strip() in ("", "[]")

    target_mask = (df["problem_type"] == "객관식") & df["question_with_options"].apply(is_blank)
    print(f"복구 대상 행: {target_mask.sum()}개")

    n_recovered, n_missing_json, n_no_option_items = 0, 0, 0

    for idx in df[target_mask].index:
        name = df.at[idx, "source_data_name"]
        json_path = json_index.get(name)
        if json_path is None:
            df.at[idx, "extraction_status"] = "missing_raw_json"
            n_missing_json += 1
            continue

        problem_json = load_problem_json(json_path)
        result = rebuild_one(problem_json)

        if result is None:
            df.at[idx, "extraction_status"] = "no_option_items_in_raw"
            n_no_option_items += 1
            continue

        df.at[idx, "question_with_options"] = result["question_with_options"]
        df.at[idx, "question_image_bbox"] = result["question_image_bbox"]
        df.at[idx, "option_type"] = result["option_type"]
        df.at[idx, "recovered_answer"] = result["recovered_answer"]
        df.at[idx, "image_regions"] = result["image_regions"]

        existing_answer = df.at[idx, "answer"]
        match = answer_matches(existing_answer, result["recovered_answer"])
        df.at[idx, "answer_match"] = match
        df.at[idx, "extraction_status"] = "recovered" if match else "recovered_needs_review"

        n_recovered += 1

    print(f"복구 완료: {n_recovered}")
    print(f"원본 JSON 자체가 없음: {n_missing_json}")
    print(f"원본 JSON엔 있지만 문항/정답/오답 항목이 비어있음: {n_no_option_items}")
    if n_recovered:
        mismatch = (df.loc[target_mask, "answer_match"] == False).sum()  # noqa: E712
        print(f"  -> 정답 텍스트 불일치(검수 필요): {mismatch} / {n_recovered}")

    df.to_csv(args.out, index=False)
    print(f"저장 완료: {args.out}")


if __name__ == "__main__":
    main()