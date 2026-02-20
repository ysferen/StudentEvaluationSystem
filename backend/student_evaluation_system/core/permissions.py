"""
Custom permission classes for the Student Evaluation System.

These permissions implement role-based access control (RBAC) ensuring:
- Students can only access their own data
- Instructors can only access their course data
- Admins have full access
- Department heads can access department-level data
"""

from rest_framework import permissions
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdmin(BasePermission):
    """Allow access only to admin users."""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_admin_user
        )


class IsInstructor(BasePermission):
    """Allow access only to instructor users."""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_instructor
        )


class IsStudent(BasePermission):
    """Allow access only to student users."""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_student
        )


class IsOwner(BasePermission):
    """
    Allow access only to the owner of the object.
    
    For objects with a 'user' or 'student' field that matches the current user.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check for various owner field names
        owner = getattr(obj, 'user', None) or getattr(obj, 'student', None)
        return owner == request.user


class IsInstructorOfCourse(BasePermission):
    """
    Allow access only to instructors of a specific course.
    
    Object must have a 'course' attribute or be a Course itself.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_instructor or request.user.is_admin_user
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin_user:
            return True
        
        # Get the course from the object
        course = getattr(obj, 'course', None) or obj
        
        # Check if user is an instructor of this course
        if hasattr(course, 'instructors'):
            return course.instructors.filter(id=request.user.id).exists()
        
        return False


class IsInstructorOfStudent(BasePermission):
    """
    Allow access to students that are enrolled in the instructor's courses.
    
    Used for grade access - instructors can see grades of students in their courses.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_instructor or request.user.is_admin_user
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin_user:
            return True
        
        # Get the student from the object
        student = getattr(obj, 'student', None) or getattr(obj, 'user', None)
        if not student:
            return False
        
        # Check if student is enrolled in any of the instructor's courses
        from evaluation.models import CourseEnrollment
        instructor_course_ids = request.user.taught_courses.values_list('id', flat=True)
        return CourseEnrollment.objects.filter(
            student=student,
            course_id__in=instructor_course_ids
        ).exists()


class ReadOnly(BasePermission):
    """Allow only read-only access (GET, HEAD, OPTIONS)."""
    
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class IsAdminOrReadOnly(BasePermission):
    """
    Allow read access to anyone, but write access only to admins.
    
    Useful for reference data like Universities, Departments.
    """
    
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_admin_user
        )


class IsOwnerOrInstructorOrAdmin(BasePermission):
    """
    Allow access if:
    - User is the owner (student)
    - User is an instructor of the student's course
    - User is an admin
    
    Primary permission for student-specific data (grades, scores).
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Admin has full access
        if user.is_admin_user:
            return True
        
        # Check if user owns this data
        owner = getattr(obj, 'user', None) or getattr(obj, 'student', None)
        if owner == user:
            return True
        
        # Instructors can see data for students in their courses
        if user.is_instructor:
            student = owner
            if student:
                from evaluation.models import CourseEnrollment
                instructor_course_ids = user.taught_courses.values_list('id', flat=True)
                return CourseEnrollment.objects.filter(
                    student=student,
                    course_id__in=instructor_course_ids
                ).exists()
        
        return False


class IsInstructorOrAdmin(BasePermission):
    """
    Allow access to instructors and admins.
    Used for course management endpoints.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_instructor or request.user.is_admin_user


class IsDepartmentHead(BasePermission):
    """
    Allow access to department heads.
    Can access all courses and data within their department.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # For now, treat admins as department heads
        # In future, could add a 'department_head' role
        return request.user.is_admin_user


class CanAccessStudentData(BasePermission):
    """
    Permission to access a specific student's data.
    
    Students: only their own data
    Instructors: students in their courses
    Admins: all students
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Admin access
        if user.is_admin_user:
            return True
        
        # Get student from object
        student = getattr(obj, 'student', None)
        if not student and hasattr(obj, 'user'):
            # Object might be the student profile itself
            student = obj
        
        if not student:
            return False
        
        # Own data
        if hasattr(student, 'user'):
            if student.user == user:
                return True
        elif student == user:
            return True
        
        # Instructor access to their students
        if user.is_instructor:
            from evaluation.models import CourseEnrollment
            instructor_course_ids = user.taught_courses.values_list('id', flat=True)
            student_user = getattr(student, 'user', student)
            return CourseEnrollment.objects.filter(
                student=student_user,
                course_id__in=instructor_course_ids
            ).exists()
        
        return False
