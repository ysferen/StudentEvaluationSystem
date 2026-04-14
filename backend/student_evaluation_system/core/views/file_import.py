"""
File Import ViewSets.

Contains ViewSets for importing data from files:
- AssignmentScoresImportViewSet
- LearningOutcomesImportViewSet
- ProgramOutcomesImportViewSet
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema

from ..serializers import FileImportResponseSerializer
from ..services.file_import import FileImportService, FileImportError


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


class LearningOutcomesImportViewSet(BaseFileImportViewSet):
    """ViewSet for importing learning outcomes from files."""

    import_type = "learning_outcomes"


class ProgramOutcomesImportViewSet(BaseFileImportViewSet):
    """ViewSet for importing program outcomes from files."""

    import_type = "program_outcomes"
