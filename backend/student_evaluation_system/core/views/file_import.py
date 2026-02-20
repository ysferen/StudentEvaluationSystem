"""
File Import ViewSets.

Contains ViewSets for importing data from files:
- AssignmentScoresImportViewSet
- LearningOutcomesImportViewSet
- ProgramOutcomesImportViewSet
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema

from ..services.file_import import FileImportService, FileImportError
from ..serializers import FileImportResponseSerializer


class FileUploadRateThrottle(UserRateThrottle):
    """Custom throttle for file upload endpoints."""
    scope = 'file_upload'

    def allow_request(self, request, view):
        if request.method == 'GET':
            return True
        return super().allow_request(request, view)


class BaseFileImportViewSet(viewsets.GenericViewSet):
    """Base ViewSet for file import operations."""
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [FileUploadRateThrottle]
    permission_classes = [IsAuthenticated]

    import_type = None

    @extend_schema(request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}}})
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Upload and process file."""
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = FileImportService(file_obj, self.import_type)
            result = service.process()
            return Response(result, status=status.HTTP_200_OK)
        except FileImportError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Validate file without importing."""
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = FileImportService(file_obj, self.import_type)
            result = service.validate()
            return Response(result, status=status.HTTP_200_OK)
        except FileImportError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class AssignmentScoresImportViewSet(BaseFileImportViewSet):
    """ViewSet for importing assignment scores from files."""
    import_type = 'assignment_scores'


class LearningOutcomesImportViewSet(BaseFileImportViewSet):
    """ViewSet for importing learning outcomes from files."""
    import_type = 'learning_outcomes'


class ProgramOutcomesImportViewSet(BaseFileImportViewSet):
    """ViewSet for importing program outcomes from files."""
    import_type = 'program_outcomes'
