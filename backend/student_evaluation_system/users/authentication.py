from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.conf import settings
from rest_framework.permissions import SAFE_METHODS


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads the access token from an HTTP-only cookie
    instead of the Authorization header.

    Security features:
    - HTTP-only cookies prevent JavaScript access (XSS protection)
    - SameSite=Strict prevents CSRF in modern browsers (configured in settings)
    - CSRF token validation for mutating requests (POST, PUT, PATCH, DELETE)
      provides defense-in-depth for older browsers
    """

    def authenticate(self, request):
        cookie_token = request.COOKIES.get(settings.SIMPLE_JWT.get("AUTH_COOKIE", "access_token"))

        if cookie_token is None:
            return None

        try:
            validated_token = self.get_validated_token(cookie_token)
            user = self.get_user(validated_token)
        except InvalidToken:
            raise AuthenticationFailed("Token is invalid or expired")
        except Exception as exc:
            raise AuthenticationFailed(f"Authentication failed: {exc}")

        if request.method not in SAFE_METHODS:
            self._validate_csrf(request)

        return user, validated_token

    def _validate_csrf(self, request):
        csrf_cookie = request.COOKIES.get("csrftoken")
        csrf_header = request.META.get("HTTP_X_CSRFTOKEN")

        if not csrf_cookie or not csrf_header:
            raise AuthenticationFailed("CSRF token missing")

        if csrf_cookie != csrf_header:
            raise AuthenticationFailed("CSRF token mismatch")
