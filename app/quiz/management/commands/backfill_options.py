import csv
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from quiz.models import Problem


class Command(BaseCommand):
    help = "merged_problems_fixed.csv 로 기존 Problem 레코드의 보기(options) 관련 필드를 백필합니다."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="실제 저장 없이 몇 건이 바뀌는지만 미리 확인",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        dry_run = options["dry_run"]

        try:
            f = open(csv_path, encoding="utf-8-sig")
        except FileNotFoundError:
            raise CommandError(f"파일을 찾을 수 없습니다: {csv_path}")

        reader = csv.DictReader(f)

        n_updated, n_not_found, n_skipped_no_status, n_errors = 0, 0, 0, 0
        to_save = []

        for row in reader:
            pid = row.get("source_data_name")
            status = row.get("extraction_status")

            # extraction_status가 비어있는 행 = 원래부터 정상이었던 23% -> 건드릴 필요 없음
            if not status:
                n_skipped_no_status += 1
                continue

            try:
                problem = Problem.objects.get(pk=pid)
            except Problem.DoesNotExist:
                n_not_found += 1
                self.stderr.write(self.style.WARNING(f"DB에 없는 problem_id: {pid}"))
                continue

            problem.question_with_options = row.get("question_with_options") or problem.question_with_options
            problem.question_image_bbox = self._parse_bbox(row.get("question_image_bbox"))
            problem.option_type = row.get("option_type") or None
            problem.extraction_status = status
            problem.recovered_answer = row.get("recovered_answer") or None
            problem.answer_match = self._parse_bool(row.get("answer_match"))
            problem.backfilled_at = timezone.now()

            to_save.append(problem)
            n_updated += 1

        f.close()

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"[DRY-RUN] 업데이트 예정: {n_updated} / DB에 없음: {n_not_found} / "
                f"건드릴 필요 없음(원래 정상): {n_skipped_no_status}"
            ))
            return

        # bulk_update로 한 번에 저장 (1,127건 정도면 충분히 빠름)
        if to_save:
            Problem.objects.bulk_update(
                to_save,
                fields=[
                    "question_with_options", "question_image_bbox", "option_type",
                    "extraction_status", "recovered_answer", "answer_match", "backfilled_at",
                ],
                batch_size=200,
            )

        self.stdout.write(self.style.SUCCESS(
            f"백필 완료: {n_updated}건 업데이트 / DB에 없음: {n_not_found}건 / "
            f"건드릴 필요 없음(원래 정상): {n_skipped_no_status}건"
        ))

    @staticmethod
    def _parse_bbox(raw):
        import json
        if not raw:
            return []
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _parse_bool(raw):
        if raw in (None, "", "nan", "NaN"):
            return None
        return str(raw).strip().lower() in ("true", "1", "yes")