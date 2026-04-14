from drf_spectacular.extensions import OpenApiAuthenticationExtension
from django.conf import settings
from .authentication import CookieJWTAuthentication


class CookieJWTAuthenticationExtension(OpenApiAuthenticationExtension):
    target_class = CookieJWTAuthentication
    name = "jwtCookie"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": settings.SIMPLE_JWT.get("AUTH_COOKIE", "access_token"),
            "description": "JWT access token stored in HTTP-only cookie",
        }
