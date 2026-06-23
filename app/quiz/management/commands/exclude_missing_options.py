import re
from django.core.management.base import BaseCommand
from quiz.models import Problem

CIRCLED = re.compile(r'[①②③④⑤⑥⑦⑧⑨⑩]')


class Command(BaseCommand):
    help = (
        "grading_answer는 ①②③ 같은 라벨로 채점되지만 question_with_options에 보기 "
        "선택지가 2개 미만(=보기 텍스트가 사실상 없음)이라 학생이 절대 맞힐 수 없는 "
        "객관식 문제를 is_quizable=False로 출제 제외한다. (보기 데이터가 추가 복구되면 "
        "extraction_status='excluded_missing_option_choices'인 문제들을 다시 검토해서 "
        "되돌릴 수 있다.)"
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        targets = []
        for p in Problem.objects.filter(is_quizable=True):
            marks = set(CIRCLED.findall(p.question_with_options or ''))
            if len(marks) < 2:
                targets.append(p)

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"[DRY-RUN] 출제 제외 예정: {len(targets)}개"
            ))
            for p in targets[:10]:
                self.stdout.write(f"  {p.id}: answer={p.answer!r}")
            return

        for p in targets:
            p.is_quizable = False
            p.extraction_status = 'excluded_missing_option_choices'
        Problem.objects.bulk_update(targets, fields=["is_quizable", "extraction_status"], batch_size=200)

        self.stdout.write(self.style.SUCCESS(
            f"출제 제외 완료: {len(targets)}개 / 남은 quizable: {Problem.objects.filter(is_quizable=True).count()}개"
        ))
