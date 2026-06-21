from django.core.management.base import BaseCommand
from quiz.models import ProblemAsset

OLD_PREFIX = "data/assets/option_images/"
NEW_PREFIX = "problem_assets/"


class Command(BaseCommand):
    help = "ProblemAsset.image_path 의 잘못된 cwd 기준 경로를 MEDIA_ROOT 기준 상대경로로 일괄 변경"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        targets = ProblemAsset.objects.filter(image_path__startswith=OLD_PREFIX)
        self.stdout.write(f"대상: {targets.count()}건")

        to_save = []
        for asset in targets:
            new_path = NEW_PREFIX + asset.image_path[len(OLD_PREFIX):]
            if dry_run:
                self.stdout.write(f"{asset.image_path} -> {new_path}")
            else:
                asset.image_path = new_path
                to_save.append(asset)

        if not dry_run and to_save:
            ProblemAsset.objects.bulk_update(to_save, fields=["image_path"], batch_size=200)

        action = "[DRY-RUN] 변경 예정" if dry_run else "변경 완료"
        self.stdout.write(self.style.SUCCESS(f"{action}: {len(to_save) if not dry_run else targets.count()}건"))