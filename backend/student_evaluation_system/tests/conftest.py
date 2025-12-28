"""
Shared pytest fixtures for Student Evaluation System tests.

This module provides common fixtures used across all test modules.
"""

import pytest
from datetime import date


@pytest.fixture
def api_client():
    """
    Returns an instance of DRF's APIClient for making API requests.
    """
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def db_setup(db):
    """
    Sets up basic database objects for testing.

    Creates a university, department, degree level, program, term, and course.
    Returns a dictionary containing all created objects.
    """
    from core.models import (
        University, Department, DegreeLevel, Program, Term, Course
    )
    
    # Create university
    university = University.objects.create(name="Test University")

    # Create department
    department = Department.objects.create(
        code="TEST",
        name="Test Department",
        university=university
    )

    # Create degree level
    degree_level = DegreeLevel.objects.create(name="Bachelor's")

    # Create program
    program = Program.objects.create(
        code="TESTPROG",
        name="Test Program",
        degree_level=degree_level,
        department=department
    )

    # Create term
    term = Term.objects.create(name="Fall 2025", is_active=True)

    # Create course
    course = Course.objects.create(
        code="TEST101",
        name="Test Course",
        credits=3,
        program=program,
        term=term
    )

    return {
        'university': university,
        'department': department,
        'degree_level': degree_level,
        'program': program,
        'term': term,
        'course': course
    }


@pytest.fixture
def user_factory(db_setup):
    """
    Factory fixture for creating users.

    Usage:
        user = user_factory('username', 'student')
        instructor = user_factory('instructor', 'instructor')
    """
    from django.contrib.auth import get_user_model
    from users.models import StudentProfile, InstructorProfile
    
    User = get_user_model()

    def _create_user(username, role='student', **kwargs):
        university = db_setup['university']
        department = db_setup['department']

        defaults = {
            'username': username,
            'email': f'{username}@test.com',
            'first_name': 'Test',
            'last_name': 'User',
            'role': role,
            'university': university,
            'department': department,
        }
        defaults.update(kwargs)

        user = User.objects.create_user(
            username=defaults['username'],
            email=defaults['email'],
            password='testpass123',
            first_name=defaults['first_name'],
            last_name=defaults['last_name'],
            role=defaults['role'],
            university=defaults['university'],
            department=defaults['department']
        )

        return user

    return _create_user


@pytest.fixture
def student_factory(db_setup, user_factory):
    """
    Factory fixture for creating students with profiles.

    Usage:
        student = student_factory('student1')
        student_with_program = student_factory('student2', program_id=1)
    """
    from users.models import StudentProfile
    
    def _create_student(username, **kwargs):
        term = db_setup['term']
        program = db_setup['program']

        defaults = {
            'student_id': f'S{username.upper()}',
            'enrollment_term': term,
            'program': program
        }
        defaults.update(kwargs)

        # Create user with student role
        user = user_factory(username, role='student')

        # Create student profile
        student = StudentProfile.objects.create(
            user=user,
            **defaults
        )

        return student

    return _create_student


@pytest.fixture
def instructor_factory(db_setup, user_factory):
    """
    Factory fixture for creating instructors with profiles.

    Usage:
        instructor = instructor_factory('instructor1')
    """
    from users.models import InstructorProfile
    
    def _create_instructor(username, title='Professor', **kwargs):
        # Create user with instructor role
        user = user_factory(username, role='instructor', **kwargs)

        # Create instructor profile
        instructor = InstructorProfile.objects.create(
            user=user,
            title=title
        )

        return instructor

    return _create_instructor


@pytest.fixture
def authenticated_client(api_client, user_factory):
    """
    Returns an authenticated API client.

    Usage:
        client = authenticated_client('student', 'student')
    """
    def _create_client(username, role='student'):
        user = user_factory(username, role=role)
        api_client.force_authenticate(user=user)
        return api_client, user

    return _create_client


@pytest.fixture
def sample_course(db_setup):
    """
    Creates a sample course with learning outcomes and program outcomes.

    Returns a dictionary with course, LOS, and POs.
    """
    from core.models import (
        ProgramOutcome, LearningOutcome, LearningOutcomeProgramOutcomeMapping
    )
    
    course = db_setup['course']
    term = db_setup['term']
    program = db_setup['program']

    # Create program outcomes
    po1 = ProgramOutcome.objects.create(
        code="PO1",
        description="Engineering Knowledge",
        program=program,
        term=term
    )
    po2 = ProgramOutcome.objects.create(
        code="PO2",
        description="Problem Analysis",
        program=program,
        term=term
    )

    # Create learning outcomes
    lo1 = LearningOutcome.objects.create(
        code="LO1",
        description="Apply knowledge of mathematics",
        course=course
    )
    lo2 = LearningOutcome.objects.create(
        code="LO2",
        description="Identify and formulate problems",
        course=course
    )

    # Create LO-PO mappings
    LearningOutcomeProgramOutcomeMapping.objects.create(
        course=course,
        learning_outcome=lo1,
        program_outcome=po1,
        weight=0.6
    )
    LearningOutcomeProgramOutcomeMapping.objects.create(
        course=course,
        learning_outcome=lo1,
        program_outcome=po2,
        weight=0.4
    )
    LearningOutcomeProgramOutcomeMapping.objects.create(
        course=course,
        learning_outcome=lo2,
        program_outcome=po1,
        weight=0.3
    )
    LearningOutcomeProgramOutcomeMapping.objects.create(
        course=course,
        learning_outcome=lo2,
        program_outcome=po2,
        weight=0.7
    )

    return {
        'course': course,
        'program_outcomes': [po1, po2],
        'learning_outcomes': [lo1, lo2],
        'mappings': LearningOutcomeProgramOutcomeMapping.objects.filter(course=course)
    }


@pytest.fixture
def sample_assessments(sample_course):
    """
    Creates sample assessments for a course.

    Returns a dictionary with course and assessments.
    """
    from evaluation.models import Assessment
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    course = sample_course['course']

    # Get or create an instructor user
    user, created = User.objects.get_or_create(
        username='test_instructor',
        defaults={
            'email': 'instructor@test.com',
            'first_name': 'Test',
            'last_name': 'Instructor',
            'role': 'instructor',
            'password': 'testpass123'
        }
    )

    # Create assessments
    midterm = Assessment.objects.create(
        name="Midterm Exam",
        assessment_type="midterm",
        course=course,
        date=date.today(),
        total_score=100,
        weight=0.3,
        created_by=user
    )

    final = Assessment.objects.create(
        name="Final Exam",
        assessment_type="final",
        course=course,
        date=date.today(),
        total_score=100,
        weight=0.4,
        created_by=user
    )

    project = Assessment.objects.create(
        name="Project",
        assessment_type="project",
        course=course,
        date=date.today(),
        total_score=100,
        weight=0.3,
        created_by=user
    )

    return {
        'course': course,
        'assessments': [midterm, final, project],
        'midterm': midterm,
        'final': final,
        'project': project
    }


@pytest.fixture
def sample_enrollment(sample_course, student_factory):
    """
    Creates sample course enrollments.

    Returns a dictionary with course and enrolled students.
    """
    from evaluation.models import CourseEnrollment
    
    course = sample_course['course']

    # Create students
    student1 = student_factory('student1')
    student2 = student_factory('student2')
    student3 = student_factory('student3')

    # Enroll students in course
    enrollment1 = CourseEnrollment.objects.create(student=student1.user, course=course)
    enrollment2 = CourseEnrollment.objects.create(student=student2.user, course=course)
    enrollment3 = CourseEnrollment.objects.create(student=student3.user, course=course)

    return {
        'course': course,
        'students': [student1, student2, student3],
        'enrollments': [enrollment1, enrollment2, enrollment3]
    }


@pytest.fixture
def sample_grades(sample_assessments, sample_enrollment):
    """
    Creates sample student grades.

    Returns a dictionary with assessments, students, and grades.
    """
    from evaluation.models import StudentGrade
    
    assessments = sample_assessments['assessments']
    students = sample_enrollment['students']

    grades = []
    for student in students:
        for assessment in assessments:
            grade = StudentGrade.objects.create(
                student=student.user,
                assessment=assessment,
                score=85.0
            )
            grades.append(grade)

    return {
        'assessments': assessments,
        'students': students,
        'grades': grades
    }


@pytest.fixture
def assessment_lo_mappings(sample_assessments, sample_course):
    """
    Creates assessment-LO mappings.

    Returns a dictionary with mappings.
    """
    from evaluation.models import AssessmentLearningOutcomeMapping
    
    assessments = sample_assessments['assessments']
    learning_outcomes = sample_course['learning_outcomes']

    mappings = []
    for assessment in assessments:
        for lo in learning_outcomes:
            mapping = AssessmentLearningOutcomeMapping.objects.create(
                assessment=assessment,
                learning_outcome=lo,
                weight=0.5
            )
            mappings.append(mapping)

    return {
        'mappings': mappings,
        'assessments': assessments,
        'learning_outcomes': learning_outcomes
    }


# Add this at the end of your conftest.py to ensure Django is setup
def pytest_configure():
    """Configure Django for pytest."""
    import os
    import django
    from django.conf import settings

    # Set the Django settings module environment variable
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_evaluation_system.settings')
    
    # Configure Django if not already configured
    if not settings.configured:
        django.setup()