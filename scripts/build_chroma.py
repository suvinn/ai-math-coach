"""
build_chroma.py — Problem 테이블 전체를 ChromaDB에 임베딩하여 저장

사용법 (프로젝트 루트에서):
    python scripts/build_chroma.py

주의사항:
- app/과 같은 레벨의 scripts/ 폴더에 두고 실행하세요
- GMS_KEY, GMS_URL 환경변수가 설정되어 있어야 합니다
- 최초 실행 시 OpenAI API 호출 비용이 발생합니다 (945개 기준 약 $0.01 미만)
- chroma_db/ 폴더가 이미 있으면 기존 collection을 삭제하고 새로 만듭니다
"""

import os
import sys
import time

# ── Django 환경 설정 ──────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()
# ────────────────────────────────────────────────────

import chromadb
from openai import OpenAI
from django.conf import settings
from quiz.models import Problem

CHROMA_PATH     = './chroma_db'
COLLECTION_NAME = 'problems'
EMBED_MODEL     = 'text-embedding-3-small'
BATCH_SIZE      = 100   # OpenAI API 한 번에 보낼 문서 수


def main():
    client = OpenAI(
        api_key=settings.GMS_KEY,
        base_url=settings.GMS_URL,
    )

    # ── ChromaDB 초기화 ──────────────────────────────
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    # 기존 collection 삭제 후 재생성 (재실행 시 중복 방지)
    existing = [c.name for c in chroma_client.list_collections()]
    if COLLECTION_NAME in existing:
        chroma_client.delete_collection(COLLECTION_NAME)
        print(f"기존 '{COLLECTION_NAME}' collection 삭제 완료")

    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={'hnsw:space': 'cosine'},
    )
    print(f"'{COLLECTION_NAME}' collection 생성 완료")

    # ── 문제 조회 ────────────────────────────────────
    # question_text가 없으면 임베딩 불가 → 제외
    problems = list(
        Problem.objects
        .filter(question_text__isnull=False)
        .exclude(question_text='')
        .values(
            'id', 'question_text', 'difficulty',
            'chapter_minor', 'problem_subtype', 'is_quizable',
        )
    )
    total = len(problems)
    print(f"임베딩 대상: {total}개 문제")

    # ── 배치 임베딩 & 저장 ──────────────────────────
    for batch_start in range(0, total, BATCH_SIZE):
        batch = problems[batch_start:batch_start + BATCH_SIZE]

        texts = [p['question_text'] for p in batch]

        # OpenAI 임베딩 API 호출
        response = client.embeddings.create(
            model=EMBED_MODEL,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]

        ids       = [p['id'] for p in batch]
        metadatas = [
            {
                'difficulty':      p['difficulty']      or '',
                'chapter_minor':   p['chapter_minor']   or '',
                'problem_subtype': p['problem_subtype'] or '',
                # ChromaDB metadata는 문자열/숫자/bool만 지원 → bool을 문자열로 저장
                'is_quizable':     str(p['is_quizable']),
            }
            for p in batch
        ]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        end = min(batch_start + BATCH_SIZE, total)
        print(f"  [{end}/{total}] 완료")

        # API rate limit 방지
        if end < total:
            time.sleep(0.5)

    print(f"\n✅ 완료 — ChromaDB에 {total}개 문제 임베딩 저장")
    print(f"   저장 경로: {os.path.abspath(CHROMA_PATH)}")


if __name__ == '__main__':
    main()