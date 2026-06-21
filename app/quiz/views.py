from django.contrib.auth import authenticate, login, logout, get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.utils.decorators import method_decorator
from .serializers import RegisterSerializer, UserSerializer
from .models import Problem, QuizSession, SessionProblem, SessionResult, WeaknessReport, WeakSubtype, Recommendation, SubtypeMastery
import random
from datetime import date, timedelta
from collections import defaultdict
from openai import OpenAI
import chromadb
from django.conf import settings


def _serialize_assets(problem, request=None):
    """option_type='mixed_with_image'인 문제의 보기 이미지 목록을 응답용 dict 리스트로 변환."""
    if problem.option_type != 'mixed_with_image':
        return []
 
    out = []
    for asset in problem.assets.all():  # prefetch_related 안 해두면 view마다 N+1 발생 -> 아래 3) 참고
        url = settings.MEDIA_URL.rstrip('/') + '/' + asset.image_path.lstrip('/')
        if request is not None:
            url = request.build_absolute_uri(url)
        out.append({
            'asset_role': asset.asset_role,
            'image_url': url,
            'bbox': [asset.bbox_x1, asset.bbox_y1, asset.bbox_x2, asset.bbox_y2],
        })
    return out


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
        return Response({
            'status': 'success',
            'data': {
                # 'user_id': user.id,
                'username': user.username,
                'name': user.first_name,
            }
        }, status=status.HTTP_201_CREATED)


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
        return Response({
            'status': 'success',
            'data': {
                # 'user_id': request.user.id,
                'username': request.user.username,
                'name': request.user.first_name,
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
        chapter_major     = request.data.get('chapter_major')
        chapter_middle    = request.data.get('chapter_middle')
        chapter_minor     = request.data.get('chapter_minor')
        problem_count     = request.data.get('problem_count')
        parent_session_id = request.data.get('parent_session_id')  # optional

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

            if parent_session.session_type == 'normal':
                session_type = 'review_1'
            elif parent_session.session_type == 'review_1':
                session_type = 'review_2'
            elif parent_session.session_type == 'review_2':
                # 3회차 초과 → 세션 생성 없이 해설만 반환
                wrong_results = SessionResult.objects.filter(
                    session=parent_session,
                    is_correct=False
                ).select_related('problem')

                explanations = [
                    {
                        'problem_id':     r.problem.id,
                        'question_text':  r.problem.question_text,
                        'user_answer':    r.student_answer,
                        'correct_answer': r.problem.answer,
                        'explanation':    r.problem.explanation,
                        'problem_subtype': r.problem.problem_subtype,
                    }
                    for r in wrong_results
                ]
                return Response({
                    'status': 'success',
                    'data': {
                        'session_created':  False,
                        'show_explanation': True,
                        'message':          '이 유형은 해설을 꼼꼼히 읽고 다음에 다시 도전해봐요!',
                        'explanations':     explanations,
                    }
                })

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

        elif session_type == 'review_1':
            # 1차 오답 보완: 취약 subtype 유사 문제, 하 위주
            weak_subtypes = _get_weak_subtypes(parent_session)
            problems = list(Problem.objects.filter(
                **base_filter,
                problem_subtype__in=weak_subtypes,
                difficulty__in=['하', '중'],
            ))
            if not problems:
                problems = list(Problem.objects.filter(**base_filter, difficulty__in=['하', '중']))

            actual_count = min(problem_count, len(problems))
            selected     = random.sample(problems, actual_count)

        else:  # review_2
            # 2차 오답 보완: 취약 subtype, 하 난이도만
            weak_subtypes = _get_weak_subtypes(parent_session)
            problems = list(Problem.objects.filter(
                **base_filter,
                problem_subtype__in=weak_subtypes,
                difficulty='하',
            ))
            if not problems:
                problems = list(Problem.objects.filter(**base_filter, difficulty='하'))

            actual_count = min(problem_count, len(problems))
            selected     = random.sample(problems, actual_count)

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

        return Response({
            'status': 'success',
            'data': {
                'session_id':      session.id,
                'session_type':    session.session_type,
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

        problems = []
        for sp in session_problems:
            p = sp.problem
            problems.append({
                'order':                sp.order_index,
                'problem_id':           p.id,
                'difficulty':           p.difficulty,
                'problem_subtype':      p.problem_subtype,
                'question_text':        p.question_text,
                'question_with_options': p.question_with_options,
                'question_image_bbox':  p.question_image_bbox,
                'option_type':          p.option_type,
                'assets':               _serialize_assets(p, request),
                'is_multi_answer':      p.is_multi_answer,
            })

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


def _recommend_similar(report, weak, sample_problem, solved_ids, session):
    """RAG로 유사 문제 추천 — 난이도 하 우선 → 없으면 전체"""
    client        = OpenAI(
        api_key=settings.GMS_KEY,
        base_url=settings.GMS_URL
    )
    chroma_client = chromadb.PersistentClient(path='./chroma_db')
    collection    = chroma_client.get_collection('problems')

    # 오답 문제 question_text로 임베딩 쿼리
    query_embedding = client.embeddings.create(
        model='text-embedding-3-small',
        input=[sample_problem.question_text],
    ).data[0].embedding

    def _query(where_filter):
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=10,
            where=where_filter,
        )

    # 1순위: 같은 subtype + 하 난이도
    results = _query({
        '$and': [
            {'problem_subtype': {'$eq': weak.problem_subtype}},
            {'difficulty':      {'$eq': '하'}},
            {'is_quizable':     {'$eq': 'True'}},
        ]
    })
    recommended_ids = [
        pid for pid in results['ids'][0] if pid not in solved_ids
    ][:3]

    # 2순위: 같은 subtype (난이도 무관)
    if not recommended_ids:
        results = _query({
            '$and': [
                {'problem_subtype': {'$eq': weak.problem_subtype}},
                {'is_quizable':     {'$eq': 'True'}},
            ]
        })
        recommended_ids = [
            pid for pid in results['ids'][0] if pid not in solved_ids
        ][:3]

    # 3순위: 같은 chapter_minor (subtype 폴백)
    if not recommended_ids:
        results = _query({
            '$and': [
                {'chapter_minor': {'$eq': sample_problem.chapter_minor}},
                {'is_quizable':   {'$eq': 'True'}},
            ]
        })
        recommended_ids = [
            pid for pid in results['ids'][0] if pid not in solved_ids
        ][:3]

    # Recommendation 저장
    for idx, problem_id in enumerate(recommended_ids):
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

    # 취약 유형별 데이터
    weak_subtypes = []
    for weak in report.weak_subtypes.all():
        weak_subtypes.append({
            'rank':            weak.rank,
            'problem_subtype': weak.problem_subtype,
            'wrong_count':     weak.wrong_count,
            'total_count':     weak.total_count,
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