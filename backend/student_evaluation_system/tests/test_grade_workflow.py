"""
Workflow tests for instructor grade entry.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestStudentGradeWorkflow:
    def test_instructor_creates_assessment_and_grades(
        self, api_client, fb_instructor_factory, fb_student_factory, fb_course_factory
    ):
        instructor = fb_instructor_factory()
        course = fb_course_factory(instructor=instructor)
        student = fb_student_factory()

        from evaluation.models import CourseEnrollment

        CourseEnrollment.objects.create(student=student, course=course)

        api_client.force_authenticate(user=instructor)

        assessment_data = {
            "name": "Final Exam",
            "course": course.id,
            "assessment_type": "final",
            "total_score": 100,
            "weight": 0.4,
        }
        response = api_client.post("/api/v1/evaluation/assessments/", assessment_data)
        assert response.status_code == status.HTTP_201_CREATED
        assessment_id = response.data["id"]

        grade_data = {
            "student": student.id,
            "assessment": assessment_id,
            "score": 85.0,
        }
        response = api_client.post("/api/v1/evaluation/grades/", grade_data)
        assert response.status_code == status.HTTP_201_CREATED

        response = api_client.get(f"/api/v1/evaluation/grades/?student={student.id}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
