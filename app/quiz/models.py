from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):
    grade = models.CharField(max_length=10, default='중2')
    streak = models.IntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)
    total_solved = models.IntegerField(default=0)

    class Meta:
        db_table = 'user'


class Problem(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    
    difficulty = models.CharField(max_length=5)
    chapter_major = models.CharField(max_length=50)
    chapter_middle = models.CharField(max_length=50)
    chapter_minor = models.CharField(max_length=50)
    problem_subtype = models.CharField(max_length=100)
    question_text = models.TextField()
    question_with_options = models.TextField(null=True, blank=True)
    question_image_bbox = models.JSONField(default=list)
    answer = models.CharField(max_length=200)
    explanation = models.TextField()
    is_quizable = models.BooleanField(default=False)

    class Meta:
        db_table = 'problem'


class QuizSession(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    SESSION_TYPE_CHOICES = [
        ('normal',   '일반 세션'),
        ('review_1', '1차 오답 보완'),
        ('review_2', '2차 오답 보완'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    chapter_major = models.CharField(max_length=50)
    chapter_middle = models.CharField(max_length=50)
    chapter_minor = models.CharField(max_length=50, null=True, blank=True)
    problem_count = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    score = models.IntegerField(null=True, blank=True)
    ai_feedback = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    session_type   = models.CharField(
        max_length=20,
        choices=SESSION_TYPE_CHOICES,
        default='normal'
    )
    parent_session = models.ForeignKey(
        'self',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='child_sessions'
    )

    class Meta:
        db_table = 'quiz_session'


class SessionProblem(models.Model):
    """세션에 출제된 문제 목록 + 순서"""
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name='session_problems')
    problem = models.ForeignKey(Problem, on_delete=models.PROTECT)  # 문제는 삭제 방지
    order_index = models.IntegerField()

    class Meta:
        db_table = 'session_problem'
        unique_together = ('session', 'order_index')  # 같은 세션에서 순서 중복 방지


class SessionResult(models.Model):
    """제출 후 채점 결과"""
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name='results')
    problem = models.ForeignKey(Problem, on_delete=models.PROTECT)
    student_answer = models.CharField(max_length=200)
    is_correct = models.BooleanField()

    class Meta:
        db_table = 'session_result'
        unique_together = ('session', 'problem')  # 같은 세션에서 같은 문제 중복 방지


class WeaknessReport(models.Model):
    """세션당 1개 생성되는 분석 리포트"""
    session = models.OneToOneField(
        QuizSession, on_delete=models.CASCADE, related_name='weakness_report'
    )
    ai_feedback = models.TextField(null=True, blank=True)  # 세션 전체 피드백
    all_correct = models.BooleanField(default=False)       # 전부 맞았을 때 True
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'weakness_report'


class WeakSubtype(models.Model):
    """취약 유형 Top N (최대 3개)"""
    report = models.ForeignKey(
        WeaknessReport, on_delete=models.CASCADE, related_name='weak_subtypes'
    )
    problem_subtype = models.CharField(max_length=100)
    wrong_count = models.IntegerField()
    total_count = models.IntegerField()
    rank = models.IntegerField()   # 1 = 가장 취약

    class Meta:
        db_table = 'weak_subtype'
        ordering = ['rank']
        unique_together = ('report', 'rank')


class Recommendation(models.Model):
    report = models.ForeignKey(
        WeaknessReport, on_delete=models.CASCADE, related_name='recommendations'
    )
    weak_subtype = models.ForeignKey(
        WeakSubtype, on_delete=models.CASCADE, related_name='recommendations',
        null=True, blank=True   # all_correct일 때는 null
    )
    problem = models.ForeignKey(Problem, on_delete=models.PROTECT)
    similarity_score = models.FloatField(null=True, blank=True)  # 난이도 추천은 null
    order_index = models.IntegerField()
    reason = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        db_table = 'recommendation'
        ordering = ['order_index']


class SubtypeMastery(models.Model):
    """유저별 유형 마스터 현황 — submit 시마다 갱신"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subtype_masteries'
    )
    problem_subtype  = models.CharField(max_length=100)
    mastered         = models.BooleanField(default=False)
    accuracy_before  = models.FloatField(null=True, blank=True)  # 마스터 직전 정답률
    accuracy_after   = models.FloatField(null=True, blank=True)  # 마스터 직후 정답률
    total_attempts   = models.IntegerField(default=0)            # 해당 유형 총 출제 수
    correct_count    = models.IntegerField(default=0)            # 해당 유형 총 정답 수
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subtype_mastery'
        unique_together = ('user', 'problem_subtype')  # 유저+유형 조합은 1개만