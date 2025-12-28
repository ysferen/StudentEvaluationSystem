"""
Tests for file import functionality.

This module tests the file import services and validation:
- FileImportService
- ExcelParser
- AssignmentScoreValidator
- File format validation
- Data import logic
"""

import pytest
from io import BytesIO
import pandas as pd
from core.services.file_import import (
    FileImportService, FileImportError, ExcelParser
)
from core.services.validation import AssignmentScoreValidator
from core.models import Course, ProgramOutcome, LearningOutcome
from evaluation.models import Assessment, StudentGrade, CourseEnrollment
from users.models import StudentProfile


@pytest.mark.django_db
class TestExcelParser:
    """Tests for ExcelParser class."""

    def test_validate_file_valid_excel(self):
        """Test validation of valid Excel file."""
        df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        buffer = BytesIO()
        df.to_excel(buffer, engine='openpyxl')
        buffer.seek(0)
        # Add name attribute for validation
        buffer.name = 'test.xlsx'
        buffer.size = buffer.getbuffer().nbytes

        parser = ExcelParser()
        assert parser.validate_file(buffer) is True

    def test_validate_file_invalid_format(self):
        """Test validation of invalid file format."""
        buffer = BytesIO()
        buffer.write(b'This is not an Excel file')
        buffer.seek(0)
        # Add name attribute for validation
        buffer.name = 'test.txt'

        parser = ExcelParser()
        with pytest.raises(FileImportError):
            parser.validate_file(buffer)

    def test_get_sheet_names(self):
        """Test getting sheet names from Excel file."""
        df = pd.DataFrame({'data': [1, 2, 3]})
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False)
            df.to_excel(writer, sheet_name='Sheet2', index=False)
        buffer.seek(0)

        parser = ExcelParser()
        sheets = parser.get_sheet_names(buffer)

        assert 'Sheet1' in sheets
        assert 'Sheet2' in sheets

    def test_parse_sheet(self):
        """Test parsing a sheet from Excel file."""
        df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        buffer = BytesIO()
        df.to_excel(buffer, sheet_name='TestData', engine='openpyxl', index=False)
        buffer.seek(0)

        parser = ExcelParser()
        parsed_df = parser.parse_sheet(buffer)

        assert len(parsed_df) == 2
        assert 'col1' in parsed_df.columns
        assert 'col2' in parsed_df.columns


@pytest.mark.django_db
class TestFileImportService:
    """Tests for FileImportService class."""

    def test_detect_file_format_xlsx(self):
        """Test detecting .xlsx file format."""
        df = pd.DataFrame({'data': [1, 2, 3]})
        buffer = BytesIO()
        df.to_excel(buffer, engine='openpyxl')
        buffer.seek(0)
        buffer.name = 'test.xlsx'

        service = FileImportService(buffer)
        format_type = service.detect_file_format()

        assert format_type == 'excel'

    def test_detect_file_format_xls(self):
        """Test detecting .xls file format."""
        df = pd.DataFrame({'data': [1, 2, 3]})
        buffer = BytesIO()
        df.to_excel(buffer, engine='openpyxl')
        buffer.seek(0)
        buffer.name = 'test.xls'

        service = FileImportService(buffer)
        format_type = service.detect_file_format()

        assert format_type == 'excel'

    def test_detect_file_format_csv(self):
        """Test detecting .csv file format."""
        df = pd.DataFrame({'data': [1, 2, 3]})
        buffer = BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        buffer.name = 'test.csv'

        service = FileImportService(buffer)
        format_type = service.detect_file_format()

        assert format_type == 'csv'

    def test_validate_file_size_too_large(self):
        """Test validation rejects file larger than 10MB."""
        # Create a large buffer
        buffer = BytesIO()
        buffer.write(b'x' * (11 * 1024 * 1024))  # 11 MB
        buffer.seek(0)
        buffer.name = 'large_test.xlsx'
        buffer.size = buffer.getbuffer().nbytes

        service = FileImportService(buffer)
        with pytest.raises(FileImportError, match='File size must be less than'):
            service.validate_file()

    def test_validate_file_empty_file(self):
        """Test validation rejects empty file."""
        buffer = BytesIO()
        buffer.write(b'')
        buffer.seek(0)
        buffer.name = 'empty_test.xlsx'
        buffer.size = buffer.getbuffer().nbytes

        service = FileImportService(buffer)
        with pytest.raises(FileImportError, match='File is empty'):
            service.validate_file()


@pytest.mark.django_db
class TestAssignmentScoreValidator:
    """Tests for AssignmentScoreValidator class."""

    def test_validate_missing_student_id_column(self, db_setup):
        """Test validation fails when student ID column is missing."""
        course = db_setup['course']

        # Create Excel without student ID column
        df = pd.DataFrame({
            'name': ['Student 1', 'Student 2'],
            'grade': [85, 90]
        })
        buffer = BytesIO()
        df.to_excel(buffer, engine='openpyxl', index=False)
        buffer.seek(0)
        buffer.name = 'test_missing_id.xlsx'
        buffer.size = buffer.getbuffer().nbytes

        result = AssignmentScoreValidator.validate_complete(buffer, course)

        assert not result.is_valid
        assert any('Student ID' in str(error) for error in result.errors)

    def test_validate_missing_assessment_columns(self, db_setup):
        """Test validation fails when no assessment columns found."""
        course = db_setup['course']

        # Create Excel with only student info
        df = pd.DataFrame({
            'öğrenci no': ['12345', '67890'],
            'adı': ['John', 'Jane'],
            'soyadı': ['Doe', 'Smith']
        })
        buffer = BytesIO()
        df.to_excel(buffer, engine='openpyxl', index=False)
        buffer.seek(0)
        buffer.name = 'test_missing_assessments.xlsx'
        buffer.size = buffer.getbuffer().nbytes

        result = AssignmentScoreValidator.validate_complete(buffer, course)

        assert not result.is_valid
        assert any('assessment' in str(error).lower() for error in result.errors)

    def test_validate_unknown_assessment(self, db_setup):
        """Test validation warns about unknown assessments."""
        course = db_setup['course']

        # Create Excel with unknown assessment
        df = pd.DataFrame({
            'öğrenci no': ['12345'],
            'adı': ['John'],
            'soyadı': ['Doe'],
            'Unknown Assessment(%25)_0833AB': [85]
        })
        buffer = BytesIO()
        df.to_excel(buffer, engine='openpyxl', index=False)
        buffer.seek(0)
        buffer.name = 'test_unknown_assessment.xlsx'
        buffer.size = buffer.getbuffer().nbytes

        result = AssignmentScoreValidator.validate_complete(buffer, course)

        # Should have warnings about unknown assessments
        assert len(result.warnings) > 0 or not result.is_valid

    def test_validate_unknown_students(self, db_setup):
        """Test validation warns about unknown student IDs."""
        course = db_setup['course']

        # Create assessment
        Assessment.objects.create(
            name="Midterm",
            course=course,
            total_score=100,
            weight=0.3,
            date="2025-12-28"
        )

        # Create Excel with unknown student
        df = pd.DataFrame({
            'öğrenci no': ['99999'],  # Unknown student
            'adı': ['Unknown'],
            'soyadı': ['Student'],
            'Midterm(%25)_0833AB': [85]
        })
        buffer = BytesIO()
        df.to_excel(buffer, engine='openpyxl', index=False)
        buffer.seek(0)
        buffer.name = 'test_unknown_student.xlsx'
        buffer.size = buffer.getbuffer().nbytes

        result = AssignmentScoreValidator.validate_complete(buffer, course)

        # Should have warnings about unknown students
        assert len(result.warnings) > 0 or not result.is_valid

    def test_validate_valid_assignment_scores(self, db_setup, student_factory, sample_assessments):
        """Test validation passes for valid assignment scores file."""
        course = db_setup['course']
        assessments = sample_assessments['assessments']
        student = student_factory('student1')

        # Create Excel with valid data
        df = pd.DataFrame({
            'öğrenci no': [student.student_id],
            'adı': [student.user.first_name],
            'soyadı': [student.user.last_name],
            'Midterm Exam(%30)_0833AB': [85.5],
            'Final Exam(%40)_0833AB': [90.0],
            'Project(%30)_0833AB': [88.0]
        })
        buffer = BytesIO()
        df.to_excel(buffer, engine='openpyxl', index=False)
        buffer.seek(0)
        buffer.name = 'test_valid_assignment_scores.xlsx'
        buffer.size = buffer.getbuffer().nbytes

        result = AssignmentScoreValidator.validate_complete(buffer, course)

        # Should be valid or have only warnings (not errors)
        assert result.is_valid or len(result.errors) == 0


@pytest.mark.django_db
class TestAssignmentScoresImport:
    """Tests for importing assignment scores."""

    def test_import_assignment_scores(self, db_setup, student_factory, sample_assessments):
        """Test successful import of assignment scores."""
        course = db_setup['course']
        assessments = sample_assessments['assessments']
        student = student_factory('student1')

        # Enroll student in course
        CourseEnrollment.objects.create(student=student.user, course=course)

        # Create Excel file with scores
        df = pd.DataFrame({
            'öğrenci no': [student.student_id],
            'adı': [student.user.first_name],
            'soyadı': [student.user.last_name],
            'Midterm Exam(%30)_0833AB': [85.5],
            'Final Exam(%40)_0833AB': [90.0],
            'Project(%30)_0833AB': [88.0]
        })
        buffer = BytesIO()
        df.to_excel(buffer, engine='openpyxl', index=False)
        buffer.seek(0)
        buffer.name = 'test_import_assignment_scores.xlsx'
        buffer.size = buffer.getbuffer().nbytes

        # Import scores
        service = FileImportService(buffer)
        service.validate_file()
        results = service.import_assignment_scores(
            course_code=course.code,
            term_id=course.term_id
        )

        assert 'created' in results
        assert 'grades' in results['created']
        assert results['created']['grades'] > 0

        # Verify grades were created
        assert StudentGrade.objects.filter(student=student.user).count() == 3

    def test_import_updates_existing_grades(self, db_setup, student_factory, sample_assessments):
        """Test that import updates existing grades."""
        course = db_setup['course']
        assessments = sample_assessments['assessments']
        student = student_factory('student1')

        # Enroll student
        CourseEnrollment.objects.create(student=student.user, course=course)

        # Create existing grade
        StudentGrade.objects.create(
            student=student.user,
            assessment=assessments[0],
            score=70.0
        )

        # Create Excel with updated score
        df = pd.DataFrame({
            'öğrenci no': [student.student_id],
            'adı': [student.user.first_name],
            'soyadı': [student.user.last_name],
            'Midterm Exam(%30)_0833AB': [85.5],
            'Final Exam(%40)_0833AB': [90.0],
            'Project(%30)_0833AB': [88.0]
        })
        buffer = BytesIO()
        df.to_excel(buffer, engine='openpyxl', index=False)
        buffer.seek(0)
        buffer.name = 'test_update_assignment_scores.xlsx'
        buffer.size = buffer.getbuffer().nbytes

        # Import scores
        service = FileImportService(buffer)
        service.validate_file()
        results = service.import_assignment_scores(
            course_code=course.code,
            term_id=course.term_id
        )

        assert 'created' in results
        assert 'grades' in results['created']
        assert results['created']['grades'] >= 0

        # Verify grade was updated
        grade = StudentGrade.objects.get(
            student=student.user,
            assessment=assessments[0]
        )
        assert grade.score == 85.5

    def test_import_skips_unenrolled_students(self, db_setup, student_factory, sample_assessments):
        """Test that import skips students not enrolled in the course."""
        course = db_setup['course']
        assessments = sample_assessments['assessments']
        student = student_factory('student_unenrolled')

        # Don't enroll student

        # Create Excel file
        df = pd.DataFrame({
            'öğrenci no': [student.student_id],
            'adı': [student.user.first_name],
            'soyadı': [student.user.last_name],
            'Midterm Exam(%30)_0833AB': [85.5],
            'Final Exam(%40)_0833AB': [90.0],
            'Project(%30)_0833AB': [88.0]
        })
        buffer = BytesIO()
        df.to_excel(buffer, engine='openpyxl', index=False)
        buffer.seek(0)
        buffer.name = 'test_unenrolled_student.xlsx'
        buffer.size = buffer.getbuffer().nbytes

        # Import scores
        service = FileImportService(buffer)
        service.validate_file()

        # Verify file import error raised for unenrolled student
        with pytest.raises(FileImportError, match='not enrolled in course'):
            service.import_assignment_scores(
                course_code=course.code,
                term_id=course.term_id
            )


@pytest.mark.django_db
class TestLearningOutcomesImport:
    """Tests for importing learning outcomes."""

    def test_import_learning_outcomes(self, db_setup):
        """Test successful import of learning outcomes."""
        course = db_setup['course']

        # Create Excel file with LOs
        df = pd.DataFrame({
            'code': ['LO1', 'LO2', 'LO3'],
            'description': [
                'Understand concepts',
                'Apply knowledge',
                'Analyze problems'
            ],
            'course_code': [course.code, course.code, course.code]
        })
        buffer = BytesIO()
        df.to_excel(buffer, sheet_name='learning_outcomes', engine='openpyxl', index=False)
        buffer.seek(0)
        buffer.name = 'test_import_learning_outcomes.xlsx'
        buffer.size = buffer.getbuffer().nbytes

        # Import LOs
        service = FileImportService(buffer)
        service.validate_file()
        results = service.import_learning_outcomes(sheet_name='learning_outcomes')

        assert 'created' in results
        assert 'learning_outcomes' in results['created']
        assert results['created']['learning_outcomes'] == 3

        # Verify LOs were created
        assert LearningOutcome.objects.filter(course=course).count() == 3
        assert LearningOutcome.objects.filter(code='LO1').exists()


@pytest.mark.django_db
class TestProgramOutcomesImport:
    """Tests for importing program outcomes."""

    def test_import_program_outcomes(self, db_setup):
        """Test successful import of program outcomes."""
        program = db_setup['program']
        term = db_setup['term']

        # Create Excel file with POs
        df = pd.DataFrame({
            'code': ['PO1', 'PO2'],
            'description': ['Engineering Knowledge', 'Problem Analysis'],
            'program_code': [program.code, program.code],
            'term_name': [term.name, term.name]
        })
        buffer = BytesIO()
        df.to_excel(buffer, sheet_name='program_outcomes', engine='openpyxl', index=False)
        buffer.seek(0)
        buffer.name = 'test_import_program_outcomes.xlsx'
        buffer.size = buffer.getbuffer().nbytes

        # Import POs
        service = FileImportService(buffer)
        service.validate_file()
        results = service.import_program_outcomes(sheet_name='program_outcomes')

        assert 'created' in results
        assert 'program_outcomes' in results['created']
        assert results['created']['program_outcomes'] == 2

        # Verify POs were created
        assert ProgramOutcome.objects.filter(program=program).count() == 2
        assert ProgramOutcome.objects.filter(code='PO1').exists()
