import pytest
from datetime import date
from django.urls import reverse
from rest_framework import status

from core.models import LearningOutcomeProgramOutcomeMapping, StudentLearningOutcomeScore, StudentProgramOutcomeScore
from core.services.reports.course_report import ReportDataError, build_course_report_data
from core.services.reports.program_report import build_program_report_data
from evaluation.models import StudentGrade


@pytest.mark.django_db
class TestCourseReportBuilder:
    def test_builds_course_report_from_course_scoped_data(
        self,
        course_factory,
        instructor_user_factory,
        student_user_factory,
        assessment_factory,
        learning_outcome_factory,
        course_enrollment_factory,
        term_factory,
    ):
        term = term_factory(name="Spring 2026")
        course = course_factory(code="CSE342", name="Software Engineering", term=term, credits=4)
        instructor = instructor_user_factory(first_name="Ada", last_name="Lovelace")
        course.instructors.add(instructor)
        student_one = student_user_factory(username="student_a", first_name="Aylin", last_name="Kaya")
        student_two = student_user_factory(username="student_b", first_name="Berk", last_name="Sahin")
        course_enrollment_factory(student=student_one, course=course)
        course_enrollment_factory(student=student_two, course=course)
        midterm = assessment_factory(
            course=course,
            name="Midterm",
            assessment_type="midterm",
            total_score=100,
            weight=0.4,
            date=date(2026, 3, 1),
        )
        final = assessment_factory(
            course=course,
            name="Final",
            assessment_type="final",
            total_score=100,
            weight=0.6,
            date=date(2026, 5, 1),
        )
        lo_one = learning_outcome_factory(course=course, code="LO1", description="Analyze requirements")
        lo_two = learning_outcome_factory(course=course, code="LO2", description="Design systems")

        StudentGrade.objects.create(student=student_one, assessment=midterm, score=80)
        StudentGrade.objects.create(student=student_one, assessment=final, score=90)
        StudentGrade.objects.create(student=student_two, assessment=midterm, score=50)
        StudentGrade.objects.create(student=student_two, assessment=final, score=70)
        StudentLearningOutcomeScore.objects.create(student=student_one, learning_outcome=lo_one, score=75)
        StudentLearningOutcomeScore.objects.create(student=student_two, learning_outcome=lo_one, score=55)
        StudentLearningOutcomeScore.objects.create(student=student_one, learning_outcome=lo_two, score=95)

        other_course = course_factory(program=course.program, term=term)
        other_assessment = assessment_factory(course=other_course, total_score=100, weight=1)
        other_lo = learning_outcome_factory(course=other_course, code="LOX")
        StudentGrade.objects.create(student=student_one, assessment=other_assessment, score=1)
        StudentLearningOutcomeScore.objects.create(student=student_one, learning_outcome=other_lo, score=1)

        data = build_course_report_data(course.id)

        assert data.course_code == "CSE342"
        assert data.course_name == "Software Engineering"
        assert data.term == "Spring 2026"
        assert data.program == course.program.name
        assert data.credits == 4
        assert data.instructors == ["Ada Lovelace"]
        assert data.enrolled_students == 2
        assert [assessment.name for assessment in data.assessments] == ["Midterm", "Final"]
        assert data.assessments[0].scores == [80, 50]
        assert data.assessments[1].scores == [90, 70]
        assert [lo.code for lo in data.learning_outcomes] == ["LO1", "LO2"]
        assert data.learning_outcomes[1].scores == [95, 0.0]
        assert [student.course_grade for student in data.students] == [86.0, 62.0]

    def test_requires_minimum_course_data(self, course_factory):
        course = course_factory()

        with pytest.raises(ReportDataError, match="at least one enrollment"):
            build_course_report_data(course.id)


@pytest.mark.django_db
class TestProgramReportBuilder:
    def test_defaults_to_active_term_and_scopes_program_report_data(
        self,
        program_factory,
        term_factory,
        course_factory,
        assessment_factory,
        learning_outcome_factory,
        program_outcome_factory,
        course_enrollment_factory,
        student_user_factory,
    ):
        active_term = term_factory(name="Spring 2026", is_active=True)
        old_term = term_factory(name="Fall 2025", is_active=False)
        program = program_factory(code="CE")
        active_course = course_factory(program=program, term=active_term, code="CSE342")
        second_course = course_factory(program=program, term=active_term, code="CSE214")
        old_course = course_factory(program=program, term=old_term, code="CSE111")
        active_po = program_outcome_factory(program=program, term=active_term, code="PO1")
        second_po = program_outcome_factory(program=program, term=active_term, code="PO2")
        old_po = program_outcome_factory(program=program, term=old_term, code="PO9")
        active_lo = learning_outcome_factory(course=active_course, code="LO1")
        second_lo = learning_outcome_factory(course=second_course, code="LO2")
        old_lo = learning_outcome_factory(course=old_course, code="LO9")
        LearningOutcomeProgramOutcomeMapping.objects.create(
            course=active_course,
            learning_outcome=active_lo,
            program_outcome=active_po,
            weight=3,
        )
        LearningOutcomeProgramOutcomeMapping.objects.create(
            course=active_course,
            learning_outcome=active_lo,
            program_outcome=second_po,
            weight=2,
        )
        LearningOutcomeProgramOutcomeMapping.objects.create(
            course=second_course,
            learning_outcome=second_lo,
            program_outcome=active_po,
            weight=1,
        )
        LearningOutcomeProgramOutcomeMapping.objects.create(
            course=old_course,
            learning_outcome=old_lo,
            program_outcome=old_po,
            weight=5,
        )
        student = student_user_factory(username="active_student", first_name="Selin", last_name="Demir")
        old_student = student_user_factory(username="old_student")
        course_enrollment_factory(student=student, course=active_course, status="active")
        course_enrollment_factory(student=student, course=second_course, status="active")
        course_enrollment_factory(student=old_student, course=old_course, status="active")
        assessment = assessment_factory(course=active_course, total_score=100, weight=1)
        second_assessment = assessment_factory(course=second_course, total_score=100, weight=1)
        old_assessment = assessment_factory(course=old_course, total_score=100, weight=1)
        StudentGrade.objects.create(student=student, assessment=assessment, score=80)
        StudentGrade.objects.create(student=student, assessment=second_assessment, score=60)
        StudentGrade.objects.create(student=old_student, assessment=old_assessment, score=10)
        StudentProgramOutcomeScore.objects.create(student=student, program_outcome=active_po, term=active_term, score=82)
        StudentProgramOutcomeScore.objects.create(student=student, program_outcome=second_po, term=active_term, score=72)
        StudentProgramOutcomeScore.objects.create(student=old_student, program_outcome=old_po, term=old_term, score=10)

        data = build_program_report_data(program.id)

        assert data.term == "Spring 2026"
        assert data.enrolled_students == 1
        assert [course.code for course in data.active_courses] == ["CSE214", "CSE342"]
        assert {course.code: course.average_score for course in data.active_courses} == {"CSE214": 60.0, "CSE342": 80.0}
        assert {course.code: course.outcome_coverage for course in data.active_courses} == {"CSE214": 1, "CSE342": 2}
        assert [po.code for po in data.program_outcomes] == ["PO1", "PO2"]
        assert {po.code: po.contributing_courses for po in data.program_outcomes} == {"PO1": 2, "PO2": 1}
        assert data.students[0].name == "Selin Demir"
        assert data.students[0].program_average == 77.0

    def test_honors_explicit_term_id(self, program_factory, term_factory, course_factory, program_outcome_factory):
        active_term = term_factory(name="Spring 2026", is_active=True)
        old_term = term_factory(name="Fall 2025", is_active=False)
        program = program_factory()
        course_factory(program=program, term=active_term, code="ACT")
        course_factory(program=program, term=old_term, code="OLD")
        program_outcome_factory(program=program, term=active_term, code="POA")
        program_outcome_factory(program=program, term=old_term, code="POO")

        data = build_program_report_data(program.id, term_id=old_term.id)

        assert data.term == "Fall 2025"
        assert [course.code for course in data.active_courses] == ["OLD"]
        assert [po.code for po in data.program_outcomes] == ["POO"]


@pytest.mark.django_db
class TestReportEndpoints:
    def test_course_report_returns_pdf(
        self,
        api_client,
        course_factory,
        course_enrollment_factory,
        assessment_factory,
        learning_outcome_factory,
        student_user_factory,
        monkeypatch,
    ):
        course = course_factory(code="CSE342")
        student = student_user_factory()
        course_enrollment_factory(student=student, course=course)
        assessment_factory(course=course)
        learning_outcome_factory(course=course)
        monkeypatch.setattr("core.views.course.generate_course_report_pdf", lambda data: b"%PDF course")

        response = api_client.get(reverse("course-report", kwargs={"pk": course.id}))

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"
        assert response["Content-Disposition"] == 'inline; filename="CSE342-course-report.pdf"'

    def test_program_report_returns_pdf(
        self,
        api_client,
        program_factory,
        term_factory,
        course_factory,
        program_outcome_factory,
        monkeypatch,
    ):
        term = term_factory(name="Spring 2026", is_active=True)
        program = program_factory(code="CE")
        course_factory(program=program, term=term)
        program_outcome_factory(program=program, term=term)
        monkeypatch.setattr("core.views.academic_structure.generate_program_report_pdf", lambda data: b"%PDF program")

        response = api_client.get(reverse("program-report", kwargs={"pk": program.id}))

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "application/pdf"
        assert response["Content-Disposition"] == 'inline; filename="CE-Spring 2026-program-report.pdf"'

    def test_missing_required_data_returns_400(self, api_client, course_factory):
        response = api_client.get(reverse("course-report", kwargs={"pk": course_factory().id}))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "at least one enrollment" in response.data["detail"]

    def test_removed_preview_endpoints_return_404(self, api_client):
        assert api_client.get("/api/core/courses/report-preview/").status_code == status.HTTP_404_NOT_FOUND
        assert api_client.get("/api/core/programs/report-preview/").status_code == status.HTTP_404_NOT_FOUND


def test_mock_report_references_removed():
    import pathlib

    backend_root = pathlib.Path(__file__).resolve().parents[1]
    forbidden = [
        "mock_course_report_data",
        "mock_program_report_data",
        "report_preview",
        "generate_mock_course_report",
        "generate_mock_program_report",
    ]
    hits = []
    for path in backend_root.rglob("*.py"):
        if path.name == "test_reports.py":
            continue
        text = path.read_text()
        hits.extend((token, path) for token in forbidden if token in text)

    assert hits == []
