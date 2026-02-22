from rest_framework import generics, viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
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
        queryset = CustomUser.objects.select_related("department", "university")
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
        # Validate input
        username = request.data.get("username")
        password = request.data.get("password")

        # Input sanitization - strip whitespace
        if isinstance(username, str):
            username = username.strip()
        if isinstance(password, str):
            password = password.strip()

        # Validate required fields
        if not username or not password:
            return Response({"error": "Please provide both username and password"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate username format (prevent injection attempts)
        if len(username) > 150:
            return Response({"error": "Username is too long (max 150 characters)"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)

        if user is None:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # Check if user account is active
        if not user.is_active:
            return Response({"error": "User account is disabled"}, status=status.HTTP_403_FORBIDDEN)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Serialize user data
        user_serializer = CustomUserSerializer(user)

        return Response({"access": str(refresh.access_token), "refresh": str(refresh), "user": user_serializer.data})


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
