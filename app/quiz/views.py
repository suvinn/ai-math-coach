from django.contrib.auth import authenticate, login, logout, get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .serializers import RegisterSerializer, UserSerializer
from .models import Problem

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