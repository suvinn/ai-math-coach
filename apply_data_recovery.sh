#!/usr/bin/env bash
#
# apply_data_recovery.sh
#
# 객관식 보기(선택지) 데이터 복구 작업 전체를 순서대로 적용하는 스크립트.
# backend/fix-data-migration 브랜치를 pull/checkout 한 직후, 프로젝트 루트
# (ai-math-coach/)에서 실행하세요.
#
# 배경/why는 data_recovery_history.md(노션 문서) 참고.
#
# 사용법:
#   bash apply_data_recovery.sh           # 실제 적용
#   bash apply_data_recovery.sh --dry-run # 각 단계 미리보기만 (지원하는 커맨드만)
#
set -e  # 중간에 하나라도 실패하면 즉시 중단

DRY_RUN=""
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN="--dry-run"
    echo "=== DRY RUN 모드 ==="
fi

APP_DIR="app"
SCRIPTS_DIR="scripts"
DATA_DIR="data"
MEDIA_DIR="media"

step() {
    echo ""
    echo "============================================================"
    echo "  $1"
    echo "============================================================"
}

confirm() {
    read -p "$1 진행할까요? [y/N] " ans
    [[ "$ans" == "y" || "$ans" == "Y" ]]
}

# ------------------------------------------------------------------
step "0. 사전 점검"
# ------------------------------------------------------------------
if [[ ! -f "$APP_DIR/manage.py" ]]; then
    echo "ERROR: $APP_DIR/manage.py 를 찾을 수 없습니다. 프로젝트 루트에서 실행해주세요."
    exit 1
fi
if [[ ! -f "$DATA_DIR/merged_problems_fixed.csv" ]]; then
    echo "ERROR: $DATA_DIR/merged_problems_fixed.csv 가 없습니다."
    echo "       rebuild_options.py로 생성하거나, repo에서 받아주세요."
    exit 1
fi
echo "OK"

# ------------------------------------------------------------------
step "1. 마이그레이션 적용 (Problem/ProblemAsset 신규 필드 + 테이블)"
# ------------------------------------------------------------------
(cd "$APP_DIR" && python manage.py migrate)

# ------------------------------------------------------------------
step "2. 문제 데이터 적재 (보기 텍스트 복구 포함)"
# ------------------------------------------------------------------
echo "merged_problems_fixed.csv 기준으로 question_with_options, option_type,"
echo "extraction_status, recovered_answer, answer_match 까지 한번에 적재됩니다."
(cd "$APP_DIR" && python manage.py import_problems "../$DATA_DIR/merged_problems_fixed.csv")

# ------------------------------------------------------------------
step "3. 그래프/도형형 보기 이미지 크롭"
# ------------------------------------------------------------------
if [[ -d "$MEDIA_DIR/problem_assets" ]] && [[ -n "$(ls -A "$MEDIA_DIR/problem_assets" 2>/dev/null)" ]]; then
    echo "$MEDIA_DIR/problem_assets 에 이미 파일이 있습니다. 건너뜁니다."
    echo "(다시 크롭하고 싶으면 이 폴더를 비우고 재실행하세요)"
else
    echo "원본 페이지 PNG 경로를 입력해주세요 (예: data/raw/TS_06.중학교_2학년_01.객관식):"
    read -p "> " PNG_DIR
    python "$SCRIPTS_DIR/crop_option_images.py" \
        --csv "$DATA_DIR/merged_problems_fixed.csv" \
        --png-dir "$PNG_DIR" \
        --out-dir "$MEDIA_DIR/problem_assets"
fi

# ------------------------------------------------------------------
step "4. 보기 이미지 자산 DB 적재"
# ------------------------------------------------------------------
(cd "$APP_DIR" && python manage.py import_problem_assets "../$MEDIA_DIR/problem_assets/manifest.csv")

# ------------------------------------------------------------------
step "5. 중복 이미지 자산 정리"
# ------------------------------------------------------------------
(cd "$APP_DIR" && python manage.py dedupe_problem_assets --dry-run)
if confirm "위 결과대로 중복 삭제를"; then
    (cd "$APP_DIR" && python manage.py dedupe_problem_assets)
fi

# ------------------------------------------------------------------
step "6. 이미지 경로 보정 (MEDIA_ROOT 기준)"
# ------------------------------------------------------------------
(cd "$APP_DIR" && python manage.py fix_asset_paths --dry-run)
if confirm "위 결과대로 경로 보정을"; then
    (cd "$APP_DIR" && python manage.py fix_asset_paths)
fi

# ------------------------------------------------------------------
step "7. 고아 이미지 파일 정리"
# ------------------------------------------------------------------
(cd "$APP_DIR" && python manage.py cleanup_orphan_assets --dry-run)
if confirm "위 결과대로 고아 파일 삭제를"; then
    (cd "$APP_DIR" && python manage.py cleanup_orphan_assets)
fi

# ------------------------------------------------------------------
step "8. 채점용 정답 라벨 정규화 (복수정답 포함)"
# ------------------------------------------------------------------
(cd "$APP_DIR" && python manage.py normalize_quiz_answers --dry-run)
if confirm "위 결과대로 정답 라벨 정규화를"; then
    (cd "$APP_DIR" && python manage.py normalize_quiz_answers)
fi

# ------------------------------------------------------------------
step "9. 원본 라벨링 오류 2건 수동 정정 (자동 실행, idempotent)"
# ------------------------------------------------------------------
(cd "$APP_DIR" && python manage.py shell << 'PYEOF'
from quiz.models import Problem

Problem.objects.filter(pk='S3_중등_2_017702').update(
    is_quizable=False,
    extraction_status='corrupted_source_missing_option_2',
)
print('017702 처리 완료')

Problem.objects.filter(pk='S3_중등_2_018953').update(
    answer='① $4x-5$',
    grading_answer='①',
    is_multi_answer=False,
    is_quizable=True,
    extraction_status='manually_fixed_swapped_answer_label',
)
print('018953 처리 완료')
PYEOF
)

# ------------------------------------------------------------------
step "완료 - 최종 검증"
# ------------------------------------------------------------------
(cd "$APP_DIR" && python manage.py shell << 'PYEOF'
from quiz.models import Problem, ProblemAsset

total = Problem.objects.filter(problem_type='객관식').count() if hasattr(Problem, 'problem_type') else Problem.objects.count()
print(f"Problem 전체: {Problem.objects.count()}")
print(f"option_type=mixed_with_image: {Problem.objects.filter(option_type='mixed_with_image').count()}")
print(f"ProblemAsset: {ProblemAsset.objects.count()}")
print(f"is_multi_answer=True: {Problem.objects.filter(is_multi_answer=True).count()}")
print(f"is_quizable=True: {Problem.objects.filter(is_quizable=True).count()}")
print(f"017702 상태: {Problem.objects.get(pk='S3_중등_2_017702').is_quizable}")
print(f"018953 정답: {Problem.objects.get(pk='S3_중등_2_018953').grading_answer}")
PYEOF
)

echo ""
echo "모든 단계 완료. 위 수치를 data_recovery_history.md의 '최종 수치'와 비교해주세요."
echo "기대값: mixed_with_image=424, ProblemAsset=625, is_multi_answer=True=17, 017702=False"
