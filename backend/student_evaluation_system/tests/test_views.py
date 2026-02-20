"""
Tests for core app API views and ViewSets.

This module tests the API endpoints in the core app including:
- UniversityViewSet, DepartmentViewSet, DegreeLevelViewSet
- ProgramViewSet, TermViewSet, CourseViewSet
- ProgramOutcomeViewSet, LearningOutcomeViewSet
- LearningOutcomeProgramOutcomeMappingViewSet
- StudentLearningOutcomeScoreViewSet, StudentProgramOutcomeScoreViewSet
- File import ViewSets
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import (
    University, Department, DegreeLevel, Program, Term,
    Course, ProgramOutcome, LearningOutcome,
    LearningOutcomeProgramOutcomeMapping, StudentLearningOutcomeScore
)
from evaluation.models import Assessment, CourseEnrollment
from users.models import StudentProfile


@pytest.mark.django_db
class TestUniversityViewSet:
    """Tests for University API endpoints."""

    def test_list_universities(self, api_client, db_setup):
        """Test GET /api/core/universities/"""
        university = db_setup['university']

        url = reverse('university-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
        assert response.data['results'][0]['name'] == university.name

    def test_retrieve_university(self, api_client, db_setup):
        """Test GET /api/core/universities/{id}/"""
        university = db_setup['university']

        url = reverse('university-detail', kwargs={'pk': university.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == university.name

    def test_create_university(self, authenticated_client):
        """Test POST /api/core/universities/"""
        client, user = authenticated_client('admin', 'admin')

        url = reverse('university-list')
        data = {'name': 'Harvard University'}
        response = client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert University.objects.filter(name='Harvard University').exists()

    def test_update_university(self, authenticated_client, db_setup):
        """Test PUT/PATCH /api/core/universities/{id}/"""
        client, user = authenticated_client('admin', 'admin')
        university = db_setup['university']

        url = reverse('university-detail', kwargs={'pk': university.pk})
        data = {'name': 'Updated University'}
        response = client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        university.refresh_from_db()
        assert university.name == 'Updated University'

    def test_delete_university(self, authenticated_client, db_setup):
        """Test DELETE /api/core/universities/{id}/"""
        client, user = authenticated_client('admin', 'admin')
        university = db_setup['university']

        url = reverse('university-detail', kwargs={'pk': university.pk})
        response = client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not University.objects.filter(pk=university.pk).exists()


@pytest.mark.django_db
class TestDepartmentViewSet:
    """Tests for Department API endpoints."""

    def test_list_departments(self, api_client, db_setup):
        """Test GET /api/core/departments/"""
        department = db_setup['department']

        url = reverse('department-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
        assert response.data['results'][0]['code'] == department.code

    def test_filter_departments_by_university(self, api_client, db_setup):
        """Test GET /api/core/departments/?university={id}"""
        university = db_setup['university']
        department = db_setup['department']

        url = reverse('department-list')
        response = api_client.get(url, {'university': university.pk})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
        assert response.data['results'][0]['code'] == department.code

@pytest.mark.django_db
class TestProgramViewSet:
    """Tests for Program API endpoints."""

    def test_list_programs(self, api_client, db_setup):
        """Test GET /api/core/programs/"""
        program = db_setup['program']

        url = reverse('program-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
        assert response.data['results'][0]['code'] == program.code

    def test_filter_programs_by_department(self, api_client, db_setup):
        """Test GET /api/core/programs/?department={id}"""
        department = db_setup['department']
        program = db_setup['program']

        url = reverse('program-list')
        response = api_client.get(url, {'department': department.pk})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_filter_programs_by_degree_level(self, api_client, db_setup):
        """Test GET /api/core/programs/?degree_level={id}"""
        degree_level = db_setup['degree_level']
        program = db_setup['program']

        url = reverse('program-list')
        response = api_client.get(url, {'degree_level': degree_level.pk})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1


@pytest.mark.django_db
class TestTermViewSet:
    """Tests for Term API endpoints."""

    def test_list_terms(self, api_client, db_setup):
        """Test GET /api/core/terms/"""
        term = db_setup['term']

        url = reverse('term-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
        assert response.data['results'][0]['name'] == term.name

    def test_get_active_term(self, api_client, db_setup):
        """Test GET /api/core/terms/active/"""
        term = db_setup['term']
        term.is_active = True
        term.save()

        url = reverse('term-active')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == term.name
        assert response.data['is_active'] is True

    def test_get_active_term_when_none_active(self, api_client, db_setup):
        """Test GET /api/core/terms/active/ when no term is active."""
        db_setup['term'].is_active = False
        db_setup['term'].save()

        url = reverse('term-active')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCourseViewSet:
    """Tests for Course API endpoints."""

    def test_list_courses(self, api_client, db_setup):
        """Test GET /api/core/courses/"""
        course = db_setup['course']

        url = reverse('course-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
        assert response.data['results'][0]['code'] == course.code

    def test_filter_courses_by_term(self, api_client, db_setup):
        """Test GET /api/core/courses/?term={id}"""
        term = db_setup['term']
        course = db_setup['course']

        url = reverse('course-list')
        response = api_client.get(url, {'term': term.pk})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_filter_courses_by_instructor(self, api_client, db_setup, instructor_factory):
        """Test GET /api/core/courses/?instructor={id}"""
        course = db_setup['course']
        instructor = instructor_factory('instructor1')
        course.instructors.add(instructor.user)

        url = reverse('course-list')
        response = api_client.get(url, {'instructor': instructor.user.pk})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_get_course_learning_outcomes(self, api_client, sample_course):
        """Test GET /api/core/courses/{id}/learning_outcomes/"""
        course = sample_course['course']

        url = reverse('course-learning-outcomes', kwargs={'pk': course.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2  # 2 LOs created in fixture


@pytest.mark.django_db
class TestProgramOutcomeViewSet:
    """Tests for ProgramOutcome API endpoints."""

    def test_list_program_outcomes(self, api_client, sample_course):
        """Test GET /api/core/program-outcomes/"""
        pos = sample_course['program_outcomes']

        url = reverse('program-outcome-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_filter_pos_by_term(self, api_client, sample_course):
        """Test GET /api/core/program-outcomes/?term={id}"""
        term = sample_course['course'].term

        url = reverse('program-outcome-list')
        response = api_client.get(url, {'term': term.pk})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1


@pytest.mark.django_db
class TestLearningOutcomeViewSet:
    """Tests for LearningOutcome API endpoints."""

    def test_list_learning_outcomes(self, api_client, sample_course):
        """Test GET /api/core/learning-outcomes/"""
        los = sample_course['learning_outcomes']

        url = reverse('learning-outcome-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_filter_los_by_course(self, api_client, sample_course):
        """Test GET /api/core/learning-outcomes/?course={id}"""
        course = sample_course['course']

        url = reverse('learning-outcome-list')
        response = api_client.get(url, {'course': course.pk})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2  # 2 LOs created in fixture


@pytest.mark.django_db
class TestLearningOutcomeProgramOutcomeMappingViewSet:
    """Tests for LO-PO Mapping API endpoints."""

    def test_list_mappings(self, api_client, sample_course):
        """Test GET /api/core/lo-po-mappings/"""
        mappings = sample_course['mappings']

        url = reverse('lo-po-mapping-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    def test_filter_mappings_by_course(self, api_client, sample_course):
        """Test GET /api/core/lo-po-mappings/?course={id}"""
        course = sample_course['course']

        url = reverse('lo-po-mapping-list')
        response = api_client.get(url, {'course': course.pk})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 4  # 4 mappings created in fixture

    def test_create_mapping(self, authenticated_client, sample_course):
        """Test POST /api/core/lo-po-mappings/"""
        client, user = authenticated_client('admin', 'admin')
        course = sample_course['course']
        
        # Create a new LO and PO that don't have existing mappings
        term = course.term
        program = course.program
        
        lo = LearningOutcome.objects.create(
            code="LO3",
            description="New Learning Outcome for testing",
            course=course
        )
        po = ProgramOutcome.objects.create(
            code="PO3",
            description="New Program Outcome for testing",
            program=program,
            term=term
        )

        url = reverse('lo-po-mapping-list')
        data = {
            'course': course.pk,
            'learning_outcome_id': lo.pk,
            'program_outcome_id': po.pk,
            'weight': 0.8
        }
        response = client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert LearningOutcomeProgramOutcomeMapping.objects.filter(
            course=course,
            learning_outcome=lo,
            program_outcome=po
        ).exists()


@pytest.mark.django_db
class TestStudentLearningOutcomeScoreViewSet:
    """Tests for Student LO Score API endpoints."""

    def test_list_student_lo_scores(self, api_client, sample_course, student_factory):
        """Test GET /api/core/student-lo-scores/"""
        lo = sample_course['learning_outcomes'][0]
        student = student_factory('student1')

        StudentLearningOutcomeScore.objects.create(
            student=student.user,
            learning_outcome=lo,
            score=85.0
        )

        url = reverse('student-lo-score-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_filter_scores_by_student(self, api_client, sample_course, student_factory):
        """Test GET /api/core/student-lo-scores/?student={id}"""
        lo = sample_course['learning_outcomes'][0]
        student = student_factory('student1')

        StudentLearningOutcomeScore.objects.create(
            student=student.user,
            learning_outcome=lo,
            score=90.0
        )

        url = reverse('student-lo-score-list')
        response = api_client.get(url, {'student': student.user.pk})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_filter_scores_by_course(self, api_client, sample_course, student_factory):
        """Test GET /api/core/student-lo-scores/?course={id}"""
        course = sample_course['course']
        lo = sample_course['learning_outcomes'][0]
        student = student_factory('student1')

        StudentLearningOutcomeScore.objects.create(
            student=student.user,
            learning_outcome=lo,
            score=88.0
        )

        url = reverse('student-lo-score-list')
        response = api_client.get(url, {'course': course.pk})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_get_course_averages(self, api_client, sample_course, sample_enrollment, assessment_lo_mappings):
        """Test GET /api/core/student-lo-scores/course_averages/"""
        from evaluation.services import calculate_course_scores

        course = sample_course['course']

        # Calculate scores first
        calculate_course_scores(course.pk)

        url = reverse('student-lo-score-course-averages')
        response = api_client.get(url, {'course': course.pk})

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) >= 1

    def test_get_course_averages_requires_parameter(self, api_client):
        """Test that course_averages requires either student or course parameter."""
        url = reverse('student-lo-score-course-averages')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data


@pytest.mark.django_db
class TestStudentProgramOutcomeScoreViewSet:
    """Tests for Student PO Score API endpoints."""

    def test_list_student_po_scores(self, api_client, db_setup, student_factory):
        """Test GET /api/core/student-po-scores/"""
        program = db_setup['program']
        term = db_setup['term']
        student = student_factory('student1')

        po = ProgramOutcome.objects.create(
            code="PO1",
            description="Test PO",
            program=program,
            term=term
        )

        from core.models import StudentProgramOutcomeScore
        StudentProgramOutcomeScore.objects.create(
            student=student.user,
            program_outcome=po,
            score=85.0,
            term=term
        )

        url = reverse('student-po-score-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1


@pytest.mark.django_db
class TestFileImportEndpoints:
    """Tests for file import endpoints."""

    def test_assignment_scores_upload_get_info(self, api_client):
        """Test GET /api/core/file-import/assignment-scores/upload/"""
        url = reverse('file-import-assignment-scores-upload')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        assert 'required_query_parameters' in response.data

    def test_assignment_scores_upload_no_file(self, authenticated_client):
        """Test POST without file returns error."""
        client, user = authenticated_client('instructor', 'instructor')
        
        url = reverse('file-import-assignment-scores-upload')
        response = client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_assignment_scores_upload_missing_course_code(self, authenticated_client, db_setup):
        """Test POST without course_code returns error."""
        from io import BytesIO
        import pandas as pd

        client, user = authenticated_client('instructor', 'instructor')

        # Create dummy Excel file
        df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})
        buffer = BytesIO()
        df.to_excel(buffer, engine='openpyxl')
        buffer.seek(0)

        url = reverse('file-import-assignment-scores-upload')
        response = client.post(
            url,
            {'file': buffer},
            format='multipart'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'course_code' in response.data['error']

    def test_learning_outcomes_upload_get_info(self, api_client):
        """Test GET /api/core/file-import/learning-outcomes/upload/"""
        url = reverse('file-import-learning-outcomes-upload')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data

    def test_program_outcomes_upload_get_info(self, api_client):
        """Test GET /api/core/file-import/program-outcomes/upload/"""
        url = reverse('file-import-program-outcomes-upload')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
