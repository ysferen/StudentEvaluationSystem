"""
Core API serializers for the Student Evaluation System.

This module defines serializers for all core models, handling data validation,
transformation, and representation for API responses. Each serializer corresponds
to a specific model and defines how it is serialized/deserialized.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers
from core.models import (
    Course,
    CourseTemplate,
    CourseTemplateAssessmentLOMapping,
    CourseTemplateLearningOutcome,
    CourseTemplateLOPOMapping,
    ProgramOutcome,
    ProgramOutcomeTemplate,
    Department,
    University,
    WeightSuggestionJob,
    Term,
    Program,
    DegreeLevel,
    LearningOutcome,
    LearningOutcomeProgramOutcomeMapping,
    StudentLearningOutcomeScore,
    StudentProgramOutcomeScore,
    InstructorPermission,
)
from users.models import InstructorProfile, ProgramHeadProfile
from typing import List, Dict, Any, Optional
from drf_spectacular.utils import extend_schema_field

User = get_user_model()


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
        fields = ["id", "name", "is_active", "academic_year", "semester"]


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
        fields = ["id", "name", "code", "department", "degree_level", "duration_years"]


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
    program_id = serializers.PrimaryKeyRelatedField(queryset=Program.objects.all(), source="program", write_only=True)
    term_id = serializers.PrimaryKeyRelatedField(queryset=Term.objects.all(), source="term", write_only=True)
    program_outcome_template_id = serializers.PrimaryKeyRelatedField(
        queryset=ProgramOutcomeTemplate.objects.all(),
        source="program_outcome_template",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = ProgramOutcome
        fields = [
            "id",
            "code",
            "description",
            "program",
            "term",
            "program_id",
            "term_id",
            "weight",
            "program_outcome_template_id",
            "created_at",
        ]


class ProgramOutcomeTemplateSerializer(serializers.ModelSerializer):
    """Serializer for reusable program outcome templates."""

    program = ProgramSerializer(read_only=True)
    program_id = serializers.PrimaryKeyRelatedField(queryset=Program.objects.all(), source="program", write_only=True)
    instance_count = serializers.SerializerMethodField()

    class Meta:
        model = ProgramOutcomeTemplate
        fields = [
            "id",
            "code",
            "description",
            "weight",
            "program",
            "program_id",
            "instance_count",
            "created_at",
            "updated_at",
        ]

    def get_instance_count(self, obj: ProgramOutcomeTemplate) -> int:
        return obj.instances.count()


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
    instructor_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.filter(role="instructor"),
        source="instructors",
        write_only=True,
        required=False,
    )

    class Meta:
        model = Course
        fields = [
            "id",
            "code",
            "name",
            "credits",
            "program",
            "term",
            "program_id",
            "term_id",
            "course_template_id",
            "instructors",
            "instructor_ids",
            "created_at",
        ]
        read_only_fields = ["course_template_id"]

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
    course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all(), source="course", write_only=True)

    class Meta:
        model = LearningOutcome
        fields = ["id", "code", "description", "course", "course_id", "created_at"]


class LearningOutcomeProgramOutcomeMappingSerializer(serializers.ModelSerializer):
    """
    Serializer for LearningOutcomeProgramOutcomeMapping model.

    Handles bidirectional serialization of LO-PO mappings with nested
    read representation and ID-based write representation.

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


class BulkLOPOMappingItem(serializers.Serializer):
    """Single item in a bulk LO-PO sync request."""

    temp_id = serializers.IntegerField(required=False)
    id = serializers.IntegerField(required=False)
    learning_outcome_id = serializers.IntegerField(required=False)
    program_outcome_id = serializers.IntegerField(required=False)
    weight = serializers.FloatField(required=False)


class BulkLOPOMappingSerializer(serializers.Serializer):
    """Bulk sync payload for LO-PO mappings."""

    course_id = serializers.IntegerField()
    creates = BulkLOPOMappingItem(many=True, required=False, default=list)
    updates = BulkLOPOMappingItem(many=True, required=False, default=list)
    deletes = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)


class BulkPermissionItem(serializers.Serializer):
    """Single permission item in a bulk permission update request."""

    resource_area = serializers.CharField()
    permission_tier = serializers.CharField()


class BulkInstructorPermissionSerializer(serializers.Serializer):
    """Bulk update payload for instructor permissions."""

    instructor_id = serializers.IntegerField()
    permissions = BulkPermissionItem(many=True)


class BulkPermissionUpdateItem(serializers.Serializer):
    """Single permission update item with ID for bulk partial updates."""

    id = serializers.IntegerField()
    permission_tier = serializers.CharField(required=False)
    resource_area = serializers.CharField(required=False)


class BulkPermissionUpdateSerializer(serializers.Serializer):
    """Bulk partial update payload for instructor permissions - sends only changed items."""

    updates = BulkPermissionUpdateItem(many=True)


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


class InstructorPermissionSerializer(serializers.ModelSerializer):
    instructor = serializers.StringRelatedField(read_only=True)
    instructor_id = serializers.PrimaryKeyRelatedField(
        queryset=InstructorProfile.objects.all(),
        source="instructor",
    )
    program_head = serializers.StringRelatedField(read_only=True)
    program_head_id = serializers.PrimaryKeyRelatedField(
        queryset=ProgramHeadProfile.objects.all(),
        source="program_head",
    )
    resource_area_display = serializers.CharField(source="get_resource_area_display", read_only=True)
    permission_tier_display = serializers.CharField(source="get_permission_tier_display", read_only=True)

    class Meta:
        model = InstructorPermission
        fields = [
            "id",
            "instructor",
            "instructor_id",
            "program_head",
            "program_head_id",
            "resource_area",
            "resource_area_display",
            "permission_tier",
            "permission_tier_display",
        ]
        read_only_fields = ["id"]


class CourseTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for CourseTemplate model.

    Provides bidirectional serialization with nested read representation
    and flat write representation for the program FK.
    """

    program = ProgramSerializer(read_only=True)
    program_id = serializers.PrimaryKeyRelatedField(queryset=Program.objects.all(), source="program", write_only=True)
    instance_count = serializers.SerializerMethodField()

    class Meta:
        model = CourseTemplate
        fields = [
            "id",
            "code",
            "name",
            "credits",
            "program",
            "program_id",
            "instance_count",
            "created_at",
            "updated_at",
        ]

    def get_instance_count(self, obj: CourseTemplate) -> int:
        """Return the number of Courses instantiated from this template."""
        return obj.instances.count()


class CourseTemplateLearningOutcomeSerializer(serializers.ModelSerializer):
    """Serializer for CourseTemplateLearningOutcome."""

    class Meta:
        model = CourseTemplateLearningOutcome
        fields = ["id", "code", "description", "course_template", "created_at", "updated_at"]
        read_only_fields = ["id", "course_template", "created_at", "updated_at"]


class CourseTemplateAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for CourseTemplateAssessment."""

    class Meta:
        model = WeightSuggestionJob
        fields = [
            "id",
            "status",
            "result",
            "error",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]


class JobProgressEventSerializer(serializers.Serializer):
    """SSE event payload for job progress and completion events."""

    type = serializers.ChoiceField(choices=["progress", "complete"], help_text="Event type")
    job_id = serializers.IntegerField(help_text="ID of the job this event relates to")
    status = serializers.ChoiceField(choices=["running", "success", "failed"], help_text="Current job status")
    current = serializers.IntegerField(required=False, help_text="Current progress step (progress events)")
    total = serializers.IntegerField(required=False, help_text="Total steps (progress events)")
    created = serializers.IntegerField(required=False, help_text="Items created so far (progress events)")
    courses_created = serializers.IntegerField(required=False, help_text="Total courses created (complete events)")
    total_templates = serializers.IntegerField(required=False, help_text="Total templates processed (complete events)")
    error = serializers.CharField(required=False, allow_blank=True, help_text="Error message if status is failed")


class CourseTemplateAssessmentLOMappingSerializer(serializers.ModelSerializer):
    """Serializer for CourseTemplateAssessmentLOMapping."""

    class Meta:
        model = CourseTemplateAssessmentLOMapping
        fields = ["id", "template_assessment", "template_learning_outcome", "weight"]


class CourseTemplateLOPOMappingSerializer(serializers.ModelSerializer):
    """Serializer for CourseTemplateLOPOMapping."""

    class Meta:
        model = CourseTemplateLOPOMapping
        fields = ["id", "template_learning_outcome", "program_outcome", "program_outcome_template", "weight"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        program_outcome = attrs.get("program_outcome") or getattr(self.instance, "program_outcome", None)
        program_outcome_template = attrs.get("program_outcome_template") or getattr(
            self.instance, "program_outcome_template", None
        )
        if bool(program_outcome) == bool(program_outcome_template):
            raise serializers.ValidationError("Provide exactly one of program_outcome or program_outcome_template.")
        return attrs


class InstantiateCourseTemplateSerializer(serializers.Serializer):
    """Serializer for instantiating a course from a template."""

    term_id = serializers.IntegerField()


class NextTermSerializer(serializers.Serializer):
    semester = serializers.ChoiceField(choices=["fall", "spring", "summer"])
    academic_year = serializers.IntegerField(min_value=2000, max_value=2100)
    template_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=True, default=list)

    def validate_template_ids(self, value):
        if not value:
            return value

        user = self.context["request"].user
        from core.models import CourseTemplate

        if getattr(user, "is_admin_user", False):
            templates = CourseTemplate.objects.filter(id__in=value)
        else:
            profile = getattr(user, "program_head_profile", None)
            if profile is None:
                raise serializers.ValidationError("Unable to determine program access.")
            templates = CourseTemplate.objects.filter(id__in=value, program_id=profile.program_id)

        found_ids = set(templates.values_list("id", flat=True))
        missing = set(value) - found_ids
        if missing:
            raise serializers.ValidationError(f"Invalid or inaccessible template IDs: {sorted(missing)}")
        return value

    def create(self, validated_data):
        from django.db import transaction
        from core.models import Term

        old_term = self.context["old_term"]
        with transaction.atomic():
            old_term.is_active = False
            old_term.save()

            semester_tr = {"fall": "Güz", "spring": "Bahar", "summer": "Yaz"}[validated_data["semester"]]
            ay = validated_data["academic_year"]
            if validated_data["semester"] == "fall":
                name = f"{semester_tr} {ay}-{ay + 1}"
            else:
                name = f"{semester_tr} {ay - 1}-{ay}"

            new_term = Term.objects.create(
                semester=validated_data["semester"],
                academic_year=ay,
                name=name,
                is_active=True,
            )

        return new_term


class WeightSuggestionJobSerializer(serializers.ModelSerializer):
    """Serializer for WeightSuggestionJob."""

    class Meta:
        model = WeightSuggestionJob
        fields = [
            "id",
            "course",
            "triggered_by",
            "status",
            "celery_task_id",
            "result",
            "error",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "celery_task_id",
            "result",
            "error",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        ]
