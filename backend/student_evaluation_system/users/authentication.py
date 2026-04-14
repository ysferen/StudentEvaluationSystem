from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.conf import settings


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads the access token from an HTTP-only cookie
    instead of the Authorization header.

    This enables cookie-based authentication for browser clients without
    exposing tokens to JavaScript (XSS protection).
    """

    def authenticate(self, request):
        """
        Authenticate the request using the token from the cookie.

        Overrides the parent method to read from cookie instead of header.
        """
        cookie_token = request.COOKIES.get(settings.SIMPLE_JWT.get("AUTH_COOKIE", "access_token"))

        if cookie_token is None:
            return None

        try:
            validated_token = self.get_validated_token(cookie_token)
            return self.get_user(validated_token), validated_token
        except InvalidToken:
            raise AuthenticationFailed("Token is invalid or expired")
        except Exception as exc:
            raise AuthenticationFailed(f"Authentication failed: {exc}")
