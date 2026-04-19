"""
Workflow tests for permissions.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestPermissionWorkflows:
    def test_student_cannot_create_course(self, api_client, fb_student_factory):
        student = fb_student_factory()
        api_client.force_authenticate(user=student)

        course_data = {
            "name": "Hacking Course",
            "code": "HACK101",
        }
        response = api_client.post("/api/v1/core/courses/", course_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_student_can_view_own_scores(self, api_client, fb_student_factory, fb_assessment_factory):
        student = fb_student_factory()
        api_client.force_authenticate(user=student)

        response = api_client.get("/api/v1/core/student-lo-scores/")
        assert response.status_code == status.HTTP_200_OK
