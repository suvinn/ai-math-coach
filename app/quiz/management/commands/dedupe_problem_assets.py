import os
from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand

from quiz.models import ProblemAsset


class Command(BaseCommand):
    help = "같은 problem + 같은 bbox로 중복 생성된 ProblemAsset을 정리합니다."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        groups = defaultdict(list)
        for asset in ProblemAsset.objects.all().order_by("id"):
            key = (asset.problem_id, asset.bbox_x1, asset.bbox_y1, asset.bbox_x2, asset.bbox_y2)
            groups[key].append(asset)

        n_dup_groups = 0
        n_deleted = 0
        n_file_missing = 0

        for key, assets in groups.items():
            if len(assets) <= 1:
                continue
            n_dup_groups += 1
            keep, *dupes = assets  # id 순으로 정렬돼있으니 가장 먼저 만든 것만 유지

            self.stdout.write(
                f"problem={key[0]} bbox={key[1:]} -> {len(assets)}개 중 {len(dupes)}개 삭제 "
                f"(유지: {keep.image_path})"
            )

            for dup in dupes:
                file_path = os.path.join(settings.MEDIA_ROOT, dup.image_path)
                if dry_run:
                    n_deleted += 1
                    continue

                if os.path.exists(file_path):
                    os.remove(file_path)
                else:
                    n_file_missing += 1

                dup.delete()
                n_deleted += 1

        action = "[DRY-RUN] 삭제 예정" if dry_run else "삭제 완료"
        self.stdout.write(self.style.SUCCESS(
            f"{action}: 중복 그룹 {n_dup_groups}개 / 삭제 대상 {n_deleted}건 "
            f"(파일 이미 없음: {n_file_missing}건)"
        ))