import json
import csv
import re
import sys
from pathlib import Path


# 대상 폴더 목록
TARGET_FOLDERS = [
    "TL_06.중학교 2학년_01.객관식",
    "TL_06.중학교 2학년_02.주관식",
    "VL_06.중학교 2학년_02.주관식",
]

# 성취기준 코드 추출 정규식 (예: [9수01-06] → 9수01-06)
CODE_PATTERN = re.compile(r'\[([^\]]+)\]')

# class_name → 역할 매핑
QUESTION_TEXT_CLASSES  = {"문항(텍스트)"}
QUESTION_IMAGE_CLASSES = {"문항(이미지)"}
ANSWER_CLASSES         = {"정답(텍스트)", "정답(이미지)"}
EXPLANATION_CLASSES    = {"해설(텍스트)", "해설(이미지)"}


def extract_achievement_standard(data: dict) -> tuple[str, str]:
    """2022 → 2015 → 2009 순으로 유효한 성취기준을 선택해 (코드, 전문) 반환."""
    source = data.get("source_data_info", {})
    for key in ["2022_achievement_standard", "2015_achievement_standard", "2009_achievement_standard"]:
        for std in source.get(key, []):
            std = std.strip()
            if std:
                match = CODE_PATTERN.search(std)
                code = match.group(1) if match else ""
                return code, std
    return "", ""


def collect_texts(learning_data: list, target_classes: set) -> list[str]:
    """target_classes에 해당하는 class_name의 text_description을 모두 수집."""
    texts = []
    for item in learning_data:
        if item.get("class_name", "") in target_classes:
            for info in item.get("class_info_list", []):
                text = info.get("text_description", "").strip()
                if text:
                    texts.append(text)
    return texts


def collect_bboxes(learning_data: list, target_classes: set) -> list:
    """target_classes에 해당하는 class_name의 Bounding_Box 좌표를 모두 수집."""
    bboxes = []
    for item in learning_data:
        if item.get("class_name", "") in target_classes:
            for info in item.get("class_info_list", []):
                if info.get("Type") == "Bounding_Box":
                    bboxes.extend(info.get("Type_value", []))
    return bboxes


def process_json_file(filepath: Path) -> dict | None:
    """JSON 파일 하나를 파싱해 CSV 한 행 분량의 dict를 반환."""
    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[WARN] 파일 읽기 실패: {filepath} → {e}", file=sys.stderr)
        return None

    source_info = data.get("source_data_info", {})
    learning    = data.get("learning_data_info", [])

    # ── 기본 메타 ──────────────────────────────────────────────
    source_data_name = source_info.get("source_data_name", filepath.stem)
    difficulty       = source_info.get("level_of_difficulty", "")
    problem_type     = source_info.get("types_of_problems", "")

    # ── 성취기준 ───────────────────────────────────────────────
    achievement_code, achievement_text = extract_achievement_standard(data)

    # ── 문제 본문 (텍스트) ─────────────────────────────────────
    q_texts       = collect_texts(learning, QUESTION_TEXT_CLASSES)
    question_text = " ".join(q_texts)

    # ── 보기 포함 전체 문제 (이미지 영역) ──────────────────────
    # 이 교재는 보기가 문항(이미지) 안에 함께 담겨 있으므로
    # question_with_options 하나로 통합 관리한다.
    q_images              = collect_texts(learning, QUESTION_IMAGE_CLASSES)
    question_with_options = " | ".join(q_images)
    question_image_bbox   = collect_bboxes(learning, QUESTION_IMAGE_CLASSES)

    # ── 정답 ───────────────────────────────────────────────────
    answer_texts = collect_texts(learning, ANSWER_CLASSES)
    answer       = " | ".join(answer_texts)

    # ── 해설 ───────────────────────────────────────────────────
    explanation_texts = collect_texts(learning, EXPLANATION_CLASSES)
    explanation       = " | ".join(explanation_texts)

    return {
        "source_data_name"         : source_data_name,
        "problem_type"             : problem_type,
        "question_text"            : question_text,
        "question_with_options"    : question_with_options,
        "question_image_bbox"      : json.dumps(question_image_bbox, ensure_ascii=False),
        "answer"                   : answer,
        "explanation"              : explanation,
        "difficulty"               : difficulty,
        "achievement_standard_code": achievement_code,
        "achievement_standard_text": achievement_text,
    }


def main():
    BASE_DIR = Path(sys.argv[1]).resolve()
    OUTPUT_CSV = BASE_DIR / "problems_extracted.csv"

    fieldnames = [
        "source_data_name",
        "problem_type",
        "question_text",
        "question_with_options",
        "question_image_bbox",
        "answer",
        "explanation",
        "difficulty",
        "achievement_standard_code",
        "achievement_standard_text",
    ]

    rows = []
    missing_folders = []

    for folder_name in TARGET_FOLDERS:
        folder_path = BASE_DIR / folder_name
        if not folder_path.exists():
            missing_folders.append(str(folder_path))
            print(f"[WARN] 폴더 없음: {folder_path}", file=sys.stderr)
            continue

        json_files = sorted(folder_path.rglob("*.json"))
        print(f"[INFO] {folder_name}: {len(json_files)}개 파일 발견")

        for json_file in json_files:
            row = process_json_file(json_file)
            if row:
                rows.append(row)

    if not rows:
        print("[ERROR] 추출된 데이터가 없습니다. 폴더 경로를 확인하세요.", file=sys.stderr)
        sys.exit(1)

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n완료: {len(rows)}개 문항 → {OUTPUT_CSV}")

    if missing_folders:
        print(f"찾지 못한 폴더 {len(missing_folders)}개:")
        for mf in missing_folders:
            print(f"   - {mf}")


if __name__ == "__main__":
    main()