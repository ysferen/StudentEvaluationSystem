"""
Core API serializers for the Student Evaluation System.

This module defines serializers for all core models, handling data validation,
transformation, and representation for API responses. Each serializer corresponds
to a specific model and defines how it is serialized/deserialized.
"""

from rest_framework import serializers
from core.models import (
    Course,
    ProgramOutcome,
    Department,
    University,
    Term,
    Program,
    DegreeLevel,
    LearningOutcome,
    LearningOutcomeProgramOutcomeMapping,
    StudentLearningOutcomeScore,
    StudentProgramOutcomeScore,
)
from typing import List, Dict, Any, Optional
from drf_spectacular.utils import extend_schema_field


class DepartmentSerializer(serializers.ModelSerializer):
    """
    Serializer for Department model.

    Handles serialization of department data including university reference.

    Fields:
        id: Department ID
        name: Department name
        code: Department code
        university: Related university ID
    """

    university = serializers.PrimaryKeyRelatedField(queryset=University.objects.all())

    class Meta:
        model = Department
        fields = ["id", "name", "code", "university"]


class UniversitySerializer(serializers.ModelSerializer):
    """
    Serializer for University model.

    Handles serialization of university data with optional auto-generated code.

    Fields:
        id: University ID
        name: University name
        code: University code (auto-generated if blank)
    """

    code = serializers.CharField(max_length=10, required=False, allow_blank=True)

    class Meta:
        model = University
        fields = ["id", "name", "code"]

    def validate_code(self, value: Optional[str]) -> Optional[str]:
        """
        Normalize whitespace-only input so model default can generate a code.

        Args:
            value: The code value to validate

        Returns:
            Stripped value or None if input was None
        """
        if value is None:
            return value
        return value.strip()


class TermSerializer(serializers.ModelSerializer):
    """
    Serializer for Term (academic semester) model.

    Fields:
        id: Term ID
        name: Term name (e.g., "Fall 2025")
        is_active: Whether this is the currently active term
    """

    class Meta:
        model = Term
        fields = ["id", "name", "is_active"]


class DegreeLevelSerializer(serializers.ModelSerializer):
    """
    Serializer for DegreeLevel model.

    Fields:
        id: Degree level ID
        name: Degree name (e.g., "Bachelor of Science")
        level: Numeric level for ordering
    """

    class Meta:
        model = DegreeLevel
        fields = ["id", "name", "level"]


class ProgramSerializer(serializers.ModelSerializer):
    """
    Serializer for Program model.

    Fields:
        id: Program ID
        name: Program name
        code: Program code
        department: Department ID
        degree_level: Degree level ID
    """

    class Meta:
        model = Program
        fields = ["id", "name", "code", "department", "degree_level"]


class ProgramOutcomeSerializer(serializers.ModelSerializer):
    """
    Serializer for ProgramOutcome model.

    Handles serialization of program outcomes. Program and term are read-only
    as they are typically set during creation and shouldn't change.

    Fields:
        id: Outcome ID
        code: Outcome code (e.g., "PO1")
        description: Detailed description
        program: Program ID (read-only)
        term: Term ID (read-only)
        weight: Relative weight (0.0 to 1.0)
        created_at: Creation timestamp
    """

    program = serializers.PrimaryKeyRelatedField(read_only=True)
    term = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ProgramOutcome
        fields = ["id", "code", "description", "program", "term", "weight", "created_at"]


class CourseSerializer(serializers.ModelSerializer):
    """
    Serializer for Course model.

    Handles bidirectional serialization with nested read representation
    and flat write representation.

    Fields:
        id: Course ID
        code: Course code (e.g., "CS101")
        name: Course name
        credits: Credit hours
        program: Nested program object (read-only)
        term: Nested term object (read-only)
        program_id: Program ID for writes (write-only)
        term_id: Term ID for writes (write-only)
        instructors: List of instructor details (read-only)
        created_at: Creation timestamp
    """

    program = ProgramSerializer(read_only=True)
    term = TermSerializer(read_only=True)
    program_id = serializers.PrimaryKeyRelatedField(queryset=Program.objects.all(), source="program", write_only=True)
    term_id = serializers.PrimaryKeyRelatedField(queryset=Term.objects.all(), source="term", write_only=True)
    instructors = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ["id", "code", "name", "credits", "program", "term", "program_id", "term_id", "instructors", "created_at"]

    @extend_schema_field(List[Dict[str, Any]])
    def get_instructors(self, obj: Course) -> List[Dict[str, Any]]:
        """
        Get instructor details including name and title.

        Args:
            obj: Course instance being serialized

        Returns:
            List of dictionaries containing instructor details:
                - id: User ID
                - first_name: Instructor's first name
                - last_name: Instructor's last name
                - title: Academic title (if available)
        """
        instructors_data = []
        for user in obj.instructors.all():
            try:
                instructor_profile = user.instructor_profile
                instructors_data.append(
                    {
                        "id": user.id,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "title": instructor_profile.title if instructor_profile else "",
                    }
                )
            except AttributeError:
                # Handle case where user might not have instructor profile
                instructors_data.append(
                    {"id": user.id, "first_name": user.first_name, "last_name": user.last_name, "title": ""}
                )
        return instructors_data


class CoreLearningOutcomeSerializer(serializers.ModelSerializer):
    """
    Serializer for LearningOutcome model (core app version).

    Renamed to avoid conflicts with evaluation app's LearningOutcomeSerializer.
    Includes nested course details for read operations.

    Fields:
        id: Learning outcome ID
        code: Outcome code (e.g., "LO1")
        description: Detailed description
        course: Nested course object (read-only)
        created_at: Creation timestamp
    """

    course = CourseSerializer(read_only=True)

    class Meta:
        model = LearningOutcome
        fields = ["id", "code", "description", "course", "created_at"]


class LearningOutcomeProgramOutcomeMappingListSerializer(serializers.ListSerializer):
    """
    Custom ListSerializer for validating LO-PO mapping weight sums.

    Validates that weights for mappings of the same learning outcome
    sum to approximately 1.0 (with 1% tolerance for floating point).

    This serializer is used when many=True is passed to the parent serializer.
    """

    def validate(self, attrs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate that total weights sum to 1.0.

        Args:
            attrs: List of mapping data dictionaries

        Returns:
            Validated data

        Raises:
            ValidationError: If weights don't sum to approximately 1.0
        """
        # Calculate total weight
        total_weight = sum(item.get("weight", 0) for item in attrs)

        # Allow 1% tolerance for floating point arithmetic
        if not (0.99 <= total_weight <= 1.01):
            raise serializers.ValidationError(
                {
                    "weights": f"Program Outcome weights must sum to 1.0, but got {total_weight:.4f}. "
                    f"Please adjust the weights so they total exactly 1.0."
                }
            )
        return attrs


class LearningOutcomeProgramOutcomeMappingSerializer(serializers.ModelSerializer):
    """
    Serializer for LearningOutcomeProgramOutcomeMapping model.

    Handles bidirectional serialization of LO-PO mappings with nested
    read representation and ID-based write representation.

    Uses LearningOutcomeProgramOutcomeMappingListSerializer for validation
    when processing multiple mappings.

    Fields:
        id: Mapping ID
        course: Course ID
        learning_outcome: Nested LO object (read-only)
        learning_outcome_id: LO ID for writes (write-only)
        program_outcome: Nested PO object (read-only)
        program_outcome_id: PO ID for writes (write-only)
        weight: Mapping weight (0.0 to 1.0)
    """

    learning_outcome = CoreLearningOutcomeSerializer(read_only=True)
    learning_outcome_id = serializers.PrimaryKeyRelatedField(
        queryset=LearningOutcome.objects.all(), source="learning_outcome", write_only=True, required=False
    )
    program_outcome = ProgramOutcomeSerializer(read_only=True)
    program_outcome_id = serializers.PrimaryKeyRelatedField(
        queryset=ProgramOutcome.objects.all(), source="program_outcome", write_only=True, required=False
    )

    class Meta:
        model = LearningOutcomeProgramOutcomeMapping
        fields = ["id", "course", "learning_outcome", "learning_outcome_id", "program_outcome", "program_outcome_id", "weight"]
        list_serializer_class = LearningOutcomeProgramOutcomeMappingListSerializer


class StudentLearningOutcomeScoreSerializer(serializers.ModelSerializer):
    """
    Serializer for StudentLearningOutcomeScore model.

    Includes student details and nested learning outcome information.

    Fields:
        id: Score record ID
        student: Student username (string representation)
        student_id: Student user ID
        learning_outcome: Nested LO object
        score: Calculated score (0-100)
    """

    student = serializers.StringRelatedField()
    student_id = serializers.IntegerField(source="student.id", read_only=True)
    learning_outcome = CoreLearningOutcomeSerializer(read_only=True)

    class Meta:
        model = StudentLearningOutcomeScore
        fields = ["id", "student", "student_id", "learning_outcome", "score"]


class StudentProgramOutcomeScoreSerializer(serializers.ModelSerializer):
    """
    Serializer for StudentProgramOutcomeScore model.

    Includes student, term, and nested program outcome information.

    Fields:
        id: Score record ID
        student: Student username (string representation)
        term: Term name (string representation)
        program_outcome: Nested PO object
        score: Calculated aggregate score (0-100)
    """

    student = serializers.StringRelatedField()
    term = serializers.StringRelatedField()
    program_outcome = ProgramOutcomeSerializer(read_only=True)

    class Meta:
        model = StudentProgramOutcomeScore
        fields = ["id", "student", "term", "program_outcome", "score"]


# Response serializers for file operations
class FileImportResponseSerializer(serializers.Serializer):
    """
    Serializer for file import operation responses.

    Fields:
        message: Human-readable status message
        results: Dictionary containing import statistics (created, updated, errors)
    """

    message = serializers.CharField()
    results = serializers.DictField()


class FileValidationResponseSerializer(serializers.Serializer):
    """
    Serializer for file validation operation responses.

    Fields:
        message: Human-readable validation status
        available_sheets: List of sheet names found in the file
        file_info: Dictionary containing file metadata (size, type, etc.)
    """

    message = serializers.CharField()
    available_sheets = serializers.ListField(child=serializers.CharField())
    file_info = serializers.DictField()


# Analytics response serializers
class CourseAverageSerializer(serializers.Serializer):
    """
    Serializer for course average LO scores.

    Used in analytics endpoints to report average scores across all
    learning outcomes in a course.

    Fields:
        course_id: ID of the course
        weighted_average: Average score across all LOs (null if no data)
    """

    course_id = serializers.IntegerField()
    weighted_average = serializers.FloatField(allow_null=True)


class LearningOutcomeAverageSerializer(serializers.Serializer):
    """
    Serializer for learning outcome average scores.

    Used in analytics endpoints to report average scores for a specific
    learning outcome across all students.

    Fields:
        lo_id: Learning outcome ID
        lo_code: Learning outcome code (e.g., "LO1")
        lo_description: Learning outcome description
        avg_score: Average score across all students
    """

    lo_id = serializers.IntegerField()
    lo_code = serializers.CharField()
    lo_description = serializers.CharField()
    avg_score = serializers.FloatField()
