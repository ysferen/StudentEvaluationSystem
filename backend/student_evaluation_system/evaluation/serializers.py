from rest_framework import serializers
from django.utils import timezone
from .models import Assessment, AssessmentLearningOutcomeMapping, StudentGrade, CourseEnrollment, ScoreRecomputeJob
from core.models import LearningOutcome


class EvaluationLearningOutcomeSerializer(serializers.ModelSerializer):
    """Learning Outcome serializer for evaluation app to avoid conflicts"""

    course = serializers.StringRelatedField()

    class Meta:
        model = LearningOutcome
        fields = ["id", "code", "description", "course", "created_at"]


class AssessmentLearningOutcomeMappingSerializer(serializers.ModelSerializer):
    """Nested inside AssessmentSerializer"""

    learning_outcome = EvaluationLearningOutcomeSerializer(read_only=True)
    learning_outcome_id = serializers.PrimaryKeyRelatedField(
        queryset=LearningOutcome.objects.all(), source="learning_outcome", write_only=True, required=False
    )
    assessment_id = serializers.PrimaryKeyRelatedField(
        queryset=Assessment.objects.all(), source="assessment", write_only=True, required=False
    )

    class Meta:
        model = AssessmentLearningOutcomeMapping
        fields = ["id", "assessment", "assessment_id", "learning_outcome", "learning_outcome_id", "weight"]
        read_only_fields = ["assessment"]


class AssessmentSerializer(serializers.ModelSerializer):
    course = serializers.StringRelatedField(read_only=True)
    lo_mappings = AssessmentLearningOutcomeMappingSerializer(many=True, read_only=True)

    class Meta:
        model = Assessment
        fields = [
            "id",
            "name",
            "assessment_type",
            "description",
            "course",
            "date",
            "total_score",
            "weight",
            "lo_mappings",
            "created_at",
        ]


class BulkAssessmentLOMappingItem(serializers.Serializer):
    """Single item in a bulk sync request."""

    temp_id = serializers.IntegerField(required=False)
    id = serializers.IntegerField(required=False)
    assessment_id = serializers.IntegerField(required=False)
    learning_outcome_id = serializers.IntegerField(required=False)
    weight = serializers.FloatField(required=False)


class BulkAssessmentLOMappingSerializer(serializers.Serializer):
    """Bulk sync payload for assessment-LO mappings."""

    course_id = serializers.IntegerField()
    creates = BulkAssessmentLOMappingItem(many=True, required=False, default=list)
    updates = BulkAssessmentLOMappingItem(many=True, required=False, default=list)
    deletes = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)


class AssessmentCreateSerializer(serializers.ModelSerializer):
    """For creating/updating assessments"""

    # Provide a date default as a plain date to avoid datetime coercion errors
    date = serializers.DateField(default=timezone.localdate)

    class Meta:
        model = Assessment
        fields = ["id", "name", "course", "date", "total_score", "weight", "assessment_type", "description"]


class StudentGradeSerializer(serializers.ModelSerializer):
    student = serializers.StringRelatedField()
    assessment = AssessmentSerializer(read_only=True)

    class Meta:
        model = StudentGrade
        fields = ["id", "student", "assessment", "score"]


class StudentGradeCreateSerializer(serializers.ModelSerializer):
    """For creating/updating grades"""

    class Meta:
        model = StudentGrade
        fields = ["id", "student", "assessment", "score"]


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    from core.serializers import CourseSerializer

    student = serializers.StringRelatedField()
    student_id = serializers.IntegerField(source="student.id", read_only=True)
    course = CourseSerializer(read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = ["id", "student", "student_id", "course", "enrolled_at"]


class MyGradesSerializer(serializers.ModelSerializer):
    """Custom serializer for students to view their grades"""

    assessment_name = serializers.CharField(source="assessment.name")
    course_name = serializers.CharField(source="assessment.course.name")
    course_code = serializers.CharField(source="assessment.course.code")
    total_score = serializers.IntegerField(source="assessment.total_score")
    percentage = serializers.SerializerMethodField()

    class Meta:
        model = StudentGrade
        fields = ["id", "course_code", "course_name", "assessment_name", "score", "total_score", "percentage"]

    def get_percentage(self, obj):
        return (obj.score / obj.assessment.total_score) * 100 if obj.assessment.total_score > 0 else 0


class ScoreRecomputeJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreRecomputeJob
        fields = [
            "id",
            "task_type",
            "status",
            "course",
            "triggered_by",
            "celery_task_id",
            "created_at",
            "updated_at",
            "started_at",
            "finished_at",
            "error",
        ]


class BulkAssessmentDescriptionUpdateSerializer(serializers.Serializer):
    """Bulk update assessment descriptions.

    Request body:
        {
            "assessments": [
                {"id": 1, "description": "Vize sınavı: ..."},
                {"id": 2, "description": "Final sınavı: ..."},
            ]
        }
    """

    assessments = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
    )

    def validate_assessments(self, value):
        for item in value:
            if "id" not in item:
                raise serializers.ValidationError("Each item must have an 'id' field.")
            if "description" not in item:
                raise serializers.ValidationError("Each item must have a 'description' field.")
            if not isinstance(item["id"], int):
                raise serializers.ValidationError("'id' must be an integer.")
            if not isinstance(item["description"], str):
                raise serializers.ValidationError("'description' must be a string.")
        return value
