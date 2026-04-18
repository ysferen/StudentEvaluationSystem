"""
Tests for assignment score validation phases and complete validation flow.
"""

import pandas as pd
import pytest

from core.services.validation import AssignmentScoreValidator
from evaluation.models import Assessment, CourseEnrollment
from tests.upload_helpers import InMemoryUpload


@pytest.mark.django_db
class TestAssignmentScoreValidator:
    """Tests for AssignmentScoreValidator class."""

    def test_validate_missing_student_id_column(self, db_setup):
        """Test validation fails when student ID column is missing."""
        course = db_setup["course"]

        df = pd.DataFrame({"name": ["Student 1", "Student 2"], "grade": [85, 90]})
        buffer = InMemoryUpload()
        df.to_excel(buffer, engine="openpyxl", index=False)
        buffer.seek(0)
        buffer.name = "test_missing_id.xlsx"

        result = AssignmentScoreValidator.validate_complete(buffer, course)

        assert not result.is_valid
        assert any("Student ID" in str(error) for error in result.errors)

    def test_validate_missing_assessment_columns(self, db_setup):
        """Test validation fails when no assessment columns found."""
        course = db_setup["course"]

        df = pd.DataFrame({"öğrenci no": ["12345", "67890"], "adı": ["John", "Jane"], "soyadı": ["Doe", "Smith"]})
        buffer = InMemoryUpload()
        df.to_excel(buffer, engine="openpyxl", index=False)
        buffer.seek(0)
        buffer.name = "test_missing_assessments.xlsx"

        result = AssignmentScoreValidator.validate_complete(buffer, course)

        assert not result.is_valid
        assert any("assessment" in str(error).lower() for error in result.errors)

    def test_validate_unknown_assessment(self, db_setup):
        """Test validation warns about unknown assessments."""
        course = db_setup["course"]

        df = pd.DataFrame(
            {"öğrenci no": ["12345"], "adı": ["John"], "soyadı": ["Doe"], "Unknown Assessment(%25)_0833AB": [85]}
        )
        buffer = InMemoryUpload()
        df.to_excel(buffer, engine="openpyxl", index=False)
        buffer.seek(0)
        buffer.name = "test_unknown_assessment.xlsx"

        result = AssignmentScoreValidator.validate_complete(buffer, course)

        assert len(result.warnings) > 0 or not result.is_valid

    def test_validate_unknown_students(self, db_setup):
        """Test validation warns about unknown student IDs."""
        course = db_setup["course"]

        Assessment.objects.create(name="Midterm", course=course, total_score=100, weight=0.3, date="2025-12-28")

        df = pd.DataFrame(
            {
                "öğrenci no": ["99999"],
                "adı": ["Unknown"],
                "soyadı": ["Student"],
                "Midterm(%25)_0833AB": [85],
            }
        )
        buffer = InMemoryUpload()
        df.to_excel(buffer, engine="openpyxl", index=False)
        buffer.seek(0)
        buffer.name = "test_unknown_student.xlsx"

        result = AssignmentScoreValidator.validate_complete(buffer, course)

        assert len(result.warnings) > 0 or not result.is_valid

    def test_validate_valid_assignment_scores(self, db_setup, student_factory, sample_assessments):
        """Test validation passes for valid assignment scores file."""
        course = db_setup["course"]
        student = student_factory("student1")
        CourseEnrollment.objects.create(student=student.user, course=course)

        df = pd.DataFrame(
            {
                "öğrenci no": [student.student_id],
                "adı": [student.user.first_name],
                "soyadı": [student.user.last_name],
                "Midterm Exam(%30)_0833AB": [85.5],
                "Final Exam(%40)_0833AB": [90.0],
                "Project(%30)_0833AB": [88.0],
            }
        )
        buffer = InMemoryUpload()
        df.to_excel(buffer, engine="openpyxl", index=False)
        buffer.seek(0)
        buffer.name = "test_valid_assignment_scores.xlsx"

        result = AssignmentScoreValidator.validate_complete(buffer, course)

        assert result.is_valid or len(result.errors) == 0


class TestPhase2ColumnStructure:
    def test_valid_column_structure_passes(self, db_setup):
        df = pd.DataFrame(
            {
                "öğrenci no": ["S001", "S002"],
                "adı": ["Ali", "Ayşe"],
                "soyadı": ["Veli", "Demir"],
                "Midterm(%30)": [80, 90],
            }
        )
        result = AssignmentScoreValidator.validate_column_structure(df)
        assert result.is_valid

    def test_missing_student_id_column_fails(self, db_setup):
        df = pd.DataFrame({"adı": ["Ali"], "soyadı": ["Veli"], "Midterm(%30)": [80]})
        result = AssignmentScoreValidator.validate_column_structure(df)
        assert not result.is_valid
        assert any("öğrenci no" in e["message"] for e in result.errors)

    def test_missing_first_name_column_fails(self, db_setup):
        df = pd.DataFrame({"öğrenci no": ["S001"], "soyadı": ["Veli"], "Midterm(%30)": [80]})
        result = AssignmentScoreValidator.validate_column_structure(df)
        assert not result.is_valid
        assert any("First Name" in e["message"] for e in result.errors)

    def test_missing_assessment_column_fails(self, db_setup):
        df = pd.DataFrame({"öğrenci no": ["S001"], "adı": ["Ali"], "soyadı": ["Veli"]})
        result = AssignmentScoreValidator.validate_column_structure(df)
        assert not result.is_valid
        assert any("No assessment" in e["message"] for e in result.errors)


class TestPhase5ScoreValidation:
    def test_valid_scores_pass(self, db_setup):
        course = db_setup["course"]
        Assessment.objects.create(course=course, name="Midterm", total_score=100)
        df = pd.DataFrame(
            {
                "öğrenci no": ["S001", "S002", "S003"],
                "adı": ["Ali", "Ayşe", "Veli"],
                "soyadı": ["Demir", "Yılmaz", "Özkan"],
                "Midterm(%30)": [80, 90, 70],
            }
        )
        result = AssignmentScoreValidator.validate_scores(df, course)
        assert result.is_valid

    def test_out_of_range_score_fails(self, db_setup):
        course = db_setup["course"]
        Assessment.objects.create(course=course, name="Midterm", total_score=100)
        df = pd.DataFrame(
            {
                "öğrenci no": ["S001", "S002"],
                "adı": ["Ali", "Ayşe"],
                "soyadı": ["Demir", "Yılmaz"],
                "Midterm(%30)": [150, 90],
            }
        )
        result = AssignmentScoreValidator.validate_scores(df, course)
        assert not result.is_valid
        assert any("out of range" in e["message"].lower() or "150" in e["message"] for e in result.errors)

    def test_negative_score_fails(self, db_setup):
        course = db_setup["course"]
        Assessment.objects.create(course=course, name="Midterm", total_score=100)
        df = pd.DataFrame(
            {
                "öğrenci no": ["S001", "S002"],
                "adı": ["Ali", "Ayşe"],
                "soyadı": ["Demir", "Yılmaz"],
                "Midterm(%30)": [-10, 90],
            }
        )
        result = AssignmentScoreValidator.validate_scores(df, course)
        assert not result.is_valid

    def test_non_numeric_score_fails(self, db_setup):
        course = db_setup["course"]
        Assessment.objects.create(course=course, name="Midterm", total_score=100)
        df = pd.DataFrame(
            {
                "öğrenci no": ["S001", "S002"],
                "adı": ["Ali", "Ayşe"],
                "soyadı": ["Demir", "Yılmaz"],
                "Midterm(%30)": ["abc", 90],
            }
        )
        result = AssignmentScoreValidator.validate_scores(df, course)
        assert not result.is_valid


def test_validate_complete_sets_phase_reached_and_checks(db_setup):
    course = db_setup["course"]
    Assessment.objects.create(course=course, name="Midterm", total_score=100)

    df = pd.DataFrame({"öğrenci no": ["S001"], "adı": ["Ali"], "soyadı": ["Veli"], "Midterm(%30)_X1": [80]})
    buf = InMemoryUpload()
    df.to_excel(buf, index=False)
    buf.seek(0)
    buf.name = "ok.xlsx"

    result = AssignmentScoreValidator.validate_complete(buf, course)

    assert "phase_reached" in result.validation_details
    checks = result.validation_details.get("checks")
    assert isinstance(checks, dict)
    assert set(checks.keys()) == {
        "file_structure",
        "column_structure",
        "assessment_validation",
        "student_validation",
        "score_validation",
    }
    assert checks["file_structure"]["passed"] is True


def test_validate_complete_hard_stops_at_column_structure(db_setup):
    course = db_setup["course"]
    df = pd.DataFrame({"adı": ["Ali"], "soyadı": ["Veli"]})
    buf = InMemoryUpload()
    df.to_excel(buf, index=False)
    buf.seek(0)
    buf.name = "missing-columns.xlsx"

    result = AssignmentScoreValidator.validate_complete(buf, course)

    assert result.is_valid is False
    assert result.validation_details["phase_reached"] == "column_structure"
    checks = result.validation_details["checks"]
    assert checks["file_structure"]["passed"] is True
    assert checks["column_structure"]["passed"] is False
