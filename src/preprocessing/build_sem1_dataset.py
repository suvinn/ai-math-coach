import os
import json
import zipfile
import shutil

from collections import Counter
import pandas as pd

# =========================
# 경로 설정
# =========================

RAW_DATA_DIR = "data/raw"
EXTRACT_DIR = "data/extracted"
OUTPUT_DIR = "data/processed/middle2_sem1"

EDA_OUTPUT_PATH = "data/processed/achievement_standard_counts.csv"

# 1학기 성취기준 prefix
SEM1_PREFIX = ("[9수01", "[9수02")


# =========================
# 폴더 생성
# =========================

os.makedirs(EXTRACT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("data/processed", exist_ok=True)


# =========================
# ZIP 압축 해제
# =========================

zip_files = [
    file for file in os.listdir(RAW_DATA_DIR)
    if file.endswith(".zip")
]

print(f"ZIP 파일 개수: {len(zip_files)}")

for zip_file in zip_files:

    zip_path = os.path.join(RAW_DATA_DIR, zip_file)

    # zip 파일명 기준 압축 해제 폴더 생성
    extract_subdir = os.path.join(
        EXTRACT_DIR,
        os.path.splitext(zip_file)[0]
    )

    os.makedirs(extract_subdir, exist_ok=True)

    print(f"\n압축 해제 중: {zip_file}")

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_subdir)

print("\n모든 압축 해제 완료")


# =========================
# EDA + 1학기 데이터 필터링
# =========================

achievement_counter = Counter()

total_json_files = 0
sem1_json_files = 0


for root, dirs, files in os.walk(EXTRACT_DIR):

    for file in files:

        if not file.endswith(".json"):
            continue

        file_path = os.path.join(root, file)

        try:

            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            total_json_files += 1

            # 성취기준 추출
            standards = data.get(
                "source_data_info", {}
            ).get(
                "2022_achievement_standard",
                []
            )

            # =========================
            # EDA 카운트
            # =========================

            for std in standards:

                std = std.strip()

                if std:
                    achievement_counter[std] += 1

            # =========================
            # 1학기 데이터 여부 판단
            # =========================

            is_sem1 = all(
                std.strip().startswith(SEM1_PREFIX)
                for std in standards
                if std.strip()
            )

            # 1학기 데이터 저장
            if is_sem1:

                # 중복 방지 위해 상대경로 유지
                relative_path = os.path.relpath(
                    file_path,
                    EXTRACT_DIR
                )

                output_path = os.path.join(
                    OUTPUT_DIR,
                    relative_path
                )

                os.makedirs(
                    os.path.dirname(output_path),
                    exist_ok=True
                )

                shutil.copy(file_path, output_path)

                sem1_json_files += 1

        except Exception as e:

            print(f"\n에러 발생: {file_path}")
            print(e)


# =========================
# EDA 결과 저장
# =========================

df = pd.DataFrame(
    achievement_counter.items(),
    columns=[
        "2022_achievement_standard",
        "count"
    ]
)

df = df.sort_values(
    by="count",
    ascending=False
).reset_index(drop=True)

df.to_csv(
    EDA_OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig"
)


# =========================
# 결과 출력
# =========================

print("\n=========================")
print("처리 완료")
print("=========================")

print(f"전체 JSON 파일 수: {total_json_files}")
print(f"1학기 JSON 파일 수: {sem1_json_files}")

print(f"\nEDA 저장 완료:")
print(EDA_OUTPUT_PATH)

print(f"\n1학기 데이터 저장 완료:")
print(OUTPUT_DIR)