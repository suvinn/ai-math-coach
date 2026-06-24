# LangGraph 기반 AI 코칭 파이프라인.
# views.py의 QuizSessionRecommendationsView에서 coaching_graph.invoke()로 호출.
#
# 그래프 흐름:
#   analyze ──(all_correct?)──▶ harder ──▶ END
#            └──(has_wrong)──▶ feedback ──▶ rag ──▶ END
#
# invoke() 반환값(state)에서 views.py가 꺼내 쓰는 키:
#   all_correct, ai_feedback,
#   weak_subtypes_data  (오답 있을 때)
#   harder_problem_ids  (전부 맞았을 때)

from typing import TypedDict, List, Optional, Tuple
from openai import OpenAI
import chromadb
from django.conf import settings
from .models import Problem
from langgraph.graph import StateGraph, END


class CoachingState(TypedDict):
    # ── 입력 (views.py가 채워줌) ──────────────
    session_id:     int
    chapter_middle: str
    session_type:   str
    solved_ids:     List[str]
    all_correct:    bool

    # wrong_problems: 오답 문제 목록
    # [{ problem_id, problem_subtype, question_text, chapter_minor, total_in_subtype }]
    wrong_problems: List[dict]

    # ── 노드 간 중간값 ────────────────────────
    # [(subtype, wrong_count), ...]  — analyze_node가 채움
    top3: List[Tuple[str, int]]

    # ── 출력 (views.py가 읽어 DB 저장) ───────
    ai_feedback: Optional[str]

    # 오답 있을 때: 취약 유형별 추천 문제 데이터
    # [{
    #   rank, problem_subtype, wrong_count,
    #   s1_ids:  [str]  — 하 난이도, 최대 2개 (index 0 = s1용, index 1 = s2용)
    #   mid_ids: [str]  — 중 난이도, 최대 1개 (s1mid용)
    # }]
    weak_subtypes_data: List[dict]

    # 전부 맞았을 때: 더 어려운 문제 ID 목록
    # [{ problem_id, difficulty, reason }]
    harder_problem_ids: List[dict]


def _get_client():
    return OpenAI(api_key=settings.GMS_KEY, base_url=settings.GMS_URL)


def _get_collection():
    chroma_client = chromadb.PersistentClient(path='./chroma_db')
    return chroma_client.get_collection('problems')


def _backfill_ids(collection, query_embedding, problem_subtype,
                  chapter_minor, exclude_ids, limit, preferred_difficulty):
    """
    ChromaDB에서 유사 문제 ID를 limit개까지 단계적으로 채운다.
    1티어: subtype + preferred_difficulty
    2티어: subtype (난이도 무관)
    — subtype이 다른 문제로는 절대 채우지 않음 (보완 문제는 같은 유형이어야 하므로)
    """
    exclude = set(exclude_ids)

    def _query(where_filter, already):
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=20,
            where=where_filter,
        )
        return [pid for pid in result['ids'][0]
                if pid not in exclude and pid not in already]

    chosen = []
    tiers = [
        {'$and': [
            {'problem_subtype': {'$eq': problem_subtype}},
            {'difficulty':      {'$eq': preferred_difficulty}},
            {'is_quizable':     {'$eq': 'True'}},
        ]},
        {'$and': [
            {'problem_subtype': {'$eq': problem_subtype}},
            {'is_quizable':     {'$eq': 'True'}},
        ]},
    ]
    for tier in tiers:
        if len(chosen) >= limit:
            break
        chosen.extend(_query(tier, chosen)[:limit - len(chosen)])
    return chosen


def analyze_node(state: CoachingState) -> dict:
    """오답을 subtype별로 집계해 top3 산출. all_correct면 아무것도 안 함."""
    if state['all_correct']:
        return {}

    from collections import defaultdict

    subtype_stats = defaultdict(lambda: {'wrong': 0, 'total': 0})
    for wp in state['wrong_problems']:
        subtype = wp['problem_subtype']
        subtype_stats[subtype]['wrong'] += 1
        subtype_stats[subtype]['total'] += wp.get('total_in_subtype', 1)

    weak_list = sorted(
        subtype_stats.items(),
        key=lambda x: x[1]['wrong'] / x[1]['total'],
        reverse=True,
    )
    top3 = [(subtype, stats['wrong']) for subtype, stats in weak_list[:3]]
    return {'top3': top3}


def feedback_node(state: CoachingState) -> dict:
    """취약 유형 Top3를 바탕으로 LLM 피드백 생성."""
    client = _get_client()

    subtype_text = '\n'.join(
        f'{rank}. {subtype} ({wrong_count}개 틀림)'
        for rank, (subtype, wrong_count) in enumerate(state['top3'], start=1)
    )

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {
                'role': 'system',
                'content': (
                    '당신은 중학교 수학 학습 코치입니다. '
                    '학생의 취약 유형을 분석해서 따뜻하고 구체적인 피드백을 제공해주세요. '
                    '3문장 이내로 간결하게 작성해주세요.'
                ),
            },
            {
                'role': 'user',
                'content': f'학생이 다음 유형에서 틀렸습니다:\n{subtype_text}',
            },
        ],
        max_tokens=300,
    )
    return {'ai_feedback': response.choices[0].message.content}


def rag_node(state: CoachingState) -> dict:
    """
    취약 유형별로 보완 학습용 문제를 RAG로 추천.
    유형당 출력:
      s1_ids:  하 난이도 최대 2개 [s1용, s2용]
      mid_ids: 중 난이도 최대 1개 [s1mid용]
    views.py가 이 ID들로 Recommendation 레코드를 생성하고
    order_index를 s1(1) → mid(2) → s2(3) 순으로 저장한다.
    """
    client     = _get_client()
    collection = _get_collection()

    weak_subtypes_data = []

    for rank, (subtype, wrong_count) in enumerate(state['top3'], start=1):
        sample = next(
            (wp for wp in state['wrong_problems']
             if wp['problem_subtype'] == subtype),
            None,
        )
        if sample is None:
            continue

        # 오답 문제 텍스트로 임베딩 생성
        query_embedding = client.embeddings.create(
            model='text-embedding-3-small',
            input=[sample['question_text']],
        ).data[0].embedding

        chapter_minor = sample.get('chapter_minor', '')

        # 하 난이도 2개 (s1용 + s2용)
        s1_ids = _backfill_ids(
            collection, query_embedding, subtype, chapter_minor,
            exclude_ids=state['solved_ids'],
            limit=2,
            preferred_difficulty='하',
        )

        # 중 난이도 1개 (s1mid용) — 하 추천 문제도 제외
        mid_ids = _backfill_ids(
            collection, query_embedding, subtype, chapter_minor,
            exclude_ids=list(set(state['solved_ids']) | set(s1_ids)),
            limit=1,
            preferred_difficulty='중',
        )

        weak_subtypes_data.append({
            'rank':            rank,
            'problem_subtype': subtype,
            'wrong_count':     wrong_count,
            's1_ids':          s1_ids,   # [s1용, s2용]
            'mid_ids':         mid_ids,  # [s1mid용]
        })

    return {'weak_subtypes_data': weak_subtypes_data}


def harder_node(state: CoachingState) -> dict:
    """전부 맞았을 때 더 어려운 문제 3개 추천."""
    if state['session_type'] in ('normal', 'review_1'):
        next_difficulties = ['중', '상']
    else:
        next_difficulties = ['상']

    harder_problems = list(
        Problem.objects.filter(
            chapter_middle=state['chapter_middle'],
            difficulty__in=next_difficulties,
            is_quizable=True,
        ).exclude(id__in=state['solved_ids'])[:3]
    )

    harder_problem_ids = [
        {
            'problem_id': p.id,
            'difficulty': p.difficulty,
            'reason':     f'현재 수준보다 높은 난이도 도전 문제 (난이도: {p.difficulty})',
        }
        for p in harder_problems
    ]

    return {
        'ai_feedback':       '모든 문제를 맞혔어요! 더 어려운 문제에 도전해보세요.',
        'harder_problem_ids': harder_problem_ids,
    }


def route_after_analyze(state: CoachingState) -> str:
    return 'harder' if state['all_correct'] else 'feedback'


def build_coaching_graph():
    graph = StateGraph(CoachingState)

    graph.add_node('analyze',  analyze_node)
    graph.add_node('feedback', feedback_node)
    graph.add_node('rag',      rag_node)
    graph.add_node('harder',   harder_node)

    graph.set_entry_point('analyze')

    graph.add_conditional_edges(
        'analyze',
        route_after_analyze,
        {'feedback': 'feedback', 'harder': 'harder'},
    )
    graph.add_edge('feedback', 'rag')
    graph.add_edge('rag',      END)
    graph.add_edge('harder',   END)

    return graph.compile()

coaching_graph = build_coaching_graph()