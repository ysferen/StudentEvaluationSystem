from rest_framework import generics, viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from django.conf import settings
from drf_spectacular.utils import extend_schema
from .models import CustomUser, StudentProfile, InstructorProfile
from .serializers import CustomUserSerializer, StudentProfileSerializer, InstructorProfileSerializer


class LoginRateThrottle(AnonRateThrottle):
    """Custom throttle for login attempts - prevents brute force attacks."""

    scope = "login"


@extend_schema(
    summary="Change password",
    description="Allow authenticated users to change their password by providing the current and new password.",
    request={"current_password": str, "new_password": str},
    responses={200: dict, 400: dict, 401: dict},
    tags=["Authentication"],
)
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not current_password or not new_password:
            return Response({"error": "current_password and new_password are required"}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(current_password):
            return Response({"error": "Current password is incorrect"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user.set_password(new_password)
            user.save()
            return Response({"detail": "Password changed successfully"})
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


# Response serializers for authentication
class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = CustomUserSerializer()


class UserViewSet(viewsets.ModelViewSet):
    """CRUD operations for users."""

    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

    def get_queryset(self):
        queryset = super().get_queryset().select_related("department", "university")
        role = self.request.query_params.get("role", None)
        if role:
            queryset = queryset.filter(role=role)
        return queryset

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Get current user info."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class StudentProfileViewSet(viewsets.ModelViewSet):
    """CRUD operations for student profiles."""

    queryset = StudentProfile.objects.select_related("user", "enrollment_term", "program", "program__department").all()
    serializer_class = StudentProfileSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        program_id = self.request.query_params.get("program", None)
        term_id = self.request.query_params.get("term", None)

        if program_id:
            queryset = queryset.filter(program_id=program_id)
        if term_id:
            queryset = queryset.filter(enrollment_term_id=term_id)

        return queryset


class InstructorProfileViewSet(viewsets.ModelViewSet):
    """CRUD operations for instructor profiles."""

    queryset = InstructorProfile.objects.select_related("user").all()
    serializer_class = InstructorProfileSerializer


class CookieTokenRefreshView(APIView):
    """
    Token refresh view that reads the refresh token from an HTTP-only cookie.

    This enables cookie-based authentication for browser clients without
    exposing tokens to JavaScript (XSS protection).
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Refresh access token",
        description="Exchange a valid refresh token (from HTTP-only cookie) for a new access token.",
        request=None,
        responses={
            200: {"type": "object", "properties": {"access": {"type": "string"}}},
            401: {"type": "object", "properties": {"error": {"type": "string"}}},
        },
        tags=["Authentication"],
    )
    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"error": "No refresh token found"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            return Response({"access": access_token}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({"error": "Token is invalid or expired"}, status=status.HTTP_401_UNAUTHORIZED)


@extend_schema(
    summary="User logout",
    description="Invalidate refresh token (when present) and clear authentication cookies.",
    request=None,
    responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
    tags=["Authentication"],
)
class LogoutView(APIView):
    """Logout endpoint for cookie-based authentication."""

    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token:
            try:
                # Blacklist current refresh token so it cannot be reused.
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                # Token may already be expired/invalid; still clear cookies.
                pass

        response = Response({"detail": "Logged out successfully"}, status=status.HTTP_200_OK)

        response.delete_cookie(
            key="access_token",
            path="/",
            domain=settings.SESSION_COOKIE_DOMAIN if hasattr(settings, "SESSION_COOKIE_DOMAIN") else None,
        )

        response.delete_cookie(
            key="refresh_token",
            path="/",
            domain=settings.SESSION_COOKIE_DOMAIN if hasattr(settings, "SESSION_COOKIE_DOMAIN") else None,
        )
        return response


# Authentication Views
@extend_schema(
    summary="User login",
    description="Authenticate user and return JWT tokens with user data. "
    "Rate limited to 5 attempts per minute per IP to prevent brute force attacks.",
    request=CustomUserSerializer,
    responses={
        200: TokenResponseSerializer,
        400: dict,
        401: dict,
        429: dict,  # Too Many Requests
    },
    tags=["Authentication"],
)
class LoginView(APIView):
    """Login endpoint that returns JWT tokens and user data.

    Rate limiting:
    - 5 attempts per minute per IP address
    - Prevents brute force password attacks
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        """
        Authenticate user and return JWT tokens via HTTP-only cookies.

        Security measures:
        - Rate limiting (5 attempts/minute) prevents brute force
        - Input sanitization strips whitespace
        - Username length validation prevents injection
        - Tokens stored in HTTP-only cookies (XSS resistant)
        - Secure/SameSite cookies for production security
        """
        # Extract and sanitize username/password from request body
        username = request.data.get("username")
        password = request.data.get("password")

        # Strip whitespace from input fields
        if isinstance(username, str):
            username = username.strip()
        if isinstance(password, str):
            password = password.strip()

        # Validate required fields are provided
        if not username or not password:
            return Response({"error": "Please provide both username and password"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate username length to prevent injection attempts
        if len(username) > 150:
            return Response({"error": "Username is too long (max 150 characters)"}, status=status.HTTP_400_BAD_REQUEST)

        # Authenticate user with Django's authentication backend
        user = authenticate(username=username, password=password)

        # Check if authentication failed
        if user is None:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # Verify user account is active (not disabled)
        if not user.is_active:
            return Response({"error": "User account is disabled"}, status=status.HTTP_403_FORBIDDEN)

        # Generate JWT tokens using SimpleJWT
        # refresh.access_token = short-lived access token (1 hour)
        # refresh = long-lived refresh token (7 days) for token rotation
        refresh = RefreshToken.for_user(user)

        # Serialize user data to include in response
        user_serializer = CustomUserSerializer(user)

        # Build response with user data
        response = Response({"user": user_serializer.data})

        # Configure cookie security based on DEBUG mode
        # production: Secure=True, SameSite=Strict (prevents CSRF)
        # development: Secure=False, SameSite=Lax (allows localhost)
        secure = not settings.DEBUG
        same_site = "Strict" if not settings.DEBUG else "Lax"

        # Set access token cookie (1 hour = 3600 seconds)
        # HttpOnly=True prevents JavaScript access (XSS protection)
        response.set_cookie(
            key="access_token",
            value=str(refresh.access_token),
            httponly=True,
            secure=secure,
            samesite=same_site,
            max_age=60 * 60,
            path="/",
        )

        # Set refresh token cookie (7 days = 604800 seconds)
        # Used to obtain new access tokens without re-login
        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=secure,
            samesite=same_site,
            max_age=60 * 60 * 24 * 7,
            path="/",
        )

        return response


@extend_schema(
    summary="Get current user",
    description="Retrieve information about the currently authenticated user",
    responses={200: CustomUserSerializer, 401: dict},
    tags=["Authentication"],
)
class CurrentUserView(APIView):
    """Get current authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CustomUserSerializer(request.user)
        return Response(serializer.data)


# Legacy views for backward compatibility
class UserListView(generics.ListAPIView):
    """List all users."""

    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer


class UserDetailView(generics.RetrieveAPIView):
    """Retrieve a single user by PK."""

    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
