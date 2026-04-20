"""
File Import ViewSets.

Contains ViewSets for importing data from files:
- AssignmentScoresImportViewSet
- LearningOutcomesImportViewSet
- ProgramOutcomesImportViewSet
"""

import json
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter

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

    def _parse_resolution_policy(self, request):
        resolution_policy_raw = request.data.get("resolution_policy")
        if resolution_policy_raw is None:
            return {}
        if isinstance(resolution_policy_raw, str):
            try:
                return json.loads(resolution_policy_raw)
            except json.JSONDecodeError:
                return Response({"error": "Invalid resolution_policy JSON"}, status=status.HTTP_400_BAD_REQUEST)
        if isinstance(resolution_policy_raw, dict):
            return resolution_policy_raw
        return {}

    @extend_schema(
        request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}}
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
                name="term_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Term ID",
            ),
        ],
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "format": "binary"},
                    "resolution_policy": {
                        "type": "string",
                        "description": "Optional JSON policy (e.g. skip_invalid_scores, clamp_scores)",
                    },
                },
                "required": ["file"],
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "created": {"type": "object"},
                    "updated": {"type": "object"},
                    "errors": {"type": "array", "items": {"type": "string"}},
                    "skipped": {"type": "integer"},
                    "total_rows": {"type": "integer"},
                },
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "is_valid": {"type": "boolean"},
                    "phase_reached": {"type": "string"},
                    "checks": {"type": "object"},
                    "errors": {"type": "array", "items": {"type": "string"}},
                    "warnings": {"type": "array", "items": {"type": "string"}},
                    "suggestions": {"type": "array", "items": {"type": "string"}},
                    "details": {"type": "object"},
                },
            },
        },
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
                resolution_policy = self._parse_resolution_policy(request)
                if isinstance(resolution_policy, Response):
                    return resolution_policy
                result = service.import_assignment_scores(
                    course_code=course_code,
                    term_id=term_id,
                    resolution_policy=resolution_policy,
                )
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

    def _build_validation_response(self, validation_result, resolutions_applied=None, status_code=status.HTTP_200_OK):
        """Build standardized validation response with canonical shape."""
        details = validation_result.validation_details
        checks = details.get("checks", {})
        payload = {
            "is_valid": validation_result.is_valid,
            "phase_reached": details.get("phase_reached", "unknown"),
            "checks": checks,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
            "suggestions": validation_result.suggestions,
            "details": details,
        }
        if resolutions_applied is not None:
            payload["resolutions_applied"] = resolutions_applied
        return Response(payload, status=status_code)

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
                name="term_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Term ID",
            ),
        ],
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "file": {"type": "string", "format": "binary"},
                    "resolution_policy": {
                        "type": "string",
                        "description": "JSON string of resolution policy flags",
                    },
                },
                "required": ["file"],
            }
        },
        responses={
            200: {"type": "object"},
            202: {"type": "object"},
            400: {"type": "object"},
            404: {"type": "object"},
        },
    )
    @action(detail=False, methods=["get", "post"])
    def upload(self, request):
        """Upload and import assignment scores. Always validates before importing."""
        if request.method.lower() == "get":
            info = {
                "message": "Upload a file to import data.",
                "required_query_parameters": "course_code and term_id",
            }
            return Response(info, status=status.HTTP_200_OK)

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
                {"error": f"Course {course_code} not found for term {term.name}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            service = FileImportService(file_obj)
            service.validate_file()

            resolution_policy = self._parse_resolution_policy(request)
            if isinstance(resolution_policy, Response):
                return resolution_policy

            # Always run full validation server-side before importing, regardless of frontend flow.
            validation_result = AssignmentScoreValidator.validate_complete(
                file_obj,
                course,
                resolution_policy=resolution_policy,
            )
            if not validation_result.is_valid:
                return self._build_validation_response(validation_result, status_code=status.HTTP_400_BAD_REQUEST)

            file_obj.seek(0)
            result = service.import_assignment_scores(
                course_code=course_code,
                term_id=term_id,
                resolution_policy=resolution_policy,
                triggered_by=request.user if getattr(request.user, "is_authenticated", False) else None,
            )
            return Response(result, status=status.HTTP_202_ACCEPTED)
        except FileImportError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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

    def _apply_student_resolutions(self, create_students, course, errors, created_counts):
        """Apply student creation resolutions."""
        for student_data in create_students:
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

    def _apply_enrollment_resolutions(self, enroll_students, course, errors, created_counts):
        """Apply enrollment resolutions."""
        for student_id in enroll_students:
            try:
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
                errors.append(f"Failed to create enrollment for {student_id}: {str(e)}")

    def _apply_assessment_resolutions(self, create_assessments, course, errors, created_counts):
        """Apply assessment creation resolutions."""
        from evaluation.models import Assessment

        for assessment_data in create_assessments:
            name = "unknown"
            try:
                if isinstance(assessment_data, dict):
                    name = assessment_data.get("name")
                    assessment_type = assessment_data.get("assessment_type", "homework")
                    total_score = assessment_data.get("total_score", 100)
                    weight = assessment_data.get("weight", 0.0)
                else:
                    name = assessment_data
                    assessment_type = "homework"
                    total_score = 100
                    weight = 0.0

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
                errors.append(f"Failed to create assessment {name}: {str(e)}")

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
        if isinstance(resolutions_json, str):
            try:
                resolutions = json.loads(resolutions_json)
            except json.JSONDecodeError:
                return Response({"error": "Invalid resolutions JSON"}, status=status.HTTP_400_BAD_REQUEST)
        elif isinstance(resolutions_json, dict):
            resolutions = resolutions_json
        else:
            resolutions = {}

        create_students = resolutions.get("create_students", [])
        enroll_students = resolutions.get("enroll_students", [])
        create_assessments = resolutions.get("create_assessments", [])

        resolution_policy = AssignmentScoreValidator.normalize_resolution_policy(resolutions)

        errors = []
        created_counts = {"students": 0, "enrollments": 0, "assessments": 0}

        with transaction.atomic():
            self._apply_student_resolutions(create_students, course, errors, created_counts)
            self._apply_enrollment_resolutions(enroll_students, course, errors, created_counts)
            self._apply_assessment_resolutions(create_assessments, course, errors, created_counts)

            file_obj.seek(0)
            validation_result = AssignmentScoreValidator.validate_complete(
                file_obj,
                course,
                resolution_policy=resolution_policy,
            )

        resolution_summary = {
            "created": created_counts,
            "errors": errors,
            "policy": resolution_policy,
        }
        return self._build_validation_response(validation_result, resolutions_applied=resolution_summary)


class LearningOutcomesImportViewSet(BaseFileImportViewSet):
    """ViewSet for importing learning outcomes from files."""

    import_type = "learning_outcomes"


class ProgramOutcomesImportViewSet(BaseFileImportViewSet):
    """ViewSet for importing program outcomes from files."""

    import_type = "program_outcomes"
