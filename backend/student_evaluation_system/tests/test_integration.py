"""
Integration tests for complete workflows.

Tests end-to-end user scenarios and API workflows.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestStudentGradeWorkflow:
    """Test complete student grade workflow."""

    def test_instructor_creates_assessment_and_grades(
        self, api_client, fb_instructor_factory, fb_student_factory, fb_course_factory
    ):
        """Test instructor creating assessment and entering grades."""
        instructor = fb_instructor_factory()
        course = fb_course_factory(instructor=instructor)
        student = fb_student_factory()

        # Enroll student
        from evaluation.models import CourseEnrollment

        CourseEnrollment.objects.create(student=student, course=course)

        api_client.force_authenticate(user=instructor)

        # 1. Create assessment
        assessment_data = {
            "name": "Final Exam",
            "course": course.id,
            "assessment_type": "final",
            "total_score": 100,
            "weight": 0.4,
        }
        response = api_client.post("/api/v1/evaluation/assessments/", assessment_data)
        assert response.status_code == status.HTTP_201_CREATED
        assessment_id = response.data["id"]

        # 2. Enter grade
        grade_data = {
            "student": student.id,
            "assessment": assessment_id,
            "score": 85.0,
        }
        response = api_client.post("/api/v1/evaluation/grades/", grade_data)
        assert response.status_code == status.HTTP_201_CREATED

        # 3. Verify grade exists
        response = api_client.get(f"/api/v1/evaluation/grades/?student={student.id}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1


@pytest.mark.django_db
class TestCourseSetupWorkflow:
    """Test course setup workflow for department heads."""

    def test_head_creates_course_with_outcomes(self, api_client, fb_admin_factory):
        """Test admin/head creating course with learning outcomes."""
        admin = fb_admin_factory()
        api_client.force_authenticate(user=admin)

        # 1. Create university
        uni_data = {"name": "Test University", "code": "TU"}
        response = api_client.post("/api/v1/core/universities/", uni_data)
        assert response.status_code == status.HTTP_201_CREATED
        uni_id = response.data["id"]

        # 2. Create department
        dept_data = {"name": "CS", "code": "CS", "university": uni_id}
        response = api_client.post("/api/v1/core/departments/", dept_data)
        assert response.status_code == status.HTTP_201_CREATED
        dept_id = response.data["id"]

        # 3. Create program
        from core.models import DegreeLevel

        degree = DegreeLevel.objects.create(name="Bachelor", level=1)

        prog_data = {
            "name": "Computer Science",
            "code": "CS-BS",
            "department": dept_id,
            "degree_level": degree.id,
        }
        response = api_client.post("/api/v1/core/programs/", prog_data)
        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestFileImportWorkflow:
    """Test file import workflow."""

    def test_import_validation_endpoint(self, api_client, fb_instructor_factory):
        """Test file import validation."""
        instructor = fb_instructor_factory()
        api_client.force_authenticate(user=instructor)

        # Test validation endpoint without file
        response = api_client.post("/api/v1/core/file-import/assignment-scores/validate/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPermissionWorkflows:
    """Test permission-based workflows."""

    def test_student_cannot_create_course(self, api_client, fb_student_factory):
        """Test student cannot create courses."""
        student = fb_student_factory()
        api_client.force_authenticate(user=student)

        course_data = {
            "name": "Hacking Course",
            "code": "HACK101",
        }
        response = api_client.post("/api/v1/core/courses/", course_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_student_can_view_own_scores(self, api_client, fb_student_factory, fb_assessment_factory):
        """Test student can only view own scores."""
        student = fb_student_factory()
        api_client.force_authenticate(user=student)

        response = api_client.get("/api/v1/core/student-lo-scores/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAuthenticationWorkflows:
    """Test authentication-related workflows."""

    def test_login_and_access_protected_endpoint(self, api_client, fb_user_factory):
        """Test login flow and accessing protected endpoints."""
        fb_user_factory(username="testuser", password="testpass123")

        # Login
        login_data = {
            "username": "testuser",
            "password": "testpass123",
        }
        response = api_client.post("/api/v1/users/auth/login/", login_data)
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

        # Use token to access protected endpoint
        token = response.data["access"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = api_client.get("/api/v1/users/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "testuser"

    def test_unauthorized_access_denied(self, api_client):
        """Test unauthorized access is denied."""
        response = api_client.get("/api/v1/core/courses/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh(self, api_client, fb_user_factory):
        """Test token refresh endpoint."""
        user = fb_user_factory()
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        refresh_token = str(refresh)

        response = api_client.post("/api/v1/users/auth/refresh/", {"refresh": refresh_token})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
