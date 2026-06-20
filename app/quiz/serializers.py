from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import Problem, ProblemAsset

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'first_name']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='first_name')

    class Meta:
        model = User
        fields = ['id', 'username', 'name']


class ProblemAssetSerializer(serializers.ModelSerializer):
    """option_type='mixed_with_image'인 문제에서, 그래프/도형 등 텍스트로
    표현 안 되는 보기 이미지를 내려줄 때 사용."""

    image_url = serializers.SerializerMethodField()
    bbox = serializers.SerializerMethodField()

    class Meta:
        model = ProblemAsset
        fields = ["asset_role", "image_url", "bbox"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        url = settings.MEDIA_URL.rstrip("/") + "/" + obj.image_path.lstrip("/")
        return request.build_absolute_uri(url) if request else url

    def get_bbox(self, obj):
        return [obj.bbox_x1, obj.bbox_y1, obj.bbox_x2, obj.bbox_y2]


class ProblemPublicSerializer(serializers.ModelSerializer):
    """
    퀴즈 풀이 화면용 (GET /quiz/sessions/{id}/problems, GET /problems/{id} 등)
    """

    problem_id = serializers.CharField(source="id")
    assets = serializers.SerializerMethodField()

    class Meta:
        model = Problem
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
        ]

    def get_assets(self, obj):
        if obj.option_type != "mixed_with_image":
            return []
        return ProblemAssetSerializer(
            obj.assets.all(), many=True, context=self.context
        ).data


class ProblemWithAnswerSerializer(ProblemPublicSerializer):
    """
    채점/오답 조회용 (POST .../submit 응답, GET .../wrong-answers)
    제출 이후에만 사용 — answer, explanation 포함.
    """

    class Meta(ProblemPublicSerializer.Meta):
        fields = ProblemPublicSerializer.Meta.fields + ["answer", "explanation"]