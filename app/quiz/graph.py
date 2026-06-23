from typing import TypedDict, List, Optional, Tuple
from openai import OpenAI
import chromadb
from django.conf import settings
from .models import Problem
from langgraph.graph import StateGraph, END


class CoachingState(TypedDict):
    session_id: int
    chapter_middle: str
    session_type: str
    solved_ids: List[str]
    wrong_problems: List[dict]   # [{problem_id, problem_subtype, question_text, chapter_minor}, ...]
    all_correct: bool

    top3: List[Tuple[str, int]]           # [(subtype, wrong_count), ...]
    ai_feedback: Optional[str]
    weak_subtypes_data: List[dict]        # [{subtype, wrong_count, total_count, recommendations}, ...]
    harder_recommendations: List[dict]



def analyze_node(state: CoachingState) -> dict:
    """wrong_problems를 subtype별로 집계해서 top3 산출"""
    if state['all_correct']:
        return {}  # 분기에서 처리하므로 여기선 별도 계산 없음

    from collections import Counter, defaultdict

    subtype_stats = defaultdict(lambda: {'wrong': 0, 'total': 0})
    for wp in state['wrong_problems']:
        subtype = wp['problem_subtype']
        subtype_stats[subtype]['wrong'] += 1
        subtype_stats[subtype]['total'] += wp.get('total_in_subtype', 1)

    weak_list = sorted(
        subtype_stats.items(),
        key=lambda x: x[1]['wrong'] / x[1]['total'],
        reverse=True
    )
    top3 = [(subtype, stats['wrong']) for subtype, stats in weak_list[:3]]

    return {'top3': top3}


def feedback_node(state: CoachingState) -> dict:
    client = OpenAI(api_key=settings.GMS_KEY, base_url=settings.GMS_URL)

    subtype_text = '\n'.join(
        f'{rank}. {subtype} ({wrong_count}개 틀림)'
        for rank, (subtype, wrong_count) in enumerate(state['top3'], start=1)
    )

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {'role': 'system', 'content': (
                '당신은 중학교 수학 학습 코치입니다. '
                '학생의 취약 유형을 분석해서 따뜻하고 구체적인 피드백을 제공해주세요. '
                '3문장 이내로 간결하게 작성해주세요.'
            )},
            {'role': 'user', 'content': f'학생이 다음 유형에서 틀렸습니다:\n{subtype_text}'}
        ],
        max_tokens=300,
    )

    # state를 직접 바꾸지 않고, "바뀐 부분만" dict로 반환
    return {'ai_feedback': response.choices[0].message.content}


def rag_node(state: CoachingState) -> dict:
    client        = OpenAI(api_key=settings.GMS_KEY, base_url=settings.GMS_URL)
    chroma_client = chromadb.PersistentClient(path='./chroma_db')
    collection    = chroma_client.get_collection('problems')

    weak_subtypes_data = []

    for rank, (subtype, wrong_count) in enumerate(state['top3'], start=1):
        # 이 subtype에 해당하는 오답 문제 하나를 쿼리 샘플로 사용
        sample = next(
            (wp for wp in state['wrong_problems'] if wp['problem_subtype'] == subtype),
            None
        )
        if sample is None:
            continue

        query_embedding = client.embeddings.create(
            model='text-embedding-3-small',
            input=[sample['question_text']],
        ).data[0].embedding

        def _query(where_filter):
            return collection.query(
                query_embeddings=[query_embedding], n_results=10, where=where_filter,
            )

        results = _query({'$and': [
            {'problem_subtype': {'$eq': subtype}},
            {'difficulty':      {'$eq': '하'}},
            {'is_quizable':     {'$eq': 'True'}},
        ]})
        recommended_ids = [pid for pid in results['ids'][0] if pid not in state['solved_ids']][:3]

        if not recommended_ids:
            results = _query({'$and': [
                {'problem_subtype': {'$eq': subtype}},
                {'is_quizable':     {'$eq': 'True'}},
            ]})
            recommended_ids = [pid for pid in results['ids'][0] if pid not in state['solved_ids']][:3]

        if not recommended_ids:
            results = _query({'$and': [
                {'chapter_minor': {'$eq': sample['chapter_minor']}},
                {'is_quizable':   {'$eq': 'True'}},
            ]})
            recommended_ids = [pid for pid in results['ids'][0] if pid not in state['solved_ids']][:3]

        weak_subtypes_data.append({
            'rank': rank,
            'problem_subtype': subtype,
            'wrong_count': wrong_count,
            'recommended_problem_ids': recommended_ids,  # ← DB 객체 아닌 ID 리스트만
        })

    return {'weak_subtypes_data': weak_subtypes_data}


def harder_node(state: CoachingState) -> dict:
    if state['session_type'] in ['normal', 'review_1']:
        next_difficulties = ['중', '상']
    else:
        next_difficulties = ['상']

    harder_problems = list(Problem.objects.filter(
        chapter_middle=state['chapter_middle'],
        difficulty__in=next_difficulties,
        is_quizable=True,
    ).exclude(id__in=state['solved_ids'])[:3])

    recommendations = [
        {
            'problem_id': p.id,
            'difficulty': p.difficulty,
            'reason': f'현재 수준보다 높은 난이도 도전 문제 (난이도: {p.difficulty})',
        }
        for p in harder_problems
    ]

    return {
        'ai_feedback': '모든 문제를 맞혔어요! 더 어려운 문제에 도전해보세요.',
        'harder_recommendations': recommendations,
    }


def route_after_analyze(state: CoachingState) -> str:
    """다음 노드를 문자열로 반환 — 그래프가 이 반환값으로 분기"""
    if state['all_correct']:
        return 'harder'
    return 'feedback'


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
        {'feedback': 'feedback', 'harder': 'harder'}
    )
    graph.add_edge('feedback', 'rag')
    graph.add_edge('rag', END)
    graph.add_edge('harder', END)

    return graph.compile()

coaching_graph = build_coaching_graph()