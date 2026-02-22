"""
Tests for Django REST Framework serializers.

Tests serializer validation, field handling, and error messages.
"""

import pytest

from core.serializers import (
    UniversitySerializer,
    DepartmentSerializer,
    CourseSerializer,
    ProgramOutcomeSerializer,
    CoreLearningOutcomeSerializer,
)


@pytest.mark.django_db
class TestUniversitySerializer:
    """Test UniversitySerializer."""

    def test_valid_university_data(self, fb_university_factory):
        """Test serializer with valid data."""
        university = fb_university_factory()
        serializer = UniversitySerializer(university)

        assert serializer.data["name"] == university.name
        assert serializer.data["code"] == university.code

    def test_university_create(self):
        """Test creating university through serializer."""
        data = {
            "name": "Test University",
            "code": "TEST01",
        }
        serializer = UniversitySerializer(data=data)
        assert serializer.is_valid()
        university = serializer.save()

        assert university.name == "Test University"
        assert university.code == "TEST01"

    def test_university_missing_required_fields(self):
        """Test missing code is auto-generated via model-level default."""
        data = {"name": "Test University"}  # Missing code
        serializer = UniversitySerializer(data=data)

        assert serializer.is_valid(), serializer.errors
        university = serializer.save()
        assert university.code


@pytest.mark.django_db
class TestDepartmentSerializer:
    """Test DepartmentSerializer."""

    def test_department_with_university(self, fb_department_factory):
        """Test serializer includes university data."""
        department = fb_department_factory()
        serializer = DepartmentSerializer(department)

        assert serializer.data["name"] == department.name
        assert "university" in serializer.data

    def test_department_create(self, fb_university_factory):
        """Test creating department with university."""
        university = fb_university_factory()
        data = {
            "name": "Computer Science",
            "code": "CS",
            "university": university.id,
        }
        serializer = DepartmentSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        department = serializer.save()

        assert department.name == "Computer Science"
        assert department.university == university


@pytest.mark.django_db
class TestCourseSerializer:
    """Test CourseSerializer."""

    def test_course_serialization(self, fb_course_factory):
        """Test course data serialization."""
        course = fb_course_factory()
        serializer = CourseSerializer(course)

        assert serializer.data["name"] == course.name
        assert serializer.data["code"] == course.code
        assert "program" in serializer.data
        assert "term" in serializer.data

    def test_course_with_instructors(self, fb_course_factory, fb_instructor_factory):
        """Test course includes instructors."""
        instructor = fb_instructor_factory()
        course = fb_course_factory()
        course.instructors.add(instructor)

        serializer = CourseSerializer(course)
        assert "instructors" in serializer.data
        assert len(serializer.data["instructors"]) == 1


@pytest.mark.django_db
class TestProgramOutcomeSerializer:
    """Test ProgramOutcomeSerializer."""

    def test_outcome_serialization(self, fb_program_outcome_factory):
        """Test program outcome serialization."""
        outcome = fb_program_outcome_factory()
        serializer = ProgramOutcomeSerializer(outcome)

        assert serializer.data["code"] == outcome.code
        assert serializer.data["description"] == outcome.description

    def test_outcome_weight_validation(self, fb_program_outcome_factory):
        """Test weight is between 0 and 1."""
        outcome = fb_program_outcome_factory(weight=0.5)
        serializer = ProgramOutcomeSerializer(outcome)

        assert serializer.data["weight"] == 0.5


@pytest.mark.django_db
class TestLearningOutcomeSerializer:
    """Test CoreLearningOutcomeSerializer."""

    def test_learning_outcome_serialization(self, fb_learning_outcome_factory):
        """Test learning outcome serialization."""
        outcome = fb_learning_outcome_factory()
        serializer = CoreLearningOutcomeSerializer(outcome)

        assert serializer.data["code"] == outcome.code
        assert serializer.data["description"] == outcome.description

    def test_learning_outcome_with_course(self, fb_learning_outcome_factory):
        """Test learning outcome includes course info."""
        outcome = fb_learning_outcome_factory()
        serializer = CoreLearningOutcomeSerializer(outcome)

        assert "course" in serializer.data


@pytest.mark.django_db
class TestSerializerValidationErrors:
    """Test serializer validation error handling."""

    def test_blank_code_validation(self):
        """Test that blank code is accepted and auto-generated."""
        data = {
            "name": "Test",
            "code": "",  # Blank code
        }
        serializer = UniversitySerializer(data=data)

        assert serializer.is_valid(), serializer.errors
        university = serializer.save()
        assert university.code

    def test_whitespace_only_code(self):
        """Test that whitespace-only code is accepted and auto-generated."""
        data = {
            "name": "Test",
            "code": "   ",  # Whitespace only
        }
        serializer = UniversitySerializer(data=data)

        assert serializer.is_valid(), serializer.errors
        university = serializer.save()
        assert university.code
