import re
from django.core.management.base import BaseCommand
from quiz.models import Problem

CIRCLED = re.compile(r'[①②③④⑤]')


CIRCLED_ORDER = "①②③④⑤⑥⑦⑧⑨⑩"


def extract_label(answer_raw: str):
    """
    'answer' 원본 텍스트에서 채점에 쓸 라벨을 추출.
    반환값: (label, is_multi) 튜플. 실패 시 (None, False).

    우선순위:
      1. '|'로 쪼갠 조각 중, 그 자체가 '①' 같은 기호 하나(+공백)뿐인 조각이 있으면 그걸 단일 정답으로 사용
         (가장 신뢰도 높음 — 원본에 이미 채점용 라벨이 명시돼 있던 케이스)
      2. 기호 단독 조각이 없을 때:
         - 전체에서 서로 다른 기호가 1종류만 나오면(중복 언급) 그 기호를 단일 정답으로 사용
         - 서로 다른 기호가 정확히 2종류면 "모두 고르시오"형 복수 정답으로 보고
           정렬된 콤마 조합(예: '①,④')을 반환 (S3_중등_2_003911 같은 사례로 검증된 패턴:
           원본 출판사가 '①내용 | ④내용 | ①,④' 형태로 마지막에 정답 조합을 명시했었음)
         - 서로 다른 기호가 3종류 이상이면 -> 정답이 아니라 보기 전체가 통째로 answer에
           잘못 들어간 데이터 오염 케이스로 판단 -> 자동 처리하지 않고 None (수동 검수)
      3. 기호가 아예 없으면 None
    """
    if not answer_raw:
        return None, False

    fragments = [f.strip() for f in answer_raw.split('|')]

    # 1순위: 기호 단독 조각
    for frag in fragments:
        if re.fullmatch(r'[①②③④⑤]', frag):
            return frag, False

    # 2순위: 전체에서 등장하는 기호 종류 확인
    found = CIRCLED.findall(answer_raw)
    distinct = sorted(set(found), key=lambda c: CIRCLED_ORDER.index(c))

    if len(distinct) == 1:
        return distinct[0], False

    if len(distinct) == 2:
        return ",".join(distinct), True  # 복수 정답

    return None, False  # 기호가 없거나 3개 이상 섞임(데이터 오염 가능성) -> 수동 검수


class Command(BaseCommand):
    help = "answer에 '|'가 섞여 채점이 깨질 수 있는 quizable 문제를 정리합니다."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # '|' 유무와 무관하게 is_quizable 전체를 스캔 (S3_중등_2_001485 사례로 확인됨:
        # '|' 없이 그냥 기호 2개가 붙어있는 복수정답 케이스도 있음). 이미 정상 처리된 행은
        # 같은 결과가 다시 나올 뿐이라 재실행해도 안전(멱등성 있음).
        targets = Problem.objects.filter(is_quizable=True)
        self.stdout.write(f"대상: {targets.count()}개")

        n_fixed, n_manual_review = 0, 0
        to_save = []

        for p in targets:
            label, is_multi = extract_label(p.answer)
            if label is None:
                n_manual_review += 1
                self.stdout.write(self.style.WARNING(
                    f"[수동검수 필요] {p.id}: answer={p.answer!r} -> 라벨 추출 실패"
                ))
                continue

            tag = " (복수정답)" if is_multi else ""
            self.stdout.write(f"{p.id}: {p.answer!r} -> grading_answer={label!r}{tag}")
            p.grading_answer = label
            p.is_multi_answer = is_multi
            to_save.append(p)
            n_fixed += 1

        if not dry_run and to_save:
            Problem.objects.bulk_update(to_save, fields=["grading_answer", "is_multi_answer"], batch_size=200)

        action = "[DRY-RUN] 정리 예정" if dry_run else "정리 완료"
        self.stdout.write(self.style.SUCCESS(
            f"{action}: {n_fixed}개 / 수동 검수 필요: {n_manual_review}개"
        ))