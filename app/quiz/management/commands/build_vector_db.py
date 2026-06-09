import os
from django.core.management.base import BaseCommand
from django.conf import settings
from quiz.models import Problem
from openai import OpenAI
import chromadb

class Command(BaseCommand):
    help = '전체 문제를 임베딩해서 ChromaDB에 저장'

    def handle(self, *args, **options):
        client = OpenAI(
            api_key=settings.GMS_KEY,
            base_url=settings.GMS_URL
        )

        # ChromaDB 초기화 (app/ 폴더 안에 저장)
        chroma_client = chromadb.PersistentClient(path='./chroma_db')

        # 기존 컬렉션 있으면 삭제 후 재생성
        try:
            chroma_client.delete_collection('problems')
        except:
            pass
        collection = chroma_client.create_collection('problems')

        problems = Problem.objects.all()
        total = problems.count()
        self.stdout.write(f'총 {total}개 문제 임베딩 시작...')

        # 한 번에 너무 많이 보내면 API 한도 초과 — 100개씩 배치 처리
        batch_size = 100
        problem_list = list(problems)

        for i in range(0, total, batch_size):
            batch = problem_list[i:i + batch_size]

            # 빈 문제 건너뛰기
            valid_batch = [
                p for p in batch
                if p.question_text and p.question_text.strip()
            ]

            # 임베딩할 텍스트: question_text 사용
            texts = [p.question_text for p in valid_batch]

            # OpenAI 임베딩 API 호출
            response = client.embeddings.create(
                model='text-embedding-3-small',
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]

            # ChromaDB에 저장
            collection.add(
                ids=[str(p.id) for p in valid_batch],
                embeddings=embeddings,
                metadatas=[
                    {
                        "problem_subtype": p.problem_subtype,
                        "chapter_minor": p.chapter_minor,
                        "chapter_middle": p.chapter_middle,
                        "difficulty": p.difficulty,
                        "is_quizable": str(p.is_quizable),
                    }
                    for p in valid_batch
                ],
                documents=texts,
            )

            self.stdout.write(f'  {min(i + batch_size, total)}/{total} 완료')

        self.stdout.write(self.style.SUCCESS('벡터 DB 구축 완료!'))