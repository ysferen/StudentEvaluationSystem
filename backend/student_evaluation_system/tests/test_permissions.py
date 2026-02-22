"""
Tests for permission classes.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

from core.views import CourseViewSet, StudentLearningOutcomeScoreViewSet
from core.models import Course, LearningOutcome, StudentLearningOutcomeScore
from core.permissions import IsAdmin, IsInstructorOrAdmin

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

        # Mock request
        class MockRequest:
            def __init__(self, user):
                self.user = user

        assert permission.has_permission(MockRequest(admin_user), None) is True
        assert permission.has_permission(MockRequest(student_user), None) is False

    def test_is_instructor_or_admin(self, instructor_user, student_user, admin_user):
        """Test IsInstructorOrAdmin permission."""
        permission = IsInstructorOrAdmin()

        class MockRequest:
            def __init__(self, user):
                self.user = user

        assert permission.has_permission(MockRequest(instructor_user), None) is True
        assert permission.has_permission(MockRequest(admin_user), None) is True
        assert permission.has_permission(MockRequest(student_user), None) is False
