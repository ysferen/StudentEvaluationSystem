import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import Department, DegreeLevel, Program, University
from users.authentication import CookieJWTAuthentication
from users.models import InstructorProfile, ProgramHeadProfile, StudentProfile


User = get_user_model()


@pytest.fixture
def departments(db):
    university = University.objects.create(name="Local", code="LOCAL")
    first = Department.objects.create(name="Computing", code="CSE", university=university)
    second = Department.objects.create(name="Mathematics", code="MATH", university=university)
    degree = DegreeLevel.objects.create(name="Bachelor", level=1)
    program = Program.objects.create(name="Computer Engineering", code="CENG", department=first, degree_level=degree)
    return first, second, program


@pytest.mark.django_db
def test_admin_provisions_staff_and_returns_password_once(departments):
    department, _, _ = departments
    admin = User.objects.create_superuser("admin", "admin@example.com", "password")
    client = APIClient()
    client.force_authenticate(admin)

    response = client.post(
        "/api/users/users/staff/",
        {"username": "head", "role": "program_head", "department_id": department.id, "title": "Professor"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["temporary_password"]
    user = User.objects.get(username="head")
    assert user.must_change_password is True
    assert user.check_password(response.data["temporary_password"])
    assert ProgramHeadProfile.objects.filter(user=user).exists()
    assert user.program_head_profile.program.department == department
    assert user.instructor_profile.title == "Professor"


@pytest.mark.django_db
def test_head_can_only_create_instructor_in_own_department(departments):
    department, other_department, _ = departments
    head = User.objects.create_user("head", password="password", role="program_head", department=department)
    ProgramHeadProfile.objects.create(user=head)
    client = APIClient()
    client.force_authenticate(head)

    response = client.post(
        "/api/users/users/staff/",
        {"username": "teacher", "role": "instructor", "department_id": other_department.id},
        format="json",
    )

    assert response.status_code == 201
    teacher = User.objects.get(username="teacher")
    assert teacher.department == department
    assert InstructorProfile.objects.filter(user=teacher).exists()


@pytest.mark.django_db
def test_head_impersonates_only_department_student(departments):
    department, other_department, program = departments
    head = User.objects.create_user("head", password="password", role="program_head", department=department)
    ProgramHeadProfile.objects.create(user=head)
    student = User.objects.create_user("student", role="student")
    StudentProfile.objects.create(user=student, student_id="1", program=program)
    outsider = User.objects.create_user("outsider", role="student", department=other_department)
    client = APIClient()
    client.force_authenticate(head)

    response = client.post(f"/api/users/users/{student.id}/impersonate/")
    denied = client.post(f"/api/users/users/{outsider.id}/impersonate/")
    reset = client.post(f"/api/users/users/{student.id}/reset-temporary-password/")

    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert "impersonator" in response.cookies
    assert denied.status_code == 404
    assert reset.status_code == 200
    assert reset.data["temporary_password"]


@pytest.mark.django_db
def test_temporary_password_blocks_normal_api(departments):
    department, _, _ = departments
    user = User.objects.create_user(
        "teacher", password="temporary-password", role="instructor", department=department, must_change_password=True
    )
    token = RefreshToken.for_user(user).access_token
    factory = APIRequestFactory()
    request = factory.get("/api/core/courses/")
    request.COOKIES["access_token"] = str(token)

    with pytest.raises(AuthenticationFailed, match="Password change required"):
        CookieJWTAuthentication().authenticate(request)

    allowed = factory.get("/api/users/auth/me/")
    allowed.COOKIES["access_token"] = str(token)
    assert CookieJWTAuthentication().authenticate(allowed)[0] == user


@pytest.mark.django_db
def test_user_directory_is_not_public_and_roles_are_admin_only(departments):
    department, _, _ = departments
    teacher = User.objects.create_user("teacher", password="password", role="instructor", department=department)
    client = APIClient()
    assert client.get("/api/users/users/").status_code == 401
    client.force_authenticate(teacher)
    assert client.patch(f"/api/users/users/{teacher.id}/", {"role": "admin"}, format="json").status_code == 403


@pytest.mark.django_db
def test_head_can_return_from_student_session(departments):
    department, _, program = departments
    head = User.objects.create_user("head", password="Strong-pass-129!", role="program_head", department=department)
    ProgramHeadProfile.objects.create(user=head)
    student = User.objects.create_user("student", role="student")
    StudentProfile.objects.create(user=student, student_id="1", program=program)
    client = APIClient()

    assert (
        client.post("/api/users/auth/login/", {"username": "head", "password": "Strong-pass-129!"}, format="json").status_code
        == 200
    )
    client.get("/api/users/auth/csrf/")
    csrf = client.cookies["csrftoken"].value
    assert client.post(f"/api/users/users/{student.id}/impersonate/", HTTP_X_CSRFTOKEN=csrf).status_code == 200
    response = client.post("/api/users/users/return_from_impersonation/", HTTP_X_CSRFTOKEN=csrf)

    assert response.status_code == 200
    assert response.data["user"]["username"] == "head"
    assert response.cookies["impersonator"].value == ""


@pytest.mark.django_db
def test_admin_edits_and_deletes_staff_profile(departments):
    department, _, _ = departments
    admin = User.objects.create_superuser("admin", "admin@example.com", "password")
    teacher = User.objects.create_user("teacher", role="instructor", department=department)
    InstructorProfile.objects.create(user=teacher, title="Dr.")
    client = APIClient()
    client.force_authenticate(admin)

    response = client.patch(
        f"/api/users/users/{teacher.id}/staff/",
        {"first_name": "Ada", "title": "Professor", "department_id": department.id},
        format="json",
    )
    assert response.status_code == 200
    teacher.refresh_from_db()
    assert teacher.first_name == "Ada"
    assert teacher.instructor_profile.title == "Professor"
    assert response.data["title"] == "Professor"

    assert client.delete(f"/api/users/users/{teacher.id}/staff/").status_code == 204
    assert not User.objects.filter(pk=teacher.id).exists()
