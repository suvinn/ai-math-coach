from django.urls import path
from . import views

urlpatterns = [
    # 인증
    path('auth/register', views.RegisterView.as_view()),
    path('auth/login',    views.LoginView.as_view()),
    path('auth/logout',   views.LogoutView.as_view()),
    path('auth/me',       views.MeView.as_view()),
    
    # 챕터
    path('chapters',                views.ChapterListView.as_view()),
    path('chapters/problem-counts', views.ChapterProblemCountView.as_view()),

    # 퀴즈 세션
    path('quiz/sessions', views.QuizSessionCreateView.as_view()),
    path('quiz/sessions/<int:session_id>/problems', views.QuizSessionProblemsView.as_view()),
    path('quiz/sessions/<int:session_id>/submit',   views.QuizSessionSubmitView.as_view()),
    path('quiz/sessions/<int:session_id>/wrong-answers', views.QuizSessionWrongAnswersView.as_view()),
    path('quiz/sessions/<int:session_id>/analysis', views.QuizSessionAnalysisView.as_view()),
    path('quiz/sessions/<int:session_id>/recommendations', views.QuizSessionRecommendationsView.as_view()),
    path('quiz/sessions/<int:session_id>/chat',            views.QuizSessionChatView.as_view()),
    path('users/me/history',              views.UserHistoryView.as_view()),
    path('users/me/dashboard',            views.UserDashboardView.as_view()),
    path('users/me/today-recommendation', views.TodayRecommendationView.as_view()),
    path('problems/<str:problem_id>',     views.ProblemDetailView.as_view()),
]