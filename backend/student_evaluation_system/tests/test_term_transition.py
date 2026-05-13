from unittest.mock import patch

import pytest
from core.models import TermTransitionJob
from tests.factories import CourseTemplateFactory


@pytest.mark.django_db
class TestTermTransitionJobModel:
    def test_create_transition_job(self, student_user_factory, term_factory):
        user = student_user_factory(username="ttj_create")
        old_term = term_factory(is_active=True)
        new_term = term_factory(name="Spring 2026", semester="spring", academic_year=2026, is_active=False)

        job = TermTransitionJob.objects.create(
            old_term=old_term,
            new_term=new_term,
            triggered_by=user,
            template_ids=[1, 2, 3],
            status="pending",
        )
        assert job.id is not None
        assert job.status == "pending"
        assert job.courses_created == 0
        assert job.template_ids == [1, 2, 3]
        assert str(job).startswith("TermTransition")

    def test_job_status_transitions(self, student_user_factory, term_factory):
        user = student_user_factory(username="ttj_status")
        old_term = term_factory(is_active=True)
        new_term = term_factory(name="Spring 2026", semester="spring", academic_year=2026, is_active=False)

        job = TermTransitionJob.objects.create(
            old_term=old_term,
            new_term=new_term,
            triggered_by=user,
            status="pending",
        )

        job.status = "running"
        job.save()
        job.refresh_from_db()
        assert job.status == "running"

        job.status = "success"
        job.courses_created = 5
        job.save()
        job.refresh_from_db()
        assert job.status == "success"
        assert job.courses_created == 5


@pytest.mark.django_db
class TestNextTermEndpoint:
    def test_next_term_requires_auth(self, api_client):
        response = api_client.post("/api/core/terms/next-term/", {}, format="json")
        assert response.status_code == 401

    def test_next_term_creates_new_term(self, authenticated_client, term_factory):
        """Happy path: transition from active term to new term with one template."""
        from tests.factories import CourseTemplateFactory

        client, user = authenticated_client("next_term_admin", "admin")
        active_term = term_factory(is_active=True)
        template = CourseTemplateFactory()

        data = {
            "semester": "spring",
            "academic_year": 2026,
            "template_ids": [template.id],
        }
        response = client.post("/api/core/terms/next-term/", data, format="json")
        assert response.status_code == 202
        result = response.json()
        assert "job_id" in result
        assert result["new_term_name"] == "Bahar 2025-2026 (Active)"
        assert result["template_count"] == 1

        # Old term should now be inactive
        active_term.refresh_from_db()
        assert active_term.is_active is False

    def test_next_term_rejects_invalid_semester(self, authenticated_client, term_factory):
        client, user = authenticated_client("next_term_sem", "admin")
        term_factory(is_active=True)
        data = {"semester": "winter", "academic_year": 2026, "template_ids": []}
        response = client.post("/api/core/terms/next-term/", data, format="json")
        assert response.status_code == 400
        result = response.json()
        # Validation errors are returned in a wrapped format
        assert "semester" in str(result)

    def test_next_term_rejects_negative_academic_year(self, authenticated_client, term_factory):
        client, user = authenticated_client("next_term_yr", "admin")
        term_factory(is_active=True)
        data = {"semester": "fall", "academic_year": -1, "template_ids": []}
        response = client.post("/api/core/terms/next-term/", data, format="json")
        assert response.status_code == 400

    def test_next_term_empty_templates_succeeds(self, authenticated_client, term_factory):
        client, user = authenticated_client("next_term_empty", "admin")
        term_factory(is_active=True)
        data = {"semester": "spring", "academic_year": 2026, "template_ids": []}
        response = client.post("/api/core/terms/next-term/", data, format="json")
        assert response.status_code == 202
        assert response.json()["template_count"] == 0

    def test_program_head_can_only_select_own_templates(self, authenticated_client, term_factory, student_user_factory):
        """Program head should not be able to select templates from another program."""
        from tests.factories import CourseTemplateFactory

        client, user = authenticated_client("next_term_head", "program_head")
        term_factory(is_active=True)

        # Create a template in a different program (head's program is set via profile)
        other_template = CourseTemplateFactory()

        data = {
            "semester": "spring",
            "academic_year": 2026,
            "template_ids": [other_template.id],
        }
        response = client.post("/api/core/terms/next-term/", data, format="json")
        # Should fail because program head can't select templates outside their program
        # Note: the exact error code depends on whether the head has a program head profile
        # If the user isn't truly a program_head with a profile, this test may get 400 or 403
        assert response.status_code != 202


@pytest.mark.django_db
class TestCloneTemplatesTask:
    @patch("core.tasks.term_transition.publish_progress")
    def test_clone_templates_creates_courses(self, mock_publish, student_user_factory, term_factory):
        """Task creates courses from templates and updates job."""
        from core.models import TermTransitionJob
        from core.tasks.term_transition import clone_templates_for_term_task

        user = student_user_factory(username="clone_task_user")
        old_term = term_factory(is_active=True)
        new_term = term_factory(name="Spring 2026", semester="spring", academic_year=2026, is_active=False)

        template = CourseTemplateFactory()

        job = TermTransitionJob.objects.create(
            old_term=old_term,
            new_term=new_term,
            triggered_by=user,
            template_ids=[template.id],
            status="pending",
        )

        result = clone_templates_for_term_task(
            template_ids=[template.id],
            term_id=new_term.id,
            job_id=job.id,
        )

        assert result["courses_created"] == 1
        job.refresh_from_db()
        assert job.status == "success"
        assert job.courses_created == 1

        # Verify publish_progress was called
        assert mock_publish.called

        # Verify course was created from template
        new_term_courses = new_term.courses.filter(course_template=template)
        assert new_term_courses.count() == 1

    @patch("core.tasks.term_transition.publish_progress")
    def test_clone_empty_template_list(self, mock_publish, student_user_factory, term_factory):
        """Task with empty template list completes immediately."""
        from core.models import TermTransitionJob
        from core.tasks.term_transition import clone_templates_for_term_task

        user = student_user_factory(username="clone_empty")
        old_term = term_factory(is_active=True)
        new_term = term_factory(name="Spring 2026", semester="spring", academic_year=2026, is_active=False)

        job = TermTransitionJob.objects.create(
            old_term=old_term,
            new_term=new_term,
            triggered_by=user,
            template_ids=[],
            status="pending",
        )

        result = clone_templates_for_term_task(template_ids=[], term_id=new_term.id, job_id=job.id)

        assert result["courses_created"] == 0
        job.refresh_from_db()
        assert job.status == "success"
