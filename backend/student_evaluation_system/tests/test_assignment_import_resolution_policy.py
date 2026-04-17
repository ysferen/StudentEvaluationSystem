import pytest
import pandas as pd
from io import BytesIO

from core.models import Term, Course, University, Department, DegreeLevel, Program
from core.services.file_import import FileImportService
from evaluation.models import Assessment, CourseEnrollment
from users.models import CustomUser, StudentProfile


def make_excel(df):
    buf = BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    buf.name = "policy.xlsx"
    buf.size = buf.getbuffer().nbytes
    return buf


@pytest.mark.django_db
def test_import_with_skip_invalid_scores_does_not_raise_for_invalid_cells():
    uni = University.objects.create(name="U")
    dep = Department.objects.create(code="D", name="Dep", university=uni)
    lvl = DegreeLevel.objects.create(name="L")
    program = Program.objects.create(code="P", name="Prog", degree_level=lvl, department=dep)
    term = Term.objects.create(name="T")
    course = Course.objects.create(code="CS101", name="C", credits=3, program=program, term=term)
    Assessment.objects.create(name="Midterm", assessment_type="midterm", total_score=100, weight=0.5, course=course)

    user = CustomUser.objects.create_user(username="S1", email="S1@example.com", first_name="A", last_name="B", role="student")
    StudentProfile.objects.create(user=user, student_id="S1", program=program)
    CourseEnrollment.objects.create(student=user, course=course, status="active")

    df = pd.DataFrame(
        {
            "öğrenci no": ["S1"],
            "adı": ["A"],
            "soyadı": ["B"],
            "Midterm(%50)_X1": [150],
        }
    )
    service = FileImportService(make_excel(df))
    service.validate_file()

    result = service.import_assignment_scores(
        course_code=course.code,
        term_id=term.id,
        resolution_policy={"skip_invalid_scores": True, "clamp_scores": False},
    )

    assert "errors" in result
