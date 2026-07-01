"""
Tests for users app models.

This module tests the models in the users app including:
- CustomUser
- StudentProfile
- InstructorProfile
"""

import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from users.models import StudentProfile, InstructorProfile

User = get_user_model()


@pytest.mark.django_db
class TestCustomUser:
    """Tests for CustomUser model."""

    def test_create_user(self, db_setup):
        """Test creating a standard user."""
        university = db_setup["university"]
        department = db_setup["department"]

        user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass123",  # nosec
            first_name="Test",
            last_name="User",
            university=university,
            department=department,
        )

        assert user.username == "testuser"
        assert user.email == "test@test.com"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.university == university
        assert user.department == department
        assert user.role == "guest"  # default role
        assert user.check_password("testpass123")

    def test_create_user_with_role(self, db_setup):
        """Test creating a user with specific role."""
        university = db_setup["university"]
        department = db_setup["department"]

        student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="testpass123",  # nosec
            role="student",
            university=university,
            department=department,
        )

        assert student.role == "student"
        assert student.is_student is True
        assert student.is_instructor is False

    def test_is_student_property(self, db_setup):
        """Test the is_student property."""
        university = db_setup["university"]
        department = db_setup["department"]

        student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="testpass123",  # nosec
            role="student",
            university=university,
            department=department,
        )

        instructor = User.objects.create_user(
            username="instructor1",
            email="instructor@test.com",
            password="testpass123",  # nosec
            role="instructor",
            university=university,
            department=department,
        )

        assert student.is_student is True
        assert instructor.is_student is False

    def test_is_instructor_property(self, db_setup):
        """Test the is_instructor property."""
        university = db_setup["university"]
        department = db_setup["department"]

        instructor = User.objects.create_user(
            username="instructor1",
            email="instructor@test.com",
            password="testpass123",  # nosec
            role="instructor",
            university=university,
            department=department,
        )

        student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="testpass123",  # nosec
            role="student",
            university=university,
            department=department,
        )

        assert instructor.is_instructor is True
        assert student.is_instructor is False

    def test_is_admin_user_property(self, db_setup):
        """Test the is_admin_user property."""
        university = db_setup["university"]
        department = db_setup["department"]

        admin = User.objects.create_user(
            username="admin1",
            email="admin@test.com",
            password="testpass123",  # nosec
            role="admin",
            university=university,
            department=department,
        )

        student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="testpass123",  # nosec
            role="student",
            university=university,
            department=department,
        )

        assert admin.is_admin_user is True
        assert student.is_admin_user is False

    def test_user_str_with_full_name(self, db_setup):
        """Test __str__ method when user has full name."""
        university = db_setup["university"]
        department = db_setup["department"]

        user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass123",  # nosec
            first_name="John",
            last_name="Doe",
            role="student",
            university=university,
            department=department,
        )

        str_repr = str(user)
        assert "John Doe" in str_repr
        assert "student" in str_repr

    def test_user_str_without_full_name(self, db_setup):
        """Test __str__ method when user doesn't have full name."""
        university = db_setup["university"]
        department = db_setup["department"]

        user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass123",  # nosec
            role="student",
            university=university,
            department=department,
        )

        str_repr = str(user)
        assert "testuser" in str_repr
        assert "student" in str_repr


@pytest.mark.django_db
class TestStudentProfile:
    """Tests for StudentProfile model."""

    def test_create_student_profile(self, db_setup, user_factory):
        """Test creating a student profile."""
        user = user_factory("student1", role="student")
        term = db_setup["term"]
        program = db_setup["program"]

        profile = StudentProfile.objects.create(user=user, student_id="S12345", enrollment_term=term, program=program)

        assert profile.user == user
        assert profile.student_id == "S12345"
        assert profile.enrollment_term == term
        assert profile.program == program
        assert str(profile) == "Test User (S12345)"

    def test_student_profile_unique_student_id(self, db_setup, user_factory):
        """Test that student_id must be unique."""
        term = db_setup["term"]
        program = db_setup["program"]

        StudentProfile.objects.create(
            user=user_factory("student1", role="student"), student_id="S12345", enrollment_term=term, program=program
        )

        # Try to create duplicate student_id
        with pytest.raises(Exception):  # IntegrityError
            StudentProfile.objects.create(
                user=user_factory("student2", role="student"), student_id="S12345", enrollment_term=term, program=program
            )

    def test_student_profile_one_to_one_user(self, db_setup, user_factory):
        """Test that one user can have only one student profile."""
        user = user_factory("student1", role="student")
        term = db_setup["term"]
        program = db_setup["program"]

        StudentProfile.objects.create(user=user, student_id="S12345", enrollment_term=term, program=program)

        # Try to create another profile for same user
        with pytest.raises(Exception):  # IntegrityError
            StudentProfile.objects.create(user=user, student_id="S67890", enrollment_term=term, program=program)

    def test_student_profile_validation_requires_student_role(self, db_setup, user_factory):
        """Test that user must have student role."""
        user = user_factory("instructor1", role="instructor")
        term = db_setup["term"]
        program = db_setup["program"]

        profile = StudentProfile(user=user, student_id="S12345", enrollment_term=term, program=program)

        with pytest.raises(ValidationError, match="must have student role"):
            profile.full_clean()

    def test_full_name_property(self, db_setup, user_factory):
        """Test the full_name property."""
        user = user_factory("student1", role="student", first_name="Jane", last_name="Smith")
        term = db_setup["term"]
        program = db_setup["program"]

        profile = StudentProfile.objects.create(user=user, student_id="S12345", enrollment_term=term, program=program)

        assert profile.full_name == "Jane Smith"

    def test_full_name_property_when_no_names(self, db_setup, user_factory):
        """Test full_name property when user has no first/last name."""
        user = user_factory("student1", role="student", first_name="", last_name="")
        term = db_setup["term"]
        program = db_setup["program"]

        profile = StudentProfile.objects.create(user=user, student_id="S12345", enrollment_term=term, program=program)

        # Should fallback to username
        assert profile.full_name == "student1"


@pytest.mark.django_db
class TestInstructorProfile:
    """Tests for InstructorProfile model."""

    def test_create_instructor_profile(self, user_factory):
        """Test creating an instructor profile."""
        user = user_factory("instructor1", role="instructor", first_name="John", last_name="Doe")

        profile = InstructorProfile.objects.create(user=user, title="Professor")

        assert profile.user == user
        assert profile.title == "Professor"
        assert "Professor John Doe" in str(profile)

    def test_instructor_profile_one_to_one_user(self, user_factory):
        """Test that one user can have only one instructor profile."""
        user = user_factory("instructor1", role="instructor")

        InstructorProfile.objects.create(user=user, title="Professor")

        # Try to create another profile for same user
        with pytest.raises(Exception):  # IntegrityError
            InstructorProfile.objects.create(user=user, title="Associate Professor")

    def test_instructor_profile_validation_requires_teaching_role(self, user_factory):
        """Test that user must have instructor role."""
        user = user_factory("student1", role="student")

        profile = InstructorProfile(user=user, title="Professor")

        with pytest.raises(ValidationError, match="must have instructor or program head role"):
            profile.full_clean()

    def test_full_name_property(self, user_factory):
        """Test the full_name property."""
        user = user_factory("instructor1", role="instructor", first_name="Jane", last_name="Smith")

        profile = InstructorProfile.objects.create(user=user, title="Dr.")

        assert profile.full_name == "Jane Smith"

    def test_full_name_property_when_no_names(self, user_factory):
        """Test full_name property when user has no first/last name."""
        user = user_factory("instructor1", role="instructor", first_name="", last_name="")

        profile = InstructorProfile.objects.create(user=user, title="Professor")

        # Should fallback to username
        assert profile.full_name == "instructor1"

    def test_str_with_title(self, user_factory):
        """Test __str__ method includes title."""
        user = user_factory("instructor1", role="instructor", first_name="John", last_name="Doe")

        profile = InstructorProfile.objects.create(user=user, title="Dr.")

        str_repr = str(profile)
        assert "Dr." in str_repr
        assert "John Doe" in str_repr

    def test_str_without_title(self, user_factory):
        """Test __str__ method without title."""
        user = user_factory("instructor1", role="instructor", first_name="John", last_name="Doe")

        profile = InstructorProfile.objects.create(user=user, title="")

        str_repr = str(profile)
        assert "John Doe" in str_repr
        assert "Dr." not in str_repr


@pytest.mark.django_db
class TestUserModelRelationships:
    """Tests for relationships between User and other models."""

    def test_user_university_foreign_key(self, db_setup, user_factory):
        """Test User-University relationship."""
        university = db_setup["university"]
        user = user_factory("testuser", role="student")

        assert user.university == university
        assert university.users.filter(pk=user.pk).exists()

    def test_user_department_foreign_key(self, db_setup, user_factory):
        """Test User-Department relationship."""
        department = db_setup["department"]
        user = user_factory("testuser", role="instructor")

        assert user.department == department
        assert department.users.filter(pk=user.pk).exists()

    def test_user_taught_courses(self, db_setup, user_factory):
        """Test User-Course relationship through instructors."""
        course = db_setup["course"]
        instructor = user_factory("instructor1", role="instructor")

        course.instructors.add(instructor)

        assert instructor in course.instructors.all()
        assert course in instructor.taught_courses.all()

    def test_user_created_learning_outcomes(self, db_setup, user_factory):
        """Test User-LearningOutcome relationship through created_by."""
        user = user_factory("instructor1", role="instructor")
        course = db_setup["course"]

        from core.models import LearningOutcome

        lo = LearningOutcome.objects.create(code="LO1", description="Test outcome", course=course, created_by=user)

        assert lo in user.created_learning_outcomes.all()
        assert user == lo.created_by

    def test_user_created_program_outcomes(self, db_setup, user_factory):
        """Test User-ProgramOutcome relationship through created_by."""
        user = user_factory("admin1", role="admin")
        program = db_setup["program"]
        term = db_setup["term"]

        from core.models import ProgramOutcome

        po = ProgramOutcome.objects.create(code="PO1", description="Test PO", program=program, term=term, created_by=user)

        assert po in user.created_program_outcomes.all()
        assert user == po.created_by


@pytest.mark.django_db
class TestProgramHeadRole:
    def test_program_head_is_valid_role(self, db):
        from users.models import CustomUser

        user = CustomUser.objects.create_user(username="headtest", password="pass", role="program_head")  # nosec
        assert user.role == "program_head"

    def test_is_program_head_property_returns_true(self, db):
        from users.models import CustomUser

        user = CustomUser.objects.create_user(username="headtest", password="pass", role="program_head")  # nosec
        assert user.is_program_head is True

    def test_is_program_head_property_returns_false_for_other_roles(self, db):
        from users.models import CustomUser

        student = CustomUser.objects.create_user(username="studenttest", password="pass", role="student")  # nosec
        assert student.is_program_head is False
        instructor = CustomUser.objects.create_user(username="instrtest", password="pass", role="instructor")  # nosec
        assert instructor.is_program_head is False
        admin = CustomUser.objects.create_user(username="admintest", password="pass", role="admin")  # nosec
        assert admin.is_program_head is False


@pytest.mark.django_db
class TestProgramHeadProfile:
    @pytest.fixture
    def setup_data(self, db):
        from core.models import University, Department, DegreeLevel, Program

        university = University.objects.create(name="Test Uni")
        dept = Department.objects.create(name="Test Dept", code="TD", university=university)
        degree = DegreeLevel.objects.create(name="Bachelor")
        program = Program.objects.create(name="Test Program", code="TP", department=dept, degree_level=degree)
        return {"university": university, "department": dept, "program": program}

    def test_create_program_head_profile(self, setup_data):
        from users.models import CustomUser, ProgramHeadProfile

        program = setup_data["program"]
        user = CustomUser.objects.create_user(
            username="head1", password="pass", role="program_head", department=program.department
        )  # nosec
        profile = ProgramHeadProfile.objects.create(user=user, program=program)
        assert profile.user == user
        assert profile.program == program
        assert profile.full_name == user.get_full_name() or user.username

    def test_program_head_profile_str_representation(self, setup_data):
        from users.models import CustomUser, ProgramHeadProfile

        program = setup_data["program"]
        user = CustomUser.objects.create_user(
            username="head1",
            password="pass",  # nosec
            role="program_head",
            first_name="Jane",
            last_name="Doe",
            department=program.department,
        )
        profile = ProgramHeadProfile.objects.create(user=user, program=program)
        assert "Jane" in str(profile)
        assert program.name in str(profile)

    def test_program_head_profile_validates_role(self, setup_data):
        from users.models import CustomUser, ProgramHeadProfile
        from django.core.exceptions import ValidationError

        program = setup_data["program"]
        user = CustomUser.objects.create_user(username="not_head", password="pass", role="instructor")  # nosec
        profile = ProgramHeadProfile(user=user, program=program)
        with pytest.raises(ValidationError):
            profile.clean()

    def test_one_head_per_program_enforced(self, setup_data):
        from users.models import CustomUser, ProgramHeadProfile
        from django.db import IntegrityError

        program = setup_data["program"]
        user1 = CustomUser.objects.create_user(
            username="head1", password="pass", role="program_head", department=program.department
        )  # nosec
        ProgramHeadProfile.objects.create(user=user1, program=program)
        user2 = CustomUser.objects.create_user(
            username="head2", password="pass", role="program_head", department=program.department
        )  # nosec
        with pytest.raises(IntegrityError):
            ProgramHeadProfile.objects.create(user=user2, program=program)

    def test_program_head_profile_created_at_auto_set(self, setup_data):
        from users.models import CustomUser, ProgramHeadProfile

        program = setup_data["program"]
        user = CustomUser.objects.create_user(
            username="head1", password="pass", role="program_head", department=program.department
        )  # nosec
        profile = ProgramHeadProfile.objects.create(user=user, program=program)
        assert profile.created_at is not None


@pytest.mark.django_db
class TestInstructorPermission:
    @pytest.fixture
    def setup_profiles(self, db):
        from users.models import CustomUser, InstructorProfile, ProgramHeadProfile
        from core.models import University, Department, DegreeLevel, Program

        university = University.objects.create(name="Test Uni")
        dept = Department.objects.create(name="Test Dept", code="TD", university=university)
        degree = DegreeLevel.objects.create(name="Bachelor")
        program = Program.objects.create(name="Test Program", code="TP", department=dept, degree_level=degree)
        instr_user = CustomUser.objects.create_user(username="instr1", password="pass", role="instructor")  # nosec
        instr_profile = InstructorProfile.objects.create(user=instr_user, title="Prof")
        head_user = CustomUser.objects.create_user(
            username="head1",
            password="pass",  # nosec
            role="program_head",
            department=dept,
        )
        head_profile = ProgramHeadProfile.objects.create(user=head_user, program=program)
        return {
            "program": program,
            "instructor_profile": instr_profile,
            "head_profile": head_profile,
        }

    def test_create_instructor_permission(self, setup_profiles):
        from core.models import InstructorPermission

        perm = InstructorPermission.objects.create(
            instructor=setup_profiles["instructor_profile"],
            program_head=setup_profiles["head_profile"],
            resource_area="courses",
            permission_tier="edit",
        )
        assert perm.resource_area == "courses"
        assert perm.permission_tier == "edit"

    def test_default_permission_tier_is_view(self, setup_profiles):
        from core.models import InstructorPermission

        perm = InstructorPermission.objects.create(
            instructor=setup_profiles["instructor_profile"],
            program_head=setup_profiles["head_profile"],
            resource_area="programs",
        )
        assert perm.permission_tier == "view"

    def test_unique_together_instructor_resource_area(self, setup_profiles):
        from core.models import InstructorPermission
        from django.db import IntegrityError

        InstructorPermission.objects.create(
            instructor=setup_profiles["instructor_profile"],
            program_head=setup_profiles["head_profile"],
            resource_area="courses",
            permission_tier="edit",
        )
        with pytest.raises(IntegrityError):
            InstructorPermission.objects.create(
                instructor=setup_profiles["instructor_profile"],
                program_head=setup_profiles["head_profile"],
                resource_area="courses",
                permission_tier="full",
            )

    def test_all_resource_areas_are_valid(self, setup_profiles):
        from core.models import ResourceArea, InstructorPermission

        for area in ResourceArea.values:
            InstructorPermission.objects.create(
                instructor=setup_profiles["instructor_profile"],
                program_head=setup_profiles["head_profile"],
                resource_area=area,
            )
            assert InstructorPermission.objects.filter(resource_area=area).exists()
            InstructorPermission.objects.filter(resource_area=area).delete()

    def test_str_representation(self, setup_profiles):
        from core.models import InstructorPermission

        perm = InstructorPermission.objects.create(
            instructor=setup_profiles["instructor_profile"],
            program_head=setup_profiles["head_profile"],
            resource_area="courses",
            permission_tier="edit",
        )
        assert "courses" in str(perm).lower() or "Courses" in str(perm)
