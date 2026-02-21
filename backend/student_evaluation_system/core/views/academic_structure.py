from rest_framework import generics, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Avg, F
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from ..services.file_import import FileImportService
from ..services.file_import import FileImportError
from ..services.validation import AssignmentScoreValidator
from ..permissions import (
    IsAdmin, IsInstructorOrAdmin, IsInstructorOfCourse,
    IsOwnerOrInstructorOrAdmin, IsAdminOrReadOnly
)
from rest_framework import serializers

from ..models import (
    University, Department, DegreeLevel, Program, Term,
    Course, ProgramOutcome, LearningOutcome,
    LearningOutcomeProgramOutcomeMapping,
    StudentLearningOutcomeScore, StudentProgramOutcomeScore
)
from ..serializers import (
    UniversitySerializer, DepartmentSerializer, DegreeLevelSerializer,
    ProgramSerializer, TermSerializer, CourseSerializer,
    ProgramOutcomeSerializer, CoreLearningOutcomeSerializer,
    LearningOutcomeProgramOutcomeMappingSerializer,
    StudentLearningOutcomeScoreSerializer, StudentProgramOutcomeScoreSerializer,
    FileImportResponseSerializer, FileValidationResponseSerializer,
    CourseAverageSerializer, LearningOutcomeAverageSerializer
)
from users.models import StudentProfile
from users.serializers import StudentProfileSerializer

# Dummy serializer for import ViewSets that only use custom actions
class DummyImportSerializer(serializers.Serializer):
    """Dummy serializer for import ViewSets that only use custom actions."""
    pass


class FileUploadRateThrottle(UserRateThrottle):
    """Custom throttle for file upload endpoints.

    Prevents abuse of file upload functionality and protects
    against DoS attacks through large file uploads.
    """
    scope = 'file_upload'

    def allow_request(self, request, view):
        # Skip throttle for GET requests (documentation)
        if request.method == 'GET':
            return True
        return super().allow_request(request, view)

@extend_schema_view(
    list=extend_schema(tags=['Academic Structure']),
    retrieve=extend_schema(tags=['Academic Structure']),
    create=extend_schema(tags=['Academic Structure']),
    update=extend_schema(tags=['Academic Structure']),
    partial_update=extend_schema(tags=['Academic Structure']),
    destroy=extend_schema(tags=['Academic Structure']),
)
class UniversityViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for universities.

    Permissions:
    - Read: Any authenticated user
    - Write: Admin only
    """
    queryset = University.objects.all()
    serializer_class = UniversitySerializer
    permission_classes = [AllowAny, IsAdminOrReadOnly]


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name='university',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter departments by university ID'
            ),
        ]
    )
)
class DepartmentViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for departments.

    Permissions:
    - Read: Any authenticated user
    - Write: Admin only
    """
    queryset = Department.objects.select_related('university').all()
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny, IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        university_id = self.request.query_params.get('university', None)
        if university_id:
            queryset = queryset.filter(university_id=university_id)
        return queryset


class DegreeLevelViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for degree levels.

    Permissions:
    - Read: Any authenticated user
    - Write: Admin only
    """
    queryset = DegreeLevel.objects.all()
    serializer_class = DegreeLevelSerializer
    permission_classes = [AllowAny, IsAdminOrReadOnly]


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name='department',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter programs by department ID'
            ),
            OpenApiParameter(
                name='degree_level',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter programs by degree level ID'
            ),
        ]
    )
)
class ProgramViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for programs.

    Permissions:
    - Read: Any authenticated user
    - Write: Admin only
    """
    queryset = Program.objects.select_related('department', 'degree_level').all()
    serializer_class = ProgramSerializer
    permission_classes = [AllowAny, IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        department_id = self.request.query_params.get('department', None)
        degree_level_id = self.request.query_params.get('degree_level', None)

        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if degree_level_id:
            queryset = queryset.filter(degree_level_id=degree_level_id)

        return queryset


class TermViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for terms.

    Permissions:
    - Read: Any authenticated user
    - Write: Admin only
    """
    queryset = Term.objects.all()
    serializer_class = TermSerializer
    permission_classes = [AllowAny, IsAdminOrReadOnly]

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get currently active term."""
        active_term = Term.objects.filter(is_active=True).first()
        if active_term:
            serializer = self.get_serializer(active_term)
            return Response(serializer.data)
        return Response({'detail': 'No active term found.'}, status=404)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name='department',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter courses by department ID'
            ),
            OpenApiParameter(
                name='term',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter courses by term ID'
            ),
            OpenApiParameter(
                name='instructor',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter courses by instructor ID'
            ),
        ]
    )
)
class CourseViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for courses.

    Permissions:
    - Read: Instructors and Admins
    - Write: Instructors (own courses) and Admins
    """
    queryset = Course.objects.select_related('program', 'term').prefetch_related('instructors').all()
    serializer_class = CourseSerializer
    permission_classes = [AllowAny, IsAdminOrReadOnly]

    def get_queryset(self):
        """
        Filter courses based on user role:
        - Instructors: only courses they teach
        - Admins: all courses
        """
        user = self.request.user
        queryset = super().get_queryset()

        # Instructors only see their own courses
        if user.is_instructor and not user.is_admin_user:
            queryset = queryset.filter(instructors=user)

        # Apply query filters
        department_id = self.request.query_params.get('department', None)
        term_id = self.request.query_params.get('term', None)
        instructor_id = self.request.query_params.get('instructor', None)

        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if term_id:
            queryset = queryset.filter(term_id=term_id)
        if instructor_id:
            queryset = queryset.filter(instructors__id=instructor_id)

        return queryset
        queryset = super().get_queryset()
        department_id = self.request.query_params.get('department', None)
        term_id = self.request.query_params.get('term', None)
        instructor_id = self.request.query_params.get('instructor', None)

        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if term_id:
            queryset = queryset.filter(term_id=term_id)
        if instructor_id:
            queryset = queryset.filter(instructors__id=instructor_id)

        return queryset

    @action(detail=True, methods=['get'])
    def learning_outcomes(self, request, pk=None):
        """Get all learning outcomes for this course."""
        course = self.get_object()
        outcomes = course.learning_outcomes.all()
        serializer = CoreLearningOutcomeSerializer(outcomes, many=True)
        return Response(serializer.data)

@extend_schema_view(
    list=extend_schema(
        tags=['Outcomes'],
        parameters=[
            OpenApiParameter(
                name='department',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter program outcomes by department ID'
            ),
            OpenApiParameter(
                name='term',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter program outcomes by term ID'
            ),
        ]
    ),
    retrieve=extend_schema(tags=['Outcomes']),
    create=extend_schema(tags=['Outcomes']),
    update=extend_schema(tags=['Outcomes']),
    partial_update=extend_schema(tags=['Outcomes']),
    destroy=extend_schema(tags=['Outcomes']),
)
class ProgramOutcomeViewSet(viewsets.ModelViewSet):
    """CRUD operations for program outcomes."""
    queryset = ProgramOutcome.objects.select_related('program', 'term', 'created_by').all()
    serializer_class = ProgramOutcomeSerializer
    permission_classes = [AllowAny, IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        program_id = self.request.query_params.get('program', None)
        term_id = self.request.query_params.get('term', None)

        if program_id:
            queryset = queryset.filter(program_id=program_id)
        if term_id:
            queryset = queryset.filter(term_id=term_id)

        return queryset


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name='course',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter learning outcomes by course ID'
            ),
        ]
    )
)
class LearningOutcomeViewSet(viewsets.ModelViewSet):
    """CRUD operations for learning outcomes."""
    queryset = LearningOutcome.objects.select_related('course', 'created_by').all()
    serializer_class = CoreLearningOutcomeSerializer
    permission_classes = [AllowAny, IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        course_id = self.request.query_params.get('course', None)

        if course_id:
            queryset = queryset.filter(course_id=course_id)

        return queryset


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name='course',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter LO-PO mappings by course ID'
            ),
        ]
    )
)
class LearningOutcomeProgramOutcomeMappingViewSet(viewsets.ModelViewSet):
    """CRUD operations for LO-PO mappings."""
    queryset = LearningOutcomeProgramOutcomeMapping.objects.select_related(
        'course', 'learning_outcome', 'program_outcome'
    ).all()
    serializer_class = LearningOutcomeProgramOutcomeMappingSerializer
    permission_classes = [AllowAny, IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        course_id = self.request.query_params.get('course', None)

        if course_id:
            queryset = queryset.filter(course_id=course_id)

        return queryset

@extend_schema_view(
    list=extend_schema(
        tags=['Scores'],
        parameters=[
            OpenApiParameter(
                name='student',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter LO scores by student ID'
            ),
            OpenApiParameter(
                name='course',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter LO scores by course ID'
            ),
        ]
    ),
    retrieve=extend_schema(tags=['Scores']),
)
class StudentLearningOutcomeScoreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only access to calculated LO scores.

    Permissions:
    - Students: can only see their own scores
    - Instructors: can see scores of students in their courses
    - Admins: can see all scores
    """
    queryset = StudentLearningOutcomeScore.objects.select_related(
        'student', 'learning_outcome', 'learning_outcome__course'
    ).all()
    serializer_class = StudentLearningOutcomeScoreSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        Filter scores based on user role:
        - Students: only their own scores
        - Instructors: scores of students in their courses
        - Admins: all scores
        """
        user = self.request.user
        queryset = super().get_queryset()

        # Students only see their own scores
        if user.is_student:
            queryset = queryset.filter(student=user)

        # Instructors see scores of students in their courses
        elif user.is_instructor and not user.is_admin_user:
            instructor_course_ids = user.taught_courses.values_list('id', flat=True)
            queryset = queryset.filter(learning_outcome__course_id__in=instructor_course_ids)

        # Apply query filters (for instructors and admins)
        student_id = self.request.query_params.get('student', None)
        course_id = self.request.query_params.get('course', None)

        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if course_id:
            queryset = queryset.filter(learning_outcome__course_id=course_id)

        return queryset

    @extend_schema(
        tags=['Analytics'],
        responses={200: CourseAverageSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name='student',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by specific student ID (optional)'
            ),
            OpenApiParameter(
                name='course',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by specific course ID (optional)'
            ),
        ]
    )
    @action(detail=False, methods=['get'], pagination_class=None)
    def course_averages(self, request):
        """
        Calculate average learning outcome scores per course.

        Query Parameters:
        - student: Student ID (optional) - filter by specific student
        - course: Course ID (optional) - filter by specific course

        At least one parameter must be provided.

        Returns:
        - List of courses with calculated average LO scores
        {"course_id": int, "weighted_average": float}

        Examples:
        - /api/core/student-lo-scores/course_averages/?student=1 (all courses for student)
        - /api/core/student-lo-scores/course_averages/?course=5 (all students in course)
        - /api/core/student-lo-scores/course_averages/?student=1&course=5 (specific student in course)
        """
        student_id = request.query_params.get('student')
        course_id = request.query_params.get('course')

        if not student_id and not course_id:
            return Response(
                {'error': 'Either student or course query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from evaluation.models import CourseEnrollment

        # Build query based on provided parameters
        if student_id and course_id:
            # Specific student in specific course
            course_ids = [int(course_id)]
        elif student_id:
            # All courses for a specific student
            enrollments = CourseEnrollment.objects.filter(
                student_id=student_id
            ).values_list('course_id', flat=True)
            course_ids = list(enrollments)
        else:
            # All students in a specific course
            course_ids = [int(course_id)]

        # Calculate average LO score for each course
        course_averages = []

        for cid in course_ids:
            # Build base query
            lo_scores_query = StudentLearningOutcomeScore.objects.filter(
                learning_outcome__course_id=cid
            )

            # Filter by student if provided
            if student_id:
                lo_scores_query = lo_scores_query.filter(student_id=student_id)

            if lo_scores_query.exists():
                # Calculate average score (scores are already in 0-100 or 0-1 format)
                avg_result = lo_scores_query.aggregate(avg_score=Avg('score'))
                avg_score = avg_result['avg_score']

                # Check if scores are in decimal format (0-1) and convert to percentage
                # Assuming scores > 1 are already percentages
                if avg_score is not None and avg_score <= 1:
                    avg_score = avg_score * 100
            else:
                avg_score = None

            course_averages.append({
                'course_id': cid,
                'weighted_average': round(avg_score, 2) if avg_score is not None else None
            })

        return Response(course_averages)

    @extend_schema(
        tags=['Analytics'],
        responses={200: LearningOutcomeAverageSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name='course',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Course ID (required)',
                required=True
            ),
        ]
    )
    @action(detail=False, methods=['get'], pagination_class=None)
    def lo_averages(self, request):
        """
        Calculate average scores grouped by learning outcome for a course.
        Used for instructor analytics (radar charts).

        Query Parameters:
        - course: Course ID (required)

        Returns:
        - List of learning outcomes with their average scores across all students

        Example: /api/core/student-lo-scores/lo_averages/?course=5
        Response: [
            {"lo_code": "LO1", "lo_description": "...", "avg_score": 85.5},
            {"lo_code": "LO2", "lo_description": "...", "avg_score": 78.2}
        ]
        """
        course_id = request.query_params.get('course')

        if not course_id:
            return Response(
                {'error': 'course query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get all LO scores for this course grouped by learning outcome
        lo_averages = (
            StudentLearningOutcomeScore.objects
            .filter(learning_outcome__course_id=course_id)
            .values('learning_outcome__code', 'learning_outcome__description')
            .annotate(avg_score=Avg('score'))
            .order_by('learning_outcome__code')
        )

        # Format and convert scores if needed
        result = []
        for item in lo_averages:
            avg_score = item['avg_score']
            # Convert to percentage if in decimal format
            if avg_score is not None and avg_score <= 1:
                avg_score = avg_score * 100

            result.append({
                'lo_code': item['learning_outcome__code'],
                'lo_description': item['learning_outcome__description'],
                'avg_score': round(avg_score, 2) if avg_score is not None else 0
            })

        return Response(result)


@extend_schema_view(
    list=extend_schema(
        tags=['Scores'],
        parameters=[
            OpenApiParameter(
                name='student',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter PO scores by student ID'
            ),
            OpenApiParameter(
                name='course',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter PO scores by course ID'
            ),
        ]
    ),
    retrieve=extend_schema(tags=['Scores']),
)
class StudentProgramOutcomeScoreViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only access to calculated PO scores.

    Permissions:
    - Students: can only see their own scores
    - Instructors: can see scores of students in their program/department
    - Admins: can see all scores
    """
    queryset = StudentProgramOutcomeScore.objects.select_related(
        'student', 'program_outcome', 'term'
    ).all()
    serializer_class = StudentProgramOutcomeScoreSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        Filter scores based on user role:
        - Students: only their own scores
        - Instructors: scores of students in their courses
        - Admins: all scores
        """
        user = self.request.user
        queryset = super().get_queryset()

        # Students only see their own scores
        if user.is_student:
            queryset = queryset.filter(student=user)

        # Instructors see scores of students in their courses
        elif user.is_instructor and not user.is_admin_user:
            from evaluation.models import CourseEnrollment
            instructor_course_ids = user.taught_courses.values_list('id', flat=True)
            student_ids = CourseEnrollment.objects.filter(
                course_id__in=instructor_course_ids
            ).values_list('student_id', flat=True)
            queryset = queryset.filter(student_id__in=student_ids)

        # Apply query filters (for instructors and admins)
        student_id = self.request.query_params.get('student', None)
        course_id = self.request.query_params.get('course', None)

        if student_id:
            queryset = queryset.filter(student_id=student_id)
        if course_id:
            queryset = queryset.filter(course_id=course_id)

        return queryset


# Legacy views for backward compatibility
class StudentListView(generics.ListAPIView):
    queryset = StudentProfile.objects.select_related('user', 'enrollment_term', 'program').all()
    serializer_class = StudentProfileSerializer


class StudentDetailView(generics.RetrieveAPIView):
    queryset = StudentProfile.objects.select_related('user', 'enrollment_term', 'program').all()
    serializer_class = StudentProfileSerializer


class CourseListView(generics.ListAPIView):
    queryset = Course.objects.select_related('department', 'term').prefetch_related('instructors').all()
    serializer_class = CourseSerializer


class CourseDetailView(generics.RetrieveAPIView):
    queryset = Course.objects.select_related('department', 'term').prefetch_related('instructors').all()
    serializer_class = CourseSerializer


class ProgramOutcomeListView(generics.ListAPIView):
    queryset = ProgramOutcome.objects.select_related('department', 'term', 'created_by').all()
    serializer_class = ProgramOutcomeSerializer


class ProgramOutcomeDetailView(generics.RetrieveAPIView):
    queryset = ProgramOutcome.objects.select_related('department', 'term', 'created_by').all()
    serializer_class = ProgramOutcomeSerializer


class BaseFileImportViewSet(viewsets.GenericViewSet):
    """
    Base ViewSet for handling file imports with common functionality.

    Rate limiting:
    - 10 file uploads per minute per user
    - Protects against DoS via large file uploads
    """
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = DummyImportSerializer # Placeholder serializer
    throttle_classes = [FileUploadRateThrottle]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_service = None

    def _initialize_service(self, file_obj):
        """Initialize file import service with uploaded file."""
        self.file_service = FileImportService(file_obj)
        return self.file_service

    def _validate_file(self, file_obj):
        """Validate uploaded file format."""
        self._initialize_service(file_obj)
        self.file_service.validate_file()
        return self.file_service

    def _get_course_by_code_and_term(self, course_code: str, term_id: int):
        """
        Get course by code and term with proper error handling.

        Args:
            course_code (str): Course code
            term_id (int): Term ID

        Returns:
            Course: Course object

        Raises:
            Response: HTTP 400 if course not found
        """
        try:
            return Course.objects.get(code=course_code, term_id=term_id)
        except Course.DoesNotExist:
            available_courses = Course.objects.filter(code=course_code).select_related('term')
            if available_courses.exists():
                terms = [f"{course.code} ({course.term.name})" for course in available_courses]
                return Response(
                    {
                        'error': f'Course with code "{course_code}" found but not for specified term.',
                        'available_terms': terms,
                        'suggestion': 'Please check the term_id parameter or use one of the available terms listed above.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                return Response(
                    {'error': f'Course with code "{course_code}" not found.'},
                    status=status.HTTP_400_BAD_REQUEST
                )


@extend_schema_view(
    upload=extend_schema(
        summary="Upload and import assessment scores",
        description="Upload a file to import student assessment scores for a specific course and term",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string', 'format': 'binary'}
                },
                'required': ['file']
            }
        },
        parameters=[
            OpenApiParameter(
                name='course_code',
                type=OpenApiTypes.STR,
                required=True,
                location=OpenApiParameter.QUERY,
                description='Code of the course for which scores are being imported'
            ),
            OpenApiParameter(
                name='term_id',
                type=OpenApiTypes.INT,
                required=True,
                location=OpenApiParameter.QUERY,
                description='ID of the academic term for which scores are being imported'
            )
        ],
        responses={200: FileImportResponseSerializer, 400: dict},
        tags=['File Import - Assessment Scores']
    ),
    validate=extend_schema(
        summary="Validate assessment scores file",
        description="Validate file format for assessment scores import",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string', 'format': 'binary'}
                },
                'required': ['file']
            }
        },
        parameters=[
            OpenApiParameter(
                name='course_code',
                type=OpenApiTypes.STR,
                required=True,
                location=OpenApiParameter.QUERY,
                description='Code of the course for which scores are being imported'
            ),
            OpenApiParameter(
                name='term_id',
                type=OpenApiTypes.INT,
                required=True,
                location=OpenApiParameter.QUERY,
                description='ID of the academic term for which scores are being imported'
            )
        ],
        responses={200: FileValidationResponseSerializer, 400: dict},
        tags=['File Import - Assessment Scores']
    )
)
class AssignmentScoresImportViewSet(BaseFileImportViewSet):
    """
    ViewSet for handling assignment scores file imports (Excel format).

    This endpoint allows bulk import of student assignment scores from Excel format
    with columns like 'öğrenci no', 'adı', 'soyadı', 'Midterm 1(%25)_0833AB', etc.

    IMPORTANT: Requires course_code and term_id as query parameters to identify the specific course.
    """

    @action(detail=False, methods=['get', 'post'])
    def upload(self, request):
        """
        Upload and process assignment scores file (Turkish format).

        Expected request format:
        - GET/POST /api/core/file-import/assignment-scores/upload/?course_code=MATH101&term_id=3
        - file: File (.xlsx, .xls) in multipart/form-data

        Query Parameters (Required):
        - course_code: Code of the course for which scores are being imported
        - term_id: ID of the academic term for which scores are being imported

        Expected Excel Columns:
        - 'öğrenci no' or 'No_0833AB': Student ID
        - 'adı' or 'Adı_0833AB': Student first name
        - 'soyadı' or 'Soyadı_0833AB': Student last name
        - Assessment columns with pattern: 'AssessmentName(%weight)_0833AB'
          Examples: 'Midterm 1(%25)_0833AB', 'Project(%40)_0833AB'

        Returns:
            dict: Import results with created/updated counts and any errors
        """
        if request.method == 'GET':
            return Response({
                'message': 'Assignment Scores Upload Endpoint (Turkish Format)',
                'description': 'POST a file here to import assignment scores from Turkish Excel format. Use multipart/form-data with query parameters.',
                'required_query_parameters': {
                    'course_code': 'Code of the course for which scores are being imported',
                    'term_id': 'ID of the academic term for which scores are being imported'
                },
                'required_fields': {
                    'file': 'File to upload (.xlsx, .xls) in Turkish Excel format'
                },
                'expected_columns': {
                    'student_id': ['öğrenci no', 'No_0833AB', 'Öğrenci No_0833AB'],
                    'first_name': ['adı', 'Adı_0833AB'],
                    'last_name': ['soyadı', 'Soyadı_0833AB'],
                    'assessment_columns': 'Pattern: AssessmentName(%weight)_0833AB (e.g., Midterm 1(%25)_0833AB, Project(%40)_0833AB)'
                },
                'example_usage': [
                    'POST /api/core/file-import/assignment-scores/upload/?course_code=MATH101&term_id=3',
                    'Content-Type: multipart/form-data',
                    'file: <your_turkish_excel_file>'
                ],
                'example_curl': [
                    'curl -X POST \\',
                    '  "http://localhost:8000/api/core/file-import/assignment-scores/upload/?course_code=MATH101&term_id=3" \\',
                    '  -H "Content-Type: multipart/form-data" \\',
                    '  -F "file=@assignment_scores_turkish.xlsx"'
                ]
            })

        try:
            # Validate file presence
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            file_obj = request.FILES['file']

            # Get required query parameters
            course_code = request.query_params.get('course_code')
            term_id = request.query_params.get('term_id')

            if not course_code:
                return Response(
                    {
                        'error': 'course_code query parameter is required',
                        'example': 'Add ?course_code=MATH101&term_id=3 to your URL'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not term_id:
                return Response(
                    {
                        'error': 'term_id query parameter is required',
                        'example': 'Add ?course_code=MATH101&term_id=3 to your URL'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                term_id = int(term_id)
            except ValueError:
                return Response(
                    {'error': 'term_id must be a valid integer'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate course and term exist
            course = self._get_course_by_code_and_term(course_code, term_id)
            if isinstance(course, Response):  # Error response
                return course

            # Run validation first
            validation_result = AssignmentScoreValidator.validate_complete(file_obj, course)

            if not validation_result.is_valid:
                return Response({
                    'error': 'Validation failed. Please fix the errors before uploading.',
                    'is_valid': False,
                    'errors': validation_result.errors,
                    'warnings': validation_result.warnings,
                    'suggestions': validation_result.suggestions,
                    'validation_details': validation_result.validation_details
                }, status=status.HTTP_400_BAD_REQUEST)

            # Reset file position after validation
            file_obj.seek(0)

            # Initialize and validate file
            self._validate_file(file_obj)

            # Import assignment scores with validated course and term
            results = self.file_service.import_assignment_scores(
                course_code=course_code,
                term_id=term_id
            )

            return Response({
                'message': f'Assignment scores imported successfully for course {course.code} ({course.term.name})',
                'course_info': {
                    'code': course.code,
                    'name': course.name,
                    'term': course.term.name
                },
                'results': results,
                'validation_passed': True
            }, status=status.HTTP_200_OK)

        except Exception as e:
            error_type = 'FileImportError' if isinstance(e, FileImportError) else 'UnexpectedError'
            return Response({
                'error': str(e),
                'error_type': error_type,
                'results': self.file_service.get_import_summary() if self.file_service else {}
            }, status=status.HTTP_400_BAD_REQUEST if isinstance(e, FileImportError) else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get', 'post'])
    def validate(self, request):
        """
        Validate assignment scores file format (Turkish format) without importing data.

        Validates:
        1. File structure: Excel format, max 10MB
        2. Assignment names: Parses and checks against database
        3. Students: Checks if students exist in database

        Query Parameters (Required):
        - course_code: Code of the course for validation
        - term_id: ID of the academic term for validation

        Returns:
            dict: Comprehensive validation results
        """
        if request.method == 'GET':
            return Response({
                'message': 'Assignment Scores Validation Endpoint (Turkish Format)',
                'description': 'POST a file here to validate its format for assignment scores import from Turkish Excel format.',
                'required_query_parameters': {
                    'course_code': 'Code of the course (REQUIRED for validation)',
                    'term_id': 'ID of the academic term (REQUIRED for validation)'
                },
                'required_fields': {
                    'file': 'File to validate (.xlsx, .xls) in Turkish Excel format'
                },
                'validates': [
                    'File structure: Excel format, max 10MB',
                    'Assignment names: Parses column headers and checks against database',
                    'Students: Checks if student IDs exist in database'
                ],
                'expected_columns': {
                    'student_id': ['öğrenci no', 'No_XXXXX', 'Öğrenci No_XXXXX'],
                    'first_name': ['adı', 'Adı_XXXXX'],
                    'last_name': ['soyadı', 'Soyadı_XXXXX'],
                    'assessment_columns': 'Pattern: AssessmentName(%weight)_XXXXX'
                },
                'example_curl': [
                    'curl -X POST \\',
                    '  "http://localhost:8000/api/core/file-import/assignment-scores/validate/?course_code=MATH101&term_id=3" \\',
                    '  -H "Content-Type: multipart/form-data" \\',
                    '  -F "file=@assignment_scores_turkish.xlsx"'
                ]
            })

        try:
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            file_obj = request.FILES['file']

            # Get required query parameters
            course_code = request.query_params.get('course_code')
            term_id = request.query_params.get('term_id')

            if not course_code:
                return Response(
                    {
                        'error': 'course_code query parameter is required for validation',
                        'example': 'Add ?course_code=MATH101&term_id=3 to your URL'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not term_id:
                return Response(
                    {
                        'error': 'term_id query parameter is required for validation',
                        'example': 'Add ?course_code=MATH101&term_id=3 to your URL'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                term_id = int(term_id)
            except ValueError:
                return Response(
                    {'error': 'term_id must be a valid integer'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate course and term exist
            course = self._get_course_by_code_and_term(course_code, term_id)
            if isinstance(course, Response):  # Error response
                return course

            # Run comprehensive validation
            validation_result = AssignmentScoreValidator.validate_complete(file_obj, course)

            response_data = {
                'is_valid': validation_result.is_valid,
                'course_info': {
                    'code': course.code,
                    'name': course.name,
                    'term': course.term.name
                },
                'file_info': validation_result.validation_details.get('file_info', {}),
                'validation_details': validation_result.validation_details
            }

            if validation_result.errors:
                response_data['errors'] = validation_result.errors

            if validation_result.warnings:
                response_data['warnings'] = validation_result.warnings

            if validation_result.suggestions:
                response_data['suggestions'] = validation_result.suggestions

            status_code = status.HTTP_200_OK if validation_result.is_valid else status.HTTP_400_BAD_REQUEST
            return Response(response_data, status=status_code)

        except Exception as e:
            error_msg = str(e) if isinstance(e, FileImportError) else f'Validation error: {str(e)}'
            return Response({'error': error_msg, 'is_valid': False}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    upload=extend_schema(
        summary="Upload and import learning outcomes",
        description="Upload a file to import learning outcomes",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string', 'format': 'binary'},
                },
                'required': ['file']
            }
        },
        responses={200: FileImportResponseSerializer, 400: dict},
        tags=['File Import - Learning Outcomes']
    ),
    validate=extend_schema(
        summary="Validate learning outcomes file",
        description="Validate file format for learning outcomes import",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string', 'format': 'binary'}
                },
                'required': ['file']
            }
        },
        responses={200: FileValidationResponseSerializer, 400: dict},
        tags=['File Import - Learning Outcomes']
    )
)
class LearningOutcomesImportViewSet(BaseFileImportViewSet):
    """
    ViewSet for handling learning outcomes file imports.

    This endpoint allows bulk import of learning outcomes through various file formats.
    Uses modular parser system to support multiple file formats (Excel, CSV, etc.).
    """

    @action(detail=False, methods=['get', 'post'])
    def upload(self, request):
        """
        Upload and process learning outcomes file.

        Expected request format:
        - file: File (.xlsx, .xls, .csv, etc.)
        - sheet_name: Name of the sheet/section to import from (optional)

        Returns:
            dict: Import results with created/updated counts and any errors
        """
        if request.method == 'GET':
            return Response({
                'message': 'Learning Outcomes Upload Endpoint',
                'description': 'POST a file here to import learning outcomes. Use multipart/form-data.',
                'required_fields': {
                    'file': 'File to upload (.xlsx, .xls, .csv)',
                    'sheet_name': 'Specific sheet name (optional, defaults to "learning_outcomes")'
                },
                'expected_columns': ['code', 'description', 'course_code'],
                'example_curl': [
                    'curl -X POST \\',
                    '  -H "Content-Type: multipart/form-data" \\',
                    '  -F "file=@learning_outcomes.xlsx" \\',
                    '  http://localhost:8000/api/core/file-import/learning-outcomes/upload/'
                ]
            })

        try:
            # Validate file presence
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            file_obj = request.FILES['file']
            sheet_name = request.data.get('sheet_name', 'learning_outcomes')

            # Initialize and validate file
            self._validate_file(file_obj)

            # Import learning outcomes
            results = self.file_service.import_learning_outcomes(sheet_name=sheet_name)

            return Response({
                'message': 'Learning outcomes import completed successfully',
                'results': results
            }, status=status.HTTP_200_OK)

        except Exception as e:
            error_type = 'FileImportError' if isinstance(e, FileImportError) else 'UnexpectedError'
            return Response({
                'error': str(e),
                'error_type': error_type,
                'results': self.file_service.get_import_summary() if self.file_service else {}
            }, status=status.HTTP_400_BAD_REQUEST if isinstance(e, FileImportError) else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get', 'post'])
    def validate(self, request):
        """
        Validate learning outcomes file format without importing data.

        Returns:
            dict: Available sheets/sections and validation results
        """
        if request.method == 'GET':
            return Response({
                'message': 'Learning Outcomes Validation Endpoint',
                'description': 'POST a file here to validate its format for learning outcomes import.',
                'required_fields': {
                    'file': 'File to validate (.xlsx, .xls, .csv)'
                },
                'expected_columns': ['code', 'description', 'course_code'],
                'example_curl': [
                    'curl -X POST \\',
                    '  -H "Content-Type: multipart/form-data" \\',
                    '  -F "file=@learning_outcomes.xlsx" \\',
                    '  http://localhost:8000/api/core/file-import/learning-outcomes/validate/'
                ]
            })

        try:
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            file_obj = request.FILES['file']
            file_service = self._validate_file(file_obj)

            available_sheets = file_service.get_available_sheets()

            return Response({
                'message': 'Learning outcomes file format is valid',
                'available_sheets': available_sheets,
                'file_info': {
                    'name': file_obj.name,
                    'size': file_obj.size,
                    'format': file_service.detect_file_format()
                },
                'expected_columns': ['code', 'description', 'course_code']
            }, status=status.HTTP_200_OK)

        except Exception as e:
            from .services.file_import import FileImportError
            error_msg = str(e) if isinstance(e, FileImportError) else f'Validation error: {str(e)}'
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    upload=extend_schema(
        summary="Upload and import program outcomes",
        description="Upload a file to import program outcomes",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string', 'format': 'binary'},
                    'sheet_name': {'type': 'string'}
                },
                'required': ['file']
            }
        },
        responses={200: FileImportResponseSerializer, 400: dict},
        tags=['File Import - Program Outcomes']
    ),
    validate=extend_schema(
        summary="Validate program outcomes file",
        description="Validate file format for program outcomes import",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string', 'format': 'binary'}
                },
                'required': ['file']
            }
        },
        responses={200: FileValidationResponseSerializer, 400: dict},
        tags=['File Import - Program Outcomes']
    )
)
class ProgramOutcomesImportViewSet(BaseFileImportViewSet):
    """
    ViewSet for handling program outcomes file imports.

    This endpoint allows bulk import of program outcomes through various file formats.
    Uses modular parser system to support multiple file formats (Excel, CSV, etc.).
    """

    @action(detail=False, methods=['get', 'post'])
    def upload(self, request):
        """
        Upload and process program outcomes file.

        Expected request format:
        - file: File (.xlsx, .xls, .csv, etc.)
        - sheet_name: Name of the sheet/section to import from (optional)

        Returns:
            dict: Import results with created/updated counts and any errors
        """
        if request.method == 'GET':
            return Response({
                'message': 'Program Outcomes Upload Endpoint',
                'description': 'POST a file here to import program outcomes. Use multipart/form-data.',
                'required_fields': {
                    'file': 'File to upload (.xlsx, .xls, .csv)',
                    'sheet_name': 'Specific sheet name (optional, defaults to "program_outcomes")'
                },
                'expected_columns': ['code', 'description', 'program_code', 'term_name'],
                'example_curl': [
                    'curl -X POST \\',
                    '  -H "Content-Type: multipart/form-data" \\',
                    '  -F "file=@program_outcomes.xlsx" \\',
                    '  http://localhost:8000/api/core/file-import/program-outcomes/upload/'
                ]
            })

        try:
            # Validate file presence
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            file_obj = request.FILES['file']
            sheet_name = request.data.get('sheet_name', 'program_outcomes')

            # Initialize and validate file
            self._validate_file(file_obj)

            # Import program outcomes
            results = self.file_service.import_program_outcomes(sheet_name=sheet_name)

            return Response({
                'message': 'Program outcomes import completed successfully',
                'results': results
            }, status=status.HTTP_200_OK)

        except Exception as e:
            error_type = 'FileImportError' if isinstance(e, FileImportError) else 'UnexpectedError'
            return Response({
                'error': str(e),
                'error_type': error_type,
                'results': self.file_service.get_import_summary() if self.file_service else {}
            }, status=status.HTTP_400_BAD_REQUEST if isinstance(e, FileImportError) else status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get', 'post'])
    def validate(self, request):
        """
        Validate program outcomes file format without importing data.

        Returns:
            dict: Available sheets/sections and validation results
        """
        if request.method == 'GET':
            return Response({
                'message': 'Program Outcomes Validation Endpoint',
                'description': 'POST a file here to validate its format for program outcomes import.',
                'required_fields': {
                    'file': 'File to validate (.xlsx, .xls, .csv)'
                },
                'expected_columns': ['code', 'description', 'program_code', 'term_name'],
                'example_curl': [
                    'curl -X POST \\',
                    '  -H "Content-Type: multipart/form-data" \\',
                    '  -F "file=@program_outcomes.xlsx" \\',
                    '  http://localhost:8000/api/core/file-import/program-outcomes/validate/'
                ]
            })

        try:
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            file_obj = request.FILES['file']
            file_service = self._validate_file(file_obj)

            available_sheets = file_service.get_available_sheets()

            return Response({
                'message': 'Program outcomes file format is valid',
                'available_sheets': available_sheets,
                'file_info': {
                    'name': file_obj.name,
                    'size': file_obj.size,
                    'format': file_service.detect_file_format()
                },
                'expected_columns': ['code', 'description', 'program_code', 'term_name']
            }, status=status.HTTP_200_OK)

        except Exception as e:
            from .services.file_import import FileImportError
            error_msg = str(e) if isinstance(e, FileImportError) else f'Validation error: {str(e)}'
            return Response({'error': error_msg}, status=status.HTTP_400_BAD_REQUEST)
