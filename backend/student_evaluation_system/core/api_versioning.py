"""
API Versioning Utilities

This module provides utilities for handling API versioning,
including deprecation warnings and version-specific serializers.
"""

import warnings
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView


class DeprecationMixin:
    """
    Mixin to add deprecation warnings to API views.
    
    Usage:
        class MyView(DeprecationMixin, APIView):
            deprecation_message = "This endpoint is deprecated. Use /api/v2/... instead."
            sunset_date = "2026-06-01"
            
            def get(self, request, *args, **kwargs):
                ...
    """
    deprecation_message = None
    sunset_date = None
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        # Add deprecation headers if this is a deprecated endpoint
        if self.deprecation_message:
            response['Deprecation'] = 'true'
            response['Sunset'] = self.sunset_date or 'TBD'
            
            # Log deprecation warning
            warnings.warn(
                f"API Deprecation: {self.deprecation_message}",
                DeprecationWarning,
                stacklevel=2
            )
        
        return response


def get_versioned_serializer(version, v1_serializer, v2_serializer=None):
    """
    Get the appropriate serializer class based on API version.
    
    Args:
        version: The API version string (e.g., 'v1', 'v2')
        v1_serializer: The serializer class for v1
        v2_serializer: The serializer class for v2 (optional)
    
    Returns:
        The appropriate serializer class
    
    Usage:
        serializer_class = get_versioned_serializer(
            request.version,
            v1_serializer=CourseSerializerV1,
            v2_serializer=CourseSerializerV2
        )
    """
    if version == 'v2' and v2_serializer is not None:
        return v2_serializer
    return v1_serializer


class VersionedSerializerViewMixin:
    """
    Mixin for views that need different serializers per API version.
    
    Usage:
        class MyView(VersionedSerializerViewMixin, generics.ListAPIView):
            v1_serializer_class = MySerializerV1
            v2_serializer_class = MySerializerV2  # Optional
    """
    v1_serializer_class = None
    v2_serializer_class = None
    
    def get_serializer_class(self):
        assert self.v1_serializer_class is not None, (
            f"'{self.__class__.__name__}' should include a `v1_serializer_class` attribute."
        )
        return get_versioned_serializer(
            self.request.version,
            self.v1_serializer_class,
            self.v2_serializer_class
        )


# API Version Information
API_VERSION_INFO = {
    'v1': {
        'status': 'current',
        'release_date': '2025-01-01',
        'documentation': '/api/docs/',
        'deprecated': False,
        'sunset_date': None,
    },
    # 'v2': {
    #     'status': 'beta',
    #     'release_date': '2026-03-01',
    #     'documentation': '/api/docs/',
    #     'deprecated': False,
    #     'sunset_date': None,
    # },
}


def get_api_version_info():
    """Return information about available API versions."""
    return API_VERSION_INFO
