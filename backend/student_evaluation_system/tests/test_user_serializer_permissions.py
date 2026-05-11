import pytest
from users.serializers import CustomUserSerializer
from core.models import InstructorPermission, ResourceArea, PermissionTier


@pytest.fixture
def admin_user(db, admin_user_factory):
    return admin_user_factory(role="admin")


@pytest.fixture
def instructor_user(db, instructor_user_factory):
    return instructor_user_factory(role="instructor")


@pytest.fixture
def student_user(db, student_user_factory):
    return student_user_factory(role="student")


@pytest.mark.django_db
def test_serializer_permissions_for_admin(admin_user):
    ser = CustomUserSerializer(admin_user)
    perms = ser.data["permissions"]
    assert "courses.change_course" in perms
    assert "courses.delete_course" in perms
    assert "courses.add_course" in perms
    assert "courses.view_course" in perms


@pytest.mark.django_db
def test_serializer_permissions_for_instructor_with_edit_tier(instructor_user):
    InstructorPermission.objects.create(
        instructor=instructor_user.instructor_profile,
        resource_area=ResourceArea.COURSES,
        permission_tier=PermissionTier.EDIT,
    )
    ser = CustomUserSerializer(instructor_user)
    perms = ser.data["permissions"]
    assert "courses.change_course" in perms
    assert "courses.view_course" in perms
    assert "courses.delete_course" not in perms
    assert "courses.add_course" not in perms


@pytest.mark.django_db
def test_serializer_permissions_for_instructor_with_full_tier(instructor_user):
    InstructorPermission.objects.create(
        instructor=instructor_user.instructor_profile,
        resource_area=ResourceArea.COURSES,
        permission_tier=PermissionTier.FULL,
    )
    ser = CustomUserSerializer(instructor_user)
    perms = ser.data["permissions"]
    assert "courses.change_course" in perms
    assert "courses.delete_course" in perms
    assert "courses.add_course" in perms
    assert "courses.view_course" in perms


@pytest.mark.django_db
def test_serializer_permissions_for_instructor_without_tier(instructor_user):
    # No InstructorPermission row created → defaults to "view"
    ser = CustomUserSerializer(instructor_user)
    perms = ser.data["permissions"]
    assert "courses.view_course" in perms
    assert "courses.change_course" not in perms
    assert "courses.delete_course" not in perms
    assert "courses.add_course" not in perms


@pytest.mark.django_db
def test_serializer_permissions_for_student(student_user):
    ser = CustomUserSerializer(student_user)
    perms = ser.data["permissions"]
    assert "courses.view_course" in perms
    assert "courses.change_course" not in perms
    assert "courses.delete_course" not in perms
    assert "courses.add_course" not in perms
