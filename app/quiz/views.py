from django.contrib.auth import authenticate, login, logout, get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from .serializers import RegisterSerializer, UserSerializer
from .models import Problem, QuizSession, SessionProblem, SessionResult, WeaknessReport, WeakSubtype, Recommendation, SubtypeMastery
import random
from datetime import date, timedelta
from collections import defaultdict
from openai import OpenAI
from django.conf import settings
from .graph import coaching_graph


def _serialize_assets(problem, request=None):
    """option_type='mixed_with_image'인 문제의 보기 이미지 목록을 응답용 dict 리스트로 변환."""
    if problem.option_type != 'mixed_with_image':
        return []

    out = []
    for asset in problem.assets.all():
        url = settings.MEDIA_URL.rstrip('/') + '/' + asset.image_path.lstrip('/')
        if request is not None:
            url = request.build_absolute_uri(url)
        out.append({
            'asset_role': asset.asset_role,
            'image_url':  url,
            'bbox':       [asset.bbox_x1, asset.bbox_y1, asset.bbox_x2, asset.bbox_y2],
        })
    return out


def _create_diagnosis_session(user):
    """
    회원가입 직후 빠른 진단 세션을 자동 생성한다.
    - user.current_chapter_major / current_chapter_middle 기준
    - 하 70% + 중 30%, 최대 10문제
    - 문제가 없으면 None 반환 (가입 자체는 막지 않음)
    """
    if not user.current_chapter_major or not user.current_chapter_middle:
        return None

    base_filter = dict(
        chapter_major  = user.current_chapter_major,
        chapter_middle = user.current_chapter_middle,
        is_quizable    = True,
    )
    problem_count = 10

    problems_low = list(Problem.objects.filter(**base_filter, difficulty='하'))
    problems_mid = list(Problem.objects.filter(**base_filter, difficulty='중'))

    if not problems_low and not problems_mid:
        return None

    low_count    = round(problem_count * 0.7)
    mid_count    = problem_count - low_count
    selected_low = random.sample(problems_low, min(low_count, len(problems_low)))
    selected_mid = random.sample(problems_mid, min(mid_count, len(problems_mid)))
    selected     = selected_low + selected_mid
    random.shuffle(selected)

    if not selected:
        return None

    session = QuizSession.objects.create(
        user           = user,
        chapter_major  = user.current_chapter_major,
        chapter_middle = user.current_chapter_middle,
        chapter_minor  = '',
        problem_count  = len(selected),
        session_type   = 'diagnosis',
    )

    for idx, problem in enumerate(selected):
        SessionProblem.objects.create(
            session     = session,
            problem     = problem,
            order_index = idx + 1,
        )

    return session


User = get_user_model()


# ─────────────────────────────────────────────
# 인증
# ─────────────────────────────────────────────

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'status': 'error', 'message': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=serializer.validated_data['username']).exists():
            return Response({'status': 'error', 'message': '이미 존재하는 아이디입니다.'},
                            status=status.HTTP_409_CONFLICT)

        user = serializer.save()

        # 빠른 진단 세션 자동 생성 (진도 입력한 경우에만)
        diagnosis_session = _create_diagnosis_session(user)

        response_data = {
            'username': user.username,
            'name':     user.first_name,
        }
        if diagnosis_session:
            response_data['diagnosis_session_id'] = diagnosis_session.id

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
                'username': user.username,
                'name':     user.first_name,
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


# ─────────────────────────────────────────────
# 챕터
# ─────────────────────────────────────────────

class ChapterListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        problems = Problem.objects.values(
            'chapter_major', 'chapter_middle', 'chapter_minor'
        ).distinct().order_by('chapter_major', 'chapter_middle', 'chapter_minor')

        result = {}
        for p in problems:
            major  = p['chapter_major']
            middle = p['chapter_middle']
            minor  = p['chapter_minor']
            if major not in result:
                result[major] = {}
            if middle not in result[major]:
                result[major][middle] = []
            result[major][middle].append(minor)

        data = [
            {
                'chapter_major':   major,
                'chapter_middles': [
                    {'chapter_middle': middle, 'chapter_minors': minors}
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


# ─────────────────────────────────────────────
# 퀴즈 세션
# ─────────────────────────────────────────────

class QuizSessionCreateView(APIView):

    def post(self, request):
        chapter_major     = request.data.get('chapter_major')
        chapter_middle    = request.data.get('chapter_middle')
        chapter_minor     = request.data.get('chapter_minor')
        problem_count     = request.data.get('problem_count')
        parent_session_id = request.data.get('parent_session_id')   # optional
        # 보완 단계 구분: 's1'(보완1·하), 's1mid'(보완1·중), 's2'(보완2·하)
        review_step       = request.data.get('review_step')         # optional
        # 보완 세션에서 제외할 문제 ID 목록 (이미 푼 문제 재출제 방지)
        exclude_ids       = request.data.get('exclude_ids', [])

        if not chapter_major or not chapter_middle or not problem_count:
            return Response(
                {'status': 'error', 'message': 'chapter_major, chapter_middle, problem_count는 필수입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            problem_count = int(problem_count)
            if problem_count < 1:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {'status': 'error', 'message': 'problem_count는 1 이상의 정수여야 합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

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

            # diagnosis → review_1 → review_2 → 해설만
            parent_type = parent_session.session_type
            if parent_type in ('normal', 'diagnosis'):
                session_type = 'review_1'
            elif parent_type == 'review_1':
                session_type = 'review_2'
            # review_2 이후는 프론트에서 explain → redo 로 직접 처리 (세션 생성 없음)

        base_filter = dict(
            chapter_major  = chapter_major,
            chapter_middle = chapter_middle,
            is_quizable    = True,
        )
        if chapter_minor:
            base_filter['chapter_minor'] = chapter_minor

        if session_type == 'normal':
            problems_low = list(Problem.objects.filter(**base_filter, difficulty='하'))
            problems_mid = list(Problem.objects.filter(**base_filter, difficulty='중'))

            if not problems_low and not problems_mid:
                return Response(
                    {'status': 'error', 'message': '해당 범위에 문제가 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            low_count    = round(problem_count * 0.7)
            mid_count    = problem_count - low_count
            selected_low = random.sample(problems_low, min(low_count, len(problems_low)))
            selected_mid = random.sample(problems_mid, min(mid_count, len(problems_mid)))
            selected     = selected_low + selected_mid
            random.shuffle(selected)

        elif session_type in ('review_1', 'review_2'):
            # 취약 subtype 1개에서 1문제만 출제. 단계별 난이도:
            #   s1    → 하  (보완 1단계 첫 문제)
            #   s1mid → 중  (s1 정답 시 난이도 업)
            #   s2    → 하  (보완 2단계, s1 오답 시)
            if review_step == 's1mid':
                target_difficulty = '중'
            else:
                target_difficulty = '하'  # s1, s2 모두 하

            weak_subtypes  = _get_weak_subtypes(parent_session)
            target_subtype = weak_subtypes[0] if weak_subtypes else None

            q_filter = {**base_filter, 'difficulty': target_difficulty}
            if target_subtype:
                q_filter['problem_subtype'] = target_subtype

            problems = list(
                Problem.objects.filter(**q_filter).exclude(id__in=exclude_ids)
            )
            # subtype 필터로 문제 없으면 난이도만으로 폴백
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

            # 보완 세션은 항상 1문제
            selected = [random.choice(problems)]

        if not selected:
            return Response(
                {'status': 'error', 'message': '해당 범위에 출제 가능한 문제가 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        actual_count = len(selected)

        session = QuizSession.objects.create(
            user           = request.user,
            chapter_major  = chapter_major,
            chapter_middle = chapter_middle,
            chapter_minor  = chapter_minor or '',
            problem_count  = actual_count,
            session_type   = session_type,
            parent_session = parent_session,
        )

        for idx, problem in enumerate(selected):
            SessionProblem.objects.create(
                session     = session,
                problem     = problem,
                order_index = idx + 1,
            )

        return Response({
            'status': 'success',
            'data': {
                'session_id':      session.id,
                'session_type':    session.session_type,
                'review_step':     review_step or ('s1' if session_type == 'review_1' else None),
                'status':          session.status,
                'requested_count': problem_count,
                'actual_count':    actual_count,
                'created_at':      session.created_at,
            }
        }, status=status.HTTP_201_CREATED)


def _get_weak_subtypes(session):
    """세션의 오답 문제에서 취약 subtype 목록 추출"""
    from collections import Counter
    wrong_results = SessionResult.objects.filter(
        session    = session,
        is_correct = False,
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

        problems = []
        for sp in session_problems:
            p = sp.problem
            problems.append({
                'order':                 sp.order_index,
                'problem_id':            p.id,
                'difficulty':            p.difficulty,
                'problem_subtype':       p.problem_subtype,
                'question_text':         p.question_text,
                'question_with_options': p.question_with_options,
                'question_image_bbox':   p.question_image_bbox,
                'option_type':           p.option_type,
                'assets':                _serialize_assets(p, request),
                'is_multi_answer':       p.is_multi_answer,
            })

        return Response({
            'status': 'success',
            'data': {
                'session_id':   session.id,
                'session_type': session.session_type,
                'status':       session.status,
                'total':        len(problems),
                'problems':     problems,
            }
        })


class QuizSessionSubmitView(APIView):

    def post(self, request, session_id):
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

        if session.status == 'completed':
            return Response(
                {'status': 'error', 'message': '이미 제출된 세션입니다.'},
                status=status.HTTP_409_CONFLICT
            )

        answers = request.data.get('answers', [])
        if not answers:
            return Response(
                {'status': 'error', 'message': 'answers가 비어있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session_problems = SessionProblem.objects.filter(
            session=session
        ).select_related('problem')

        problem_map = {sp.problem.id: sp.problem for sp in session_problems}

        results = []
        score   = 0

        for answer in answers:
            problem_id  = answer.get('problem_id')
            user_answer = answer.get('user_answer', '').strip()

            if problem_id not in problem_map:
                continue

            problem       = problem_map[problem_id]
            correct_label = problem.grading_answer or problem.answer.strip()

            if problem.is_multi_answer:
                submitted  = set(s.strip() for s in user_answer.split(','))
                correct    = set(correct_label.split(','))
                is_correct = (submitted == correct)
            else:
                is_correct = (user_answer == correct_label)

            if is_correct:
                score += 1

            SessionResult.objects.create(
                session        = session,
                problem        = problem,
                student_answer = user_answer,
                is_correct     = is_correct,
            )

            results.append({
                'problem_id':      problem_id,
                'user_answer':     user_answer,
                'correct_answer':  problem.answer,
                'is_correct':      is_correct,
                'explanation':     problem.explanation,
                'problem_subtype': problem.problem_subtype,
                'difficulty':      problem.difficulty,
            })

        session.status = 'completed'
        session.score  = score
        session.save()

        _update_subtype_mastery(request.user, results)
        _update_user_stats(request.user, len(results))

        return Response({
            'status': 'success',
            'data': {
                'session_id':   session.id,
                'session_type': session.session_type,
                'score':        score,
                'total':        len(results),
                'accuracy':     round(score / len(results), 2) if results else 0,
                'results':      results,
            }
        })


def _update_subtype_mastery(user, results):
    subtype_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
    for r in results:
        subtype = r['problem_subtype']
        subtype_stats[subtype]['total']   += 1
        subtype_stats[subtype]['correct'] += 1 if r['is_correct'] else 0

    for subtype, stats in subtype_stats.items():
        mastery, _ = SubtypeMastery.objects.get_or_create(
            user            = user,
            problem_subtype = subtype,
            defaults        = {'total_attempts': 0, 'correct_count': 0}
        )

        prev_accuracy = (
            mastery.correct_count / mastery.total_attempts
            if mastery.total_attempts > 0 else None
        )

        mastery.total_attempts += stats['total']
        mastery.correct_count  += stats['correct']

        new_accuracy  = mastery.correct_count / mastery.total_attempts
        was_mastered  = mastery.mastered

        if not was_mastered and new_accuracy >= 0.8 and mastery.total_attempts >= 3:
            mastery.mastered        = True
            mastery.accuracy_before = round(prev_accuracy, 2) if prev_accuracy else None
            mastery.accuracy_after  = round(new_accuracy, 2)

        mastery.save()


def _update_user_stats(user, solved_count):
    today = date.today()
    user.total_solved += solved_count

    if user.last_active_date is None:
        user.streak = 1
    elif user.last_active_date == today:
        pass
    elif (today - user.last_active_date).days == 1:
        user.streak += 1
    else:
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
            session    = session,
            is_correct = False,
        ).select_related('problem').prefetch_related('problem__assets')

        wrong_problems = []
        for result in wrong_results:
            p = result.problem
            wrong_problems.append({
                'problem_id':            p.id,
                'user_answer':           result.student_answer,
                'correct_answer':        p.answer,
                'explanation':           p.explanation,
                'problem_subtype':       p.problem_subtype,
                'difficulty':            p.difficulty,
                'question_text':         p.question_text,
                'question_with_options': p.question_with_options,
                'question_image_bbox':   p.question_image_bbox,
                'option_type':           p.option_type,
                'assets':                _serialize_assets(p, request),
                'is_multi_answer':       p.is_multi_answer,
            })

        return Response({
            'status': 'success',
            'data': {
                'session_id':     session.id,
                'session_type':   session.session_type,
                'wrong_count':    len(wrong_problems),
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

        results = SessionResult.objects.filter(session=session).select_related('problem')
        total   = results.count()
        score   = results.filter(is_correct=True).count()

        wrong_results = results.filter(is_correct=False)
        if not wrong_results.exists():
            return Response({
                'status': 'success',
                'data': {
                    'session_id':    session.id,
                    'session_type':  session.session_type,
                    'score':         score,
                    'total':         total,
                    'accuracy':      1.0,
                    'all_correct':   True,
                    'weak_subtypes': [],
                }
            })

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
                'session_type':  session.session_type,
                'score':         score,
                'total':         total,
                'accuracy':      round(score / total, 2),
                'all_correct':   False,
                'weak_subtypes': weak_subtypes,
            }
        })


class UserHistoryView(APIView):

    def get(self, request):
        sessions = QuizSession.objects.filter(
            user   = request.user,
            status = 'completed',
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

        masteries = SubtypeMastery.objects.filter(user=request.user).order_by('-updated_at')

        subtype_mastery = []
        for m in masteries:
            accuracy = (
                round(m.correct_count / m.total_attempts, 2)
                if m.total_attempts > 0 else 0
            )
            next_difficulty = None
            if m.mastered:
                next_difficulty = '상' if accuracy >= 0.95 else '중'

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
                'accuracy':         round(accuracy * 100),
                'accuracy_before':  round(m.accuracy_before * 100) if m.accuracy_before else None,
                'accuracy_after':   round(m.accuracy_after  * 100) if m.accuracy_after  else None,
                'total_attempts':   m.total_attempts,
                'next_difficulty':  next_difficulty,
                'updated_at':       m.updated_at,
            })

        return Response({
            'status': 'success',
            'data': {
                'sessions':        session_list,
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
            'data': {
                'problem_id':            problem.id,
                'difficulty':            problem.difficulty,
                'chapter_major':         problem.chapter_major,
                'chapter_middle':        problem.chapter_middle,
                'chapter_minor':         problem.chapter_minor,
                'problem_subtype':       problem.problem_subtype,
                'question_text':         problem.question_text,
                'question_with_options': problem.question_with_options,
                'question_image_bbox':   problem.question_image_bbox,
                'option_type':           problem.option_type,
                'assets':                _serialize_assets(problem, request),
                'is_multi_answer':       problem.is_multi_answer,
            }
        })


class QuizSessionRecommendationsView(APIView):

    def get(self, request, session_id):
        try:
            session = QuizSession.objects.get(id=session_id)
        except QuizSession.DoesNotExist:
            return Response({'status': 'error', 'message': '세션을 찾을 수 없습니다.'}, status=404)

        if session.user != request.user:
            return Response({'status': 'error', 'message': '접근 권한이 없습니다.'}, status=403)

        if session.status != 'completed':
            return Response({'status': 'error', 'message': '아직 제출되지 않은 세션입니다.'}, status=400)

        try:
            report = session.weakness_report
            return Response({'status': 'success', 'data': _serialize_report(report)})
        except WeaknessReport.DoesNotExist:
            pass

        results       = SessionResult.objects.filter(session=session).select_related('problem')
        wrong_results = results.filter(is_correct=False)
        solved_ids    = list(results.values_list('problem__id', flat=True))
        all_correct   = not wrong_results.exists()

        wrong_problems = [
            {
                'problem_id':       r.problem.id,
                'problem_subtype':  r.problem.problem_subtype,
                'question_text':    r.problem.question_text,
                'chapter_minor':    r.problem.chapter_minor,
                'total_in_subtype': results.filter(
                    problem__problem_subtype=r.problem.problem_subtype
                ).count(),
            }
            for r in wrong_results
        ]

        result = coaching_graph.invoke({
            'session_id':     session.id,
            'chapter_middle': session.chapter_middle,
            'session_type':   session.session_type,
            'solved_ids':     solved_ids,
            'wrong_problems': wrong_problems,
            'all_correct':    all_correct,
        })

        report = WeaknessReport.objects.create(
            session     = session,
            all_correct = all_correct,
            ai_feedback = result['ai_feedback'],
        )

        if all_correct:
            for idx, rec in enumerate(result['harder_recommendations']):
                Recommendation.objects.create(
                    report      = report,
                    weak_subtype= None,
                    problem_id  = rec['problem_id'],
                    order_index = idx + 1,
                    reason      = rec['reason'],
                )
        else:
            for weak_data in result['weak_subtypes_data']:
                weak = WeakSubtype.objects.create(
                    report          = report,
                    problem_subtype = weak_data['problem_subtype'],
                    wrong_count     = weak_data['wrong_count'],
                    total_count     = next(
                        wp['total_in_subtype'] for wp in wrong_problems
                        if wp['problem_subtype'] == weak_data['problem_subtype']
                    ),
                    rank = weak_data['rank'],
                )
                for idx, pid in enumerate(weak_data['recommended_problem_ids']):
                    Recommendation.objects.create(
                        report      = report,
                        weak_subtype= weak,
                        problem_id  = pid,
                        order_index = idx + 1,
                        reason      = f"{weak_data['problem_subtype']} 유형 유사 문제",
                    )

        return Response({'status': 'success', 'data': _serialize_report(report)})


def _serialize_report(report):
    if report.all_correct:
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

    weak_subtypes = []
    for weak in report.weak_subtypes.all():
        weak_subtypes.append({
            'rank':            weak.rank,
            'problem_subtype': weak.problem_subtype,
            'wrong_count':     weak.wrong_count,
            'total_count':     weak.total_count,
        })

    all_recommendations = report.recommendations.select_related('problem', 'weak_subtype').all()

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
            'rank':            r.weak_subtype.rank if r.weak_subtype else None,
        }
        for r in all_recommendations
    ]

    return {
        'all_correct':     False,
        'ai_feedback':     report.ai_feedback,
        'weak_subtypes':   weak_subtypes,
        'recommendations': recommendations,
    }


class UserDashboardView(APIView):

    def get(self, request):
        user  = request.user
        today = date.today()

        monday    = today - timedelta(days=today.weekday())
        week_days = [monday + timedelta(days=i) for i in range(7)]

        active_dates = set(
            QuizSession.objects.filter(
                user   = user,
                status = 'completed',
                created_at__date__gte = monday,
                created_at__date__lte = today,
            ).values_list('created_at__date', flat=True)
        )
        weekly_activity = [d in active_dates for d in week_days]

        masteries = SubtypeMastery.objects.filter(user=user).order_by('-updated_at')[:3]
        subtype_mastery = []
        for m in masteries:
            accuracy = m.correct_count / m.total_attempts if m.total_attempts > 0 else 0
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

        latest_session = QuizSession.objects.filter(
            user=user, status='completed'
        ).order_by('-created_at').first()

        latest_session_data = None
        if latest_session:
            latest_session_data = {
                'session_id':     latest_session.id,
                'chapter_middle': latest_session.chapter_middle,
                'accuracy':       round(latest_session.score / latest_session.problem_count, 2)
                                  if latest_session.score is not None else None,
                'created_at':     latest_session.created_at.strftime('%Y-%m-%d'),
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
                'weekly_activity': weekly_activity,
                'subtype_mastery': subtype_mastery,
                'latest_session':  latest_session_data,
            }
        })


class TodayRecommendationView(APIView):

    def get(self, request):
        user = request.user

        weak_masteries = SubtypeMastery.objects.filter(
            user    = user,
            mastered= False,
        ).order_by('correct_count')

        if weak_masteries.exists():
            target = weak_masteries.first()
            reason = f'{target.problem_subtype} 유형에서 아직 보완이 필요해요'
            mode   = 'review'
        else:
            latest_mastered = SubtypeMastery.objects.filter(
                user    = user,
                mastered= True,
            ).order_by('-updated_at').first()

            if not latest_mastered:
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

        sample_problem = Problem.objects.filter(
            problem_subtype = target.problem_subtype,
            is_quizable     = True,
        ).first()

        if not sample_problem:
            return Response({
                'status': 'success',
                'data': {
                    'has_recommendation': False,
                    'message': '추천할 문제가 없어요.',
                }
            })

        if mode == 'review':
            preview_problems = Problem.objects.filter(
                problem_subtype = target.problem_subtype,
                is_quizable     = True,
                difficulty      = '하',
            )[:3]
        else:
            accuracy = (
                target.correct_count / target.total_attempts
                if target.total_attempts > 0 else 0
            )
            next_difficulty  = '상' if accuracy >= 0.95 else '중'
            preview_problems = Problem.objects.filter(
                problem_subtype = target.problem_subtype,
                is_quizable     = True,
                difficulty      = next_difficulty,
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
                'mode':                mode,
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

    - session_id: 원본(normal/diagnosis) 세션 ID — 본인 세션 검증용
    - problem_id: 재도전할 문제 ID (원본 세션의 오답 중 1개)
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
            session    = session,
            problem_id = problem_id,
            is_correct = False,
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
            'data': {
                'problem_id':            problem.id,
                'difficulty':            problem.difficulty,
                'problem_subtype':       problem.problem_subtype,
                'question_text':         problem.question_text,
                'question_with_options': problem.question_with_options,
                'question_image_bbox':   problem.question_image_bbox,
                'option_type':           problem.option_type,
                'assets':                _serialize_assets(problem, request),
                'is_multi_answer':       problem.is_multi_answer,
                'correct_answer':        problem.answer,
            }
        })


class QuizSessionChatView(APIView):

    def post(self, request, session_id):
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

        problem_id = request.data.get('problem_id')
        question   = request.data.get('question', '').strip()

        if not problem_id or not question:
            return Response(
                {'status': 'error', 'message': 'problem_id와 question은 필수입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            return Response(
                {'status': 'error', 'message': '문제를 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

        answer = _generate_chat_answer(problem, question)

        return Response({
            'status': 'success',
            'data': {
                'question': question,
                'answer':   answer,
            }
        })


def _generate_chat_answer(problem, question):
    client = OpenAI(
        api_key  = settings.GMS_KEY,
        base_url = settings.GMS_URL,
    )

    response = client.chat.completions.create(
        model    = 'gpt-4o-mini',
        messages = [
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
        max_tokens = 300,
    )
    return response.choices[0].message.content