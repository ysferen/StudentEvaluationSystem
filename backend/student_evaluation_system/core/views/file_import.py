"""
File Import ViewSets.

Contains ViewSets for importing data from files:
- AssignmentScoresImportViewSet
- LearningOutcomesImportViewSet
- ProgramOutcomesImportViewSet
"""

import json
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from ..serializers import FileImportResponseSerializer
from ..services.file_import import FileImportService, FileImportError
from ..services.validation import AssignmentScoreValidator
from ..models import Term, Course
from evaluation.models import CourseEnrollment
from users.models import CustomUser, StudentProfile


class FileUploadRateThrottle(UserRateThrottle):
    """Custom throttle for file upload endpoints."""

    scope = "file_upload"

    def allow_request(self, request, view):
        if request.method == "GET":
            return True
        return super().allow_request(request, view)


class BaseFileImportViewSet(viewsets.GenericViewSet):
    """Base ViewSet for file import operations."""

    serializer_class = FileImportResponseSerializer
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [FileUploadRateThrottle]
    permission_classes = [AllowAny]

    import_type = None

    @extend_schema(
        request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}}
    )
    @action(detail=False, methods=["get", "post"])
    def upload(self, request):
        """Upload and process file."""
        if request.method.lower() == "get":
            required_query_parameters = []
            if self.import_type == "assignment_scores":
                required_query_parameters = "course_code and term_id"

            info = {
                "message": "Upload a file to import data.",
                "required_query_parameters": required_query_parameters,
            }
            return Response(info, status=status.HTTP_200_OK)

        course_code = request.query_params.get("course_code")
        term_id = request.query_params.get("term_id")
        if self.import_type == "assignment_scores" and (not course_code or not term_id):
            return Response(
                {"error": {"course_code": "course_code is required", "term_id": "term_id is required"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = FileImportService(file_obj)
            service.validate_file()

            if self.import_type == "assignment_scores":
                result = service.import_assignment_scores(course_code=course_code, term_id=term_id)
            elif self.import_type == "learning_outcomes":
                result = service.import_learning_outcomes()
            elif self.import_type == "program_outcomes":
                result = service.import_program_outcomes()
            else:
                return Response({"error": f"Unsupported import type: {self.import_type}"}, status=status.HTTP_400_BAD_REQUEST)

            return Response(result, status=status.HTTP_200_OK)
        except FileImportError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def validate(self, request):
        """Validate file without importing."""
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = FileImportService(file_obj)
            service.validate_file()
            return Response({"valid": True}, status=status.HTTP_200_OK)
        except FileImportError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AssignmentScoresImportViewSet(BaseFileImportViewSet):
    """ViewSet for importing assignment scores from files."""

    import_type = "assignment_scores"

    def _build_validation_response(self, validation_result, phase_reached=None):
        """Build standardized validation response."""
        phases_completed = validation_result.validation_details.get("phases_completed", [])
        if phase_reached and phases_completed:
            current_phase = phases_completed[-1]["phase"] if phases_completed else None
        else:
            current_phase = phases_completed[-1]["phase"] if phases_completed else None

        return Response(
            {
                "is_valid": validation_result.is_valid,
                "phase_reached": current_phase,
                "checks": {
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                    "suggestions": validation_result.suggestions,
                },
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "suggestions": validation_result.suggestions,
                "details": validation_result.validation_details,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="course_code",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Course code",
            ),
            OpenApiParameter(
                name="term_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True, description="Term ID"
            ),
        ],
        request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}},
        responses={
            200: {
                "type": "object",
                "properties": {
                    "is_valid": {"type": "boolean"},
                    "phase_reached": {"type": "string"},
                    "checks": {"type": "object"},
                    "errors": {"type": "array", "items": {"type": "string"}},
                    "warnings": {"type": "array", "items": {"type": "string"}},
                    "suggestions": {"type": "array", "items": {"type": "string"}},
                },
            }
        },
    )
    @action(detail=False, methods=["post"])
    def validate(self, request):
        """Validate file without importing."""
        course_code = request.query_params.get("course_code")
        term_id = request.query_params.get("term_id")

        if not course_code or not term_id:
            return Response(
                {"error": {"course_code": "course_code is required", "term_id": "term_id is required"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            term = Term.objects.get(id=term_id)
        except Term.DoesNotExist:
            return Response({"error": f"Term with id {term_id} not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            course = Course.objects.get(code=course_code, term=term)
        except Course.DoesNotExist:
            return Response(
                {"error": f"Course {course_code} not found for term {term.name}"}, status=status.HTTP_404_NOT_FOUND
            )

        validation_result = AssignmentScoreValidator.validate_complete(file_obj, course)
        return self._build_validation_response(validation_result)

    def _apply_student_resolutions(self, resolutions, course, errors, created_counts):
        """Apply student creation resolutions."""
        for student_data in resolutions.get("students", []):
            try:
                student_id = student_data.get("student_id")
                first_name = student_data.get("first_name", "")
                last_name = student_data.get("last_name", "")

                if StudentProfile.objects.filter(student_id=student_id).exists():
                    continue

                user = CustomUser.objects.create_user(
                    username=student_id,
                    email=f"{student_id}@example.com",
                    first_name=first_name,
                    last_name=last_name,
                    role="student",
                )

                StudentProfile.objects.create(user=user, student_id=student_id, program=course.program)
                created_counts["students"] += 1
            except Exception as e:
                errors.append(f"Failed to create student {student_data.get('student_id', 'unknown')}: {str(e)}")

    def _apply_enrollment_resolutions(self, resolutions, course, errors, created_counts):
        """Apply enrollment resolutions."""
        for enrollment_data in resolutions.get("enrollments", []):
            try:
                student_id = enrollment_data.get("student_id")

                try:
                    student_profile = StudentProfile.objects.get(student_id=student_id)
                except StudentProfile.DoesNotExist:
                    errors.append(f"Student {student_id} not found for enrollment")
                    continue

                student_user = student_profile.user

                if not CourseEnrollment.objects.filter(student=student_user, course=course).exists():
                    CourseEnrollment.objects.create(student=student_user, course=course, status="active")
                    created_counts["enrollments"] += 1
            except Exception as e:
                errors.append(f"Failed to create enrollment for {enrollment_data.get('student_id', 'unknown')}: {str(e)}")

    def _apply_assessment_resolutions(self, resolutions, course, errors, created_counts):
        """Apply assessment creation resolutions."""
        from evaluation.models import Assessment

        for assessment_data in resolutions.get("assessments", []):
            try:
                name = assessment_data.get("name")
                assessment_type = assessment_data.get("assessment_type", "homework")
                total_score = assessment_data.get("total_score", 100)
                weight = assessment_data.get("weight", 0.0)

                if not Assessment.objects.filter(name=name, course=course).exists():
                    Assessment.objects.create(
                        name=name,
                        assessment_type=assessment_type,
                        total_score=total_score,
                        weight=weight,
                        course=course,
                    )
                    created_counts["assessments"] += 1
            except Exception as e:
                errors.append(f"Failed to create assessment {assessment_data.get('name', 'unknown')}: {str(e)}")

    @extend_schema(
        parameters=[
            OpenApiParameter(name="course_code", type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name="term_id", type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=True),
        ],
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "format": "binary"},
                    "resolutions": {"type": "string", "description": "JSON string of ResolutionChoices"},
                },
            }
        },
        responses={200: {"type": "object"}},
    )
    @action(detail=False, methods=["post"])
    def resolve(self, request):
        """Apply resolutions and re-validate."""
        course_code = request.query_params.get("course_code")
        term_id = request.query_params.get("term_id")

        if not course_code or not term_id:
            return Response(
                {"error": {"course_code": "course_code is required", "term_id": "term_id is required"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            term = Term.objects.get(id=term_id)
        except Term.DoesNotExist:
            return Response({"error": f"Term with id {term_id} not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            course = Course.objects.get(code=course_code, term=term)
        except Course.DoesNotExist:
            return Response(
                {"error": f"Course {course_code} not found for term {term.name}"}, status=status.HTTP_404_NOT_FOUND
            )

        resolutions_json = request.data.get("resolutions")
        if not resolutions_json:
            return Response({"error": "resolutions JSON is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            resolutions = json.loads(resolutions_json)
        except json.JSONDecodeError:
            return Response({"error": "Invalid resolutions JSON"}, status=status.HTTP_400_BAD_REQUEST)

        errors = []
        created_counts = {"students": 0, "enrollments": 0, "assessments": 0}

        self._apply_student_resolutions(resolutions, course, errors, created_counts)
        self._apply_enrollment_resolutions(resolutions, course, errors, created_counts)
        self._apply_assessment_resolutions(resolutions, course, errors, created_counts)

        file_obj.seek(0)
        validation_result = AssignmentScoreValidator.validate_complete(file_obj, course)

        phases = validation_result.validation_details.get("phases_completed", [])
        phase_reached = phases[-1]["phase"] if phases else None

        return Response(
            {
                "is_valid": validation_result.is_valid,
                "phase_reached": phase_reached,
                "checks": {
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                    "suggestions": validation_result.suggestions,
                },
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "suggestions": validation_result.suggestions,
                "details": validation_result.validation_details,
                "resolutions_applied": {
                    "created": created_counts,
                    "errors": errors,
                },
            },
            status=status.HTTP_200_OK,
        )


class LearningOutcomesImportViewSet(BaseFileImportViewSet):
    """ViewSet for importing learning outcomes from files."""

    import_type = "learning_outcomes"


class ProgramOutcomesImportViewSet(BaseFileImportViewSet):
    """ViewSet for importing program outcomes from files."""

    import_type = "program_outcomes"
