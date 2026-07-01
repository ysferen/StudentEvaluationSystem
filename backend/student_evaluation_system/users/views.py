from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import generics, viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from core.permissions import IsAdmin
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from django.contrib.auth import authenticate
from django.conf import settings
from django.core import signing
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
import secrets
from drf_spectacular.utils import extend_schema
from .models import CustomUser, StudentProfile, InstructorProfile, ProgramHeadProfile
from .serializers import (
    CustomUserSerializer,
    StudentProfileSerializer,
    InstructorProfileSerializer,
    ProgramHeadProfileSerializer,
)
from core.models import Department, Program
from core.services.audit import log_audit


def _temporary_password():
    return secrets.token_urlsafe(12)


def _set_auth_cookie(response, key, value, max_age):
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Strict" if not settings.DEBUG else "Lax",
        max_age=max_age,
        path="/",
    )


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
            validate_password(new_password, user=user)
            user.set_password(new_password)
            user.must_change_password = False
            user.save(update_fields=["password", "must_change_password"])
            log_audit(user, "UPDATE", "CustomUser", user.id, metadata={"event": "password_changed"})
            return Response({"detail": "Password changed successfully"})
        except ValidationError as exc:
            return Response({"error": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)


# Response serializers for authentication
class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = CustomUserSerializer()


class UserViewSet(viewsets.ModelViewSet):
    """CRUD operations for users."""

    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset().select_related("department", "university")
        user = self.request.user
        if user.is_admin_user:
            pass
        elif user.is_program_head and user.department_id:
            queryset = queryset.filter(
                Q(department_id=user.department_id) | Q(student_profile__program__department_id=user.department_id),
                role__in=["program_head", "instructor", "student"],
            )
        else:
            queryset = queryset.filter(pk=user.pk)
        role = self.request.query_params.get("role", None)
        if role:
            queryset = queryset.filter(role=role)
        return queryset

    def _admin_only(self):
        if not self.request.user.is_admin_user:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("System administrator access required.")

    def perform_create(self, serializer):
        self._admin_only()
        serializer.save()

    def perform_update(self, serializer):
        self._admin_only()
        serializer.save()

    def perform_destroy(self, instance):
        self._admin_only()
        instance.delete()

    @action(detail=False, methods=["get", "post"], url_path="staff")
    def staff(self, request):  # noqa: C901 - provisioning and listing share one resource
        actor = request.user
        if not (actor.is_admin_user or actor.is_program_head):
            return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)
        if request.method == "GET":
            queryset = CustomUser.objects.filter(role__in=["program_head", "instructor"]).select_related(
                "department", "instructor_profile", "program_head_profile"
            )
            if actor.is_program_head:
                queryset = queryset.filter(role="instructor", department_id=actor.department_id)
            elif actor.is_admin_user:
                for head in queryset.filter(role="program_head", program_head_profile__program__isnull=True):
                    program = Program.objects.filter(department=head.department, program_head_profile__isnull=True).first()
                    if program:
                        head.program_head_profile.program = program
                        head.program_head_profile.save(update_fields=["program"])
                for head in queryset.filter(role="program_head", instructor_profile__isnull=True):
                    InstructorProfile.objects.create(user=head)
            return Response(CustomUserSerializer(queryset, many=True).data)

        role = request.data.get("role")
        if role not in ({"program_head", "instructor"} if actor.is_admin_user else {"instructor"}):
            return Response({"role": "Invalid role."}, status=status.HTTP_400_BAD_REQUEST)
        department_id = request.data.get("department_id")
        if actor.is_program_head:
            department_id = actor.department_id
        try:
            department = Department.objects.get(pk=department_id)
        except (Department.DoesNotExist, TypeError, ValueError):
            return Response({"department_id": "A valid department is required."}, status=status.HTTP_400_BAD_REQUEST)

        username = str(request.data.get("username", "")).strip()
        if not username:
            return Response({"username": "Username is required."}, status=status.HTTP_400_BAD_REQUEST)
        password = _temporary_password()
        try:
            with transaction.atomic():
                user = CustomUser.objects.create_user(
                    username=username,
                    email=str(request.data.get("email", "")).strip(),
                    first_name=str(request.data.get("first_name", "")).strip(),
                    last_name=str(request.data.get("last_name", "")).strip(),
                    password=password,
                    role=role,
                    department=department,
                    university=department.university,
                    must_change_password=True,
                )
                if role == "instructor":
                    InstructorProfile.objects.create(user=user, title=str(request.data.get("title", "")).strip())
                else:
                    program_id = request.data.get("program_id")
                    program = (
                        Program.objects.filter(pk=program_id, department=department).first()
                        if program_id
                        else Program.objects.filter(department=department, program_head_profile__isnull=True).first()
                    )
                    ProgramHeadProfile.objects.create(user=user, program=program)
                    InstructorProfile.objects.create(user=user, title=str(request.data.get("title", "")).strip())
                log_audit(actor, "CREATE", "CustomUser", user.id, metadata={"role": role, "temporary_password": True})
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"user": CustomUserSerializer(user).data, "temporary_password": password},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["patch", "delete"], url_path="staff")
    def manage_staff(self, request, pk=None):  # noqa: C901 - one endpoint owns the small staff lifecycle
        actor = request.user
        target = self.get_object()
        allowed = actor.is_admin_user or (
            actor.is_program_head and target.role == "instructor" and actor.department_id == target.department_id
        )
        if not allowed or target.role not in {"program_head", "instructor"}:
            return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)
        if request.method == "DELETE":
            target_id = target.id
            log_audit(actor, "DELETE", "CustomUser", target_id, metadata={"role": target.role})
            target.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        department = target.department
        department_id = request.data.get("department_id")
        if department_id is not None:
            if not actor.is_admin_user:
                return Response({"department_id": "Only administrators can move accounts."}, status=403)
            try:
                department = Department.objects.get(pk=department_id)
            except (Department.DoesNotExist, TypeError, ValueError):
                return Response({"department_id": "A valid department is required."}, status=400)
        for field in ("username", "email", "first_name", "last_name"):
            if field in request.data:
                setattr(target, field, str(request.data[field]).strip())
        target.department = department
        target.university = department.university if department else None
        try:
            with transaction.atomic():
                target.save()
                if target.role in {"instructor", "program_head"}:
                    profile, _ = InstructorProfile.objects.get_or_create(user=target)
                    profile.title = str(request.data.get("title", profile.title)).strip()
                    profile.save(update_fields=["title"])
                if target.role == "program_head":
                    profile, _ = ProgramHeadProfile.objects.get_or_create(user=target)
                    if not profile.program or profile.program.department_id != target.department_id:
                        profile.program = Program.objects.filter(
                            department=target.department, program_head_profile__isnull=True
                        ).first()
                        profile.save(update_fields=["program"])
                log_audit(actor, "UPDATE", "CustomUser", target.id, metadata={"event": "staff_updated"})
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CustomUserSerializer(target).data)

    @action(detail=True, methods=["post"], url_path="reset-temporary-password")
    def reset_temporary_password(self, request, pk=None):
        actor = request.user
        target = self.get_object()
        target_department_id = target.department_id
        if target.role == "student" and not target_department_id:
            target_program = getattr(getattr(target, "student_profile", None), "program", None)
            target_department_id = getattr(target_program, "department_id", None)
        allowed = actor.is_admin_user or (
            actor.is_program_head and target.role in {"instructor", "student"} and actor.department_id == target_department_id
        )
        if not allowed:
            return Response({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)
        password = _temporary_password()
        target.set_password(password)
        target.must_change_password = target.role != "student"
        target.save(update_fields=["password", "must_change_password"])
        log_audit(actor, "UPDATE", "CustomUser", target.id, metadata={"event": "temporary_password_reset"})
        return Response({"temporary_password": password, "must_change_password": target.must_change_password})

    @action(detail=True, methods=["post"])
    def impersonate(self, request, pk=None):
        actor = request.user
        target = self.get_object()
        target_department_id = target.department_id
        if target.role == "student" and not target_department_id:
            target_department_id = getattr(getattr(target, "student_profile", None), "program", None)
            target_department_id = getattr(target_department_id, "department_id", None)
        if not actor.is_program_head or target.role != "student" or actor.department_id != target_department_id:
            return Response({"detail": "Student is outside your department."}, status=status.HTTP_403_FORBIDDEN)
        token = RefreshToken.for_user(target).access_token
        token["impersonated_by"] = actor.id
        response = Response({"user": CustomUserSerializer(target).data, "impersonated_by": actor.id})
        access_age = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
        refresh_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
        _set_auth_cookie(response, "access_token", str(token), access_age)
        _set_auth_cookie(response, "impersonator", signing.dumps(actor.id), refresh_age)
        log_audit(actor, "UPDATE", "CustomUser", target.id, metadata={"event": "impersonation_started"})
        return response

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], authentication_classes=[])
    def return_from_impersonation(self, request):
        marker = request.COOKIES.get("impersonator")
        refresh_raw = request.COOKIES.get("refresh_token")
        try:
            actor_id = signing.loads(marker, max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()))
            refresh = RefreshToken(refresh_raw)
            if int(refresh["user_id"]) != int(actor_id):
                raise ValueError
            actor = CustomUser.objects.get(pk=actor_id, role="program_head", is_active=True)
        except Exception:
            return Response({"detail": "Impersonation session is invalid."}, status=status.HTTP_401_UNAUTHORIZED)
        response = Response({"user": CustomUserSerializer(actor).data})
        access_age = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
        _set_auth_cookie(response, "access_token", str(refresh.access_token), access_age)
        response.delete_cookie("impersonator", path="/")
        log_audit(actor, "UPDATE", "CustomUser", actor.id, metadata={"event": "impersonation_ended"})
        return response

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Get current user info."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class StudentProfileViewSet(viewsets.ModelViewSet):
    """CRUD operations for student profiles."""

    queryset = StudentProfile.objects.select_related("user", "enrollment_term", "program", "program__department").all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        permissions = [IsAuthenticated()]
        if self.request.method not in {"GET", "HEAD", "OPTIONS"}:
            permissions.append(IsAdmin())
        return permissions

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_admin_user:
            pass
        elif user.is_program_head and user.department_id:
            queryset = queryset.filter(program__department_id=user.department_id)
        elif user.is_instructor:
            queryset = queryset.filter(user__course_enrollments__course__instructors=user)
        elif user.is_student:
            queryset = queryset.filter(user=user)
        else:
            queryset = queryset.none()
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
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        permissions = [IsAuthenticated()]
        if self.request.method not in {"GET", "HEAD", "OPTIONS"}:
            permissions.append(IsAdmin())
        return permissions

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_admin_user:
            return queryset
        if user.is_program_head:
            InstructorProfile.objects.get_or_create(user=user)
            return queryset.filter(user__department_id=user.department_id)
        if user.is_instructor:
            return queryset.filter(user=user)
        return queryset.none()


class ProgramHeadProfileViewSet(viewsets.ModelViewSet):
    """CRUD operations for program head profiles."""

    queryset = ProgramHeadProfile.objects.select_related("user", "program").all()
    serializer_class = ProgramHeadProfileSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


class CookieTokenRefreshView(APIView):
    """
    Token refresh view that reads the refresh token from an HTTP-only cookie.

    This enables cookie-based authentication for browser clients without
    exposing tokens to JavaScript (XSS protection).
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Refresh access token",
        description="Exchange a valid refresh token (from HTTP-only cookie) for a new access token.",
        request=None,
        responses={
            200: {"type": "object", "properties": {"detail": {"type": "string"}}},
            401: {"type": "object", "properties": {"error": {"type": "string"}}},
        },
        tags=["Authentication"],
    )
    def post(self, request):
        if request.COOKIES.get("impersonator"):
            return Response({"error": "Return to the head account before refreshing."}, status=status.HTTP_401_UNAUTHORIZED)
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"error": "No refresh token found"}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
        try:
            if not serializer.is_valid():
                return Response({"error": "Token is invalid or expired"}, status=status.HTTP_401_UNAUTHORIZED)
        except TokenError:
            return Response({"error": "Token is invalid or expired"}, status=status.HTTP_401_UNAUTHORIZED)

        validated_data = serializer.validated_data or {}
        access_token_raw = validated_data.get("access")
        refresh_token_raw = validated_data.get("refresh")

        if not isinstance(access_token_raw, str) or not access_token_raw:
            return Response({"error": "Token is invalid or expired"}, status=status.HTTP_401_UNAUTHORIZED)

        access_token = access_token_raw
        refresh_token_value = refresh_token_raw if isinstance(refresh_token_raw, str) and refresh_token_raw else None

        secure = not settings.DEBUG
        same_site = "Strict" if not settings.DEBUG else "Lax"
        access_max_age = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
        refresh_max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())

        response = Response({"detail": "Token refreshed"}, status=status.HTTP_200_OK)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=secure,
            samesite=same_site,
            max_age=access_max_age,
            path="/",
        )
        if refresh_token_value is not None:
            response.set_cookie(
                key="refresh_token",
                value=refresh_token_value,
                httponly=True,
                secure=secure,
                samesite=same_site,
                max_age=refresh_max_age,
                path="/",
            )
        return response


@extend_schema(
    summary="User logout",
    description="Invalidate refresh token (when present) and clear authentication cookies.",
    request=None,
    responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
    tags=["Authentication"],
)
class LogoutView(APIView):
    """Logout endpoint for cookie-based authentication."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        response = Response({"detail": "Logged out successfully"}, status=status.HTTP_200_OK)

        response.delete_cookie(
            key="access_token",
            path="/",
            domain=settings.SESSION_COOKIE_DOMAIN if hasattr(settings, "SESSION_COOKIE_DOMAIN") else None,
        )
        response.delete_cookie(key="impersonator", path="/")

        response.delete_cookie(
            key="refresh_token",
            path="/",
            domain=settings.SESSION_COOKIE_DOMAIN if hasattr(settings, "SESSION_COOKIE_DOMAIN") else None,
        )
        return response


@extend_schema(
    summary="Get CSRF token",
    description="Bootstrap endpoint that ensures csrftoken cookie is set for SPA usage.",
    responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
    tags=["Authentication"],
)
class CsrfTokenView(APIView):
    """CSRF bootstrap endpoint for SPA usage."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        get_token(request)
        return Response({"detail": "CSRF cookie set"})


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
        429: dict,
    },
    tags=["Authentication"],
)
class LoginView(APIView):
    """Login endpoint that returns JWT tokens and user data.

    Rate limiting:
    - 5 attempts per minute per IP address
    - Prevents brute force password attacks
    """

    authentication_classes = []
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
        data = CustomUserSerializer(request.user).data
        data["impersonated_by"] = request.auth.get("impersonated_by") if request.auth else None
        return Response(data)


# Legacy views for backward compatibility
class UserListView(generics.ListAPIView):
    """List all users."""

    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer


class UserDetailView(generics.RetrieveAPIView):
    """Retrieve a single user by PK."""

    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
