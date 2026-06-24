from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import Problem, ProblemAsset, Comment

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password                = serializers.CharField(write_only=True)
    # 선택 입력 — 빠른 진단에 사용
    grade                   = serializers.CharField(required=False, default='중2')
    current_chapter_major   = serializers.CharField(required=False, allow_blank=True, default='')
    current_chapter_middle  = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model  = User
        fields = [
            'username', 'password', 'first_name',
            'grade',
            'current_chapter_major', 'current_chapter_middle',
        ]

    def create(self, validated_data):
        user = User.objects.create_user(
            username   = validated_data['username'],
            password   = validated_data['password'],
            first_name = validated_data.get('first_name', ''),
        )
        user.grade                   = validated_data.get('grade', '중2')
        user.current_chapter_major   = validated_data.get('current_chapter_major', '')
        user.current_chapter_middle  = validated_data.get('current_chapter_middle', '')
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='first_name')

    class Meta:
        model  = User
        fields = ['id', 'username', 'name']


class ProblemAssetSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    bbox      = serializers.SerializerMethodField()

    class Meta:
        model  = ProblemAsset
        fields = ["asset_role", "image_url", "bbox"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        url = settings.MEDIA_URL.rstrip("/") + "/" + obj.image_path.lstrip("/")
        return request.build_absolute_uri(url) if request else url

    def get_bbox(self, obj):
        return [obj.bbox_x1, obj.bbox_y1, obj.bbox_x2, obj.bbox_y2]


class ProblemPublicSerializer(serializers.ModelSerializer):
    """퀴즈 풀이 화면용 (GET /quiz/sessions/{id}/problems, GET /problems/{id} 등)"""
    problem_id = serializers.CharField(source="id")
    assets     = serializers.SerializerMethodField()

    class Meta:
        model  = Problem
        fields = [
            "problem_id",
            "difficulty",
            "chapter_major",
            "chapter_middle",
            "chapter_minor",
            "problem_subtype",
            "question_text",
            "question_with_options",
            "question_image_bbox",
            "option_type",
            "assets",
            "is_multi_answer",
        ]

    def get_assets(self, obj):
        if obj.option_type != "mixed_with_image":
            return []
        return ProblemAssetSerializer(
            obj.assets.all(), many=True, context=self.context
        ).data

    def to_representation(self, instance):
        """context에 extra_fields가 있으면 직렬화 결과에 병합한다.

        사용 예시 — SessionProblem의 order_index 같이 내보내기:
            serializer = ProblemPublicSerializer(
                problem,
                context={'request': request, 'extra_fields': {'order': sp.order_index}},
            )
        """
        data = super().to_representation(instance)
        for key, value in self.context.get("extra_fields", {}).items():
            data[key] = value
        return data


class ProblemWithAnswerSerializer(ProblemPublicSerializer):
    """채점/오답 조회용 — answer, explanation, grading_answer 포함"""
    class Meta(ProblemPublicSerializer.Meta):
        fields = ProblemPublicSerializer.Meta.fields + [
            "answer", "grading_answer", "explanation",
        ]


class CommentSerializer(serializers.ModelSerializer):
    """문제별 댓글 직렬화"""
    username = serializers.CharField(source='user.username', read_only=True)
    name     = serializers.CharField(source='user.first_name', read_only=True)

    class Meta:
        model  = Comment
        fields = ['id', 'username', 'name', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'username', 'name', 'created_at', 'updated_at']