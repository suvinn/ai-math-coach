from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    DRF의 SessionAuthentication은 미들웨어와 별개로 자체 CSRF 검사를 하는데,
    이 프로젝트는 토큰 인증 도입 전까지는 CSRF 검사를 생략하기로 한 컨벤션
    (RegisterView/LoginView 등에서 csrf_exempt 사용)에 맞춰 여기서도 생략한다.
    """
    def enforce_csrf(self, request):
        return  # 아무것도 안 함 = CSRF 검사 생략