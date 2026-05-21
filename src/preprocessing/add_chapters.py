import sys
import pandas as pd
from pathlib import Path

# ── 성취기준 코드 → (대단원, 중단원) 매핑 ───────────────────────────────────
CHAPTER_MAP: dict[str, tuple[str, str]] = {
    "9수01-06": ("1. 수와 식",                    "1. 유리수와 순환소수"),
    "9수02-08": ("1. 수와 식",                    "2. 단항식의 계산"),
    "9수02-09": ("1. 수와 식",                    "3. 다항식의 계산"),
    "9수02-10": ("1. 수와 식",                    "3. 다항식의 계산"),
    "9수02-11": ("2. 일차부등식과 연립일차방정식", "1. 일차부등식"),
    "9수02-12": ("2. 일차부등식과 연립일차방정식", "1. 일차부등식"),
    "9수02-13": ("2. 일차부등식과 연립일차방정식", "2. 연립일차방정식"),
    "9수02-14": ("3. 일차함수",                   "1. 일차함수와 그 그래프"),
    "9수02-15": ("3. 일차함수",                   "1. 일차함수와 그 그래프"),
    "9수02-16": ("3. 일차함수",                   "1. 일차함수와 그 그래프"),
    "9수02-17": ("3. 일차함수",                   "2. 일차함수와 일차방정식의 관계"),
    "9수02-18": ("3. 일차함수",                   "2. 일차함수와 일차방정식의 관계"),
}


def classify_row(row: pd.Series) -> tuple[str, str]:
    code = str(row.get("achievement_standard_code", "")).strip()
    if code in CHAPTER_MAP:
        return CHAPTER_MAP[code]
    return ("미분류", "미분류")


def main():

    input_path  = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.parent / "problems_classified.csv"

    print(f"[INFO] 읽는 중: {input_path}")
    df = pd.read_csv(input_path, encoding="utf-8-sig")
    print(f"[INFO] {len(df)}행 로드 완료")

    # 대단원 / 중단원 분류 적용
    chapters = df.apply(classify_row, axis=1, result_type="expand")
    chapters.columns = ["chapter_major", "chapter_middle"]
    df = pd.concat([df, chapters], axis=1)

    # 소단원 / 세부유형은 AI가 채울 자리만 빈 컬럼으로 추가
    df["chapter_minor"]   = ""
    df["problem_subtype"] = ""

    # 컬럼 순서 정리
    ordered_cols = [
        "source_data_name",
        "problem_type",
        "difficulty",
        "achievement_standard_code",
        "achievement_standard_text",
        "chapter_major",
        "chapter_middle",
        "chapter_minor",       # AI 분류 예정
        "problem_subtype",     # AI 분류 예정
        "question_text",
        "question_with_options",
        "question_image_bbox",
        "answer",
        "explanation",
    ]
    ordered_cols = [c for c in ordered_cols if c in df.columns]
    df = df[ordered_cols]

    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {output_path}")

    # 분류 결과 요약
    print("\n── 중단원별 문항 수 ──────────────────────────────────")
    summary = (
        df.groupby(["chapter_major", "chapter_middle"])
        .size()
        .reset_index(name="count")
    )
    print(summary.to_string(index=False))

    unclassified = (df["chapter_major"] == "미분류").sum()
    if unclassified:
        codes = df.loc[df["chapter_major"] == "미분류", "achievement_standard_code"].unique()
        print(f"\n미분류 {unclassified}건 (코드: {codes})")


if __name__ == "__main__":
    main()