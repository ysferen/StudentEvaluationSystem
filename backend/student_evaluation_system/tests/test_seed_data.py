import pytest

from core.models import (
    InstructorPermission,
    PermissionTier,
    ResourceArea,
    University,
    Department,
    DegreeLevel,
    Program,
    Term,
    CourseTemplate,
    Course,
    ProgramOutcome,
)
from evaluation.models import AssessmentLearningOutcomeMapping
from users.models import CustomUser, InstructorProfile, ProgramHeadProfile


@pytest.fixture(scope="module")
def seeded(django_db_blocker):
    """Run seed_data once for the entire module — skip students to keep it fast."""
    from django.core.management import call_command

    with django_db_blocker.unblock():
        call_command("seed_data", skip_students=True)


class TestSeedAcademicStructure:
    def test_creates_university(self, db, seeded):
        assert University.objects.filter(name="Acıbadem University").exists()

    def test_creates_department_linked_to_university(self, db, seeded):
        uni = University.objects.get(name="Acıbadem University")
        dept = Department.objects.filter(name__icontains="Mühendislik", university=uni).first()
        assert dept is not None
        assert dept.code == "ENS"

    def test_creates_degree_and_program(self, db, seeded):
        assert DegreeLevel.objects.filter(name="Lisans").exists()
        program = Program.objects.filter(code="CSE").first()
        assert program is not None
        assert program.department.code == "ENS"

    def test_creates_terms_with_academic_years(self, db, seeded):
        terms = Term.objects.all()
        assert terms.count() >= 1
        # Verify at least one term has the expected fields set
        sample = terms.first()
        assert sample.academic_year is not None
        assert sample.semester in ("fall", "spring")


class TestSeedCreatesProgramHead:
    def test_program_head_user_and_profile_exist(self, db, seeded):
        head_user = CustomUser.objects.filter(username="headuser").first()
        assert head_user is not None
        assert head_user.role == "program_head"
        assert ProgramHeadProfile.objects.filter(user=head_user).exists()


class TestSeedCreatesInstructors:
    def test_instructors_get_full_permissions(self, db, seeded):
        profiles = InstructorProfile.objects.select_related("user").all()
        assert profiles.count() >= 1, "Seed command should create at least one instructor"

        for profile in profiles:
            permission_count = InstructorPermission.objects.filter(
                instructor=profile,
                permission_tier=PermissionTier.FULL,
            ).count()
            assert permission_count == len(ResourceArea.values), (
                f"Instructor {profile.user.username} should have FULL permissions for all resource areas"
            )


class TestSeedCurriculum:
    def test_creates_course_templates(self, db, seeded):
        templates = CourseTemplate.objects.all()
        assert templates.count() >= 1, "Should create at least one course template"
        # Each template should have a code, name, credits
        for t in templates:
            assert t.code
            assert t.name
            assert t.credits > 0

    def test_instantiates_courses_from_templates(self, db, seeded):
        courses = Course.objects.select_related("course_template").all()
        assert courses.count() >= 1, "Should create at least one course"
        templated_courses = courses.filter(course_template__isnull=False)
        assert templated_courses.count() == courses.count(), "Every instantiated course should have a course_template"

    def test_every_course_belongs_to_a_term(self, db, seeded):
        for course in Course.objects.all():
            assert course.term is not None, f"Course {course.code} should belong to a term"

    def test_every_course_has_at_least_one_instructor(self, db, seeded):
        for course in Course.objects.all():
            assert course.instructors.count() >= 1, f"Course {course.code} should have at least one instructor assigned"

    def test_courses_are_spread_across_terms(self, db, seeded):
        term_course_counts = {t.id: Course.objects.filter(term=t).count() for t in Term.objects.all()}
        populated_terms = sum(1 for c in term_course_counts.values() if c > 0)
        assert populated_terms >= 2, "Courses should span at least 2 terms"


class TestSeedProgramOutcomes:
    def test_creates_program_outcomes(self, db, seeded):
        pos = ProgramOutcome.objects.all()
        assert pos.count() >= 1, "Should create at least one program outcome"
        for po in pos:
            assert po.code.startswith("PO"), f"Program outcome code should start with 'PO', got {po.code}"
            assert po.description

    def test_outcomes_belong_to_program_and_term(self, db, seeded):
        program = Program.objects.get(code="CSE")
        for po in ProgramOutcome.objects.all():
            assert po.program == program
            assert po.term is not None


class TestSeedLearningOutcomesAndAssessments:
    def test_courses_have_learning_outcomes(self, db, seeded):
        courses_with_missing_los = []
        for course in Course.objects.all():
            if course.learning_outcomes.count() == 0:
                courses_with_missing_los.append(course.code)
        assert not courses_with_missing_los, f"Courses missing LOs: {courses_with_missing_los}"

    def test_lo_po_mappings_exist(self, db, seeded):
        from core.models import LearningOutcomeProgramOutcomeMapping

        assert LearningOutcomeProgramOutcomeMapping.objects.count() >= 1, "Should create at least one LO-PO mapping"

    def test_courses_have_assessments(self, db, seeded):
        courses_without_assessments = []
        for course in Course.objects.all():
            if course.assessments.count() == 0:
                courses_without_assessments.append(course.code)
        assert not courses_without_assessments, f"Courses missing assessments: {courses_without_assessments}"

    def test_assessments_are_mapped_to_learning_outcomes(self, db, seeded):
        assert AssessmentLearningOutcomeMapping.objects.count() >= 1, "Should create at least one assessment-LO mapping"

    def test_students_not_created_when_skipped(self, db, seeded):
        """Sanity: --skip-students should prevent student creation."""
        from users.models import StudentProfile

        assert StudentProfile.objects.count() == 0, "Students should not be created when --skip-students is used"
