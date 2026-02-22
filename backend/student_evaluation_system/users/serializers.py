from rest_framework import serializers
from .models import CustomUser, StudentProfile, InstructorProfile
from core.models import Department, University


class CustomUserSerializer(serializers.ModelSerializer):
    """Full user serializer with all fields."""

    department = serializers.StringRelatedField(read_only=True)
    university = serializers.StringRelatedField(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source="department", write_only=True, required=False, allow_null=True
    )
    university_id = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.all(), source="university", write_only=True, required=False, allow_null=True
    )

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
            "department_id",
            "university",
            "university_id",
            "is_active",
            "is_staff",
            "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]


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
        queryset=__import__("core.models", fromlist=["Term"]).Term.objects.all(),
        source="enrollment_term",
        write_only=True,
        required=False,
        allow_null=True,
    )
    program_id = serializers.PrimaryKeyRelatedField(
        queryset=__import__("core.models", fromlist=["Program"]).Program.objects.all(),
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
