import csv
import json
import re
from django.core.management.base import BaseCommand
from quiz.models import Problem


class Command(BaseCommand):
    help = 'CSV 파일에서 객관식 문제만 Problem 테이블에 적재'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)

    def handle(self, *args, **options):
        path = options['csv_path']
        created, skipped = 0, 0

        with open(path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['problem_type'] != '객관식':
                    skipped += 1
                    continue

                try:
                    bbox = json.loads(row['question_image_bbox'])
                except (json.JSONDecodeError, TypeError):
                    bbox = []

                # is_quizable 판별
                question_with_options = row.get('question_with_options') or ''
                answer = row.get('answer', '').strip()
                is_quizable = _is_quizable(question_with_options, answer)

                Problem.objects.update_or_create(
                    id=row['source_data_name'],
                    defaults={
                        'difficulty':             row['difficulty'],
                        'chapter_major':          row['chapter_major'],
                        'chapter_middle':         row['chapter_middle'],
                        'chapter_minor':          row['chapter_minor'],
                        'problem_subtype':        row['problem_subtype'],
                        'question_text':          row['question_text'],
                        'question_with_options':  question_with_options or None,
                        'question_image_bbox':    bbox,
                        'answer':                 answer,
                        'explanation':            row['explanation'],
                        'is_quizable':            is_quizable,
                    }
                )
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f'완료: 적재 {created}개 / 주관식 제외 {skipped}개')
        )


def _is_quizable(question_with_options, answer):
    answer = answer.strip()
    # answer가 ①②③④⑤ 로 시작하면 퀴즈 출제 가능
    return bool(re.match(r'^[①②③④⑤]', answer))