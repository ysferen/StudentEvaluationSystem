import pytest
import pandas as pd
from core.services.validation import AssignmentScoreValidator


@pytest.fixture
def db_setup(db):
    from core.models import University, Department, DegreeLevel, Program, Term, Course

    university = University.objects.create(name="Test University")
    department = Department.objects.create(code="TEST", name="Test Department", university=university)
    degree_level = DegreeLevel.objects.create(name="Bachelor's")
    program = Program.objects.create(code="TESTPROG", name="Test Program", degree_level=degree_level, department=department)
    term = Term.objects.create(name="2025 Spring", is_active=True)
    course = Course.objects.create(code="CS101", name="Intro to CS", credits=3, program=program, term=term)

    return {
        "university": university,
        "department": department,
        "degree_level": degree_level,
        "program": program,
        "term": term,
        "course": course,
    }


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
        df = pd.DataFrame(
            {
                "adı": ["Ali"],
                "soyadı": ["Veli"],
                "Midterm(%30)": [80],
            }
        )
        result = AssignmentScoreValidator.validate_column_structure(df)
        assert not result.is_valid
        assert any("öğrenci no" in e["message"] for e in result.errors)

    def test_missing_first_name_column_fails(self, db_setup):
        df = pd.DataFrame(
            {
                "öğrenci no": ["S001"],
                "soyadı": ["Veli"],
                "Midterm(%30)": [80],
            }
        )
        result = AssignmentScoreValidator.validate_column_structure(df)
        assert not result.is_valid

    def test_missing_assessment_column_fails(self, db_setup):
        df = pd.DataFrame(
            {
                "öğrenci no": ["S001"],
                "adı": ["Ali"],
                "soyadı": ["Veli"],
            }
        )
        result = AssignmentScoreValidator.validate_column_structure(df)
        assert not result.is_valid
        assert any("No assessment" in e["message"] for e in result.errors)


class TestPhase5ScoreValidation:
    def test_valid_scores_pass(self, db_setup):
        course = db_setup["course"]
        from evaluation.models import Assessment

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
        from evaluation.models import Assessment

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
        from evaluation.models import Assessment

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
        from evaluation.models import Assessment

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
