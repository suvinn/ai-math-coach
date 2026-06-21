import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from quiz.models import ProblemAsset

ASSET_SUBDIR = "problem_assets"
KEEP_FILENAMES = {"manifest.csv"}  # 자산 아닌 부산물 파일은 건드리지 않음


class Command(BaseCommand):
    help = "DB에서 참조하지 않는 고아 이미지 파일을 찾아 삭제합니다."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        media_root = Path(settings.MEDIA_ROOT)
        asset_root = media_root / ASSET_SUBDIR

        if not asset_root.exists():
            self.stderr.write(self.style.ERROR(f"경로 없음: {asset_root}"))
            return

        referenced = set(
            ProblemAsset.objects.values_list("image_path", flat=True)
        )
        # DB에는 'problem_assets/xxx/yyy.png' 형태로 저장돼있다고 가정 (fix_asset_paths.py 이후)

        n_total, n_orphan, n_deleted = 0, 0, 0

        for file_path in asset_root.rglob("*"):
            if file_path.is_dir():
                continue
            if file_path.name in KEEP_FILENAMES:
                continue

            n_total += 1
            rel_path = str(file_path.relative_to(media_root))

            if rel_path in referenced:
                continue

            n_orphan += 1
            self.stdout.write(f"고아 파일: {rel_path}")

            if not dry_run:
                file_path.unlink()
                n_deleted += 1

        action = "[DRY-RUN]" if dry_run else "삭제 완료"
        self.stdout.write(self.style.SUCCESS(
            f"{action}: 전체 파일 {n_total}개 중 고아 파일 {n_orphan}개"
            + ("" if dry_run else f" / 삭제 {n_deleted}개")
        ))