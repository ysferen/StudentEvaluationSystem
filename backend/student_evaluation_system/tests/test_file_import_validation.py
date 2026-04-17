"""
Integration tests for file import validation endpoints.

Tests the validate and resolve endpoints for the file import system.
"""

import json
import pytest
from io import BytesIO
import pandas as pd
from django.contrib.auth import get_user_model
from rest_framework import status

from core.models import Term, Course
from evaluation.models import Assessment, CourseEnrollment
from users.models import StudentProfile

User = get_user_model()


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def term(db):
    """Create a test term."""
    return Term.objects.create(name="Fall 2025", is_active=True)


@pytest.fixture
def course(db, term):
    """Create a test course with program and department."""
    from core.models import University, Department, DegreeLevel, Program

    university = University.objects.create(name="Test University")
    department = Department.objects.create(code="TEST", name="Test Department", university=university)
    degree_level = DegreeLevel.objects.create(name="Bachelor's")
    program = Program.objects.create(code="TESTPROG", name="Test Program", degree_level=degree_level, department=department)

    return Course.objects.create(code="CS101", name="Introduction to Computer Science", credits=3, program=program, term=term)


@pytest.fixture
def instructor(db, course):
    """Create an instructor user."""
    user = User.objects.create_user(
        username="instructor",
        email="instructor@test.com",
        password="testpass123",
        first_name="Test",
        last_name="Instructor",
        role="instructor",
    )
    course.instructors.add(user)
    return user


@pytest.fixture
def student(db, course, term):
    """Create a test student with profile and enrollment."""
    user = User.objects.create_user(
        username="student1",
        email="student1@test.com",
        password="testpass123",
        first_name="John",
        last_name="Doe",
        role="student",
    )
    StudentProfile.objects.create(user=user, student_id="STU001", program=course.program, enrollment_term=term)
    CourseEnrollment.objects.create(student=user, course=course)
    return user


@pytest.fixture
def assessments(db, course, instructor):
    """Create sample assessments for the course."""
    midterm = Assessment.objects.create(
        name="Midterm Exam",
        assessment_type="midterm",
        course=course,
        date="2025-10-15",
        total_score=100,
        weight=0.3,
        created_by=instructor,
    )
    final = Assessment.objects.create(
        name="Final Exam",
        assessment_type="final",
        course=course,
        date="2025-12-15",
        total_score=100,
        weight=0.4,
        created_by=instructor,
    )
    project = Assessment.objects.create(
        name="Project",
        assessment_type="project",
        course=course,
        date="2025-11-15",
        total_score=100,
        weight=0.3,
        created_by=instructor,
    )
    return [midterm, final, project]


def create_excel_buffer(dataframe):
    """Helper to create an Excel file buffer from a DataFrame."""
    buffer = BytesIO()
    dataframe.to_excel(buffer, engine="openpyxl", index=False)
    buffer.seek(0)
    buffer.size = buffer.getbuffer().nbytes
    return buffer


class TestValidateEndpoint:
    """Tests for the /validate/ endpoint."""

    def setup_method(self):
        """Set up test fixtures."""
        pass

    @pytest.mark.django_db
    def test_validate_returns_structured_response(self, api_client, course, term, student, assessments):
        """Test that validate endpoint returns structured response with phases."""
        df = pd.DataFrame(
            {
                "öğrenci no": [student.student_profile.student_id],
                "adı": [student.first_name],
                "soyadı": [student.last_name],
                "Midterm Exam(%30)_0833AB": [85.5],
                "Final Exam(%40)_0833AB": [90.0],
                "Project(%30)_0833AB": [88.0],
            }
        )
        buffer = create_excel_buffer(df)
        buffer.name = "valid_scores.xlsx"

        response = api_client.post(
            f"/api/v1/core/file-import/assignment-scores/validate/?course_code={course.code}&term_id={term.id}",
            {"file": buffer},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert "is_valid" in data
        assert "phase_reached" in data
        assert "checks" in data
        assert "errors" in data
        assert "warnings" in data
        assert "suggestions" in data
        assert "details" in data

        assert "checks" in data
        for key in [
            "file_structure",
            "column_structure",
            "assessment_validation",
            "student_validation",
            "score_validation",
        ]:
            assert key in data["checks"]
            assert "passed" in data["checks"][key]
        assert data["is_valid"] is True

    @pytest.mark.django_db
    def test_validate_missing_students_returns_soft_failure(self, api_client, course, term, assessments):
        """Test that validation doesn't hard-fail when students are missing from database."""
        df = pd.DataFrame(
            {
                "öğrenci no": ["UNKNOWN_STUDENT_1", "UNKNOWN_STUDENT_2"],
                "adı": ["Unknown", "Another"],
                "soyadı": ["Student1", "Student2"],
                "Midterm Exam(%30)_0833AB": [75.0, 80.0],
                "Final Exam(%40)_0833AB": [85.0, 88.0],
                "Project(%30)_0833AB": [90.0, 92.0],
            }
        )
        buffer = create_excel_buffer(df)
        buffer.name = "unknown_students.xlsx"

        response = api_client.post(
            f"/api/v1/core/file-import/assignment-scores/validate/?course_code={course.code}&term_id={term.id}",
            {"file": buffer},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert data["is_valid"] is False
        assert len(data["errors"]) > 0

        error_messages = [e.get("message", "") if isinstance(e, dict) else str(e) for e in data["errors"]]
        assert any("students not found" in msg.lower() or "not found" in msg.lower() for msg in error_messages)

    @pytest.mark.django_db
    def test_validate_missing_course_returns_404(self, api_client, term):
        """Test validation returns 404 for non-existent course."""
        df = pd.DataFrame(
            {
                "öğrenci no": ["STU001"],
                "adı": ["John"],
                "soyadı": ["Doe"],
                "Midterm Exam(%30)_0833AB": [85.0],
            }
        )
        buffer = create_excel_buffer(df)
        buffer.name = "test.xlsx"

        response = api_client.post(
            f"/api/v1/core/file-import/assignment-scores/validate/?course_code=NONEXISTENT&term_id={term.id}",
            {"file": buffer},
            format="multipart",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_validate_missing_file_returns_400(self, api_client, course, term):
        """Test validation returns 400 when no file is provided."""
        response = api_client.post(
            f"/api/v1/core/file-import/assignment-scores/validate/?course_code={course.code}&term_id={term.id}",
            {},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_validate_missing_params_returns_400(self, api_client):
        """Test validation returns 400 when required params are missing."""
        response = api_client.post(
            "/api/v1/core/file-import/assignment-scores/validate/",
            {},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestResolveEndpoint:
    """Tests for the /resolve/ endpoint."""

    @pytest.mark.django_db
    def test_resolve_endpoint_creates_students(self, api_client, course, term, assessments):
        """Test that /resolve/ endpoint creates missing students from file data."""
        df = pd.DataFrame(
            {
                "öğrenci no": ["NEW_STUDENT_001", "NEW_STUDENT_002"],
                "adı": ["New", "Another"],
                "soyadı": ["Student1", "Student2"],
                "Midterm Exam(%30)_0833AB": [75.0, 80.0],
                "Final Exam(%40)_0833AB": [85.0, 88.0],
                "Project(%30)_0833AB": [90.0, 92.0],
            }
        )
        buffer = create_excel_buffer(df)
        buffer.name = "new_students.xlsx"

        resolutions = {
            "create_students": [
                {"student_id": "NEW_STUDENT_001", "first_name": "New", "last_name": "Student1"},
                {"student_id": "NEW_STUDENT_002", "first_name": "Another", "last_name": "Student2"},
            ]
        }

        response = api_client.post(
            f"/api/v1/core/file-import/assignment-scores/resolve/?course_code={course.code}&term_id={term.id}",
            {"file": buffer, "resolutions": json.dumps(resolutions)},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert "resolutions_applied" in data
        assert "created" in data["resolutions_applied"]
        assert data["resolutions_applied"]["created"]["students"] == 2

        assert StudentProfile.objects.filter(student_id="NEW_STUDENT_001").exists()
        assert StudentProfile.objects.filter(student_id="NEW_STUDENT_002").exists()

    @pytest.mark.django_db
    def test_resolve_endpoint_creates_enrollments(self, api_client, course, term, assessments):
        """Test that /resolve/ endpoint creates enrollments for existing students."""
        new_user = User.objects.create_user(
            username="pre_existing",
            email="preexisting@test.com",
            password="testpass123",
            first_name="Pre",
            last_name="Existing",
            role="student",
        )
        StudentProfile.objects.create(user=new_user, student_id="EXISTING_001", program=course.program, enrollment_term=term)

        df = pd.DataFrame(
            {
                "öğrenci no": ["EXISTING_001"],
                "adı": ["Pre"],
                "soyadı": ["Existing"],
                "Midterm Exam(%30)_0833AB": [85.0],
                "Final Exam(%40)_0833AB": [90.0],
                "Project(%30)_0833AB": [88.0],
            }
        )
        buffer = create_excel_buffer(df)
        buffer.name = "enroll_student.xlsx"

        resolutions = {
            "create_students": [{"student_id": "EXISTING_001", "first_name": "Pre", "last_name": "Existing"}],
            "enroll_students": ["EXISTING_001"],
        }

        response = api_client.post(
            f"/api/v1/core/file-import/assignment-scores/resolve/?course_code={course.code}&term_id={term.id}",
            {"file": buffer, "resolutions": json.dumps(resolutions)},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert data["resolutions_applied"]["created"]["enrollments"] == 1
        assert CourseEnrollment.objects.filter(student=new_user, course=course).exists()

    @pytest.mark.django_db
    def test_resolve_endpoint_creates_assessments(self, api_client, course, term):
        """Test that /resolve/ endpoint creates missing assessments."""
        df = pd.DataFrame(
            {
                "öğrenci no": ["STU001"],
                "adı": ["John"],
                "soyadı": ["Doe"],
                "Quiz 1(%10)_0833AB": [90.0],
            }
        )
        buffer = create_excel_buffer(df)
        buffer.name = "new_assessment.xlsx"

        resolutions = {"create_assessments": [{"name": "Quiz 1", "assessment_type": "quiz", "total_score": 20, "weight": 0.1}]}

        response = api_client.post(
            f"/api/v1/core/file-import/assignment-scores/resolve/?course_code={course.code}&term_id={term.id}",
            {"file": buffer, "resolutions": json.dumps(resolutions)},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert data["resolutions_applied"]["created"]["assessments"] == 1
        assert Assessment.objects.filter(name="Quiz 1", course=course).exists()

    @pytest.mark.django_db
    def test_resolve_after_student_creation_is_valid(self, api_client, course, term, assessments):
        """Test that after creating students via resolve, validation passes."""
        df = pd.DataFrame(
            {
                "öğrenci no": ["RESOLVED_STUDENT_001"],
                "adı": ["Resolved"],
                "soyadı": ["Student"],
                "Midterm Exam(%30)_0833AB": [85.0],
                "Final Exam(%40)_0833AB": [90.0],
                "Project(%30)_0833AB": [88.0],
            }
        )
        buffer = create_excel_buffer(df)
        buffer.name = "resolved_student.xlsx"

        resolutions = {
            "create_students": [{"student_id": "RESOLVED_STUDENT_001", "first_name": "Resolved", "last_name": "Student"}],
        }

        response = api_client.post(
            f"/api/v1/core/file-import/assignment-scores/resolve/?course_code={course.code}&term_id={term.id}",
            {"file": buffer, "resolutions": json.dumps(resolutions)},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert data["resolutions_applied"]["created"]["students"] == 1
        assert data["is_valid"] is True

    @pytest.mark.django_db
    def test_resolve_accepts_assignment_resolution_keys(self, api_client, course, term, assessments):
        df = pd.DataFrame(
            {
                "öğrenci no": ["NEW001"],
                "adı": ["Yeni"],
                "soyadı": ["Ogrenci"],
                "Midterm Exam(%30)_0833AB": [75],
            }
        )
        buffer = create_excel_buffer(df)
        buffer.name = "resolve-keys.xlsx"

        resolutions = {
            "create_students": [{"student_id": "NEW001", "first_name": "Yeni", "last_name": "Ogrenci"}],
            "skip_unenrolled_students": False,
            "enroll_students": ["NEW001"],
            "create_assessments": [],
            "skip_invalid_scores": False,
            "clamp_scores": False,
        }

        response = api_client.post(
            f"/api/v1/core/file-import/assignment-scores/resolve/?course_code={course.code}&term_id={term.id}",
            {"file": buffer, "resolutions": json.dumps(resolutions)},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "resolutions_applied" in response.data
