from django.contrib.auth import authenticate, login, logout, get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .serializers import RegisterSerializer, UserSerializer
from .models import Problem, QuizSession, SessionProblem, SessionResult
import random


User = get_user_model()

@method_decorator(csrf_exempt, name='dispatch')
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

@method_decorator(csrf_exempt, name='dispatch')
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

@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'status': 'success', 'message': '로그아웃 되었습니다.'})

@method_decorator(csrf_exempt, name='dispatch')
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
        chapter_major  = request.data.get('chapter_major')
        chapter_middle = request.data.get('chapter_middle')
        chapter_minor  = request.data.get('chapter_minor')
        problem_count  = request.data.get('problem_count')

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

        problems = Problem.objects.filter(
            chapter_major=chapter_major,
            chapter_middle=chapter_middle,
            is_quizable=True,
        )
        if chapter_minor:
            problems = problems.filter(chapter_minor=chapter_minor)

        if not problems.exists():
            return Response(
                {'status': 'error', 'message': '해당 범위에 문제가 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        problem_list = list(problems)
        actual_count = min(problem_count, len(problem_list))  # 요청한 수보다 실제 문제가 적으면 있는 만큼만
        selected     = random.sample(problem_list, actual_count)

        session = QuizSession.objects.create(
            user=request.user,
            chapter_major=chapter_major,
            chapter_middle=chapter_middle,
            chapter_minor=chapter_minor or '',
            problem_count=actual_count,
        )

        for idx, problem in enumerate(selected):
            SessionProblem.objects.create(
                session=session,
                problem=problem,
                order_index=idx + 1
            )

        return Response({
            'status': 'success',
            'data': {
                'session_id':      session.id,
                'status':          session.status,
                'requested_count': problem_count,
                'actual_count':    actual_count,
                'created_at':      session.created_at,
            }
        }, status=status.HTTP_201_CREATED)


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
        ).select_related('problem').order_by('order_index')

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
        score = 0

        for answer in answers:
            problem_id  = answer.get('problem_id')
            user_answer = answer.get('user_answer', '').strip()

            if problem_id not in problem_map:
                continue

            problem    = problem_map[problem_id]
            is_correct = (user_answer == problem.answer.strip())

            if is_correct:
                score += 1

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

        session.status = 'completed'
        session.score  = score
        session.save()

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
        ).select_related('problem')

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
            })

        return Response({
            'status': 'success',
            'data': {
                'session_id':    session.id,
                'wrong_count':   len(wrong_problems),
                'wrong_problems': wrong_problems,
            }
        })