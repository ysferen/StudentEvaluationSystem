import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from users.models import InstructorProfile, DepartmentHeadProfile
from core.models import (
    University,
    Department,
    DegreeLevel,
    Program,
    Term,
    InstructorPermission,
    ResourceArea,
    PermissionTier,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def setup_data(db):
    university = University.objects.create(name="Test University")
    dept = Department.objects.create(
        name="Engineering", code="ENG", university=university
    )
    degree = DegreeLevel.objects.create(name="Bachelor")
    program = Program.objects.create(
        name="Computer Engineering",
        code="CSE",
        degree_level=degree,
        department=dept,
    )
    term = Term.objects.create(name="Spring 2026", is_active=True)

    head_user = User.objects.create_user(
        username="headuser",
        password="headpass123",
        role="department_head",
        department=dept,
    )
    head_profile = DepartmentHeadProfile.objects.create(
        user=head_user, department=dept
    )

    instructor_user = User.objects.create_user(
        username="instruser",
        password="instrpass123",
        role="instructor",
        department=dept,
        university=university,
    )
    instructor_profile = InstructorProfile.objects.create(
        user=instructor_user, title="Professor"
    )

    admin_user = User.objects.create_user(
        username="adminuser",
        password="adminpass123",
        role="admin",
        is_staff=True,
    )

    return {
        "university": university,
        "department": dept,
        "program": program,
        "term": term,
        "head_user": head_user,
        "head_profile": head_profile,
        "instructor_user": instructor_user,
        "instructor_profile": instructor_profile,
        "admin_user": admin_user,
    }


class TestDepartmentHeadAPI:
    def test_admin_can_list_heads(self, api_client, setup_data):
        api_client.force_authenticate(user=setup_data["admin_user"])
        response = api_client.get("/api/v1/users/heads/")
        assert response.status_code == 200

    def test_head_cannot_list_heads(self, api_client, setup_data):
        api_client.force_authenticate(user=setup_data["head_user"])
        response = api_client.get("/api/v1/users/heads/")
        assert response.status_code == 403

    def test_instructor_cannot_list_heads(self, api_client, setup_data):
        api_client.force_authenticate(user=setup_data["instructor_user"])
        response = api_client.get("/api/v1/users/heads/")
        assert response.status_code == 403

    def test_unauthenticated_cannot_list_heads(self, api_client, db):
        response = api_client.get("/api/v1/users/heads/")
        assert response.status_code in (401, 403)


class TestInstructorPermissionAPI:
    def test_admin_can_list_permissions(self, api_client, setup_data):
        InstructorPermission.objects.create(
            instructor=setup_data["instructor_profile"],
            department_head=setup_data["head_profile"],
            resource_area=ResourceArea.COURSES,
            permission_tier=PermissionTier.EDIT,
        )
        api_client.force_authenticate(user=setup_data["admin_user"])
        response = api_client.get("/api/v1/core/permissions/")
        assert response.status_code == 200

    def test_head_can_list_own_permissions(self, api_client, setup_data):
        InstructorPermission.objects.create(
            instructor=setup_data["instructor_profile"],
            department_head=setup_data["head_profile"],
            resource_area=ResourceArea.COURSES,
            permission_tier=PermissionTier.EDIT,
        )
        api_client.force_authenticate(user=setup_data["head_user"])
        response = api_client.get("/api/v1/core/permissions/")
        assert response.status_code == 200

    def test_instructor_can_view_own_permissions(
        self, api_client, setup_data
    ):
        InstructorPermission.objects.create(
            instructor=setup_data["instructor_profile"],
            department_head=setup_data["head_profile"],
            resource_area=ResourceArea.COURSES,
            permission_tier=PermissionTier.EDIT,
        )
        api_client.force_authenticate(user=setup_data["instructor_user"])
        response = api_client.get(
            "/api/v1/core/permissions/my-permissions/"
        )
        assert response.status_code == 200

    def test_instructor_cannot_create_permission(self, api_client, setup_data):
        api_client.force_authenticate(user=setup_data["instructor_user"])
        response = api_client.post(
            "/api/v1/core/permissions/",
            {
                "instructor_id": setup_data["instructor_profile"].id,
                "resource_area": "courses",
                "permission_tier": "edit",
            },
            format="json",
        )
        assert response.status_code == 403

    def test_head_can_set_permissions_bulk(self, api_client, setup_data):
        api_client.force_authenticate(user=setup_data["head_user"])
        response = api_client.put(
            "/api/v1/core/permissions/bulk/",
            {
                "instructor_id": setup_data[
                    "instructor_profile"
                ].id,
                "permissions": [
                    {
                        "resource_area": "courses",
                        "permission_tier": "edit",
                    },
                    {
                        "resource_area": "programs",
                        "permission_tier": "view",
                    },
                ],
            },
            format="json",
        )
        assert response.status_code == 200

    def test_admin_can_set_permissions_bulk(self, api_client, setup_data):
        api_client.force_authenticate(user=setup_data["admin_user"])
        response = api_client.put(
            "/api/v1/core/permissions/bulk/",
            {
                "instructor_id": setup_data[
                    "instructor_profile"
                ].id,
                "permissions": [
                    {
                        "resource_area": "courses",
                        "permission_tier": "full",
                    },
                ],
            },
            format="json",
        )
        assert response.status_code == 200

    def test_bulk_set_requires_instructor_id(
        self, api_client, setup_data
    ):
        api_client.force_authenticate(user=setup_data["admin_user"])
        response = api_client.put(
            "/api/v1/core/permissions/bulk/",
            {"permissions": []},
            format="json",
        )
        assert response.status_code == 400

    def test_my_permissions_returns_forbidden_for_non_instructor(
        self, api_client, setup_data
    ):
        api_client.force_authenticate(user=setup_data["head_user"])
        response = api_client.get(
            "/api/v1/core/permissions/my-permissions/"
        )
        assert response.status_code == 403


class TestSeedData:
    def test_seed_command_creates_department_head(self, db):
        from django.core.management import call_command
        call_command("seed_data")
        from users.models import CustomUser, DepartmentHeadProfile
        head_user = CustomUser.objects.filter(username="headuser").first()
        assert head_user is not None
        assert head_user.role == "department_head"
        assert DepartmentHeadProfile.objects.filter(user=head_user).exists()