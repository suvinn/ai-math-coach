import os
import django

from quiz.models import Problem

# S3_중등_2_017702
# 원본 raw JSON에 2번 선택지 자체가 누락된 데이터 결손
# 퀴즈 출제 대상에서 제외, RAG 추천용으로는 유지
count = Problem.objects.filter(pk='S3_중등_2_017702').update(
    is_quizable=False,
    extraction_status='corrupted_source_missing_option_2',
)
print(f'017702 처리 완료 (updated: {count})')

# S3_중등_2_018953
# 원본 raw JSON의 정답/오답 클래스 라벨이 서로 뒤바뀜
# 해설("y=4x-5") 대조로 정답이 1번임을 확인
count = Problem.objects.filter(pk='S3_중등_2_018953').update(
    answer='1 $4x-5$',
    grading_answer='1',
    is_multi_answer=False,
    is_quizable=True,
    extraction_status='manually_fixed_swapped_answer_label',
)
print(f'018953 처리 완료 (updated: {count})')

# 검증
p1 = Problem.objects.get(pk='S3_중등_2_017702')
p2 = Problem.objects.get(pk='S3_중등_2_018953')
print(f'017702 is_quizable: {p1.is_quizable} (False 여야 정상)')
print(f'018953 grading_answer: {p2.grading_answer} (1 이여야 정상)')