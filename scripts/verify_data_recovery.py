# 최종 검증: 데이터 복구 완료 후 수치 확인
#
# 사용법 (app/ 디렉토리에서):
#   python manage.py shell -c "exec(open('../scripts/verify_data_recovery.py').read())"

from quiz.models import Problem, ProblemAsset

print('=== 데이터 복구 최종 검증 ===')
print(f'Problem 전체: {Problem.objects.count()}')
print(f'option_type=mixed_with_image: {Problem.objects.filter(option_type="mixed_with_image").count()} (기대값: 424)')
print(f'ProblemAsset 전체: {ProblemAsset.objects.count()} (기대값: 625)')
print(f'is_multi_answer=True: {Problem.objects.filter(is_multi_answer=True).count()} (기대값: 17)')
print(f'is_quizable=True: {Problem.objects.filter(is_quizable=True).count()} (기대값: 1221~1222)')
print()

p1 = Problem.objects.filter(pk='S3_중등_2_017702').first()
p2 = Problem.objects.filter(pk='S3_중등_2_018953').first()

if p1:
    status = 'OK' if not p1.is_quizable else 'FAIL - 여전히 True임'
    print(f'017702 is_quizable={p1.is_quizable} [{status}]')
else:
    print('017702: DB에 없음')

if p2:
    status = 'OK' if p2.grading_answer == '1' else f'FAIL - {p2.grading_answer}'
    print(f'018953 grading_answer={p2.grading_answer} [{status}]')
else:
    print('018953: DB에 없음')