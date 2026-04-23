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
from core.permissions import IsAdmin, IsInstructorOrAdmin, IsDepartmentHead, IsAdminOrDepartmentHead, get_instructor_permission_tier

User = get_user_model()
factory = APIRequestFactory()


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_user(username="admin", password="admin123", role="admin")


@pytest.fixture
def instructor_user(db):
    """Create an instructor user."""
    return User.objects.create_user(username="instructor", password="instructor123", role="instructor")


@pytest.fixture
def student_user(db):
    """Create a student user."""
    return User.objects.create_user(username="student", password="student123", role="student")


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
class TestIsDepartmentHeadPermission:
    def test_department_head_has_permission(self, db):
        from users.models import CustomUser, DepartmentHeadProfile
        from core.models import University, Department

        university = University.objects.create(name="Test Uni")
        dept = Department.objects.create(
            name="Test Dept", code="TD", university=university
        )
        head_user = CustomUser.objects.create_user(
            username="head1",
            password="pass",
            role="department_head",
            department=dept,
        )
        DepartmentHeadProfile.objects.create(user=head_user, department=dept)
        request = factory.get("/api/test/")
        request.user = head_user
        perm = IsDepartmentHead()
        assert perm.has_permission(cast(Request, request), None) is True

    def test_admin_does_not_pass_department_head_check(self, db, admin_user):
        request = factory.get("/api/test/")
        request.user = admin_user
        perm = IsDepartmentHead()
        assert perm.has_permission(cast(Request, request), None) is False

    def test_anonymous_denied(self, db):
        request = factory.get("/api/test/")
        perm = IsDepartmentHead()
        assert perm.has_permission(cast(Request, request), None) is False

    def test_instructor_denied(self, db, instructor_user):
        request = factory.get("/api/test/")
        request.user = instructor_user
        perm = IsDepartmentHead()
        assert perm.has_permission(cast(Request, request), None) is False

    def test_department_head_object_permission_same_department(self, db):
        from users.models import CustomUser, DepartmentHeadProfile
        from core.models import University, Department

        university = University.objects.create(name="Test Uni")
        dept = Department.objects.create(
            name="Test Dept", code="TD", university=university
        )
        head_user = CustomUser.objects.create_user(
            username="head1",
            password="pass",
            role="department_head",
            department=dept,
        )
        DepartmentHeadProfile.objects.create(user=head_user, department=dept)
        request = factory.get("/api/test/")
        request.user = head_user
        perm = IsDepartmentHead()
        assert perm.has_object_permission(cast(Request, request), None, dept) is True

    def test_department_head_object_permission_different_department(self, db):
        from users.models import CustomUser, DepartmentHeadProfile
        from core.models import University, Department

        university = University.objects.create(name="Test Uni")
        dept1 = Department.objects.create(
            name="Dept1", code="D1", university=university
        )
        dept2 = Department.objects.create(
            name="Dept2", code="D2", university=university
        )
        head_user = CustomUser.objects.create_user(
            username="head1",
            password="pass",
            role="department_head",
            department=dept1,
        )
        DepartmentHeadProfile.objects.create(user=head_user, department=dept1)
        request = factory.get("/api/test/")
        request.user = head_user
        perm = IsDepartmentHead()
        assert perm.has_object_permission(cast(Request, request), None, dept2) is False


@pytest.mark.django_db
class TestIsAdminOrDepartmentHeadPermission:
    def test_admin_has_permission(self, db, admin_user):
        request = factory.get("/api/test/")
        request.user = admin_user
        perm = IsAdminOrDepartmentHead()
        assert perm.has_permission(cast(Request, request), None) is True

    def test_department_head_has_permission(self, db):
        from users.models import CustomUser, DepartmentHeadProfile
        from core.models import University, Department

        university = University.objects.create(name="Test Uni")
        dept = Department.objects.create(
            name="Test Dept", code="TD", university=university
        )
        head_user = CustomUser.objects.create_user(
            username="head1",
            password="pass",
            role="department_head",
            department=dept,
        )
        DepartmentHeadProfile.objects.create(user=head_user, department=dept)
        request = factory.get("/api/test/")
        request.user = head_user
        perm = IsAdminOrDepartmentHead()
        assert perm.has_permission(cast(Request, request), None) is True

    def test_instructor_denied(self, db, instructor_user):
        request = factory.get("/api/test/")
        request.user = instructor_user
        perm = IsAdminOrDepartmentHead()
        assert perm.has_permission(cast(Request, request), None) is False

    def test_student_denied(self, db, student_user):
        request = factory.get("/api/test/")
        request.user = student_user
        perm = IsAdminOrDepartmentHead()
        assert perm.has_permission(cast(Request, request), None) is False


@pytest.mark.django_db
class TestGetInstructorPermissionTier:
    def test_admin_gets_full(self, db, admin_user):
        assert get_instructor_permission_tier(admin_user, "courses") == "full"

    def test_department_head_gets_full(self, db):
        from users.models import CustomUser, DepartmentHeadProfile
        from core.models import University, Department

        university = University.objects.create(name="Test Uni")
        dept = Department.objects.create(
            name="Test Dept", code="TD", university=university
        )
        head_user = CustomUser.objects.create_user(
            username="head1",
            password="pass",
            role="department_head",
            department=dept,
        )
        DepartmentHeadProfile.objects.create(user=head_user, department=dept)
        assert get_instructor_permission_tier(head_user, "courses") == "full"

    def test_instructor_without_permission_gets_view(self, db, instructor_user):
        assert get_instructor_permission_tier(instructor_user, "courses") == "view"

    def test_instructor_with_permission_gets_tier(self, db):
        from users.models import CustomUser, InstructorProfile, DepartmentHeadProfile
        from core.models import University, Department, InstructorPermission

        university = University.objects.create(name="Perm Uni")
        dept = Department.objects.create(
            name="Perm Dept", code="PD", university=university
        )
        instr_user = CustomUser.objects.create_user(
            username="instrperm", password="pass", role="instructor"
        )
        instr_profile = InstructorProfile.objects.create(
            user=instr_user, title="Prof"
        )
        head_user = CustomUser.objects.create_user(
            username="headperm",
            password="pass",
            role="department_head",
            department=dept,
        )
        head_profile = DepartmentHeadProfile.objects.create(
            user=head_user, department=dept
        )
        InstructorPermission.objects.create(
            instructor=instr_profile,
            department_head=head_profile,
            resource_area="courses",
            permission_tier="edit",
        )
        assert get_instructor_permission_tier(instr_user, "courses") == "edit"


@pytest.mark.django_db
class TestDepartmentHeadWriteAccess:
    @pytest.fixture
    def head_setup(self, db):
        from users.models import CustomUser, DepartmentHeadProfile
        from core.models import University, Department

        university = University.objects.create(name="Test Uni")
        dept = Department.objects.create(
            name="Test Dept", code="TD", university=university
        )
        head_user = CustomUser.objects.create_user(
            username="head_write",
            password="pass",
            role="department_head",
            department=dept,
        )
        DepartmentHeadProfile.objects.create(
            user=head_user, department=dept
        )
        return {
            "client": APIRequestFactory().post("/"),
            "head_user": head_user,
            "department": dept,
        }

    def test_department_head_can_create_program(self, head_setup):
        from core.models import DegreeLevel
        from rest_framework.test import APIRequestFactory

        DegreeLevel.objects.create(name="Bachelor")
        factory = APIRequestFactory()
        client = APIRequestFactory()
        from rest_framework.test import APIRequestFactory, force_authenticate
        from core.views import ProgramViewSet

        request = factory.post(
            "/api/v1/core/programs/",
            {
                "name": "New Program",
                "code": "NP",
                "degree_level": DegreeLevel.objects.first().id,
                "department": head_setup["department"].id,
            },
            format="json",
        )
        force_authenticate(request, user=head_setup["head_user"])
        view = ProgramViewSet.as_view({"post": "create"})
        response = view(request)
        assert response.status_code in (201, 200)

    def test_department_head_has_permission_flag(self, head_setup):
        assert head_setup["head_user"].is_department_head is True
