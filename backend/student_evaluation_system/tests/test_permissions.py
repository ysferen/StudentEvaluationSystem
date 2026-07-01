"""
Tests for permission classes.
"""

import pytest
from typing import cast
from django.contrib.auth import get_user_model
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.test import APIRequestFactory, force_authenticate

from core.views import CourseViewSet, StudentLearningOutcomeScoreViewSet
from core.models import Course, LearningOutcome, StudentLearningOutcomeScore
from core.permissions import IsAdmin, IsInstructorOrAdmin, IsProgramHead, IsAdminOrProgramHead, get_instructor_permission_tier

User = get_user_model()
factory = APIRequestFactory()


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_user(username="admin", password="admin123", role="admin")  # nosec


@pytest.fixture
def instructor_user(db):
    """Create an instructor user."""
    return User.objects.create_user(username="instructor", password="instructor123", role="instructor")  # nosec


@pytest.fixture
def student_user(db):
    """Create a student user."""
    return User.objects.create_user(username="student", password="student123", role="student")  # nosec


@pytest.fixture
def course(db, instructor_user):
    """Create a course with instructor."""
    from core.models import University, Department, DegreeLevel, Program, Term

    university = University.objects.create(name="Test University")
    department = Department.objects.create(name="Test Dept", code="TD", university=university)
    degree = DegreeLevel.objects.create(name="Bachelor")
    program = Program.objects.create(name="Test Program", code="TP", degree_level=degree, department=department)
    term = Term.objects.create(name="Fall 2025")

    course = Course.objects.create(name="Test Course", code="TC101", credits=3, program=program, term=term)
    course.instructors.add(instructor_user)
    return course


class TestCourseViewSetPermissions:
    """Test permissions for CourseViewSet."""

    def test_student_cannot_list_all_courses(self, student_user, course):
        """Students should not see courses they're not enrolled in."""
        request = factory.get("/api/core/courses/")
        force_authenticate(request, user=student_user)

        view = CourseViewSet.as_view({"get": "list"})
        response = view(request)

        # Student should get empty list or 403
        assert response.status_code in [200, 403]
        if response.status_code == 200:
            assert len(response.data.get("results", [])) == 0

    def test_instructor_sees_only_own_courses(self, instructor_user, course):
        """Instructors should only see courses they teach."""
        request = factory.get("/api/core/courses/")
        force_authenticate(request, user=instructor_user)

        view = CourseViewSet.as_view({"get": "list"})
        response = view(request)

        assert response.status_code == 200
        assert len(response.data.get("results", [])) == 1
        assert response.data["results"][0]["id"] == course.id

    def test_admin_can_see_all_courses(self, admin_user, course):
        """Admins should see all courses."""
        request = factory.get("/api/core/courses/")
        force_authenticate(request, user=admin_user)

        view = CourseViewSet.as_view({"get": "list"})
        response = view(request)

        assert response.status_code == 200


class TestStudentScorePermissions:
    """Test permissions for student score access."""

    def test_student_sees_only_own_scores(self, student_user, course, db):
        """Students should only see their own scores."""
        # Create a learning outcome
        lo = LearningOutcome.objects.create(code="LO1", description="Test LO", course=course)

        # Create a score for the student
        StudentLearningOutcomeScore.objects.create(student=student_user, learning_outcome=lo, score=85.0)

        request = factory.get("/api/core/student-lo-scores/")
        force_authenticate(request, user=student_user)

        view = StudentLearningOutcomeScoreViewSet.as_view({"get": "list"})
        response = view(request)

        assert response.status_code == 200
        results = response.data.get("results", [])

        # Should see exactly 1 score (their own)
        assert len(results) == 1
        assert results[0]["student_id"] == student_user.id


class TestPermissionClasses:
    """Test individual permission classes."""

    def test_is_admin_permission(self, admin_user, student_user):
        """Test IsAdmin permission."""
        permission = IsAdmin()
        view = cast(APIView, None)

        admin_request = factory.get("/api/core/courses/")
        admin_request.user = admin_user

        student_request = factory.get("/api/core/courses/")
        student_request.user = student_user

        assert permission.has_permission(cast(Request, admin_request), view) is True
        assert permission.has_permission(cast(Request, student_request), view) is False

    def test_is_instructor_or_admin(self, instructor_user, student_user, admin_user):
        """Test IsInstructorOrAdmin permission."""
        permission = IsInstructorOrAdmin()
        view = cast(APIView, None)

        instructor_request = factory.get("/api/core/courses/")
        instructor_request.user = instructor_user

        admin_request = factory.get("/api/core/courses/")
        admin_request.user = admin_user

        student_request = factory.get("/api/core/courses/")
        student_request.user = student_user

        assert permission.has_permission(cast(Request, instructor_request), view) is True
        assert permission.has_permission(cast(Request, admin_request), view) is True
        assert permission.has_permission(cast(Request, student_request), view) is False


@pytest.mark.django_db
class TestIsProgramHeadPermission:
    def test_program_head_has_permission(self, db):
        from users.models import CustomUser, ProgramHeadProfile
        from core.models import University, Department, DegreeLevel, Program

        university = University.objects.create(name="Test Uni")
        dept = Department.objects.create(name="Test Dept", code="TD", university=university)
        degree = DegreeLevel.objects.create(name="Bachelor")
        program = Program.objects.create(name="Test Program", code="TP", department=dept, degree_level=degree)
        head_user = CustomUser.objects.create_user(
            username="head1",
            password="pass",  # nosec
            role="program_head",
            department=dept,
        )
        ProgramHeadProfile.objects.create(user=head_user, program=program)
        request = factory.get("/api/test/")
        request.user = head_user
        perm = IsProgramHead()
        assert perm.has_permission(cast(Request, request), None) is True

    def test_admin_does_not_pass_program_head_check(self, db, admin_user):
        request = factory.get("/api/test/")
        request.user = admin_user
        perm = IsProgramHead()
        assert perm.has_permission(cast(Request, request), None) is False

    def test_anonymous_denied(self, db):
        request = factory.get("/api/test/")
        perm = IsProgramHead()
        assert perm.has_permission(cast(Request, request), None) is False

    def test_instructor_denied(self, db, instructor_user):
        request = factory.get("/api/test/")
        request.user = instructor_user
        perm = IsProgramHead()
        assert perm.has_permission(cast(Request, request), None) is False

    def test_program_head_object_permission_same_program(self, db):
        from users.models import CustomUser, ProgramHeadProfile
        from core.models import University, Department, DegreeLevel, Program

        university = University.objects.create(name="Test Uni")
        dept = Department.objects.create(name="Test Dept", code="TD", university=university)
        degree = DegreeLevel.objects.create(name="Bachelor")
        program = Program.objects.create(name="Test Program", code="TP", department=dept, degree_level=degree)
        head_user = CustomUser.objects.create_user(
            username="head1",
            password="pass",  # nosec
            role="program_head",
            department=dept,
        )
        ProgramHeadProfile.objects.create(user=head_user, program=program)
        request = factory.get("/api/test/")
        request.user = head_user
        perm = IsProgramHead()
        assert perm.has_object_permission(cast(Request, request), None, program) is True

    def test_department_head_can_access_another_program_in_department(self, db):
        from users.models import CustomUser, ProgramHeadProfile
        from core.models import University, Department, DegreeLevel, Program

        university = University.objects.create(name="Test Uni")
        dept = Department.objects.create(name="Dept1", code="D1", university=university)
        degree = DegreeLevel.objects.create(name="Bachelor")
        program1 = Program.objects.create(name="Program1", code="P1", department=dept, degree_level=degree)
        program2 = Program.objects.create(name="Program2", code="P2", department=dept, degree_level=degree)
        head_user = CustomUser.objects.create_user(
            username="head1",
            password="pass",  # nosec
            role="program_head",
            department=dept,
        )
        ProgramHeadProfile.objects.create(user=head_user, program=program1)
        request = factory.get("/api/test/")
        request.user = head_user
        perm = IsProgramHead()
        assert perm.has_object_permission(cast(Request, request), None, program2) is True


@pytest.mark.django_db
class TestIsAdminOrProgramHeadPermission:
    def test_admin_has_permission(self, db, admin_user):
        request = factory.get("/api/test/")
        request.user = admin_user
        perm = IsAdminOrProgramHead()
        assert perm.has_permission(cast(Request, request), None) is True

    def test_program_head_has_permission(self, db):
        from users.models import CustomUser, ProgramHeadProfile
        from core.models import University, Department, DegreeLevel, Program

        university = University.objects.create(name="Test Uni")
        dept = Department.objects.create(name="Test Dept", code="TD", university=university)
        degree = DegreeLevel.objects.create(name="Bachelor")
        program = Program.objects.create(name="Test Program", code="TP", department=dept, degree_level=degree)
        head_user = CustomUser.objects.create_user(
            username="head1",
            password="pass",  # nosec
            role="program_head",
            department=dept,
        )
        ProgramHeadProfile.objects.create(user=head_user, program=program)
        request = factory.get("/api/test/")
        request.user = head_user
        perm = IsAdminOrProgramHead()
        assert perm.has_permission(cast(Request, request), None) is True

    def test_instructor_denied(self, db, instructor_user):
        request = factory.get("/api/test/")
        request.user = instructor_user
        perm = IsAdminOrProgramHead()
        assert perm.has_permission(cast(Request, request), None) is False

    def test_student_denied(self, db, student_user):
        request = factory.get("/api/test/")
        request.user = student_user
        perm = IsAdminOrProgramHead()
        assert perm.has_permission(cast(Request, request), None) is False


@pytest.mark.django_db
class TestGetInstructorPermissionTier:
    def test_admin_gets_full(self, db, admin_user):
        assert get_instructor_permission_tier(admin_user, "courses") == "full"

    def test_program_head_gets_full(self, db):
        from users.models import CustomUser, ProgramHeadProfile
        from core.models import University, Department, DegreeLevel, Program

        university = University.objects.create(name="Test Uni")
        dept = Department.objects.create(name="Test Dept", code="TD", university=university)
        degree = DegreeLevel.objects.create(name="Bachelor")
        program = Program.objects.create(name="Test Program", code="TP", department=dept, degree_level=degree)
        head_user = CustomUser.objects.create_user(
            username="head1",
            password="pass",  # nosec
            role="program_head",
            department=dept,
        )
        ProgramHeadProfile.objects.create(user=head_user, program=program)
        assert get_instructor_permission_tier(head_user, "courses") == "full"

    def test_instructor_without_permission_gets_view(self, db, instructor_user):
        assert get_instructor_permission_tier(instructor_user, "courses") == "view"

    def test_instructor_with_permission_gets_tier(self, db):
        from users.models import CustomUser, InstructorProfile, ProgramHeadProfile
        from core.models import University, Department, DegreeLevel, Program, InstructorPermission

        university = University.objects.create(name="Perm Uni")
        dept = Department.objects.create(name="Perm Dept", code="PD", university=university)
        degree = DegreeLevel.objects.create(name="Bachelor")
        program = Program.objects.create(name="Perm Program", code="PP", department=dept, degree_level=degree)
        instr_user = CustomUser.objects.create_user(username="instrperm", password="pass", role="instructor")
        instr_profile = InstructorProfile.objects.create(user=instr_user, title="Prof")
        head_user = CustomUser.objects.create_user(
            username="headperm",
            password="pass",  # nosec
            role="program_head",
            department=dept,
        )
        head_profile = ProgramHeadProfile.objects.create(user=head_user, program=program)
        InstructorPermission.objects.create(
            instructor=instr_profile,
            program_head=head_profile,
            resource_area="courses",
            permission_tier="edit",
        )
        assert get_instructor_permission_tier(instr_user, "courses") == "edit"


@pytest.mark.django_db
class TestProgramHeadWriteAccess:
    @pytest.fixture
    def head_setup(self, db):
        from users.models import CustomUser, ProgramHeadProfile
        from core.models import University, Department, DegreeLevel, Program

        university = University.objects.create(name="Test Uni")
        dept = Department.objects.create(name="Test Dept", code="TD", university=university)
        degree = DegreeLevel.objects.create(name="Bachelor")
        program = Program.objects.create(name="Test Program", code="TP", department=dept, degree_level=degree)
        head_user = CustomUser.objects.create_user(
            username="head_write",
            password="pass",  # nosec
            role="program_head",
            department=dept,
        )
        ProgramHeadProfile.objects.create(user=head_user, program=program)
        return {
            "client": APIRequestFactory().post("/"),
            "head_user": head_user,
            "program": program,
        }

    def test_program_head_can_create_program(self, head_setup):
        from core.models import DegreeLevel
        from rest_framework.test import APIRequestFactory

        DegreeLevel.objects.create(name="Master")
        factory = APIRequestFactory()
        from rest_framework.test import APIRequestFactory, force_authenticate
        from core.views import ProgramViewSet

        request = factory.post(
            "/api/v1/core/programs/",
            {
                "name": "New Program",
                "code": "NP",
                "degree_level": DegreeLevel.objects.first().id,
                "department": head_setup["program"].department.id,
            },
            format="json",
        )
        force_authenticate(request, user=head_setup["head_user"])
        view = ProgramViewSet.as_view({"post": "create"})
        response = view(request)
        assert response.status_code in (201, 200)

    def test_program_head_has_permission_flag(self, head_setup):
        assert head_setup["head_user"].is_program_head is True


@pytest.mark.django_db
class TestInstructorPermissionMixin:
    """Test InstructorPermissionMixin for tiered access control."""

    @pytest.fixture
    def setup_data(self, db):
        from users.models import CustomUser, InstructorProfile, ProgramHeadProfile
        from core.models import University, Department, DegreeLevel, Program, Term, Course, InstructorPermission

        university = University.objects.create(name="Test Uni")
        dept = Department.objects.create(name="Test Dept", code="TDM", university=university)
        degree = DegreeLevel.objects.create(name="Bachelor")
        program = Program.objects.create(name="Test Program", code="TP", department=dept, degree_level=degree)
        term = Term.objects.create(name="Fall 2025")

        admin = CustomUser.objects.create_user(username="admin_perm", password="pass", role="admin")

        head_user = CustomUser.objects.create_user(username="head_perm", password="pass", role="program_head", department=dept)
        head_profile = ProgramHeadProfile.objects.create(user=head_user, program=program)

        instr_view = CustomUser.objects.create_user(username="instr_view", password="pass", role="instructor")
        instr_view_profile = InstructorProfile.objects.create(user=instr_view, title="Dr.")
        InstructorPermission.objects.create(
            instructor=instr_view_profile,
            program_head=head_profile,
            resource_area="courses",
            permission_tier="view",
        )

        instr_edit = CustomUser.objects.create_user(username="instr_edit", password="pass", role="instructor")
        instr_edit_profile = InstructorProfile.objects.create(user=instr_edit, title="Dr.")
        InstructorPermission.objects.create(
            instructor=instr_edit_profile,
            program_head=head_profile,
            resource_area="courses",
            permission_tier="edit",
        )

        instr_full = CustomUser.objects.create_user(username="instr_full", password="pass", role="instructor")
        instr_full_profile = InstructorProfile.objects.create(user=instr_full, title="Dr.")
        InstructorPermission.objects.create(
            instructor=instr_full_profile,
            program_head=head_profile,
            resource_area="courses",
            permission_tier="full",
        )

        instr_none = CustomUser.objects.create_user(username="instr_none", password="pass", role="instructor")
        InstructorProfile.objects.create(user=instr_none, title="Dr.")

        course = Course.objects.create(name="Perm Course", code="PC101", credits=3, program=program, term=term)
        course.instructors.add(instr_view, instr_edit, instr_full)

        return {
            "admin": admin,
            "head_user": head_user,
            "instr_view": instr_view,
            "instr_edit": instr_edit,
            "instr_full": instr_full,
            "instr_none": instr_none,
            "course": course,
            "program": program,
        }

    def test_safe_methods_allowed_for_all_authenticated(self, setup_data):
        """GET requests should be allowed for all authenticated users."""
        from core.permissions import InstructorPermissionMixin
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        perm = InstructorPermissionMixin()
        perm.resource_area = "courses"
        view = type("View", (), {"action": "list", "resource_area": "courses"})()

        for user_key in ["admin", "head_user", "instr_view", "instr_edit", "instr_full", "instr_none"]:
            request = factory.get("/api/core/courses/")
            request.user = setup_data[user_key]
            assert perm.has_permission(request, view) is True

    def test_unauthenticated_denied(self, setup_data):
        """Unauthenticated users should be denied for write operations."""
        from core.permissions import InstructorPermissionMixin
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        perm = InstructorPermissionMixin()
        perm.resource_area = "courses"
        view = type("View", (), {"action": "create", "resource_area": "courses"})()

        from django.contrib.auth.models import AnonymousUser

        request = factory.post("/api/core/courses/")
        request.user = AnonymousUser()
        assert perm.has_permission(request, view) is False

    def test_admin_always_passes(self, setup_data):
        """Admins should pass all permission checks."""
        from core.permissions import InstructorPermissionMixin
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        perm = InstructorPermissionMixin()
        perm.resource_area = "courses"

        for action in ["create", "destroy", "update", "partial_update"]:
            view = type("View", (), {"action": action, "resource_area": "courses"})()
            request = factory.post("/api/core/courses/")
            request.user = setup_data["admin"]
            assert perm.has_permission(request, view) is True

    def test_program_head_always_passes(self, setup_data):
        """Program heads should pass all permission checks."""
        from core.permissions import InstructorPermissionMixin
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        perm = InstructorPermissionMixin()
        perm.resource_area = "courses"

        for action in ["create", "destroy", "update", "partial_update"]:
            view = type("View", (), {"action": action, "resource_area": "courses"})()
            request = factory.post("/api/core/courses/")
            request.user = setup_data["head_user"]
            assert perm.has_permission(request, view) is True

    def test_view_tier_cannot_write(self, setup_data):
        """Instructors with 'view' tier should be denied all write operations."""
        from core.permissions import InstructorPermissionMixin
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        perm = InstructorPermissionMixin()
        perm.resource_area = "courses"

        for action in ["create", "destroy", "update", "partial_update"]:
            view = type("View", (), {"action": action, "resource_area": "courses"})()
            request = factory.post("/api/core/courses/")
            request.user = setup_data["instr_view"]
            assert perm.has_permission(request, view) is False

    def test_edit_tier_can_edit_but_not_create_or_delete(self, setup_data):
        """Instructors with 'edit' tier can PUT/PATCH but not POST/DELETE."""
        from core.permissions import InstructorPermissionMixin
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        perm = InstructorPermissionMixin()
        perm.resource_area = "courses"

        for action in ["update", "partial_update"]:
            view = type("View", (), {"action": action, "resource_area": "courses"})()
            request = factory.put("/api/core/courses/1/")
            request.user = setup_data["instr_edit"]
            assert perm.has_permission(request, view) is True

        for action in ["create", "destroy"]:
            view = type("View", (), {"action": action, "resource_area": "courses"})()
            request = factory.delete("/api/core/courses/1/")
            request.user = setup_data["instr_edit"]
            assert perm.has_permission(request, view) is False

    def test_full_tier_can_do_everything(self, setup_data):
        """Instructors with 'full' tier should pass all write operations."""
        from core.permissions import InstructorPermissionMixin
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        perm = InstructorPermissionMixin()
        perm.resource_area = "courses"

        for action in ["create", "destroy", "update", "partial_update"]:
            view = type("View", (), {"action": action, "resource_area": "courses"})()
            request = factory.post("/api/core/courses/")
            request.user = setup_data["instr_full"]
            assert perm.has_permission(request, view) is True

    def test_custom_action_can_use_action_resource_area(self, setup_data):
        """Custom actions can opt into another resource area's tier checks."""
        from core.permissions import InstructorPermissionMixin
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        perm = InstructorPermissionMixin()
        view = type(
            "View",
            (),
            {
                "action": "instantiate",
                "resource_area": "course_templates",
                "action_resource_areas": {"instantiate": "courses"},
            },
        )()

        request = factory.post("/api/core/course-templates/1/instantiate/")
        request.user = setup_data["instr_full"]
        assert perm.has_permission(request, view) is True

        request.user = setup_data["instr_edit"]
        assert perm.has_permission(request, view) is False

    def test_no_permission_entry_defaults_to_view(self, setup_data):
        """Instructors without a permission entry default to 'view' tier."""
        from core.permissions import InstructorPermissionMixin
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        perm = InstructorPermissionMixin()
        perm.resource_area = "courses"

        for action in ["create", "destroy", "update", "partial_update"]:
            view = type("View", (), {"action": action, "resource_area": "courses"})()
            request = factory.post("/api/core/courses/")
            request.user = setup_data["instr_none"]
            assert perm.has_permission(request, view) is False
