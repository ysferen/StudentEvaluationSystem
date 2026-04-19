"""
Workflow tests for authentication and token handling.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestAuthenticationWorkflows:
    def test_login_and_access_protected_endpoint(self, api_client, fb_user_factory):
        fb_user_factory(username="testuser", password="testpass123")

        login_data = {
            "username": "testuser",
            "password": "testpass123",
        }
        response = api_client.post("/api/v1/users/auth/login/", login_data)
        assert response.status_code == status.HTTP_200_OK
        assert "user" in response.data
        assert response.cookies["access_token"].value
        assert response.cookies["refresh_token"].value

        token = response.cookies["access_token"].value
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = api_client.get("/api/v1/users/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "testuser"

    def test_unauthorized_access_denied(self, api_client):
        response = api_client.get("/api/v1/core/courses/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh(self, api_client, fb_user_factory):
        user = fb_user_factory()
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        refresh_token = str(refresh)
        api_client.cookies["refresh_token"] = refresh_token

        response = api_client.post("/api/v1/users/auth/refresh/", {})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
