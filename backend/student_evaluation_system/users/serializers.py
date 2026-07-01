from rest_framework import serializers
from .models import CustomUser, StudentProfile, InstructorProfile, ProgramHeadProfile
from core.models import Department, Program, Term, University
from core.models import ResourceArea
from core.permissions import get_instructor_permission_tier


class CustomUserSerializer(serializers.ModelSerializer):
    """Full user serializer with all fields."""

    department = serializers.StringRelatedField(read_only=True)
    university = serializers.StringRelatedField(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source="department", required=False, allow_null=True
    )
    university_id = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.all(), source="university", write_only=True, required=False, allow_null=True
    )
    permissions = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()

    def get_title(self, obj):
        profile = getattr(obj, "instructor_profile", None)
        return profile.title if profile else ""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_superuser:
            data["role"] = "admin"
        return data

    def get_permissions(self, obj):
        """Return effective permission codenames for the user.

        Combines Django's built-in permissions with synthesized permissions
        derived from the instructor permission tier system. This allows the
        frontend to check for standard codenames like
        ``courses.change_course`` even when the backend uses tier-based
        access control.
        """
        perms = set(obj.get_all_permissions())

        # Mapping from resource area code to the singular model name used in
        # Django-style permission codenames (e.g. ``courses`` → ``course``).
        MODEL_SUFFIX = {
            "courses": "course",
            "programs": "program",
            "learning_outcomes": "learningoutcome",
            "program_outcomes": "programoutcome",
            "students": "student",
            "lo_po_weights": "learningoutcomeprogramoutcomemapping",
            "assessment_lo_weights": "assessmentlearningoutcomemapping",
            "assessments": "assessment",
            "course_templates": "coursetemplate",
        }

        for area_code, _area_label in ResourceArea.choices:
            tier = get_instructor_permission_tier(obj, area_code)
            model = MODEL_SUFFIX.get(area_code, area_code)

            if tier in ("view", "edit", "full"):
                perms.add(f"{area_code}.view_{model}")
            if tier in ("edit", "full"):
                perms.add(f"{area_code}.change_{model}")
            if tier == "full":
                perms.add(f"{area_code}.delete_{model}")
                perms.add(f"{area_code}.add_{model}")

        # Also translate real Django permissions (e.g. ``core.change_course``)
        # into the resource-area format (``courses.change_course``) so that
        # superusers and staff users with explicit Django permissions are
        # recognised by the frontend checks.
        DJANGO_TO_RESOURCE = {
            "core.add_course": "courses.add_course",
            "core.change_course": "courses.change_course",
            "core.delete_course": "courses.delete_course",
            "core.view_course": "courses.view_course",
            "core.add_program": "programs.add_program",
            "core.change_program": "programs.change_program",
            "core.delete_program": "programs.delete_program",
            "core.view_program": "programs.view_program",
            "core.add_learningoutcome": "learning_outcomes.add_learningoutcome",
            "core.change_learningoutcome": "learning_outcomes.change_learningoutcome",
            "core.delete_learningoutcome": "learning_outcomes.delete_learningoutcome",
            "core.view_learningoutcome": "learning_outcomes.view_learningoutcome",
            "core.add_programoutcome": "program_outcomes.add_programoutcome",
            "core.change_programoutcome": "program_outcomes.change_programoutcome",
            "core.delete_programoutcome": "program_outcomes.delete_programoutcome",
            "core.view_programoutcome": "program_outcomes.view_programoutcome",
            "evaluation.add_assessment": "assessments.add_assessment",
            "evaluation.change_assessment": "assessments.change_assessment",
            "evaluation.delete_assessment": "assessments.delete_assessment",
            "evaluation.view_assessment": "assessments.view_assessment",
            "core.add_coursetemplate": "course_templates.add_coursetemplate",
            "core.change_coursetemplate": "course_templates.change_coursetemplate",
            "core.delete_coursetemplate": "course_templates.delete_coursetemplate",
            "core.view_coursetemplate": "course_templates.view_coursetemplate",
        }
        for django_perm, resource_perm in DJANGO_TO_RESOURCE.items():
            if django_perm in perms:
                perms.add(resource_perm)

        return sorted(perms)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "title",
            "department",
            "department_id",
            "university",
            "university_id",
            "is_active",
            "is_staff",
            "must_change_password",
            "date_joined",
            "permissions",
        ]
        read_only_fields = ["id", "date_joined", "permissions", "must_change_password", "title"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "username", "email", "first_name", "last_name", "role"]
        read_only_fields = ["id"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})
    password2 = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}, label="Confirm Password"
    )

    class Meta:
        model = CustomUser
        fields = ["username", "email", "password", "password2", "first_name", "last_name", "role"]

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        return data

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user


class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    enrollment_term = serializers.StringRelatedField(read_only=True)
    program = serializers.StringRelatedField(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), source="user", write_only=True)
    enrollment_term_id = serializers.PrimaryKeyRelatedField(
        queryset=Term.objects.all(),
        source="enrollment_term",
        write_only=True,
        required=False,
        allow_null=True,
    )
    program_id = serializers.PrimaryKeyRelatedField(
        queryset=Program.objects.all(),
        source="program",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = StudentProfile
        fields = ["id", "user", "user_id", "student_id", "enrollment_term", "enrollment_term_id", "program", "program_id"]


class InstructorProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), source="user", write_only=True)

    class Meta:
        model = InstructorProfile
        fields = ["id", "user", "user_id", "title"]


class ProgramHeadProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        source="user",
        write_only=True,
    )
    program = serializers.StringRelatedField(read_only=True)
    program_id = serializers.PrimaryKeyRelatedField(
        queryset=Program.objects.all(),
        source="program",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ProgramHeadProfile
        fields = [
            "id",
            "user",
            "user_id",
            "program",
            "program_id",
            "department",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    department = serializers.CharField(source="user.department", read_only=True)


class UserDetailSerializer(serializers.ModelSerializer):
    department = serializers.StringRelatedField()
    university = serializers.StringRelatedField()
    student_profile = StudentProfileSerializer(source="studentprofile", read_only=True)
    instructor_profile = InstructorProfileSerializer(source="instructorprofile", read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "department",
            "university",
            "student_profile",
            "instructor_profile",
        ]
