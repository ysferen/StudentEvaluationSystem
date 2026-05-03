"""
TDD tests for the weight suggestion REST endpoint.

These tests define the expected API contract BEFORE the endpoint exists.
All tests should FAIL on first run, then pass after implementation.
"""

from django.urls import reverse
from rest_framework import status
from unittest.mock import patch


ENDPOINT_LIST = "weightsuggestion-list"
ENDPOINT_DETAIL = "weightsuggestion-detail"


def _post_body(course_id=1):
    return {"course_id": course_id}


class TestWeightSuggestionCreate:
    """POST /api/v1/core/weight-suggestion/"""

    def test_create_requires_authentication(self, api_client):
        """Unauthenticated users should get 401."""
        url = reverse(ENDPOINT_LIST)
        response = api_client.post(url, _post_body(), format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_by_student_returns_403(self, api_client, student_factory):
        """Students cannot trigger weight suggestion."""
        student = student_factory("ws_student")
        api_client.force_authenticate(user=student.user)
        url = reverse(ENDPOINT_LIST)
        response = api_client.post(url, _post_body(), format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_by_instructor_returns_201(self, api_client, instructor_factory, course_with_los):
        """Instructors can trigger weight suggestion -- returns job id."""
        instructor = instructor_factory("ws_instructor")
        api_client.force_authenticate(user=instructor.user)
        url = reverse(ENDPOINT_LIST)
        response = api_client.post(url, _post_body(course_id=course_with_los["course"].id), format="json")
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"

    def test_create_by_admin_returns_201(self, api_client, admin_user_factory, course_with_los):
        """Admins can trigger weight suggestion."""
        admin_cls = admin_user_factory
        admin = admin_cls(username="ws_admin")
        api_client.force_authenticate(user=admin)
        url = reverse(ENDPOINT_LIST)
        response = api_client.post(url, _post_body(course_id=course_with_los["course"].id), format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_queues_celery_task(self, api_client, instructor_factory, course_with_los):
        """The POST should call task.delay() with the right args."""
        instructor = instructor_factory("ws_instructor2")
        api_client.force_authenticate(user=instructor.user)

        with patch("core.views.weight_suggestion.suggest_assessment_lo_weights_task.delay") as mock_delay:
            mock_delay.return_value.id = "fake-task-id-123"
            url = reverse(ENDPOINT_LIST)
            response = api_client.post(
                url,
                _post_body(course_id=course_with_los["course"].id),
                format="json",
            )

            assert response.status_code == status.HTTP_201_CREATED
            mock_delay.assert_called_once()
            call_kwargs = mock_delay.call_args[1]
            assert call_kwargs["course_id"] == course_with_los["course"].id

    def test_create_requires_course_id(self, api_client, instructor_factory):
        """POST without course_id should return 400."""
        instructor = instructor_factory("ws_instructor3")
        api_client.force_authenticate(user=instructor.user)
        url = reverse(ENDPOINT_LIST)
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestWeightSuggestionDetail:
    """GET /api/v1/core/weight-suggestion/<id>/"""

    def test_detail_requires_authentication(self, api_client, weight_suggestion_job_factory):
        """Unauthenticated users should get 401."""
        job = weight_suggestion_job_factory()
        url = reverse(ENDPOINT_DETAIL, args=[job.id])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_detail_returns_job_data(self, api_client, instructor_factory, weight_suggestion_job_factory):
        """GET should return full job detail including result."""
        instructor = instructor_factory("ws_instructor4")
        api_client.force_authenticate(user=instructor.user)

        job = weight_suggestion_job_factory(
            status="success",
            result={"assessment_lo": {"Midterm": {"LO1": 3, "LO2": 4}}},
        )
        url = reverse(ENDPOINT_DETAIL, args=[job.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == job.id
        assert data["status"] == "success"
        assert data["result"] == {"assessment_lo": {"Midterm": {"LO1": 3, "LO2": 4}}}

    def test_detail_404_for_missing_job(self, api_client, instructor_factory):
        """Non-existent job should return 404."""
        instructor = instructor_factory("ws_instructor5")
        api_client.force_authenticate(user=instructor.user)
        url = reverse(ENDPOINT_DETAIL, args=[99999])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_shows_failed_status(self, api_client, instructor_factory, weight_suggestion_job_factory):
        """Failed job should show error text."""
        instructor = instructor_factory("ws_instructor6")
        api_client.force_authenticate(user=instructor.user)

        job = weight_suggestion_job_factory(
            status="failed",
            error="Course not found",
        )
        url = reverse(ENDPOINT_DETAIL, args=[job.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Course not found"
        assert data["result"] is None
