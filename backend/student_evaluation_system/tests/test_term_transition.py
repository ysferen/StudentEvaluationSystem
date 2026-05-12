import pytest
from core.models import TermTransitionJob


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
