import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from quiz.models import Problem, ProblemAsset


def to_media_relative_path(file_path: str) -> str:
    """
    file_path가 MEDIA_ROOT 하위 절대/상대 경로 어느 쪽으로 들어와도
    DB에는 MEDIA_ROOT 기준 상대경로만 저장 (URL 조합을 위해).
    이미 MEDIA_ROOT 바깥 경로라면 그대로 둔다(경고만 출력).
    """
    p = Path(file_path).resolve()
    media_root = Path(settings.MEDIA_ROOT).resolve()
    try:
        return str(p.relative_to(media_root))
    except ValueError:
        return file_path  # MEDIA_ROOT 밖 경로 -> 그대로 저장(나중에 옮겨야 함)


class Command(BaseCommand):
    help = "crop_option_images.py 결과물(manifest.csv)을 ProblemAsset 테이블에 적재합니다."

    def add_arguments(self, parser):
        parser.add_argument("manifest_csv_path", type=str)
        parser.add_argument(
            "--replace",
            action="store_true",
            help="같은 problem에 대한 기존 ProblemAsset을 지우고 새로 넣음 (재실행 시 중복 방지용)",
        )

    def handle(self, *args, **options):
        path = options["manifest_csv_path"]
        replace = options["replace"]

        try:
            f = open(path, encoding="utf-8")
        except FileNotFoundError:
            raise CommandError(f"파일을 찾을 수 없습니다: {path}")

        reader = csv.DictReader(f)
        rows = list(reader)
        f.close()

        problem_ids = {r["source_data_name"] for r in rows}
        existing_problems = set(
            Problem.objects.filter(pk__in=problem_ids).values_list("pk", flat=True)
        )

        if replace:
            ProblemAsset.objects.filter(problem_id__in=existing_problems).delete()

        to_create = []
        n_missing_problem = 0

        for row in rows:
            pid = row["source_data_name"]
            if pid not in existing_problems:
                n_missing_problem += 1
                continue

            to_create.append(ProblemAsset(
                problem_id=pid,
                asset_role=row["class_name"],
                image_path=to_media_relative_path(row["file_path"]),
                bbox_x1=float(row["bbox_x1"]),
                bbox_y1=float(row["bbox_y1"]),
                bbox_x2=float(row["bbox_x2"]),
                bbox_y2=float(row["bbox_y2"]),
            ))

        ProblemAsset.objects.bulk_create(to_create, batch_size=200)

        self.stdout.write(self.style.SUCCESS(
            f"ProblemAsset {len(to_create)}건 생성 완료. "
            f"매칭되는 Problem 없어서 스킵: {n_missing_problem}건"
        ))