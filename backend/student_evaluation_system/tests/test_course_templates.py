"""
Tests for CourseTemplate model, clone service, and API endpoints.
"""

import pytest
from django.core.exceptions import ValidationError

from core.models import (
    CourseTemplate,
    CourseTemplateLearningOutcome,
    CourseTemplateAssessment,
    CourseTemplateAssessmentLOMapping,
    CourseTemplateLOPOMapping,
    Course,
    InstructorPermission,
    LearningOutcomeProgramOutcomeMapping,
)
from evaluation.models import AssessmentLearningOutcomeMapping


# --- Model tests ---


@pytest.mark.django_db
class TestCourseTemplateModel:
    def test_create_template(self, db_setup):
        template = CourseTemplate.objects.create(
            name="Intro to CS",
            code="CS101",
            credits=3,
            program=db_setup["program"],
        )
        assert template.code == "CS101"
        assert str(template) == "CS101: Intro to CS (Template)"

    def test_unique_code_per_program(self, db_setup):
        CourseTemplate.objects.create(name="First", code="CS101", credits=3, program=db_setup["program"])
        with pytest.raises(Exception):
            CourseTemplate.objects.create(name="Second", code="CS101", credits=4, program=db_setup["program"])

    def test_string_representation(self, db_setup):
        template = CourseTemplate.objects.create(name="Data Structures", code="CS201", program=db_setup["program"])
        assert str(template) == "CS201: Data Structures (Template)"


@pytest.mark.django_db
class TestCourseTemplateLearningOutcomeModel:
    def test_create_template_lo(self, db_setup):
        template = CourseTemplate.objects.create(name="Math", code="MATH101", credits=3, program=db_setup["program"])
        lo = CourseTemplateLearningOutcome.objects.create(
            code="LO1",
            description="Understand basic algebra",
            course_template=template,
        )
        assert lo.course_template == template
        assert template.learning_outcomes.count() == 1

    def test_unique_lo_code_per_template(self, db_setup):
        template = CourseTemplate.objects.create(name="Math", code="MATH101", credits=3, program=db_setup["program"])
        CourseTemplateLearningOutcome.objects.create(code="LO1", description="First", course_template=template)
        with pytest.raises(Exception):
            CourseTemplateLearningOutcome.objects.create(code="LO1", description="Second", course_template=template)


@pytest.mark.django_db
class TestCourseTemplateAssessmentModel:
    def test_create_template_assessment(self, db_setup):
        template = CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        assessment = CourseTemplateAssessment.objects.create(
            name="Midterm",
            assessment_type="midterm",
            total_score=100,
            weight=0.3,
            course_template=template,
        )
        assert assessment.course_template == template
        assert template.assessments.count() == 1


@pytest.mark.django_db
class TestCourseTemplateAssessmentLOMappingModel:
    def test_valid_mapping(self, db_setup):
        template = CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        lo = CourseTemplateLearningOutcome.objects.create(
            code="LO1", description="Programming basics", course_template=template
        )
        assessment = CourseTemplateAssessment.objects.create(
            name="Final", assessment_type="final", total_score=100, weight=0.5, course_template=template
        )
        mapping = CourseTemplateAssessmentLOMapping.objects.create(
            template_assessment=assessment,
            template_learning_outcome=lo,
            weight=1.0,
        )
        assert mapping.weight == 1.0

    def test_cross_template_validation(self, db_setup):
        template1 = CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        template2 = CourseTemplate.objects.create(name="CS102", code="CS102", credits=3, program=db_setup["program"])
        lo = CourseTemplateLearningOutcome.objects.create(
            code="LO1", description="Different template", course_template=template1
        )
        assessment = CourseTemplateAssessment.objects.create(
            name="Midterm", assessment_type="midterm", total_score=100, weight=0.5, course_template=template2
        )
        mapping = CourseTemplateAssessmentLOMapping(
            template_assessment=assessment,
            template_learning_outcome=lo,
            weight=0.5,
        )
        with pytest.raises(ValidationError):
            mapping.clean()


# --- Clone service tests ---


@pytest.mark.django_db
class TestCloneCourseFromTemplate:
    def test_clone_basic_course(self, db_setup):
        template = CourseTemplate.objects.create(
            name="Intro to Programming",
            code="CS100",
            credits=4,
            program=db_setup["program"],
        )
        from core.services.course_template import clone_course_from_template

        course = clone_course_from_template(template, db_setup["term"])

        assert course.name == "Intro to Programming"
        assert course.code == "CS100"
        assert course.credits == 4
        assert course.program == db_setup["program"]
        assert course.term == db_setup["term"]
        assert course.course_template == template

    def test_clone_with_learning_outcomes(self, db_setup):
        template = CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        CourseTemplateLearningOutcome.objects.create(code="LO1", description="Understand variables", course_template=template)
        CourseTemplateLearningOutcome.objects.create(code="LO2", description="Understand loops", course_template=template)

        from core.services.course_template import clone_course_from_template

        course = clone_course_from_template(template, db_setup["term"])

        assert course.learning_outcomes.count() == 2
        lo_codes = set(course.learning_outcomes.values_list("code", flat=True))
        assert lo_codes == {"LO1", "LO2"}

    def test_clone_with_assessments(self, db_setup):
        template = CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        CourseTemplateAssessment.objects.create(
            name="Midterm",
            assessment_type="midterm",
            total_score=100,
            weight=0.3,
            course_template=template,
        )
        CourseTemplateAssessment.objects.create(
            name="Final",
            assessment_type="final",
            total_score=100,
            weight=0.7,
            course_template=template,
        )

        from core.services.course_template import clone_course_from_template

        course = clone_course_from_template(template, db_setup["term"])

        assert course.assessments.count() == 2
        assessment_names = set(course.assessments.values_list("name", flat=True))
        assert assessment_names == {"Midterm", "Final"}

    def test_clone_with_assessment_lo_mappings(self, db_setup):
        template = CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        lo = CourseTemplateLearningOutcome.objects.create(
            code="LO1",
            description="Coding basics",
            course_template=template,
        )
        assessment = CourseTemplateAssessment.objects.create(
            name="Homework",
            assessment_type="homework",
            total_score=50,
            weight=0.5,
            course_template=template,
        )
        CourseTemplateAssessmentLOMapping.objects.create(
            template_assessment=assessment,
            template_learning_outcome=lo,
            weight=1.0,
        )

        from core.services.course_template import clone_course_from_template

        course = clone_course_from_template(template, db_setup["term"])

        cloned_assessment = course.assessments.first()
        cloned_lo = course.learning_outcomes.first()
        mapping = AssessmentLearningOutcomeMapping.objects.get(assessment=cloned_assessment, learning_outcome=cloned_lo)
        assert mapping.weight == 1.0

    def test_clone_with_lo_po_mappings(self, db_setup):
        from core.models import ProgramOutcome

        template = CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        lo = CourseTemplateLearningOutcome.objects.create(
            code="LO1",
            description="Coding basics",
            course_template=template,
        )
        po = ProgramOutcome.objects.create(
            code="PO1",
            description="Problem solving",
            program=db_setup["program"],
            term=db_setup["term"],
        )
        CourseTemplateLOPOMapping.objects.create(
            template_learning_outcome=lo,
            program_outcome=po,
            weight=0.5,
        )

        from core.services.course_template import clone_course_from_template

        course = clone_course_from_template(template, db_setup["term"])

        cloned_lo = course.learning_outcomes.first()
        mapping = LearningOutcomeProgramOutcomeMapping.objects.get(
            learning_outcome=cloned_lo,
            program_outcome=po,
        )
        assert mapping.weight == 0.5
        assert mapping.course == course

    def test_clone_preserves_term_independence(self, db_setup):
        """Two clones from the same template should be independent."""
        from core.models import Term

        template = CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        CourseTemplateLearningOutcome.objects.create(
            code="LO1",
            description="Basics",
            course_template=template,
        )

        term_fall = db_setup["term"]
        term_spring = Term.objects.create(name="Spring 2025", is_active=True)

        from core.services.course_template import clone_course_from_template

        course_fall = clone_course_from_template(template, term_fall)
        course_spring = clone_course_from_template(template, term_spring)

        assert course_fall.learning_outcomes.count() == 1
        assert course_spring.learning_outcomes.count() == 1
        assert course_fall.learning_outcomes.first().id != course_spring.learning_outcomes.first().id

    def test_clone_raises_on_none_template(self, db_setup):
        from core.services.course_template import clone_course_from_template

        with pytest.raises(ValueError, match="template is required"):
            clone_course_from_template(None, db_setup["term"])

    def test_clone_raises_on_none_term(self, db_setup):
        template = CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        from core.services.course_template import clone_course_from_template

        with pytest.raises(ValueError, match="term is required"):
            clone_course_from_template(template, None)


# --- API tests ---


@pytest.mark.django_db
class TestCourseTemplateAPI:
    def test_list_templates(self, api_client, db_setup):
        CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        response = api_client.get("/api/core/course-templates/")
        assert response.status_code == 200
        assert len(response.data) >= 1

    def test_create_template(self, api_client, db_setup, fb_admin_factory):
        admin = fb_admin_factory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            "/api/core/course-templates/",
            {
                "name": "New Template",
                "code": "NT101",
                "credits": 3,
                "program_id": db_setup["program"].id,
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["code"] == "NT101"
        assert response.data["name"] == "New Template"

    def test_get_template_learning_outcomes(self, api_client, db_setup):
        template = CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        CourseTemplateLearningOutcome.objects.create(code="LO1", description="Basics", course_template=template)
        response = api_client.get(f"/api/core/course-templates/{template.id}/learning-outcomes/")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["code"] == "LO1"

    def test_add_learning_outcome_to_template(self, api_client, db_setup, fb_admin_factory):
        admin = fb_admin_factory()
        api_client.force_authenticate(user=admin)
        template = CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        response = api_client.post(
            f"/api/core/course-templates/{template.id}/learning-outcomes/",
            {"code": "LO1", "description": "New outcome"},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["code"] == "LO1"
        assert template.learning_outcomes.count() == 1

    def test_get_template_assessments(self, api_client, db_setup):
        template = CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        CourseTemplateAssessment.objects.create(
            name="Midterm",
            assessment_type="midterm",
            total_score=100,
            weight=0.3,
            course_template=template,
        )
        response = api_client.get(f"/api/core/course-templates/{template.id}/assessments/")
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_instantiate_creates_course(self, api_client, db_setup, fb_admin_factory):
        admin = fb_admin_factory()
        api_client.force_authenticate(user=admin)
        template = CourseTemplate.objects.create(name="CS101", code="CS101", credits=4, program=db_setup["program"])
        CourseTemplateLearningOutcome.objects.create(
            code="LO1",
            description="Basics",
            course_template=template,
        )
        CourseTemplateAssessment.objects.create(
            name="Final",
            assessment_type="final",
            total_score=100,
            weight=0.5,
            course_template=template,
        )

        response = api_client.post(
            f"/api/core/course-templates/{template.id}/instantiate/",
            {"term_id": db_setup["term"].id},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["code"] == "CS101"
        assert response.data["credits"] == 4

        # Verify the course was created with cloned data
        course = Course.objects.get(id=response.data["id"])
        assert course.course_template == template
        assert course.learning_outcomes.count() == 1
        assert course.assessments.count() == 1

    def test_instantiate_same_template_same_term_is_idempotent(self, api_client, db_setup, fb_admin_factory):
        admin = fb_admin_factory()
        api_client.force_authenticate(user=admin)
        template = CourseTemplate.objects.create(name="CHE 101", code="CHE 101", credits=4, program=db_setup["program"])
        CourseTemplateLearningOutcome.objects.create(
            code="LO1",
            description="Basics",
            course_template=template,
        )

        first_response = api_client.post(
            f"/api/core/course-templates/{template.id}/instantiate/",
            {"term_id": db_setup["term"].id},
            format="json",
        )
        second_response = api_client.post(
            f"/api/core/course-templates/{template.id}/instantiate/",
            {"term_id": db_setup["term"].id},
            format="json",
        )

        assert first_response.status_code == 201
        assert second_response.status_code == 200
        assert second_response.data["id"] == first_response.data["id"]
        assert Course.objects.filter(code="CHE 101", program=db_setup["program"], term=db_setup["term"]).count() == 1
        course = Course.objects.get(id=first_response.data["id"])
        assert course.learning_outcomes.count() == 1

    def test_instructor_with_full_courses_permission_can_instantiate(self, api_client, db_setup, instructor_user_factory):
        instructor_user = instructor_user_factory(username="template_instructor")
        profile = instructor_user.instructor_profile
        InstructorPermission.objects.create(
            instructor=profile,
            resource_area="courses",
            permission_tier="full",
        )
        api_client.force_authenticate(user=instructor_user)
        template = CourseTemplate.objects.create(name="CS102", code="CS102", credits=3, program=db_setup["program"])

        response = api_client.post(
            f"/api/core/course-templates/{template.id}/instantiate/",
            {"term_id": db_setup["term"].id},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["code"] == "CS102"
        assert Course.objects.get(id=response.data["id"]).instructors.filter(id=instructor_user.id).exists()

    def test_instantiate_missing_term_id(self, api_client, db_setup, fb_admin_factory):
        admin = fb_admin_factory()
        api_client.force_authenticate(user=admin)
        template = CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        response = api_client.post(
            f"/api/core/course-templates/{template.id}/instantiate/",
            {},
            format="json",
        )
        assert response.status_code == 400
        assert "term_id" in str(response.data)

    def test_instantiate_invalid_term_id(self, api_client, db_setup, fb_admin_factory):
        admin = fb_admin_factory()
        api_client.force_authenticate(user=admin)
        template = CourseTemplate.objects.create(name="CS101", code="CS101", credits=3, program=db_setup["program"])
        response = api_client.post(
            f"/api/core/course-templates/{template.id}/instantiate/",
            {"term_id": 99999},
            format="json",
        )
        assert response.status_code == 404
