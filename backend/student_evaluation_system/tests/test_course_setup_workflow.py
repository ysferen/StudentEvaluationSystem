"""
Workflow tests for course setup.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestCourseSetupWorkflow:
    def test_head_creates_course_with_outcomes(self, api_client, fb_admin_factory):
        admin = fb_admin_factory()
        api_client.force_authenticate(user=admin)

        uni_data = {"name": "Test University", "code": "TU"}
        response = api_client.post("/api/v1/core/universities/", uni_data)
        assert response.status_code == status.HTTP_201_CREATED
        uni_id = response.data["id"]

        dept_data = {"name": "CS", "code": "CS", "university": uni_id}
        response = api_client.post("/api/v1/core/departments/", dept_data)
        assert response.status_code == status.HTTP_201_CREATED
        dept_id = response.data["id"]

        from core.models import DegreeLevel

        degree = DegreeLevel.objects.create(name="Bachelor", level=1)

        prog_data = {
            "name": "Computer Science",
            "code": "CS-BS",
            "department": dept_id,
            "degree_level": degree.id,
        }
        response = api_client.post("/api/v1/core/programs/", prog_data)
        assert response.status_code == status.HTTP_201_CREATED
