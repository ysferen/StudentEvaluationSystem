#!/usr/bin/env python
"""
Quick test script for permission changes.
Run with: python test_permissions.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_evaluation_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from core.views import CourseViewSet, StudentLearningOutcomeScoreViewSet
from core.models import Course, University, Department, DegreeLevel, Program, Term
from evaluation.models import CourseEnrollment

User = get_user_model()
factory = APIRequestFactory()


def test_student_cannot_access_all_courses():
    """Test that students only see courses they're enrolled in."""
    print("\n🧪 Test: Student Course Access")
    print("-" * 50)
    
    # Create test data
    try:
        student = User.objects.get(username='test_student')
    except User.DoesNotExist:
        print("❌ Create a test user first with: python manage.py shell")
        print("   User.objects.create_user('test_student', password='test123', role='student')")
        return
    
    # Make request
    request = factory.get('/api/core/courses/')
    force_authenticate(request, user=student)
    
    view = CourseViewSet.as_view({'get': 'list'})
    response = view(request)
    
    print(f"   Student: {student.username}")
    print(f"   Response status: {response.status_code}")
    print(f"   Courses count: {len(response.data.get('results', []))}")
    
    # Student should either get 403 or empty list (since not enrolled in any courses)
    if response.status_code == 403:
        print("   ✅ Students cannot access all courses (403 Forbidden)")
    elif response.status_code == 200:
        if len(response.data.get('results', [])) == 0:
            print("   ✅ Students see empty list (not enrolled in any courses)")
        else:
            print("   ⚠️  Students see courses - may need to verify enrollment filter")
    else:
        print(f"   ❌ Unexpected status code: {response.status_code}")


def test_instructor_sees_only_own_courses():
    """Test that instructors only see courses they teach."""
    print("\n🧪 Test: Instructor Course Access")
    print("-" * 50)
    
    try:
        instructor = User.objects.get(username='test_instructor')
    except User.DoesNotExist:
        print("❌ Create a test instructor first")
        return
    
    request = factory.get('/api/core/courses/')
    force_authenticate(request, user=instructor)
    
    view = CourseViewSet.as_view({'get': 'list'})
    response = view(request)
    
    taught_count = instructor.taught_courses.count()
    response_count = len(response.data.get('results', []))
    
    print(f"   Instructor: {instructor.username}")
    print(f"   Courses taught: {taught_count}")
    print(f"   Response courses: {response_count}")
    
    if response.status_code == 200 and taught_count == response_count:
        print("   ✅ Instructors see only their own courses")
    else:
        print(f"   ⚠️  Response status: {response.status_code}")


def test_student_scores_access():
    """Test that students can only see their own scores."""
    print("\n🧪 Test: Student Score Access")
    print("-" * 50)
    
    try:
        student = User.objects.get(username='test_student')
    except User.DoesNotExist:
        print("❌ Create a test student first")
        return
    
    request = factory.get('/api/core/student-lo-scores/')
    force_authenticate(request, user=student)
    
    view = StudentLearningOutcomeScoreViewSet.as_view({'get': 'list'})
    response = view(request)
    
    print(f"   Student: {student.username}")
    print(f"   Response status: {response.status_code}")
    print(f"   Scores returned: {len(response.data.get('results', []))}")
    
    if response.status_code == 200:
        print("   ✅ Students can access scores endpoint")
        
        # Verify all returned scores belong to this student
        scores = response.data.get('results', [])
        all_own_scores = all(
            score.get('student') == student.id 
            for score in scores
        )
        
        if all_own_scores:
            print("   ✅ All returned scores belong to the student")
        else:
            print("   ❌ Some scores belong to other students!")


def run_all_tests():
    """Run all permission tests."""
    print("=" * 60)
    print("PERMISSION TESTS")
    print("=" * 60)
    
    test_student_cannot_access_all_courses()
    test_instructor_sees_only_own_courses()
    test_student_scores_access()
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == '__main__':
    run_all_tests()
