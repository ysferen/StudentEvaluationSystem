from rest_framework import serializers
from core.models import (
    Course, ProgramOutcome, Department, University, Term, Program, DegreeLevel,
    LearningOutcome, LearningOutcomeProgramOutcomeMapping,
    StudentLearningOutcomeScore, StudentProgramOutcomeScore
)
from evaluation.models import Assessment, StudentGrade, CourseEnrollment
from users.models import CustomUser
from typing import List, Dict, Any
from drf_spectacular.utils import extend_schema_field

class DepartmentSerializer(serializers.ModelSerializer):
    university = serializers.PrimaryKeyRelatedField(queryset=University.objects.all())

    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'university']

class UniversitySerializer(serializers.ModelSerializer):
    code = serializers.CharField(max_length=10, required=False, allow_blank=True)

    class Meta:
        model = University
        fields = ['id', 'name', 'code']

    def validate_code(self, value: str) -> str:
        """Normalize whitespace-only input so model default/fallback can generate a code."""
        if value is None:
            return value
        return value.strip()

class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = ['id', 'name', 'is_active']

class DegreeLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = DegreeLevel
        fields = ['id', 'name', 'level']

class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = ['id', 'name', 'code', 'department', 'degree_level']

class ProgramOutcomeSerializer(serializers.ModelSerializer):
    program = serializers.PrimaryKeyRelatedField(read_only=True)
    term = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ProgramOutcome
        fields = ['id', 'code', 'description', 'program', 'term', 'weight', 'created_at']

class CourseSerializer(serializers.ModelSerializer):
    program = ProgramSerializer(read_only=True)
    term = TermSerializer(read_only=True)
    program_id = serializers.PrimaryKeyRelatedField(
        queryset=Program.objects.all(), source='program', write_only=True
    )
    term_id = serializers.PrimaryKeyRelatedField(
        queryset=Term.objects.all(), source='term', write_only=True
    )
    instructors = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'code', 'name', 'credits', 'program', 'term', 'program_id', 'term_id', 'instructors', 'created_at']

    @extend_schema_field(List[Dict[str, Any]])
    def get_instructors(self, obj: Course) -> List[Dict[str, Any]]:
        """Get instructor details including name, surname, and title."""
        instructors_data = []
        for user in obj.instructors.all():
            try:
                instructor_profile = user.instructor_profile
                instructors_data.append({
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'title': instructor_profile.title if instructor_profile else ''
                })
            except AttributeError:
                # Handle case where user might not have instructor profile
                instructors_data.append({
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'title': ''
                })
        return instructors_data

class CoreLearningOutcomeSerializer(serializers.ModelSerializer):
    """Renamed to avoid conflicts with evaluation app"""
    course = CourseSerializer(read_only=True)

    class Meta:
        model = LearningOutcome
        fields = ['id', 'code', 'description', 'course', 'created_at']


class LearningOutcomeProgramOutcomeMappingListSerializer(serializers.ListSerializer):
    """
    Custom ListSerializer to validate that weights sum to 1.0
    This is called when many=True is used
    """
    def validate(self, attrs):
        # Calculate total weight
        total_weight = sum(item.get('weight', 0) for item in attrs)

        # Allow 1% tolerance for floating point arithmetic
        if not (0.99 <= total_weight <= 1.01):
            raise serializers.ValidationError(
                {
                    'weights': f"Program Outcome weights must sum to 1.0, but got {total_weight:.4f}. "
                              f"Please adjust the weights so they total exactly 1.0."
                }
            )
        return attrs


class LearningOutcomeProgramOutcomeMappingSerializer(serializers.ModelSerializer):
    learning_outcome = CoreLearningOutcomeSerializer(read_only=True)
    learning_outcome_id = serializers.PrimaryKeyRelatedField(
        queryset=LearningOutcome.objects.all(),
        source='learning_outcome',
        write_only=True,
        required=False
    )
    program_outcome = ProgramOutcomeSerializer(read_only=True)
    program_outcome_id = serializers.PrimaryKeyRelatedField(
        queryset=ProgramOutcome.objects.all(),
        source='program_outcome',
        write_only=True,
        required=False
    )

    class Meta:
        model = LearningOutcomeProgramOutcomeMapping
        fields = ['id', 'course', 'learning_outcome', 'learning_outcome_id', 'program_outcome', 'program_outcome_id', 'weight']

class StudentLearningOutcomeScoreSerializer(serializers.ModelSerializer):
    student = serializers.StringRelatedField()
    student_id = serializers.IntegerField(source='student.id', read_only=True)
    learning_outcome = CoreLearningOutcomeSerializer(read_only=True)

    class Meta:
        model = StudentLearningOutcomeScore
        fields = ['id', 'student', 'student_id', 'learning_outcome', 'score']

class StudentProgramOutcomeScoreSerializer(serializers.ModelSerializer):
    student = serializers.StringRelatedField()
    term = serializers.StringRelatedField()
    program_outcome = ProgramOutcomeSerializer(read_only=True)

    class Meta:
        model = StudentProgramOutcomeScore
        fields = ['id', 'student', 'term', 'program_outcome', 'score']

# Response serializers for file operations
class FileImportResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    results = serializers.DictField()

class FileValidationResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    available_sheets = serializers.ListField(child=serializers.CharField())
    file_info = serializers.DictField()

# Analytics response serializers
class CourseAverageSerializer(serializers.Serializer):
    """Serializer for course average LO scores."""
    course_id = serializers.IntegerField()
    weighted_average = serializers.FloatField(allow_null=True)

class LearningOutcomeAverageSerializer(serializers.Serializer):
    """Serializer for learning outcome average scores."""
    lo_id = serializers.IntegerField()
    lo_code = serializers.CharField()
    lo_description = serializers.CharField()
    avg_score = serializers.FloatField()
