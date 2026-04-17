"""
Tests for file import service behavior.
"""

from io import BytesIO

import pandas as pd
import pytest

from core.models import LearningOutcome, ProgramOutcome
from core.services.file_import import FileImportError, FileImportService
from evaluation.models import CourseEnrollment, StudentGrade


@pytest.mark.django_db
class TestFileImportService:
    """Tests for FileImportService class."""

    def test_detect_file_format_xlsx(self):
        """Test detecting .xlsx file format."""
        df = pd.DataFrame({"data": [1, 2, 3]})
        buffer = BytesIO()
        df.to_excel(buffer, engine="openpyxl")
        buffer.seek(0)
        buffer.name = "test.xlsx"

        service = FileImportService(buffer)
        format_type = service.detect_file_format()

        assert format_type == "excel"

    def test_detect_file_format_xls(self):
        """Test detecting .xls file format."""
        df = pd.DataFrame({"data": [1, 2, 3]})
        buffer = BytesIO()
        df.to_excel(buffer, engine="openpyxl")
        buffer.seek(0)
        buffer.name = "test.xls"

        service = FileImportService(buffer)
        format_type = service.detect_file_format()

        assert format_type == "excel"

    def test_detect_file_format_csv(self):
        """Test detecting .csv file format."""
        df = pd.DataFrame({"data": [1, 2, 3]})
        buffer = BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        buffer.name = "test.csv"

        service = FileImportService(buffer)
        format_type = service.detect_file_format()

        assert format_type == "csv"

    def test_validate_file_size_too_large(self):
        """Test validation rejects file larger than 10MB."""
        buffer = BytesIO()
        buffer.write(b"x" * (11 * 1024 * 1024))
        buffer.seek(0)
        buffer.name = "large_test.xlsx"
        buffer.size = buffer.getbuffer().nbytes

        service = FileImportService(buffer)
        with pytest.raises(FileImportError, match="File size must be less than"):
            service.validate_file()

    def test_validate_file_empty_file(self):
        """Test validation rejects empty file."""
        buffer = BytesIO()
        buffer.write(b"")
        buffer.seek(0)
        buffer.name = "empty_test.xlsx"
        buffer.size = buffer.getbuffer().nbytes

        service = FileImportService(buffer)
        with pytest.raises(FileImportError, match="File is empty"):
            service.validate_file()


@pytest.mark.django_db
class TestAssignmentScoresImport:
    """Tests for importing assignment scores."""

    def test_import_assignment_scores(self, db_setup, student_factory, sample_assessments):
        """Test successful import of assignment scores."""
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
        buffer = BytesIO()
        df.to_excel(buffer, engine="openpyxl", index=False)
        buffer.seek(0)
        buffer.name = "test_import_assignment_scores.xlsx"
        buffer.size = buffer.getbuffer().nbytes

        service = FileImportService(buffer)
        service.validate_file()
        results = service.import_assignment_scores(course_code=course.code, term_id=course.term_id)

        assert "created" in results
        assert "grades" in results["created"]
        assert results["created"]["grades"] > 0
        assert StudentGrade.objects.filter(student=student.user).count() == 3

    def test_import_updates_existing_grades(self, db_setup, student_factory, sample_assessments):
        """Test that import updates existing grades."""
        course = db_setup["course"]
        assessments = sample_assessments["assessments"]
        student = student_factory("student1")

        CourseEnrollment.objects.create(student=student.user, course=course)
        StudentGrade.objects.create(student=student.user, assessment=assessments[0], score=70.0)

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
        buffer = BytesIO()
        df.to_excel(buffer, engine="openpyxl", index=False)
        buffer.seek(0)
        buffer.name = "test_update_assignment_scores.xlsx"
        buffer.size = buffer.getbuffer().nbytes

        service = FileImportService(buffer)
        service.validate_file()
        results = service.import_assignment_scores(course_code=course.code, term_id=course.term_id)

        assert "created" in results
        assert "grades" in results["created"]
        assert results["created"]["grades"] >= 0

        grade = StudentGrade.objects.get(student=student.user, assessment=assessments[0])
        assert grade.score == 85.5

    def test_import_skips_unenrolled_students(self, db_setup, student_factory, sample_assessments):
        """Test that import skips students not enrolled in the course."""
        course = db_setup["course"]
        student = student_factory("student_unenrolled")

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
        buffer = BytesIO()
        df.to_excel(buffer, engine="openpyxl", index=False)
        buffer.seek(0)
        buffer.name = "test_unenrolled_student.xlsx"
        buffer.size = buffer.getbuffer().nbytes

        service = FileImportService(buffer)
        service.validate_file()

        with pytest.raises(FileImportError, match="not enrolled in course"):
            service.import_assignment_scores(course_code=course.code, term_id=course.term_id)


@pytest.mark.django_db
class TestLearningOutcomesImport:
    """Tests for importing learning outcomes."""

    def test_import_learning_outcomes(self, db_setup):
        """Test successful import of learning outcomes."""
        course = db_setup["course"]

        df = pd.DataFrame(
            {
                "code": ["LO1", "LO2", "LO3"],
                "description": ["Understand concepts", "Apply knowledge", "Analyze problems"],
                "course_code": [course.code, course.code, course.code],
            }
        )
        buffer = BytesIO()
        df.to_excel(buffer, sheet_name="learning_outcomes", engine="openpyxl", index=False)
        buffer.seek(0)
        buffer.name = "test_import_learning_outcomes.xlsx"
        buffer.size = buffer.getbuffer().nbytes

        service = FileImportService(buffer)
        service.validate_file()
        results = service.import_learning_outcomes(sheet_name="learning_outcomes")

        assert "created" in results
        assert "learning_outcomes" in results["created"]
        assert results["created"]["learning_outcomes"] == 3
        assert LearningOutcome.objects.filter(course=course).count() == 3
        assert LearningOutcome.objects.filter(code="LO1").exists()


@pytest.mark.django_db
class TestProgramOutcomesImport:
    """Tests for importing program outcomes."""

    def test_import_program_outcomes(self, db_setup):
        """Test successful import of program outcomes."""
        program = db_setup["program"]
        term = db_setup["term"]

        df = pd.DataFrame(
            {
                "code": ["PO1", "PO2"],
                "description": ["Engineering Knowledge", "Problem Analysis"],
                "program_code": [program.code, program.code],
                "term_name": [term.name, term.name],
            }
        )
        buffer = BytesIO()
        df.to_excel(buffer, sheet_name="program_outcomes", engine="openpyxl", index=False)
        buffer.seek(0)
        buffer.name = "test_import_program_outcomes.xlsx"
        buffer.size = buffer.getbuffer().nbytes

        service = FileImportService(buffer)
        service.validate_file()
        results = service.import_program_outcomes(sheet_name="program_outcomes")

        assert "created" in results
        assert "program_outcomes" in results["created"]
        assert results["created"]["program_outcomes"] == 2
        assert ProgramOutcome.objects.filter(program=program).count() == 2
        assert ProgramOutcome.objects.filter(code="PO1").exists()
