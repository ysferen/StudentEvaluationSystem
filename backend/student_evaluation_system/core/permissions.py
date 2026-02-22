"""
Custom permission classes for the Student Evaluation System.

These permissions implement role-based access control (RBAC) ensuring:
- Students can only access their own data
- Instructors can only access their course data
- Admins have full access
- Department heads can access department-level data

All permission classes follow DRF's BasePermission interface with
has_permission() for view-level checks and has_object_permission()
for object-level checks.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.views import APIView
from rest_framework.request import Request
from typing import Any


# Type alias for view type
ViewType = APIView


class IsAdmin(BasePermission):
    """
    Allow access only to admin users.

    Checks the user's is_admin_user property to determine admin status.
    """

    def has_permission(self, request: Request, view: ViewType) -> bool:
        """
        Check if the user is an admin.

        Args:
            request: The incoming request
            view: The view being accessed

        Returns:
            True if user is authenticated and has admin role
        """
        return request.user and request.user.is_authenticated and request.user.is_admin_user


class IsInstructor(BasePermission):
    """
    Allow access only to instructor users.

    Checks the user's is_instructor property to determine instructor status.
    """

    def has_permission(self, request: Request, view: ViewType) -> bool:
        """
        Check if the user is an instructor.

        Args:
            request: The incoming request
            view: The view being accessed

        Returns:
            True if user is authenticated and has instructor role
        """
        return request.user and request.user.is_authenticated and request.user.is_instructor


class IsStudent(BasePermission):
    """
    Allow access only to student users.

    Checks the user's is_student property to determine student status.
    """

    def has_permission(self, request: Request, view: ViewType) -> bool:
        """
        Check if the user is a student.

        Args:
            request: The incoming request
            view: The view being accessed

        Returns:
            True if user is authenticated and has student role
        """
        return request.user and request.user.is_authenticated and request.user.is_student


class IsOwner(BasePermission):
    """
    Allow access only to the owner of the object.

    For objects with a 'user' or 'student' field that matches the current user.
    """

    def has_object_permission(self, request: Request, view: ViewType, obj: Any) -> bool:
        """
        Check if the requesting user owns the object.

        Args:
            request: The incoming request
            view: The view being accessed
            obj: The object being accessed

        Returns:
            True if the object's user/student matches the requesting user
        """
        # Check for various owner field names
        owner = getattr(obj, "user", None) or getattr(obj, "student", None)
        return owner == request.user


class IsInstructorOfCourse(BasePermission):
    """
    Allow access only to instructors of a specific course.

    Object must have a 'course' attribute or be a Course itself.
    Admins always have access.
    """

    def has_permission(self, request: Request, view: ViewType) -> bool:
        """
        Check basic permission - user must be instructor or admin.

        Args:
            request: The incoming request
            view: The view being accessed

        Returns:
            True if user is authenticated and is instructor or admin
        """
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_instructor or request.user.is_admin_user

    def has_object_permission(self, request: Request, view: ViewType, obj: Any) -> bool:
        """
        Check if user is instructor of the object's course.

        Args:
            request: The incoming request
            view: The view being accessed
            obj: The object being accessed (must have course attribute or be Course)

        Returns:
            True if user is admin or instructor of the course
        """
        if request.user.is_admin_user:
            return True

        # Get the course from the object
        course = getattr(obj, "course", None) or obj

        # Check if user is an instructor of this course
        if hasattr(course, "instructors"):
            return course.instructors.filter(id=request.user.id).exists()

        return False


class IsInstructorOfStudent(BasePermission):
    """
    Allow access to students that are enrolled in the instructor's courses.

    Used for grade access - instructors can see grades of students in their courses.
    Admins always have access.
    """

    def has_permission(self, request: Request, view: ViewType) -> bool:
        """
        Check basic permission - user must be instructor or admin.

        Args:
            request: The incoming request
            view: The view being accessed

        Returns:
            True if user is authenticated and is instructor or admin
        """
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_instructor or request.user.is_admin_user

    def has_object_permission(self, request: Request, view: ViewType, obj: Any) -> bool:
        """
        Check if student is enrolled in instructor's courses.

        Args:
            request: The incoming request
            view: The view being accessed
            obj: The object being accessed (must have student or user attribute)

        Returns:
            True if user is admin or student is in instructor's course
        """
        if request.user.is_admin_user:
            return True

        # Get the student from the object
        student = getattr(obj, "student", None) or getattr(obj, "user", None)
        if not student:
            return False

        # Check if student is enrolled in any of the instructor's courses
        from evaluation.models import CourseEnrollment

        instructor_course_ids = request.user.taught_courses.values_list("id", flat=True)
        return CourseEnrollment.objects.filter(student=student, course_id__in=instructor_course_ids).exists()


class ReadOnly(BasePermission):
    """
    Allow only read-only access (GET, HEAD, OPTIONS).

    Useful for publicly readable resources.
    """

    def has_permission(self, request: Request, view: ViewType) -> bool:
        """
        Check if request method is read-only.

        Args:
            request: The incoming request
            view: The view being accessed

        Returns:
            True if method is GET, HEAD, or OPTIONS
        """
        return request.method in SAFE_METHODS


class IsAdminOrReadOnly(BasePermission):
    """
    Allow read access to anyone, but write access only to admins.

    Useful for reference data like Universities, Departments where
    public read access is acceptable but modifications require admin privileges.
    """

    def has_permission(self, request: Request, view: ViewType) -> bool:
        """
        Check permission based on request method.

        Args:
            request: The incoming request
            view: The view being accessed

        Returns:
            True for safe methods, or if user is authenticated admin
        """
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.is_admin_user


class IsOwnerOrInstructorOrAdmin(BasePermission):
    """
    Allow access if user is the owner, an instructor of the student, or an admin.

    This is the primary permission for student-specific data (grades, scores).
    Access hierarchy:
    1. Admin: Full access to all data
    2. Owner: Students can access their own data
    3. Instructor: Can access data for students in their courses
    """

    def has_permission(self, request: Request, view: ViewType) -> bool:
        """
        Check basic authentication.

        Args:
            request: The incoming request
            view: The view being accessed

        Returns:
            True if user is authenticated
        """
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request: Request, view: ViewType, obj: Any) -> bool:
        """
        Check object-level permissions.

        Args:
            request: The incoming request
            view: The view being accessed
            obj: The object being accessed

        Returns:
            True if user is admin, owner, or instructor of the student
        """
        user = request.user

        # Admin has full access
        if user.is_admin_user:
            return True

        # Check if user owns this data
        owner = getattr(obj, "user", None) or getattr(obj, "student", None)
        if owner == user:
            return True

        # Instructors can see data for students in their courses
        if user.is_instructor:
            student = owner
            if student:
                from evaluation.models import CourseEnrollment

                instructor_course_ids = user.taught_courses.values_list("id", flat=True)
                return CourseEnrollment.objects.filter(student=student, course_id__in=instructor_course_ids).exists()

        return False


class IsInstructorOrAdmin(BasePermission):
    """
    Allow access to instructors and admins.

    Used for course management endpoints where both instructors and
    administrators need access.
    """

    def has_permission(self, request: Request, view: ViewType) -> bool:
        """
        Check if user is instructor or admin.

        Args:
            request: The incoming request
            view: The view being accessed

        Returns:
            True if user is authenticated and is instructor or admin
        """
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_instructor or request.user.is_admin_user


class IsDepartmentHead(BasePermission):
    """
    Allow access to department heads.

    Can access all courses and data within their department.

    Note:
        Currently treats admins as department heads. Future enhancement
        could add a dedicated 'department_head' role to the user model.
    """

    def has_permission(self, request: Request, view: ViewType) -> bool:
        """
        Check if user is a department head (currently admin).

        Args:
            request: The incoming request
            view: The view being accessed

        Returns:
            True if user is authenticated admin
        """
        if not request.user or not request.user.is_authenticated:
            return False
        # For now, treat admins as department heads
        # In future, could add a 'department_head' role
        return request.user.is_admin_user


class CanAccessStudentData(BasePermission):
    """
    Permission to access a specific student's data.

    Access rules:
    - Students: only their own data
    - Instructors: students enrolled in their courses
    - Admins: all students
    """

    def has_permission(self, request: Request, view: ViewType) -> bool:
        """
        Check basic authentication.

        Args:
            request: The incoming request
            view: The view being accessed

        Returns:
            True if user is authenticated
        """
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request: Request, view: ViewType, obj: Any) -> bool:
        """
        Check if user can access this student's data.

        Args:
            request: The incoming request
            view: The view being accessed
            obj: The object being accessed (should have student or user attribute)

        Returns:
            True if user is admin, the student themselves, or their instructor
        """
        user = request.user

        # Admin access
        if user.is_admin_user:
            return True

        # Get student from object
        student = getattr(obj, "student", None)
        if not student and hasattr(obj, "user"):
            # Object might be the student profile itself
            student = obj

        if not student:
            return False

        # Own data
        if hasattr(student, "user"):
            if student.user == user:
                return True
        elif student == user:
            return True

        # Instructor access to their students
        if user.is_instructor:
            from evaluation.models import CourseEnrollment

            instructor_course_ids = user.taught_courses.values_list("id", flat=True)
            student_user = getattr(student, "user", student)
            return CourseEnrollment.objects.filter(student=student_user, course_id__in=instructor_course_ids).exists()

        return False
