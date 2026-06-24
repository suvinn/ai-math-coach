from django.contrib.auth import authenticate, login, logout, get_user_model
from django.middleware.csrf import get_token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.utils.decorators import method_decorator
from .serializers import RegisterSerializer, UserSerializer, ProblemPublicSerializer, ProblemWithAnswerSerializer
from .models import Problem, QuizSession, SessionProblem, SessionResult, WeaknessReport, WeakSubtype, Recommendation, SubtypeMastery
import random
from datetime import date, timedelta
from collections import defaultdict
from openai import OpenAI
import chromadb
from django.conf import settings


def _serialize_problem(problem, request, extra_fields=None):
    """Problem 객체를 퀴즈 풀이용 dict로 변환한다.

    - ProblemPublicSerializer를 단일 진입점으로 사용해 assets 직렬화 중복을 제거한다.
    - extra_fields: {'order': sp.order_index} 처럼 Problem 모델 밖의 필드를 병합할 때 사용.
    """
    context = {'request': request}
    if extra_fields:
        context['extra_fields'] = extra_fields
    return ProblemPublicSerializer(problem, context=context).data


def _serialize_problem_with_answer(problem, request, extra_fields=None):
    """오답/채점 조회용 — answer, grading_answer, explanation 포함."""
    context = {'request': request}
    if extra_fields:
        context['extra_fields'] = extra_fields
    return ProblemWithAnswerSerializer(problem, context=context).data


def _make_warning(requested, actual):
    """요청 문제 수보다 실제 출제 수가 적을 때 안내 메시지 반환. 같으면 None."""
    if actual < requested:
        return (
            f'해당 범위에 문제가 {actual}개밖에 없어서 '
            f'{actual}문제로 시작해요.'
        )
    return None


User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'status': 'error', 'message': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        # username 중복 체크
        if User.objects.filter(username=serializer.validated_data['username']).exists():
            return Response({'status': 'error', 'message': '이미 존재하는 아이디입니다.'},
                            status=status.HTTP_409_CONFLICT)

        user = serializer.save()

        response_data = {
            'username': user.username,
            'name':     user.first_name,
        }

        return Response({'status': 'success', 'data': response_data},
                        status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'status': 'error', 'message': 'username과 password를 입력해주세요.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({'status': 'error', 'message': '아이디 또는 비밀번호가 틀렸습니다.'},
                            status=status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        return Response({
            'status': 'success',
            'data': {
                # 'user_id': user.id,
                'username': user.username,
                'name': user.first_name,
            }
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'status': 'success', 'message': '로그아웃 되었습니다.'})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        return Response({
            'status': 'success',
            'data': {
                'username':               u.username,
                'name':                   u.first_name,
                'grade':                  u.grade,
                'current_chapter_major':  u.current_chapter_major,
                'current_chapter_middle': u.current_chapter_middle,
            }
        })


class ChapterListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # DB에서 챕터 정보 distinct로 추출
        problems = Problem.objects.values(
            'chapter_major', 'chapter_middle', 'chapter_minor'
        ).distinct().order_by('chapter_major', 'chapter_middle', 'chapter_minor')

        # 중첩 구조로 가공
        result = {}
        for p in problems:
            major = p['chapter_major']
            middle = p['chapter_middle']
            minor = p['chapter_minor']

            if major not in result:
                result[major] = {}
            if middle not in result[major]:
                result[major][middle] = []
            result[major][middle].append(minor)

        data = [
            {
                'chapter_major': major,
                'chapter_middles': [
                    {
                        'chapter_middle': middle,
                        'chapter_minors': minors
                    }
                    for middle, minors in middles.items()
                ]
            }
            for major, middles in result.items()
        ]

        return Response({'status': 'success', 'data': data})


class ChapterProblemCountView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.db.models import Count

        rows = Problem.objects.values(
            'chapter_major', 'chapter_middle', 'chapter_minor'
        ).annotate(count=Count('id')).order_by(
            'chapter_major', 'chapter_middle', 'chapter_minor'
        )

        data = [
            {
                'chapter_major':  r['chapter_major'],
                'chapter_middle': r['chapter_middle'],
                'chapter_minor':  r['chapter_minor'],
                'count':          r['count'],
            }
            for r in rows
        ]

        return Response({'status': 'success', 'data': data})


class QuizSessionCreateView(APIView):

    def post(self, request):
        is_diagnosis      = request.data.get('mode') == 'diagnosis'
        problem_ids       = request.data.get('problem_ids')  # 보완 풀이: AI가 추천한 문제 그대로 세션 구성
        chapter_major     = request.data.get('chapter_major')
        chapter_middle    = request.data.get('chapter_middle')
        chapter_minor     = request.data.get('chapter_minor')
        problem_count     = request.data.get('problem_count')
        parent_session_id = request.data.get('parent_session_id')  # optional
        # 보완 단계 구분: 's1'(보완1·하), 's1mid'(보완1·중), 's2'(보완2·하)
        review_step       = request.data.get('review_step')        # optional
        # 보완 세션에서 제외할 문제 ID 목록 (이미 푼 문제 재출제 방지)
        exclude_ids       = request.data.get('exclude_ids', [])

        if problem_ids and not parent_session_id:
            return Response(
                {'status': 'error', 'message': 'problem_ids로 세션을 만들려면 parent_session_id가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not is_diagnosis and not problem_ids and (not chapter_major or not chapter_middle or not problem_count):
            return Response(
                {'status': 'error', 'message': 'chapter_major, chapter_middle, problem_count는 필수입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not problem_ids:
            try:
                problem_count = int(problem_count)
                if problem_count < 1:
                    raise ValueError
            except (ValueError, TypeError):
                return Response(
                    {'status': 'error', 'message': 'problem_count는 1 이상의 정수여야 합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 빠른 진단: 단원 선택 없이 바로 시작
        # - 진도 입력 O → current_chapter_middle 범위에서 하 70% + 중 30%, 10문제
        # - 진도 입력 X → 전체 단원에서 대단원별 균등 추출, 10문제
        # - 문제가 부족하면 실제 출제 가능한 수와 안내 메시지를 함께 반환
        if is_diagnosis:
            has_chapter = bool(
                request.user.current_chapter_major and
                request.user.current_chapter_middle
            )
            if has_chapter:
                # 진도 입력 O → 해당 중단원에서 하 70% + 중 30%
                base_filter = dict(
                    chapter_major  = request.user.current_chapter_major,
                    chapter_middle = request.user.current_chapter_middle,
                    is_quizable    = True,
                )
                DIAGNOSIS_COUNT = problem_count
                problems_low = list(Problem.objects.filter(**base_filter, difficulty='하'))
                problems_mid = list(Problem.objects.filter(**base_filter, difficulty='중'))
                low_count    = round(DIAGNOSIS_COUNT * 0.7)
                mid_count    = DIAGNOSIS_COUNT - low_count
                selected_low = random.sample(problems_low, min(low_count, len(problems_low)))
                selected_mid = random.sample(problems_mid, min(mid_count, len(problems_mid)))
                selected     = selected_low + selected_mid
                random.shuffle(selected)
                chapter_major  = request.user.current_chapter_major
                chapter_middle = request.user.current_chapter_middle
            else:
                # 진도 입력 X → 전체 단원 균등 추출
                selected       = _select_diagnosis_problems(problem_count)
                chapter_major  = '전체 진단'
                chapter_middle = '전체 진단'

            if not selected:
                return Response(
                    {'status': 'error', 'message': '출제 가능한 문제가 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            session = QuizSession.objects.create(
                user=request.user,
                chapter_major=chapter_major,
                chapter_middle=chapter_middle,
                chapter_minor='',
                problem_count=len(selected),
                session_type='normal',
            )
            for idx, problem in enumerate(selected):
                SessionProblem.objects.create(
                    session=session,
                    problem=problem,
                    order_index=idx + 1,
                )

            warning = _make_warning(problem_count, len(selected))
            resp = {
                'session_id':      session.id,
                'session_type':    session.session_type,
                'status':          session.status,
                'requested_count': problem_count,
                'actual_count':    len(selected),
                'created_at':      session.created_at,
            }
            if warning:
                resp['warning'] = warning
            return Response({'status': 'success', 'data': resp},
                            status=status.HTTP_201_CREATED)
        
        session_type   = 'normal'
        parent_session = None

        if parent_session_id:
            try:
                parent_session = QuizSession.objects.get(
                    id=parent_session_id,
                    user=request.user
                )
            except QuizSession.DoesNotExist:
                return Response(
                    {'status': 'error', 'message': '부모 세션을 찾을 수 없습니다.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            if parent_session.session_type == 'normal':
                session_type = 'review_1'
            elif parent_session.session_type == 'review_1':
                session_type = 'review_2'
            # review_2 이후는 프론트에서 explain → redo 로 직접 처리 (세션 생성 없음)

        # 보완 풀이: AI 코칭이 추천한 문제 id 그대로 세션 구성 (단원 필터 없이, 순서 유지)
        if problem_ids:
            pool = Problem.objects.filter(id__in=problem_ids, is_quizable=True)
            by_id = {p.id: p for p in pool}
            selected = [by_id[pid] for pid in problem_ids if pid in by_id]

            if not selected:
                return Response(
                    {'status': 'error', 'message': '추천된 문제를 찾을 수 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            session = QuizSession.objects.create(
                user=request.user,
                chapter_major=parent_session.chapter_major,
                chapter_middle=parent_session.chapter_middle,
                chapter_minor=parent_session.chapter_minor or '',
                problem_count=len(selected),
                session_type=session_type,
                parent_session=parent_session,
            )
            for idx, problem in enumerate(selected):
                SessionProblem.objects.create(
                    session=session,
                    problem=problem,
                    order_index=idx + 1,
                )

            warning = _make_warning(len(problem_ids), len(selected))
            resp = {
                'session_id':      session.id,
                'session_type':    session.session_type,
                'status':          session.status,
                'requested_count': len(problem_ids),
                'actual_count':    len(selected),
                'created_at':      session.created_at,
            }
            if warning:
                resp['warning'] = warning
            return Response({'status': 'success', 'data': resp},
                            status=status.HTTP_201_CREATED)

        base_filter = dict(
            chapter_major=chapter_major,
            chapter_middle=chapter_middle,
            is_quizable=True,
        )
        if chapter_minor:
            base_filter['chapter_minor'] = chapter_minor

        if session_type == 'normal':
            # 첫 세션: 하 70% + 중 30%, 상 제외
            problems_low = list(Problem.objects.filter(**base_filter, difficulty='하'))
            problems_mid = list(Problem.objects.filter(**base_filter, difficulty='중'))

            if not problems_low and not problems_mid:
                return Response(
                    {'status': 'error', 'message': '해당 범위에 문제가 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            low_count = round(problem_count * 0.7)
            mid_count = problem_count - low_count

            selected_low = random.sample(problems_low, min(low_count, len(problems_low)))
            selected_mid = random.sample(problems_mid, min(mid_count, len(problems_mid)))
            selected     = selected_low + selected_mid
            random.shuffle(selected)

        elif session_type in ('review_1', 'review_2'):
            # 취약 subtype 1개에서 1문제만 출제. 단계별 난이도:
            #   s1    → 하  (보완 1단계 첫 문제)     → Recommendation order_index=1
            #   s1mid → 중  (s1 정답 시 난이도 업)   → Recommendation order_index=2
            #   s2    → 하  (보완 2단계, s1 오답 시)  → Recommendation order_index=3
            if review_step == 's1mid':
                target_difficulty = '중'
                rec_order_index   = 2
            elif review_step == 's2':
                target_difficulty = '하'
                rec_order_index   = 3
            else:  # s1 (기본)
                target_difficulty = '하'
                rec_order_index   = 1

            weak_subtypes  = _get_weak_subtypes(parent_session)
            target_subtype = weak_subtypes[0] if weak_subtypes else None

            # ── 1순위: 원본 세션 WeaknessReport → Recommendation에서 RAG 추천 문제 사용
            selected = []
            try:
                origin_session = parent_session
                # review_2의 부모는 review_1이므로 한 단계 더 올라가 origin 세션 참조
                if origin_session and origin_session.session_type in ('review_1', 'review_2'):
                    origin_session = origin_session.parent_session

                if origin_session and hasattr(origin_session, 'weakness_report'):
                    report_obj = origin_session.weakness_report
                    weak_obj = report_obj.weak_subtypes.filter(
                        problem_subtype=target_subtype
                    ).first() if target_subtype else None

                    if weak_obj:
                        rec = weak_obj.recommendations.filter(
                            order_index=rec_order_index
                        ).select_related('problem').first()

                        if rec and rec.problem.id not in exclude_ids:
                            selected = [rec.problem]
            except (Exception,):
                pass  # WeaknessReport 없거나 기타 오류면 폴백으로

            # ── 2순위: RAG 추천 없으면 DB에서 랜덤 추출 (폴백)
            if not selected:
                q_filter = {**base_filter, 'difficulty': target_difficulty}
                if target_subtype:
                    q_filter['problem_subtype'] = target_subtype

                problems = list(
                    Problem.objects.filter(**q_filter).exclude(id__in=exclude_ids)
                )
                if not problems and target_subtype:
                    problems = list(
                        Problem.objects.filter(**base_filter, difficulty=target_difficulty)
                        .exclude(id__in=exclude_ids)
                    )

                if not problems:
                    return Response(
                        {'status': 'error', 'message': '출제 가능한 보완 문제가 없습니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                selected = [random.choice(problems)]

        # 6. 문제가 0개면 에러
        if not selected:
            return Response(
                {'status': 'error', 'message': '해당 범위에 출제 가능한 문제가 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        actual_count = len(selected)

        session = QuizSession.objects.create(
            user=request.user,
            chapter_major=chapter_major,
            chapter_middle=chapter_middle,
            chapter_minor=chapter_minor or '',
            problem_count=actual_count,
            session_type=session_type,
            parent_session=parent_session,
        )

        for idx, problem in enumerate(selected):
            SessionProblem.objects.create(
                session=session,
                problem=problem,
                order_index=idx + 1,
            )

        warning = _make_warning(problem_count, actual_count)
        resp = {
            'session_id':      session.id,
            'session_type':    session.session_type,
            'review_step':     review_step or ('s1' if session_type == 'review_1' else None),
            'status':          session.status,
            'requested_count': problem_count,
            'actual_count':    actual_count,
            'created_at':      session.created_at,
        }
        if warning:
            resp['warning'] = warning
        return Response({'status': 'success', 'data': resp},
                        status=status.HTTP_201_CREATED)


def _select_diagnosis_problems(total_count):
    """대단원별로 골고루 랜덤 추출 (특정 단원에 쏠리지 않게). 단원 내 난이도는 가리지 않음."""
    majors = list(
        Problem.objects.filter(is_quizable=True)
        .values_list('chapter_major', flat=True)
        .distinct()
    )
    if not majors:
        return []
    random.shuffle(majors)

    n = len(majors)
    base = total_count // n
    remainder = total_count % n
    quotas = {m: base + (1 if i < remainder else 0) for i, m in enumerate(majors)}

    pools = {m: list(Problem.objects.filter(is_quizable=True, chapter_major=m)) for m in majors}

    selected = []
    shortfall = 0
    for m in majors:
        pool = pools[m]
        take = min(quotas[m], len(pool))
        if take:
            selected.extend(random.sample(pool, take))
        shortfall += quotas[m] - take

    if shortfall > 0:
        chosen_ids = {p.id for p in selected}
        remaining_pool = [p for m in majors for p in pools[m] if p.id not in chosen_ids]
        extra = min(shortfall, len(remaining_pool))
        if extra:
            selected.extend(random.sample(remaining_pool, extra))

    random.shuffle(selected)
    return selected


def _get_weak_subtypes(session):
    """세션의 오답 문제에서 취약 subtype 목록 추출"""
    from collections import Counter
    wrong_results = SessionResult.objects.filter(
        session=session,
        is_correct=False
    ).select_related('problem')

    counter = Counter(r.problem.problem_subtype for r in wrong_results)
    return [subtype for subtype, _ in counter.most_common(3)]


class QuizSessionProblemsView(APIView):

    def get(self, request, session_id):
        try:
            session = QuizSession.objects.get(id=session_id)
        except QuizSession.DoesNotExist:
            return Response(
                {'status': 'error', 'message': '세션을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if session.user != request.user:
            return Response(
                {'status': 'error', 'message': '접근 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        session_problems = SessionProblem.objects.filter(
            session=session
        ).select_related('problem').prefetch_related('problem__assets').order_by('order_index')

        problems = [
            _serialize_problem(sp.problem, request, extra_fields={'order': sp.order_index})
            for sp in session_problems
        ]

        return Response({
            'status': 'success',
            'data': {
                'session_id': session.id,
                'status':     session.status,
                'total':      len(problems),
                'problems':   problems,
            }
        })


class QuizSessionSubmitView(APIView):

    def post(self, request, session_id):
        # 1. 세션 존재 여부 확인
        try:
            session = QuizSession.objects.get(id=session_id)
        except QuizSession.DoesNotExist:
            return Response(
                {'status': 'error', 'message': '세션을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. 본인 세션인지 확인
        if session.user != request.user:
            return Response(
                {'status': 'error', 'message': '접근 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 3. 이미 제출된 세션인지 확인
        if session.status == 'completed':
            return Response(
                {'status': 'error', 'message': '이미 제출된 세션입니다.'},
                status=status.HTTP_409_CONFLICT
            )

        # 4. 답안 데이터 꺼내기
        answers = request.data.get('answers', [])
        if not answers:
            return Response(
                {'status': 'error', 'message': 'answers가 비어있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 5. 이 세션에 출제된 문제 목록 (정답 확인용)
        session_problems = SessionProblem.objects.filter(
            session=session
        ).select_related('problem')

        # problem_id → Problem 객체 딕셔너리로 변환 (빠른 조회용)
        problem_map = {sp.problem.id: sp.problem for sp in session_problems}

        # 6. 채점
        results = []
        score = 0

        for answer in answers:
            problem_id  = answer.get('problem_id')
            user_answer = answer.get('user_answer', '').strip()

            # 세션에 없는 문제 ID가 들어오면 무시
            if problem_id not in problem_map:
                continue

            problem    = problem_map[problem_id]
            correct_label = problem.grading_answer or problem.answer.strip()
            if problem.is_multi_answer:
                submitted = set(s.strip() for s in user_answer.split(','))
                correct   = set(correct_label.split(','))
                is_correct = (submitted == correct)
            else:
                is_correct = (user_answer == correct_label)

            if is_correct:
                score += 1

            # SessionResult 저장
            SessionResult.objects.create(
                session=session,
                problem=problem,
                student_answer=user_answer,
                is_correct=is_correct,
            )

            results.append({
                'problem_id':      problem_id,
                'user_answer':     user_answer,
                'correct_answer':  problem.answer,
                'grading_answer':  correct_label,  # 채점에 쓰인 깨끗한 라벨(①②③ 등) — 프론트 정오답 표시용
                'is_correct':      is_correct,
                'explanation':     problem.explanation,
                'problem_subtype': problem.problem_subtype,
                'difficulty':      problem.difficulty,
            })

        # 7. 세션 상태 업데이트
        session.status = 'completed'
        session.score  = score
        session.save()

        # 8. SubtypeMastery 갱신 ← 추가
        _update_subtype_mastery(request.user, results)

        # 9. 유저 통계 갱신 (streak, total_solved) ← 추가
        _update_user_stats(request.user, len(results))

        return Response({
            'status': 'success',
            'data': {
                'session_id': session.id,
                'score':      score,
                'total':      len(results),
                'accuracy':   round(score / len(results), 2) if results else 0,
                'results':    results,
            }
        })


def _update_subtype_mastery(user, results):
    """
    채점 결과를 SubtypeMastery에 반영.
    subtype별로 맞은 수 / 총 수를 누적하고 마스터 여부를 판정.
    """
    # 이번 세션 결과를 subtype별로 집계
    subtype_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
    for r in results:
        subtype = r['problem_subtype']
        subtype_stats[subtype]['total']   += 1
        subtype_stats[subtype]['correct'] += 1 if r['is_correct'] else 0

    for subtype, stats in subtype_stats.items():
        mastery, _ = SubtypeMastery.objects.get_or_create(
            user=user,
            problem_subtype=subtype,
            defaults={'total_attempts': 0, 'correct_count': 0}
        )

        prev_accuracy = (
            mastery.correct_count / mastery.total_attempts
            if mastery.total_attempts > 0 else None
        )

        # 누적값 업데이트
        mastery.total_attempts += stats['total']
        mastery.correct_count  += stats['correct']

        new_accuracy = mastery.correct_count / mastery.total_attempts

        # 마스터 판정: 누적 정답률 80% 이상 + 최소 3문제 이상 풀었을 때
        was_mastered = mastery.mastered
        if not was_mastered and new_accuracy >= 0.8 and mastery.total_attempts >= 3:
            mastery.mastered        = True
            mastery.accuracy_before = round(prev_accuracy, 2) if prev_accuracy else None
            mastery.accuracy_after  = round(new_accuracy, 2)

        mastery.save()


def _update_user_stats(user, solved_count):
    """
    streak(연속 학습일)과 total_solved(누적 푼 문제 수) 업데이트.
    오늘 이미 학습했으면 streak 중복 증가 방지.
    """
    today = date.today()

    # total_solved 누적
    user.total_solved += solved_count

    # streak 계산
    if user.last_active_date is None:
        # 첫 학습
        user.streak = 1
    elif user.last_active_date == today:
        # 오늘 이미 학습함 → streak 변경 없음
        pass
    elif (today - user.last_active_date).days == 1:
        # 어제 학습 → 연속
        user.streak += 1
    else:
        # 하루 이상 공백 → streak 초기화
        user.streak = 1

    user.last_active_date = today
    user.save()


class QuizSessionWrongAnswersView(APIView):

    def get(self, request, session_id):
        try:
            session = QuizSession.objects.get(id=session_id)
        except QuizSession.DoesNotExist:
            return Response(
                {'status': 'error', 'message': '세션을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if session.user != request.user:
            return Response(
                {'status': 'error', 'message': '접근 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if session.status != 'completed':
            return Response(
                {'status': 'error', 'message': '아직 제출되지 않은 세션입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        wrong_results = SessionResult.objects.filter(
            session=session,
            is_correct=False
        ).select_related('problem').prefetch_related('problem__assets')

        wrong_problems = [
            _serialize_problem_with_answer(
                result.problem, request,
                extra_fields={'user_answer': result.student_answer},
            )
            for result in wrong_results
        ]

        return Response({
            'status': 'success',
            'data': {
                'session_id':    session.id,
                'wrong_count':   len(wrong_problems),
                'wrong_problems': wrong_problems,
            }
        })


class QuizSessionAnalysisView(APIView):

    def get(self, request, session_id):
        try:
            session = QuizSession.objects.get(id=session_id)
        except QuizSession.DoesNotExist:
            return Response(
                {'status': 'error', 'message': '세션을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if session.user != request.user:
            return Response(
                {'status': 'error', 'message': '접근 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if session.status != 'completed':
            return Response(
                {'status': 'error', 'message': '아직 제출되지 않은 세션입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = SessionResult.objects.filter(
            session=session
        ).select_related('problem')

        total = results.count()
        score = results.filter(is_correct=True).count()

        wrong_results = results.filter(is_correct=False)
        if not wrong_results.exists():
            return Response({
                'status': 'success',
                'data': {
                    'session_id':   session.id,
                    'score':        score,
                    'total':        total,
                    'accuracy':     1.0,
                    'all_correct':  True,
                    'weak_subtypes': [],
                }
            })

        # subtype별 집계 (최대 3개)
        subtype_stats = defaultdict(lambda: {'wrong': 0, 'total': 0})
        for r in results:
            subtype = r.problem.problem_subtype
            subtype_stats[subtype]['total'] += 1
            if not r.is_correct:
                subtype_stats[subtype]['wrong'] += 1

        # 틀린 문제가 있는 subtype만 필터링 후 accuracy 낮은 순 정렬
        weak_list = [
            (subtype, stats)
            for subtype, stats in subtype_stats.items()
            if stats['wrong'] > 0
        ]
        weak_list.sort(key=lambda x: x[1]['wrong'] / x[1]['total'], reverse=True)  # accuracy 낮은 순

        top3 = weak_list[:3]

        weak_subtypes = []
        for rank, (subtype, stats) in enumerate(top3, start=1):
            accuracy = round((stats['total'] - stats['wrong']) / stats['total'], 2)
            weak_subtypes.append({
                'rank':            rank,
                'problem_subtype': subtype,
                'wrong_count':     stats['wrong'],
                'total_count':     stats['total'],
                'accuracy':        accuracy,
            })

        return Response({
            'status': 'success',
            'data': {
                'session_id':    session.id,
                'score':         score,
                'total':         total,
                'accuracy':      round(score / total, 2),
                'all_correct':   False,
                'weak_subtypes': weak_subtypes,
            }
        })


class UserHistoryView(APIView):

    def get(self, request):
        # 1. 기존 세션 목록 (최신순)
        sessions = QuizSession.objects.filter(
            user=request.user,
            status='completed'
        ).order_by('-created_at')

        session_list = []
        for session in sessions:
            session_list.append({
                'session_id':     session.id,
                'session_type':   session.session_type,
                'status':         session.status,
                'chapter_major':  session.chapter_major,
                'chapter_middle': session.chapter_middle,
                'chapter_minor':  session.chapter_minor or None,
                'score':          session.score,
                'total':          session.problem_count,
                'accuracy':       round(session.score / session.problem_count, 2)
                                  if session.score is not None else None,
                'created_at':     session.created_at,
            })

        # 2. 유형별 마스터 현황
        masteries = SubtypeMastery.objects.filter(
            user=request.user
        ).order_by('-updated_at')

        subtype_mastery = []
        for m in masteries:
            accuracy = (
                round(m.correct_count / m.total_attempts, 2)
                if m.total_attempts > 0 else 0
            )

            # 마스터한 유형 → 다음 도전 난이도 결정
            next_difficulty = None
            if m.mastered:
                next_difficulty = '상' if accuracy >= 0.95 else '중'

            # 레벨 판정
            if m.mastered:
                level = '숙달'
            elif accuracy >= 0.6:
                level = '연습 중'
            else:
                level = '보완 필요'

            subtype_mastery.append({
                'problem_subtype':  m.problem_subtype,
                'mastered':         m.mastered,
                'level':            level,
                'accuracy':         round(accuracy * 100),       # 퍼센트로
                'accuracy_before':  round(m.accuracy_before * 100)
                                    if m.accuracy_before else None,
                'accuracy_after':   round(m.accuracy_after * 100)
                                    if m.accuracy_after else None,
                'total_attempts':   m.total_attempts,
                'next_difficulty':  next_difficulty,             # 마스터 시에만
                'updated_at':       m.updated_at,
            })

        return Response({
            'status': 'success',
            'data': {
                'sessions':       session_list,
                'subtype_mastery': subtype_mastery,
            }
        })
    

class ProblemDetailView(APIView):

    def get(self, request, problem_id):
        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            return Response(
                {'status': 'error', 'message': '문제를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'status': 'success',
            'data': _serialize_problem(problem, request),
        })


class QuizSessionRecommendationsView(APIView):

    def get(self, request, session_id):
        # 세션 확인
        try:
            session = QuizSession.objects.get(id=session_id)
        except QuizSession.DoesNotExist:
            return Response(
                {'status': 'error', 'message': '세션을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if session.user != request.user:
            return Response(
                {'status': 'error', 'message': '접근 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if session.status != 'completed':
            return Response(
                {'status': 'error', 'message': '아직 제출되지 않은 세션입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 이미 생성된 리포트면 DB에서 바로 반환 (LLM 재호출 방지)
        try:
            report = session.weakness_report
            return Response({'status': 'success', 'data': _serialize_report(report)})
        except WeaknessReport.DoesNotExist:
            pass

        # 전체 결과 조회
        results      = SessionResult.objects.filter(session=session).select_related('problem')
        wrong_results = results.filter(is_correct=False)
        total        = results.count()
        score        = results.filter(is_correct=True).count()
        solved_ids   = list(results.values_list('problem__id', flat=True))

        # 전부 맞은 경우
        if not wrong_results.exists():
            report = WeaknessReport.objects.create(
                session=session,
                all_correct=True,
                ai_feedback='모든 문제를 맞혔어요! 더 어려운 문제에 도전해보세요.',
            )
            _recommend_harder(report, session, solved_ids)
            return Response({'status': 'success', 'data': _serialize_report(report)})

        # 취약 유형 Top 3 집계
        subtype_stats = defaultdict(lambda: {'wrong': 0, 'total': 0})
        for r in results:
            subtype = r.problem.problem_subtype
            subtype_stats[subtype]['total'] += 1
            if not r.is_correct:
                subtype_stats[subtype]['wrong'] += 1

        weak_list = [
            (subtype, stats)
            for subtype, stats in subtype_stats.items()
            if stats['wrong'] > 0
        ]
        weak_list.sort(key=lambda x: x[1]['wrong'] / x[1]['total'], reverse=True)

        top3 = [(subtype, stats['wrong']) for subtype, stats in weak_list[:3]]

        # LLM 피드백 생성
        ai_feedback = _generate_feedback(top3)

        # WeaknessReport 생성
        report = WeaknessReport.objects.create(
            session=session,
            all_correct=False,
            ai_feedback=ai_feedback,
        )

        # WeakSubtype + RAG 추천
        for rank, (subtype, wrong_count) in enumerate(top3, start=1):
            total_in_subtype = results.filter(
                problem__problem_subtype=subtype
            ).count()
            weak = WeakSubtype.objects.create(
                report=report,
                problem_subtype=subtype,
                wrong_count=wrong_count,
                total_count=total_in_subtype,
                rank=rank,
            )
            sample_wrong = wrong_results.filter(
                problem__problem_subtype=subtype
            ).first()
            _recommend_similar(report, weak, sample_wrong.problem, solved_ids, session)

        return Response({'status': 'success', 'data': _serialize_report(report)})


def _generate_feedback(top3):
    """LLM으로 취약 유형 자연어 피드백 생성"""
    client = OpenAI(
        api_key=settings.GMS_KEY,
        base_url=settings.GMS_URL
    )

    subtype_text = '\n'.join(
        f'{rank}. {subtype} ({wrong_count}개 틀림)'
        for rank, (subtype, wrong_count) in enumerate(top3, start=1)
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
                )
            },
            {
                'role': 'user',
                'content': f'학생이 다음 유형에서 틀렸습니다:\n{subtype_text}'
            }
        ],
        max_tokens=300,
    )
    return response.choices[0].message.content


def _backfill_similar_ids(collection, query_embedding, problem_subtype, chapter_minor, exclude_ids,
                           limit=3, preferred_difficulty='하', allow_cross_subtype_fallback=True):
    """RAG로 유사 문제 id를 limit개까지 채움. 한 단계에서 모자라면(데이터 부족) 다음 단계로 내려가
    이미 고른 것 + exclude_ids를 제외하고 부족한 만큼만 더 채운다 — 1~2개만 찾고 멈추지 않게.
    allow_cross_subtype_fallback=False면 같은 chapter_minor라도 subtype이 다른 문제로는 채우지 않음
    (보완 학습 단계별 문제는 반드시 같은 유형이어야 해서 — 데이터 부족하면 그냥 개수가 줄어든다)."""
    def _query(where_filter, already_chosen):
        result = collection.query(query_embeddings=[query_embedding], n_results=20, where=where_filter)
        return [pid for pid in result['ids'][0] if pid not in exclude_ids and pid not in already_chosen]

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
    if allow_cross_subtype_fallback:
        tiers.append({'$and': [
            {'chapter_minor': {'$eq': chapter_minor}},
            {'is_quizable':   {'$eq': 'True'}},
        ]})
    for tier in tiers:
        if len(chosen) >= limit:
            break
        chosen.extend(_query(tier, chosen)[:limit - len(chosen)])
    return chosen


def _recommend_similar(report, weak, sample_problem, solved_ids, session):
    """RAG로 보완 학습용 문제 추천 — 오답 루프(1문제씩 단계별 진행)에서 쓸 후보를 준비.
    하 난이도 2개(보완1용 + 보완1 오답 시 보완2용) + 중 난이도 1개(보완1 정답 시 보완2용)를 구해서
    난이도로 구분해 저장한다 (프론트는 difficulty로 s1/s1mid/s2 역할을 가른다)."""
    client        = OpenAI(
        api_key=settings.GMS_KEY,
        base_url=settings.GMS_URL
    )
    import os
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chroma_client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, 'chroma_db'))
    collection    = chroma_client.get_collection('problems')

    # 오답 문제 question_text로 임베딩 쿼리
    query_embedding = client.embeddings.create(
        model='text-embedding-3-small',
        input=[sample_problem.question_text],
    ).data[0].embedding

    easy_ids = _backfill_similar_ids(
        collection, query_embedding, weak.problem_subtype, sample_problem.chapter_minor, solved_ids,
        limit=2, preferred_difficulty='하', allow_cross_subtype_fallback=False,
    )
    mid_exclude = set(solved_ids) | set(easy_ids)
    mid_ids = _backfill_similar_ids(
        collection, query_embedding, weak.problem_subtype, sample_problem.chapter_minor, mid_exclude,
        limit=1, preferred_difficulty='중', allow_cross_subtype_fallback=False,
    )

    # Recommendation 저장 (순서: 보완1용 하, 중 난이도, 보완1 오답 시용 하)
    ordered_ids = easy_ids[:1] + mid_ids + easy_ids[1:2]
    for idx, problem_id in enumerate(ordered_ids):
        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            continue

        Recommendation.objects.create(
            report=report,
            weak_subtype=weak,
            problem=problem,
            similarity_score=None,
            order_index=idx + 1,
            reason=f'{weak.problem_subtype} 유형 유사 문제 (난이도: {problem.difficulty})',
        )


def _recommend_harder(report, session, solved_ids):
    """전부 맞았을 때 현재 세션보다 높은 난이도 문제 추천"""
    # session_type에 따라 다음 난이도 결정
    if session.session_type in ['normal', 'review_1']:
        next_difficulties = ['중', '상']
    else:
        next_difficulties = ['상']

    harder_problems = Problem.objects.filter(
        chapter_middle=session.chapter_middle,
        difficulty__in=next_difficulties,
        is_quizable=True,
    ).exclude(id__in=solved_ids)[:3]

    for idx, problem in enumerate(harder_problems):
        Recommendation.objects.create(
            report=report,
            weak_subtype=None,
            problem=problem,
            similarity_score=None,
            order_index=idx + 1,
            reason=f'현재 수준보다 높은 난이도 도전 문제 (난이도: {problem.difficulty})',
        )


def _serialize_report(report):
    """WeaknessReport → 응답 딕셔너리 변환"""

    if report.all_correct:
        # 전부 맞은 경우 — 기존과 동일
        recommendations = [
            {
                'problem_id':      r.problem.id,
                'difficulty':      r.problem.difficulty,
                'problem_subtype': r.problem.problem_subtype,
                'chapter_major':   r.problem.chapter_major,
                'chapter_middle':  r.problem.chapter_middle,
                'chapter_minor':   r.problem.chapter_minor,
                'question_text':   r.problem.question_text,
                'reason':          r.reason,
            }
            for r in report.recommendations.select_related('problem').all()
        ]
        return {
            'all_correct':     True,
            'ai_feedback':     report.ai_feedback,
            'weak_subtypes':   [],
            'recommendations': recommendations,
        }

    # 취약 유형별 데이터 (오답 루프의 "원래 틀린 문제" = 이 세션에서 해당 유형으로 틀렸던 문제 1개)
    weak_subtypes = []
    for weak in report.weak_subtypes.all():
        sample_wrong = SessionResult.objects.filter(
            session=report.session,
            problem__problem_subtype=weak.problem_subtype,
            is_correct=False,
        ).select_related('problem').first()
        weak_subtypes.append({
            'rank':               weak.rank,
            'problem_subtype':    weak.problem_subtype,
            'wrong_count':        weak.wrong_count,
            'total_count':        weak.total_count,
            'original_problem_id': sample_wrong.problem.id if sample_wrong else None,
        })

    # 추천 문제 — 평탄한 리스트로 변환 ← 핵심 변경
    all_recommendations = report.recommendations.select_related(
        'problem', 'weak_subtype'
    ).all()

    recommendations = [
        {
            'problem_id':      r.problem.id,
            'difficulty':      r.problem.difficulty,
            'problem_subtype': r.problem.problem_subtype,
            'chapter_major':   r.problem.chapter_major,    # ← review_1 세션 생성용
            'chapter_middle':  r.problem.chapter_middle,   # ← review_1 세션 생성용
            'chapter_minor':   r.problem.chapter_minor,    # ← review_1 세션 생성용
            'question_text':   r.problem.question_text,
            'reason':          r.reason,
            'rank':            r.weak_subtype.rank if r.weak_subtype else None,
        }
        for r in all_recommendations
    ]

    return {
        'all_correct':     False,
        'ai_feedback':     report.ai_feedback,
        'weak_subtypes':   weak_subtypes,   # 취약 유형 요약 (rank, subtype, 오답수)
        'recommendations': recommendations, # 추천 문제 평탄 리스트
    }


class CSRFTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = get_token(request)
        return Response({
            "status": "success",
            "data": {
                "csrfToken": token
            }
        })


class UserDashboardView(APIView):

    def get(self, request):
        user = request.user

        # 1. 주간 학습 활동 (월~일)
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        week_days = [monday + timedelta(days=i) for i in range(7)]

        # 이번 주에 completed 세션이 있는 날짜 목록
        active_dates = set(
            QuizSession.objects.filter(
                user=user,
                status='completed',
                created_at__date__gte=monday,
                created_at__date__lte=today,
            ).values_list('created_at__date', flat=True)
        )
        weekly_activity = [d in active_dates for d in week_days]

        # 2. 유형별 마스터 진척 (상위 3개)
        masteries = SubtypeMastery.objects.filter(user=user).order_by('-updated_at')[:3]
        subtype_mastery = []
        for m in masteries:
            accuracy = (
                m.correct_count / m.total_attempts
                if m.total_attempts > 0 else 0
            )
            # 레벨 판정
            if m.mastered:
                level = '숙달'
            elif accuracy >= 0.6:
                level = '연습 중'
            else:
                level = '보완 필요'

            subtype_mastery.append({
                'problem_subtype': m.problem_subtype,
                'level':           level,
                'pct':             round(accuracy * 100),
                'mastered':        m.mastered,
            })

        # 3. 최근 세션
        latest_session = QuizSession.objects.filter(
            user=user,
            status='completed'
        ).order_by('-created_at').first()

        latest_session_data = None
        if latest_session:
            latest_session_data = {
                'session_id':      latest_session.id,
                'chapter_middle':  latest_session.chapter_middle,
                'accuracy':        round(latest_session.score / latest_session.problem_count, 2)
                                   if latest_session.score is not None else None,
                'created_at':      latest_session.created_at.strftime('%Y-%m-%d'),
            }

        return Response({
            'status': 'success',
            'data': {
                'user': {
                    'name':        user.first_name or user.username,
                    'grade':       user.grade,
                    'joined_days': (date.today() - user.date_joined.date()).days + 1,
                },
                'streak':          user.streak,
                'total_solved':    user.total_solved,
                'weekly_activity': weekly_activity,   # [True, True, False, ...] 월~일
                'subtype_mastery': subtype_mastery,
                'latest_session':  latest_session_data,
            }
        })


class TodayRecommendationView(APIView):

    def get(self, request):
        user = request.user

        # 1. 보완 필요한 subtype 우선 (mastered=False, 오답률 높은 순)
        weak_masteries = SubtypeMastery.objects.filter(
            user=user,
            mastered=False,
        ).order_by('correct_count')  # 정답 수 적은 순 = 취약한 순

        if weak_masteries.exists():
            # 가장 취약한 subtype
            target = weak_masteries.first()
            reason = f'{target.problem_subtype} 유형에서 아직 보완이 필요해요'
            mode   = 'review'

        else:
            # 전부 마스터했으면 → 가장 최근 마스터한 유형의 난이도 업
            latest_mastered = SubtypeMastery.objects.filter(
                user=user,
                mastered=True,
            ).order_by('-updated_at').first()

            if not latest_mastered:
                # 아직 아무 기록 없음
                return Response({
                    'status': 'success',
                    'data': {
                        'has_recommendation': False,
                        'message': '퀴즈를 풀면 맞춤 추천을 드려요!',
                    }
                })

            target = latest_mastered
            reason = f'{target.problem_subtype} 유형을 마스터했어요! 더 어려운 문제에 도전해봐요'
            mode   = 'challenge'

        # 2. 해당 subtype의 문제가 속한 챕터 정보 조회
        sample_problem = Problem.objects.filter(
            problem_subtype=target.problem_subtype,
            is_quizable=True,
        ).first()

        if not sample_problem:
            return Response({
                'status': 'success',
                'data': {
                    'has_recommendation': False,
                    'message': '추천할 문제가 없어요.',
                }
            })

        # 3. 추천 문제 미리보기 (최대 3개)
        if mode == 'review':
            preview_problems = Problem.objects.filter(
                problem_subtype=target.problem_subtype,
                is_quizable=True,
                difficulty='하',
            )[:3]
        else:
            accuracy = (
                target.correct_count / target.total_attempts
                if target.total_attempts > 0 else 0
            )
            next_difficulty = '상' if accuracy >= 0.95 else '중'
            preview_problems = Problem.objects.filter(
                problem_subtype=target.problem_subtype,
                is_quizable=True,
                difficulty=next_difficulty,
            )[:3]

        problems_data = [
            {
                'problem_id':      p.id,
                'problem_subtype': p.problem_subtype,
                'difficulty':      p.difficulty,
                'question_text':   p.question_text,
            }
            for p in preview_problems
        ]

        # 4. C6 퀴즈 만들기 프리필 데이터
        prefill = {
            'chapter_major':   sample_problem.chapter_major,
            'chapter_middle':  sample_problem.chapter_middle,
            'chapter_minor':   sample_problem.chapter_minor,
            'problem_subtype': target.problem_subtype,
            'suggested_count': 10,
        }

        return Response({
            'status': 'success',
            'data': {
                'has_recommendation':  True,
                'mode':                mode,           # 'review' | 'challenge'
                'recommended_subtype': target.problem_subtype,
                'reason':              reason,
                'problems':            problems_data,
                'prefill':             prefill,
            }
        })


class ReviewProblemView(APIView):
    """
    재도전(Redo)용: 처음 틀렸던 원본 문제 1개를 세션 생성 없이 반환.
    GET /quiz/sessions/<session_id>/redo-problem?problem_id=<id>
    """

    def get(self, request, session_id):
        problem_id = request.query_params.get('problem_id')
        if not problem_id:
            return Response(
                {'status': 'error', 'message': 'problem_id가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = QuizSession.objects.get(id=session_id, user=request.user)
        except QuizSession.DoesNotExist:
            return Response(
                {'status': 'error', 'message': '세션을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        is_wrong = SessionResult.objects.filter(
            session=session,
            problem_id=problem_id,
            is_correct=False,
        ).exists()
        if not is_wrong:
            return Response(
                {'status': 'error', 'message': '해당 세션의 오답 문제가 아닙니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            problem = Problem.objects.prefetch_related('assets').get(id=problem_id)
        except Problem.DoesNotExist:
            return Response(
                {'status': 'error', 'message': '문제를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'status': 'success',
            'data': _serialize_problem_with_answer(problem, request),
        })


class QuizSessionChatView(APIView):

    def post(self, request, session_id):
        # 1. 세션 확인
        try:
            session = QuizSession.objects.get(id=session_id)
        except QuizSession.DoesNotExist:
            return Response(
                {'status': 'error', 'message': '세션을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if session.user != request.user:
            return Response(
                {'status': 'error', 'message': '접근 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 2. 요청 데이터
        problem_id = request.data.get('problem_id')
        question   = request.data.get('question', '').strip()

        if not problem_id or not question:
            return Response(
                {'status': 'error', 'message': 'problem_id와 question은 필수입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. 문제 조회
        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            return Response(
                {'status': 'error', 'message': '문제를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4. LLM 호출
        answer = _generate_chat_answer(problem, question)

        return Response({
            'status': 'success',
            'data': {
                'question': question,
                'answer':   answer,
            }
        })


def _generate_chat_answer(problem, question):
    """문제 해설 AI 챗봇 — 문제 컨텍스트 포함해서 LLM 호출"""
    client = OpenAI(
        api_key=settings.GMS_KEY,
        base_url=settings.GMS_URL
    )

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {
                'role': 'system',
                'content': (
                    '당신은 중학교 수학 해설 튜터입니다. '
                    '학생이 문제를 이해할 수 있도록 친절하고 단계적으로 설명해주세요. '
                    '수식은 LaTeX 형식($...$)으로 작성해주세요. '
                    '3문장 이내로 핵심만 간결하게 답해주세요.'
                )
            },
            {
                'role': 'user',
                'content': (
                    f'[문제]\n{problem.question_text}\n\n'
                    f'[정답]\n{problem.answer}\n\n'
                    f'[해설]\n{problem.explanation}\n\n'
                    f'[학생 질문]\n{question}'
                )
            }
        ],
        max_tokens=300,
    )
    return response.choices[0].message.content