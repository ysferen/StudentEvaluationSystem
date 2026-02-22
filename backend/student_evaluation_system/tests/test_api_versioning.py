"""
Tests for API versioning functionality.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestAPIVersioning:
    """Test API versioning functionality."""

    def test_api_v1_url_accessible(self, api_client, fb_user_factory):
        """Test that versioned API URLs (v1) are accessible."""
        user = fb_user_factory()
        api_client.force_authenticate(user=user)

        # Test that v1 URLs work - use auth/me/ endpoint
        response = api_client.get("/api/v1/users/auth/me/")
        assert response.status_code == status.HTTP_200_OK

    def test_backward_compatibility_non_versioned_url(self, api_client, fb_user_factory):
        """Test that non-versioned URLs still work for backward compatibility."""
        user = fb_user_factory()
        api_client.force_authenticate(user=user)

        # Test that non-versioned URLs still work
        response = api_client.get("/api/users/auth/me/")
        assert response.status_code == status.HTTP_200_OK

    def test_v1_and_non_versioned_return_same_data(self, api_client, fb_user_factory):
        """Test that v1 and non-versioned URLs return the same data."""
        user = fb_user_factory()
        api_client.force_authenticate(user=user)

        response_v1 = api_client.get("/api/v1/users/auth/me/")
        response_non_versioned = api_client.get("/api/users/auth/me/")

        assert response_v1.status_code == status.HTTP_200_OK
        assert response_non_versioned.status_code == status.HTTP_200_OK
        # Both should return the same user data
        assert response_v1.data["id"] == response_non_versioned.data["id"]
        assert response_v1.data["username"] == response_non_versioned.data["username"]

    def test_invalid_version_returns_404(self, api_client, fb_user_factory):
        """Test that invalid API versions return 404."""
        user = fb_user_factory()
        api_client.force_authenticate(user=user)

        # Test that an invalid version returns 404
        response = api_client.get("/api/v999/users/auth/me/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestAPIVersionInfo:
    """Test API version information utilities."""

    def test_api_version_info_structure(self):
        """Test that API version info has correct structure."""
        from core.api_versioning import get_api_version_info

        info = get_api_version_info()
        assert "v1" in info
        assert info["v1"]["status"] == "current"
        assert "release_date" in info["v1"]
        assert "deprecated" in info["v1"]

    def test_v1_is_not_deprecated(self):
        """Test that v1 is not marked as deprecated."""
        from core.api_versioning import API_VERSION_INFO

        assert API_VERSION_INFO["v1"]["deprecated"] is False


@pytest.mark.django_db
class TestVersionedSerializerMixin:
    """Test VersionedSerializerViewMixin functionality."""

    def test_get_versioned_serializer_v1(self):
        """Test that v1 serializer is returned for v1 requests."""
        from core.api_versioning import get_versioned_serializer
        from users.serializers import UserSerializer

        # When only v1 serializer is provided
        result = get_versioned_serializer("v1", UserSerializer)
        assert result == UserSerializer

    def test_get_versioned_serializer_defaults_to_v1(self):
        """Test that v1 serializer is returned when v2 is not provided."""
        from core.api_versioning import get_versioned_serializer
        from users.serializers import UserSerializer

        # When v2 is requested but not provided, should default to v1
        result = get_versioned_serializer("v2", UserSerializer)
        assert result == UserSerializer


@pytest.mark.django_db
class TestCoreAPIEndpointsVersioning:
    """Test that core API endpoints support versioning."""

    def test_core_courses_v1(self, api_client, fb_user_factory, fb_course_factory):
        """Test that core courses endpoint works with v1."""
        user = fb_user_factory(role="admin")
        api_client.force_authenticate(user=user)

        # Create a course
        fb_course_factory()

        response = api_client.get("/api/v1/core/courses/")
        assert response.status_code == status.HTTP_200_OK

    def test_evaluation_assessments_v1(self, api_client, fb_user_factory):
        """Test that evaluation assessments endpoint works with v1."""
        user = fb_user_factory(role="admin")  # Admin can see all assessments
        api_client.force_authenticate(user=user)

        response = api_client.get("/api/v1/evaluation/assessments/")
        assert response.status_code == status.HTTP_200_OK
