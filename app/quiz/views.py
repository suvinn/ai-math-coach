from django.contrib.auth import authenticate, login, logout, get_user_model
from django.middleware.csrf import get_token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.utils.decorators import method_decorator
from .serializers import RegisterSerializer, UserSerializer, ProblemPublicSerializer, ProblemWithAnswerSerializer
from .models import Problem, QuizSession, SessionProblem, SessionResult, WeaknessReport, WeakSubtype, Recommendation, SubtypeMastery, Post, Comment
import random
from datetime import date, timedelta
from collections import defaultdict
from .graph import coaching_graph, chat_graph


def _serialize_problem(problem, request, extra_fields=None):
    context = {'request': request}
    if extra_fields:
        context['extra_fields'] = extra_fields
    return ProblemPublicSerializer(problem, context=context).data


def _serialize_problem_with_answer(problem, request, extra_fields=None):
    context = {'request': request}
    if extra_fields:
        context['extra_fields'] = extra_fields
    return ProblemWithAnswerSerializer(problem, context=context).data


def _make_warning(requested, actual):
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
        problems = Problem.objects.values(
            'chapter_major', 'chapter_middle', 'chapter_minor'
        ).distinct().order_by('chapter_major', 'chapter_middle', 'chapter_minor')
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
        rows = Problem.objects.filter(
            is_quizable=True
        ).values(
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


class ChapterSubtypeCountView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.db.models import Count
        rows = Problem.objects.filter(
            is_quizable=True
        ).values(
            'chapter_major', 'chapter_middle', 'problem_subtype'
        ).annotate(count=Count('id')).order_by(
            'chapter_major', 'chapter_middle', 'problem_subtype'
        )
        data = [
            {
                'chapter_major':   r['chapter_major'],
                'chapter_middle':  r['chapter_middle'],
                'problem_subtype': r['problem_subtype'],
                'count':           r['count'],
            }
            for r in rows
        ]
        return Response({'status': 'success', 'data': data})


class QuizSessionCreateView(APIView):

    def post(self, request):
        is_diagnosis      = request.data.get('mode') == 'diagnosis'
        problem_ids       = request.data.get('problem_ids')
        chapter_major     = request.data.get('chapter_major')
        chapter_middle    = request.data.get('chapter_middle')
        chapter_minor     = request.data.get('chapter_minor')
        problem_subtype   = request.data.get('problem_subtype')
        problem_count     = request.data.get('problem_count')
        parent_session_id = request.data.get('parent_session_id')
        review_step       = request.data.get('review_step')
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

        if is_diagnosis:
            has_chapter = bool(
                request.user.current_chapter_major and
                request.user.current_chapter_middle
            )
            if has_chapter:
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
                SessionProblem.objects.create(session=session, problem=problem, order_index=idx + 1)
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
            return Response({'status': 'success', 'data': resp}, status=status.HTTP_201_CREATED)

        session_type   = 'normal'
        parent_session = None

        if parent_session_id:
            try:
                parent_session = QuizSession.objects.get(id=parent_session_id, user=request.user)
            except QuizSession.DoesNotExist:
                return Response(
                    {'status': 'error', 'message': '부모 세션을 찾을 수 없습니다.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            if parent_session.session_type == 'normal':
                session_type = 'review_1'
            elif parent_session.session_type == 'review_1':
                session_type = 'review_2'

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
                SessionProblem.objects.create(session=session, problem=problem, order_index=idx + 1)
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
            return Response({'status': 'success', 'data': resp}, status=status.HTTP_201_CREATED)

        base_filter = dict(chapter_major=chapter_major, chapter_middle=chapter_middle, is_quizable=True)
        if chapter_minor:
            base_filter['chapter_minor'] = chapter_minor
        if problem_subtype:
            base_filter['problem_subtype'] = problem_subtype

        if session_type == 'normal':
            problems = list(Problem.objects.filter(**base_filter))
            if not problems:
                return Response(
                    {'status': 'error', 'message': '해당 범위에 문제가 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            selected = random.sample(problems, min(problem_count, len(problems)))

        elif session_type in ('review_1', 'review_2'):
            if review_step == 's1mid':
                target_difficulty = '중'
                rec_order_index   = 2
            elif review_step == 's2':
                target_difficulty = '하'
                rec_order_index   = 3
            else:
                target_difficulty = '하'
                rec_order_index   = 1

            weak_subtypes  = _get_weak_subtypes(parent_session)
            target_subtype = weak_subtypes[0] if weak_subtypes else None

            selected = []
            try:
                origin_session = parent_session
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
                pass

            if not selected:
                q_filter = {**base_filter, 'difficulty': target_difficulty}
                if target_subtype:
                    q_filter['problem_subtype'] = target_subtype
                problems = list(Problem.objects.filter(**q_filter).exclude(id__in=exclude_ids))
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
            SessionProblem.objects.create(session=session, problem=problem, order_index=idx + 1)
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
        return Response({'status': 'success', 'data': resp}, status=status.HTTP_201_CREATED)


def _select_diagnosis_problems(total_count):
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
    from collections import Counter
    wrong_results = SessionResult.objects.filter(
        session=session, is_correct=False
    ).select_related('problem')
    counter = Counter(r.problem.problem_subtype for r in wrong_results)
    return [subtype for subtype, _ in counter.most_common(3)]


class QuizSessionProblemsView(APIView):

    def get(self, request, session_id):
        try:
            session = QuizSession.objects.get(id=session_id)
        except QuizSession.DoesNotExist:
            return Response({'status': 'error', 'message': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        if session.user != request.user:
            return Response({'status': 'error', 'message': '접근 권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
        session_problems = SessionProblem.objects.filter(
            session=session
        ).select_related('problem').prefetch_related('problem__assets').order_by('order_index')
        problems = [
            _serialize_problem(sp.problem, request, extra_fields={'order': sp.order_index})
            for sp in session_problems
        ]
        return Response({'status': 'success', 'data': {'session_id': session.id, 'status': session.status, 'total': len(problems), 'problems': problems}})


class QuizSessionSubmitView(APIView):

    def post(self, request, session_id):
        try:
            session = QuizSession.objects.get(id=session_id)
        except QuizSession.DoesNotExist:
            return Response({'status': 'error', 'message': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        if session.user != request.user:
            return Response({'status': 'error', 'message': '접근 권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
        if session.status == 'completed':
            return Response({'status': 'error', 'message': '이미 제출된 세션입니다.'}, status=status.HTTP_409_CONFLICT)
        answers = request.data.get('answers', [])
        if not answers:
            return Response({'status': 'error', 'message': 'answers가 비어있습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        session_problems = SessionProblem.objects.filter(session=session).select_related('problem')
        problem_map = {sp.problem.id: sp.problem for sp in session_problems}
        results = []
        score = 0
        for answer in answers:
            problem_id  = answer.get('problem_id')
            user_answer = answer.get('user_answer', '').strip()
            if problem_id not in problem_map:
                continue
            problem = problem_map[problem_id]
            correct_label = problem.grading_answer or problem.answer.strip()
            if problem.is_multi_answer:
                submitted = set(s.strip() for s in user_answer.split(','))
                correct   = set(correct_label.split(','))
                is_correct = (submitted == correct)
            else:
                is_correct = (user_answer == correct_label)
            if is_correct:
                score += 1
            SessionResult.objects.create(
                session=session, problem=problem,
                student_answer=user_answer, is_correct=is_correct,
            )
            results.append({
                'problem_id':      problem_id,
                'user_answer':     user_answer,
                'correct_answer':  problem.answer,
                'grading_answer':  correct_label,
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
        return Response({'status': 'success', 'data': {'session_id': session.id, 'score': score, 'total': len(results), 'accuracy': round(score / len(results), 2) if results else 0, 'results': results}})


def _update_subtype_mastery(user, results):
    subtype_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
    for r in results:
        subtype = r['problem_subtype']
        subtype_stats[subtype]['total']   += 1
        subtype_stats[subtype]['correct'] += 1 if r['is_correct'] else 0
    for subtype, stats in subtype_stats.items():
        mastery, _ = SubtypeMastery.objects.get_or_create(
            user=user, problem_subtype=subtype,
            defaults={'total_attempts': 0, 'correct_count': 0}
        )
        prev_accuracy = (mastery.correct_count / mastery.total_attempts if mastery.total_attempts > 0 else None)
        mastery.total_attempts += stats['total']
        mastery.correct_count  += stats['correct']
        new_accuracy = mastery.correct_count / mastery.total_attempts
        was_mastered = mastery.mastered
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
            return Response({'status': 'error', 'message': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        if session.user != request.user:
            return Response({'status': 'error', 'message': '접근 권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
        if session.status != 'completed':
            return Response({'status': 'error', 'message': '아직 제출되지 않은 세션입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        wrong_results = SessionResult.objects.filter(
            session=session, is_correct=False
        ).select_related('problem').prefetch_related('problem__assets')
        wrong_problems = [
            _serialize_problem_with_answer(result.problem, request, extra_fields={'user_answer': result.student_answer})
            for result in wrong_results
        ]
        return Response({'status': 'success', 'data': {'session_id': session.id, 'wrong_count': len(wrong_problems), 'wrong_problems': wrong_problems}})


class QuizSessionAnalysisView(APIView):

    def get(self, request, session_id):
        try:
            session = QuizSession.objects.get(id=session_id)
        except QuizSession.DoesNotExist:
            return Response({'status': 'error', 'message': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        if session.user != request.user:
            return Response({'status': 'error', 'message': '접근 권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
        if session.status != 'completed':
            return Response({'status': 'error', 'message': '아직 제출되지 않은 세션입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        results = SessionResult.objects.filter(session=session).select_related('problem')
        total = results.count()
        score = results.filter(is_correct=True).count()
        wrong_results = results.filter(is_correct=False)
        if not wrong_results.exists():
            return Response({'status': 'success', 'data': {'session_id': session.id, 'score': score, 'total': total, 'accuracy': 1.0, 'all_correct': True, 'weak_subtypes': []}})
        subtype_stats = defaultdict(lambda: {'wrong': 0, 'total': 0})
        for r in results:
            subtype = r.problem.problem_subtype
            subtype_stats[subtype]['total'] += 1
            if not r.is_correct:
                subtype_stats[subtype]['wrong'] += 1
        weak_list = [(subtype, stats) for subtype, stats in subtype_stats.items() if stats['wrong'] > 0]
        weak_list.sort(key=lambda x: x[1]['wrong'] / x[1]['total'], reverse=True)
        top3 = weak_list[:3]
        weak_subtypes = []
        for rank, (subtype, stats) in enumerate(top3, start=1):
            accuracy = round((stats['total'] - stats['wrong']) / stats['total'], 2)
            weak_subtypes.append({'rank': rank, 'problem_subtype': subtype, 'wrong_count': stats['wrong'], 'total_count': stats['total'], 'accuracy': accuracy})
        return Response({'status': 'success', 'data': {'session_id': session.id, 'score': score, 'total': total, 'accuracy': round(score / total, 2), 'all_correct': False, 'weak_subtypes': weak_subtypes}})


def _build_subtype_mastery_list(user):
    from django.db.models import Count
    masteries = SubtypeMastery.objects.filter(user=user).order_by('-updated_at')
    all_subtypes_qs = Problem.objects.filter(is_quizable=True).values('problem_subtype', 'chapter_major', 'chapter_middle').distinct()
    chapter_map = {}
    for p in all_subtypes_qs:
        subtype = p['problem_subtype']
        if subtype not in chapter_map:
            chapter_map[subtype] = {'chapter_major': p['chapter_major'], 'chapter_middle': p['chapter_middle']}
    total_map = {r['problem_subtype']: r['count'] for r in Problem.objects.filter(is_quizable=True).values('problem_subtype').annotate(count=Count('id'))}
    mastery_map = {m.problem_subtype: m for m in masteries}
    all_subtype_names = list(chapter_map.keys())
    attempted_map = {}
    for subtype in all_subtype_names:
        attempted_map[subtype] = SessionProblem.objects.filter(
            session__user=user, session__status='completed',
            problem__is_quizable=True, problem__problem_subtype=subtype
        ).values('problem_id').distinct().count()
    subtype_mastery = []
    for subtype in all_subtype_names:
        m = mastery_map.get(subtype)
        if m:
            accuracy        = round(m.correct_count / m.total_attempts, 2) if m.total_attempts > 0 else 0
            mastered        = m.mastered
            accuracy_before = round(m.accuracy_before * 100) if m.accuracy_before else None
            accuracy_after  = round(m.accuracy_after * 100)  if m.accuracy_after  else None
            next_difficulty = ('상' if accuracy >= 0.95 else '중') if mastered else None
            updated_at      = m.updated_at
        else:
            accuracy = mastered = 0
            mastered        = False
            accuracy_before = accuracy_after = next_difficulty = updated_at = None
        attempted_count = min(attempted_map.get(subtype, 0), total_map.get(subtype, 0))
        total_count     = total_map.get(subtype, 0)
        if attempted_count == 0:
            level = '풀이 필요'
        elif attempted_count < total_count:
            level = '풀이 중'
        elif m and m.total_attempts > 0 and m.correct_count == m.total_attempts:
            level = '숙달 완료'
        else:
            level = '풀이 완료'
        chapter = chapter_map.get(subtype, {})
        subtype_mastery.append({
            'problem_subtype':  subtype,
            'chapter_major':    chapter.get('chapter_major'),
            'chapter_middle':   chapter.get('chapter_middle'),
            'mastered':         mastered,
            'level':            level,
            'accuracy':         round(accuracy * 100),
            'accuracy_before':  accuracy_before,
            'accuracy_after':   accuracy_after,
            'total_attempts':   attempted_count,
            'total_in_subtype': total_count,
            'next_difficulty':  next_difficulty,
            'updated_at':       updated_at,
        })
    return subtype_mastery


class UserHistoryView(APIView):

    def get(self, request):
        sessions = QuizSession.objects.filter(user=request.user, status='completed').order_by('-created_at')
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
                'accuracy':       round(session.score / session.problem_count, 2) if session.score is not None else None,
                'created_at':     session.created_at,
            })
        subtype_mastery = _build_subtype_mastery_list(request.user)
        return Response({'status': 'success', 'data': {'sessions': session_list, 'subtype_mastery': subtype_mastery}})


class ProblemDetailView(APIView):

    def get(self, request, problem_id):
        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            return Response({'status': 'error', 'message': '문제를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'status': 'success', 'data': _serialize_problem(problem, request)})


class QuizSessionRecommendationsView(APIView):

    def get(self, request, session_id):
        try:
            session = QuizSession.objects.get(id=session_id)
        except QuizSession.DoesNotExist:
            return Response({'status': 'error', 'message': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        if session.user != request.user:
            return Response({'status': 'error', 'message': '접근 권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
        if session.status != 'completed':
            return Response({'status': 'error', 'message': '아직 제출되지 않은 세션입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 이미 생성된 리포트면 DB에서 바로 반환 (LLM 재호출 방지)
        try:
            report = session.weakness_report
            return Response({'status': 'success', 'data': _serialize_report(report)})
        except WeaknessReport.DoesNotExist:
            pass

        results       = SessionResult.objects.filter(session=session).select_related('problem')
        wrong_results = results.filter(is_correct=False)
        solved_ids    = list(results.values_list('problem__id', flat=True))
        all_correct   = not wrong_results.exists()

        subtype_total = defaultdict(int)
        for r in results:
            subtype_total[r.problem.problem_subtype] += 1

        wrong_problems = [
            {
                'problem_id':       r.problem.id,
                'problem_subtype':  r.problem.problem_subtype,
                'question_text':    r.problem.question_text,
                'chapter_minor':    r.problem.chapter_minor,
                'total_in_subtype': subtype_total[r.problem.problem_subtype],
            }
            for r in wrong_results
        ]

        # ── coaching_graph 호출 ─────────────────────────────────────
        try:
            state = coaching_graph.invoke({
                'session_id':          session.id,
                'chapter_middle':      session.chapter_middle,
                'session_type':        session.session_type,
                'solved_ids':          solved_ids,
                'all_correct':         all_correct,
                'wrong_problems':      wrong_problems,
                'top3':                [],
                'ai_feedback':         None,
                'weak_subtypes_data':  [],
                'harder_problem_ids':  [],
            })
        except Exception:
            state = {
                'all_correct':        all_correct,
                'ai_feedback':        '취약 유형을 집중적으로 보완해 보세요!' if not all_correct
                                      else '모든 문제를 맞혔어요! 더 어려운 문제에 도전해보세요.',
                'weak_subtypes_data': [],
                'harder_problem_ids': [],
            }

        # ── DB 저장 ─────────────────────────────────────────────────
        report = WeaknessReport.objects.create(
            session=session,
            all_correct=all_correct,
            ai_feedback=state.get('ai_feedback', ''),
        )

        if all_correct:
            for idx, item in enumerate(state.get('harder_problem_ids', [])):
                try:
                    problem = Problem.objects.get(id=item['problem_id'])
                    Recommendation.objects.create(
                        report=report, weak_subtype=None, problem=problem,
                        similarity_score=None, order_index=idx + 1, reason=item.get('reason', ''),
                    )
                except Problem.DoesNotExist:
                    continue
        else:
            for item in state.get('weak_subtypes_data', []):
                total_in_subtype = results.filter(problem__problem_subtype=item['problem_subtype']).count()
                weak = WeakSubtype.objects.create(
                    report=report,
                    problem_subtype=item['problem_subtype'],
                    wrong_count=item['wrong_count'],
                    total_count=total_in_subtype,
                    rank=item['rank'],
                )
                ordered_ids = (
                    item.get('s1_ids', [])[:1]
                    + item.get('mid_ids', [])
                    + item.get('s1_ids', [])[1:2]
                )
                for idx, problem_id in enumerate(ordered_ids):
                    try:
                        problem = Problem.objects.get(id=problem_id)
                        Recommendation.objects.create(
                            report=report, weak_subtype=weak, problem=problem,
                            similarity_score=None, order_index=idx + 1,
                            reason=f'{item["problem_subtype"]} 유형 유사 문제 (난이도: {problem.difficulty})',
                        )
                    except Problem.DoesNotExist:
                        continue

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
        return {'all_correct': True, 'ai_feedback': report.ai_feedback, 'weak_subtypes': [], 'recommendations': recommendations}

    weak_subtypes = []
    for weak in report.weak_subtypes.all():
        sample_wrong = SessionResult.objects.filter(
            session=report.session, problem__problem_subtype=weak.problem_subtype, is_correct=False,
        ).select_related('problem').first()
        weak_subtypes.append({
            'rank':                weak.rank,
            'problem_subtype':     weak.problem_subtype,
            'wrong_count':         weak.wrong_count,
            'total_count':         weak.total_count,
            'original_problem_id': sample_wrong.problem.id if sample_wrong else None,
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
    return {'all_correct': False, 'ai_feedback': report.ai_feedback, 'weak_subtypes': weak_subtypes, 'recommendations': recommendations}


class CSRFTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = get_token(request)
        return Response({"status": "success", "data": {"csrfToken": token}})


class UserDashboardView(APIView):

    def get(self, request):
        user = request.user
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        week_days = [monday + timedelta(days=i) for i in range(7)]
        active_dates = set(
            QuizSession.objects.filter(
                user=user, status='completed',
                created_at__date__gte=monday, created_at__date__lte=today,
            ).values_list('created_at__date', flat=True)
        )
        weekly_activity = [d in active_dates for d in week_days]
        full_mastery_list    = _build_subtype_mastery_list(user)
        mastered_count       = sum(1 for m in full_mastery_list if m['level'] == '숙달 완료')
        solving_count        = sum(1 for m in full_mastery_list if m['level'] == '풀이 중')
        total_subtype_count  = len(full_mastery_list)
        total_problem_count  = Problem.objects.filter(is_quizable=True).count()
        recently_updated = sorted([m for m in full_mastery_list if m['updated_at']], key=lambda m: m['updated_at'], reverse=True)
        subtype_mastery = [
            {'problem_subtype': m['problem_subtype'], 'level': m['level'], 'pct': m['accuracy'], 'mastered': m['mastered']}
            for m in recently_updated[:3]
        ]
        latest_session = QuizSession.objects.filter(user=user, status='completed').order_by('-created_at').first()
        latest_session_data = None
        if latest_session:
            latest_session_data = {
                'session_id':     latest_session.id,
                'chapter_middle': latest_session.chapter_middle,
                'accuracy':       round(latest_session.score / latest_session.problem_count, 2) if latest_session.score is not None else None,
                'created_at':     latest_session.created_at.strftime('%Y-%m-%d'),
            }
        return Response({'status': 'success', 'data': {
            'user': {'name': user.first_name or user.username, 'grade': user.grade, 'joined_days': (date.today() - user.date_joined.date()).days + 1},
            'streak': user.streak, 'total_solved': user.total_solved,
            'total_problem_count': total_problem_count, 'mastered_count': mastered_count,
            'solving_count': solving_count, 'total_subtype_count': total_subtype_count,
            'weekly_activity': weekly_activity, 'subtype_mastery': subtype_mastery,
            'latest_session': latest_session_data,
        }})


class TodayRecommendationView(APIView):

    def get(self, request):
        user = request.user
        weak_masteries = SubtypeMastery.objects.filter(user=user, mastered=False).order_by('correct_count')
        if weak_masteries.exists():
            target = weak_masteries.first()
            reason = f'{target.problem_subtype} 유형에서 아직 보완이 필요해요'
            mode   = 'review'
        else:
            latest_mastered = SubtypeMastery.objects.filter(user=user, mastered=True).order_by('-updated_at').first()
            if not latest_mastered:
                return Response({'status': 'success', 'data': {'has_recommendation': False, 'message': '퀴즈를 풀면 맞춤 추천을 드려요!'}})
            target = latest_mastered
            reason = f'{target.problem_subtype} 유형을 마스터했어요! 더 어려운 문제에 도전해봐요'
            mode   = 'challenge'
        sample_problem = Problem.objects.filter(problem_subtype=target.problem_subtype, is_quizable=True).first()
        if not sample_problem:
            return Response({'status': 'success', 'data': {'has_recommendation': False, 'message': '추천할 문제가 없어요.'}})
        if mode == 'review':
            preview_problems = Problem.objects.filter(problem_subtype=target.problem_subtype, is_quizable=True, difficulty='하')[:3]
        else:
            accuracy = target.correct_count / target.total_attempts if target.total_attempts > 0 else 0
            next_difficulty = '상' if accuracy >= 0.95 else '중'
            preview_problems = Problem.objects.filter(problem_subtype=target.problem_subtype, is_quizable=True, difficulty=next_difficulty)[:3]
        problems_data = [{'problem_id': p.id, 'problem_subtype': p.problem_subtype, 'difficulty': p.difficulty, 'question_text': p.question_text} for p in preview_problems]
        prefill = {'chapter_major': sample_problem.chapter_major, 'chapter_middle': sample_problem.chapter_middle, 'chapter_minor': sample_problem.chapter_minor, 'problem_subtype': target.problem_subtype, 'suggested_count': 10}
        return Response({'status': 'success', 'data': {'has_recommendation': True, 'mode': mode, 'recommended_subtype': target.problem_subtype, 'reason': reason, 'problems': problems_data, 'prefill': prefill}})


class ReviewProblemView(APIView):

    def get(self, request, session_id):
        problem_id = request.query_params.get('problem_id')
        if not problem_id:
            return Response({'status': 'error', 'message': 'problem_id가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            session = QuizSession.objects.get(id=session_id, user=request.user)
        except QuizSession.DoesNotExist:
            return Response({'status': 'error', 'message': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        is_wrong = SessionResult.objects.filter(session=session, problem_id=problem_id, is_correct=False).exists()
        if not is_wrong:
            return Response({'status': 'error', 'message': '해당 세션의 오답 문제가 아닙니다.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            problem = Problem.objects.prefetch_related('assets').get(id=problem_id)
        except Problem.DoesNotExist:
            return Response({'status': 'error', 'message': '문제를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'status': 'success', 'data': _serialize_problem_with_answer(problem, request)})


class QuizSessionChatView(APIView):

    def post(self, request, session_id):
        try:
            session = QuizSession.objects.get(id=session_id)
        except QuizSession.DoesNotExist:
            return Response({'status': 'error', 'message': '세션을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        if session.user != request.user:
            return Response({'status': 'error', 'message': '접근 권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
        problem_id = request.data.get('problem_id')
        question   = request.data.get('question', '').strip()
        history    = request.data.get('history', [])
        if not problem_id or not question:
            return Response({'status': 'error', 'message': 'problem_id와 question은 필수입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            return Response({'status': 'error', 'message': '문제를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        # chat_graph 호출
        result = chat_graph.invoke({
            'problem_text':   problem.question_text,
            'correct_answer': problem.answer,
            'explanation':    problem.explanation,
            'question':       question,
            'history':        history,
            'block_reason':   None,
            'retry_count':    0,
            'answer':         None,
        })
        return Response({'status': 'success', 'data': {
            'question':     question,
            'answer':       result['answer'],
            'is_blocked':   result.get('block_reason') is not None,
            'block_reason': result.get('block_reason'),
        }})


class ProblemCommentView(APIView):
    """
    문제별 공개 Q&A 댓글 (커뮤니티)
    GET    /problems/{problem_id}/comments
    POST   /problems/{problem_id}/comments
    DELETE /problems/{problem_id}/comments/{comment_id}
    """
    from .models import Comment
    from .serializers import CommentSerializer

    def _get_problem_or_404(self, problem_id):
        try:
            return Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            return None

    def get(self, request, problem_id, post_id=None):
        problem = self._get_problem_or_404(problem_id)
        if not problem:
            return Response({'status': 'error', 'message': '문제를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        from .models import Comment
        from .serializers import CommentSerializer
        comments = problem.comments.select_related('user').all()
        serializer = CommentSerializer(comments, many=True)
        return Response({'status': 'success', 'data': {'problem_id': problem_id, 'comment_count': comments.count(), 'comments': serializer.data}})

    def post(self, request, problem_id, post_id=None):
        if not request.user.is_authenticated:
            return Response({'status': 'error', 'message': '로그인이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)
        problem = self._get_problem_or_404(problem_id)
        if not problem:
            return Response({'status': 'error', 'message': '문제를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'status': 'error', 'message': '댓글 내용을 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)
        from .models import Comment
        from .serializers import CommentSerializer
        comment = Comment.objects.create(post_id=post_id, user=request.user, content=content)
        return Response({'status': 'success', 'data': CommentSerializer(comment).data}, status=status.HTTP_201_CREATED)

    def delete(self, request, problem_id, post_id=None, comment_id=None):
        if not request.user.is_authenticated:
            return Response({'status': 'error', 'message': '로그인이 필요합니다.'}, status=status.HTTP_401_UNAUTHORIZED)
        from .models import Comment
        try:
            comment = Comment.objects.get(id=comment_id, problem_id=problem_id)
        except Comment.DoesNotExist:
            return Response({'status': 'error', 'message': '댓글을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        if comment.user != request.user:
            return Response({'status': 'error', 'message': '본인 댓글만 삭제할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response({'status': 'success', 'message': '삭제되었습니다.'})


class PostListView(APIView):

    def get(self, request, problem_id):
        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            return Response({'status': 'error', 'message': '문제를 찾을 수 없습니다.'}, status=404)
        from .serializers import PostSerializer
        posts = problem.posts.select_related('user').prefetch_related('comments').all()
        serializer = PostSerializer(posts, many=True)
        return Response({'status': 'success', 'data': {'problem_id': problem_id, 'post_count': posts.count(), 'posts': serializer.data}})

    def post(self, request, problem_id, post_id=None):
        if not request.user.is_authenticated:
            return Response({'status': 'error', 'message': '로그인이 필요합니다.'}, status=401)
        try:
            problem = Problem.objects.get(id=problem_id)
        except Problem.DoesNotExist:
            return Response({'status': 'error', 'message': '문제를 찾을 수 없습니다.'}, status=404)
        title   = request.data.get('title', '').strip()
        content = request.data.get('content', '').strip()
        if not title or not content:
            return Response({'status': 'error', 'message': '제목과 내용을 입력해주세요.'}, status=400)
        from .serializers import PostSerializer
        post = Post.objects.create(problem=problem, user=request.user, title=title, content=content)
        return Response({'status': 'success', 'data': PostSerializer(post).data}, status=201)


class PostDetailView(APIView):

    def get(self, request, problem_id, post_id):
        from .serializers import PostDetailSerializer
        try:
            post = Post.objects.prefetch_related('comments__user').get(id=post_id, problem_id=problem_id)
        except Post.DoesNotExist:
            return Response({'status': 'error', 'message': '게시글을 찾을 수 없습니다.'}, status=404)
        return Response({'status': 'success', 'data': PostDetailSerializer(post).data})

    def delete(self, request, problem_id, post_id):
        if not request.user.is_authenticated:
            return Response({'status': 'error', 'message': '로그인이 필요합니다.'}, status=401)
        try:
            post = Post.objects.get(id=post_id, problem_id=problem_id)
        except Post.DoesNotExist:
            return Response({'status': 'error', 'message': '게시글을 찾을 수 없습니다.'}, status=404)
        if post.user != request.user:
            return Response({'status': 'error', 'message': '본인 게시글만 삭제할 수 있습니다.'}, status=403)
        post.delete()
        return Response({'status': 'success', 'message': '삭제되었습니다.'})


PostCommentView = ProblemCommentView