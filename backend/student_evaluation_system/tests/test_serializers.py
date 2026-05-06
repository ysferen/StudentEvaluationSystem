"""
Tests for Django REST Framework serializers.

Tests serializer validation, field handling, and error messages.
"""

import pytest
from typing import Any, cast

from core.serializers import (
    UniversitySerializer,
    DepartmentSerializer,
    CourseSerializer,
    ProgramOutcomeSerializer,
    CoreLearningOutcomeSerializer,
)
from evaluation.serializers import AssessmentLearningOutcomeMappingSerializer


def serializer_data_as_dict(data: Any) -> dict[str, Any]:
    """Cast serializer output to dict for static type checkers."""
    return cast(dict[str, Any], data)


@pytest.mark.django_db
class TestUniversitySerializer:
    """Test UniversitySerializer."""

    def test_valid_university_data(self, fb_university_factory):
        """Test serializer with valid data."""
        university = fb_university_factory()
        serializer = UniversitySerializer(university)
        data = serializer_data_as_dict(serializer.data)

        assert data["name"] == university.name
        assert data["code"] == university.code

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
        data = serializer_data_as_dict(serializer.data)

        assert data["name"] == department.name
        assert "university" in data

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
        data = serializer_data_as_dict(serializer.data)

        assert data["name"] == course.name
        assert data["code"] == course.code
        assert "program" in data
        assert "term" in data

    def test_course_with_instructors(self, fb_course_factory, fb_instructor_factory):
        """Test course includes instructors."""
        instructor = fb_instructor_factory()
        course = fb_course_factory()
        course.instructors.add(instructor)

        serializer = CourseSerializer(course)
        data = serializer_data_as_dict(serializer.data)
        assert "instructors" in data
        assert len(cast(list[Any], data["instructors"])) == 1


@pytest.mark.django_db
class TestProgramOutcomeSerializer:
    """Test ProgramOutcomeSerializer."""

    def test_outcome_serialization(self, fb_program_outcome_factory):
        """Test program outcome serialization."""
        outcome = fb_program_outcome_factory()
        serializer = ProgramOutcomeSerializer(outcome)
        data = serializer_data_as_dict(serializer.data)

        assert data["code"] == outcome.code
        assert data["description"] == outcome.description

    def test_outcome_weight_validation(self, fb_program_outcome_factory):
        """Test weight is between 0 and 1."""
        outcome = fb_program_outcome_factory(weight=0.5)
        serializer = ProgramOutcomeSerializer(outcome)
        data = serializer_data_as_dict(serializer.data)

        assert data["weight"] == 0.5


@pytest.mark.django_db
class TestLearningOutcomeSerializer:
    """Test CoreLearningOutcomeSerializer."""

    def test_learning_outcome_serialization(self, fb_learning_outcome_factory):
        """Test learning outcome serialization."""
        outcome = fb_learning_outcome_factory()
        serializer = CoreLearningOutcomeSerializer(outcome)
        data = serializer_data_as_dict(serializer.data)

        assert data["code"] == outcome.code
        assert data["description"] == outcome.description

    def test_learning_outcome_with_course(self, fb_learning_outcome_factory):
        """Test learning outcome includes course info."""
        outcome = fb_learning_outcome_factory()
        serializer = CoreLearningOutcomeSerializer(outcome)
        data = serializer_data_as_dict(serializer.data)

        assert "course" in data


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


@pytest.mark.django_db
class TestAssessmentLearningOutcomeMappingSerializer:
    """Test AssessmentLearningOutcomeMappingSerializer validation."""

    def test_blocks_weight_that_exceeds_total(self, fb_assessment_factory, fb_learning_outcome_factory):
        """Cannot create a mapping that pushes total weight over 1.0."""
        from evaluation.models import AssessmentLearningOutcomeMapping

        assessment = fb_assessment_factory()
        lo1 = fb_learning_outcome_factory(course=assessment.course)
        lo2 = fb_learning_outcome_factory(course=assessment.course)

        AssessmentLearningOutcomeMapping.objects.create(assessment=assessment, learning_outcome=lo1, weight=0.8)

        data = {
            "assessment_id": assessment.id,
            "learning_outcome_id": lo2.id,
            "weight": 0.3,
        }
        serializer = AssessmentLearningOutcomeMappingSerializer(data=data)
        assert not serializer.is_valid()
        assert "weight" in serializer.errors

    def test_allows_weight_that_sums_to_one(self, fb_assessment_factory, fb_learning_outcome_factory):
        """Creating a mapping that makes total exactly 1.0 should pass."""
        from evaluation.models import AssessmentLearningOutcomeMapping

        assessment = fb_assessment_factory()
        lo1 = fb_learning_outcome_factory(course=assessment.course)
        lo2 = fb_learning_outcome_factory(course=assessment.course)

        AssessmentLearningOutcomeMapping.objects.create(assessment=assessment, learning_outcome=lo1, weight=0.6)

        data = {
            "assessment_id": assessment.id,
            "learning_outcome_id": lo2.id,
            "weight": 0.4,
        }
        serializer = AssessmentLearningOutcomeMappingSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_allows_weight_below_one_for_intermediate_states(self, fb_assessment_factory, fb_learning_outcome_factory):
        """Sum < 1.0 should be allowed (intermediate state during edits)."""
        from evaluation.models import AssessmentLearningOutcomeMapping

        assessment = fb_assessment_factory()
        lo1 = fb_learning_outcome_factory(course=assessment.course)
        lo2 = fb_learning_outcome_factory(course=assessment.course)

        AssessmentLearningOutcomeMapping.objects.create(assessment=assessment, learning_outcome=lo1, weight=0.3)

        data = {
            "assessment_id": assessment.id,
            "learning_outcome_id": lo2.id,
            "weight": 0.3,
        }
        serializer = AssessmentLearningOutcomeMappingSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_update_respects_existing_mappings(self, fb_assessment_factory, fb_learning_outcome_factory):
        """Updating a mapping should check against other mappings (excluding itself)."""
        from evaluation.models import AssessmentLearningOutcomeMapping

        assessment = fb_assessment_factory()
        lo1 = fb_learning_outcome_factory(course=assessment.course)
        lo2 = fb_learning_outcome_factory(course=assessment.course)

        mapping1 = AssessmentLearningOutcomeMapping.objects.create(assessment=assessment, learning_outcome=lo1, weight=0.5)
        AssessmentLearningOutcomeMapping.objects.create(assessment=assessment, learning_outcome=lo2, weight=0.5)

        data = {"weight": 0.3}
        serializer = AssessmentLearningOutcomeMappingSerializer(mapping1, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors

    def test_update_blocks_weight_that_exceeds_total(self, fb_assessment_factory, fb_learning_outcome_factory):
        """Updating a mapping that pushes total over 1.0 should be rejected."""
        from evaluation.models import AssessmentLearningOutcomeMapping

        assessment = fb_assessment_factory()
        lo1 = fb_learning_outcome_factory(course=assessment.course)
        lo2 = fb_learning_outcome_factory(course=assessment.course)

        mapping1 = AssessmentLearningOutcomeMapping.objects.create(assessment=assessment, learning_outcome=lo1, weight=0.5)
        AssessmentLearningOutcomeMapping.objects.create(assessment=assessment, learning_outcome=lo2, weight=0.5)

        data = {"weight": 0.6}
        serializer = AssessmentLearningOutcomeMappingSerializer(mapping1, data=data, partial=True)
        assert not serializer.is_valid()
        assert "weight" in serializer.errors
