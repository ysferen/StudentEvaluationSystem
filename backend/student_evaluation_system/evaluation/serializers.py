from rest_framework import serializers
from django.db.models import Sum
from django.utils import timezone
from .models import Assessment, AssessmentLearningOutcomeMapping, StudentGrade, CourseEnrollment, ScoreRecomputeJob
from core.models import LearningOutcome


class EvaluationLearningOutcomeSerializer(serializers.ModelSerializer):
    """Learning Outcome serializer for evaluation app to avoid conflicts"""

    course = serializers.StringRelatedField()

    class Meta:
        model = LearningOutcome
        fields = ["id", "code", "description", "course", "created_at"]


class AssessmentLearningOutcomeMappingListSerializer(serializers.ListSerializer):
    """
    Custom ListSerializer to validate that weights sum to 1.0 per assessment.
    Called when many=True is used.
    """

    def validate(self, attrs):
        # Group by assessment
        by_assessment = {}
        for item in attrs:
            ass_id = item.get("assessment_id") or (item.get("assessment") and item["assessment"].id)
            if ass_id is None:
                continue
            if ass_id not in by_assessment:
                by_assessment[ass_id] = []
            by_assessment[ass_id].append(item.get("weight", 0))

        for ass_id, weights in by_assessment.items():
            total_weight = sum(weights)
            if not (0.99 <= total_weight <= 1.01):
                raise serializers.ValidationError(
                    {
                        "weights": (
                            f"Learning Outcome weights for assessment {ass_id} must sum to 1.0, "
                            f"but got {total_weight:.4f}. Please adjust the weights so they total exactly 1.0."
                        )
                    }
                )
        return attrs


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
        list_serializer_class = AssessmentLearningOutcomeMappingListSerializer

    def validate(self, data):
        instance = self.instance
        assessment = data.get("assessment") or (instance.assessment if instance else None)
        new_weight = data.get("weight", instance.weight if instance else 0)

        if assessment is None:
            return data

        existing_mappings = AssessmentLearningOutcomeMapping.objects.filter(assessment=assessment)
        if instance and instance.pk:
            existing_mappings = existing_mappings.exclude(pk=instance.pk)

        current_total = existing_mappings.aggregate(total=Sum("weight"))["total"] or 0
        projected_total = current_total + new_weight

        if projected_total > 1.01:
            raise serializers.ValidationError(
                {
                    "weight": (
                        f"Total weight for this assessment would be {projected_total:.2f}, "
                        f"which exceeds the maximum of 1.0. "
                        f"Existing mappings sum to {current_total:.2f}. "
                        f"Please adjust weights so the total equals 1.0."
                    )
                }
            )

        return data


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
    course = CourseSerializer(read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = ["id", "student", "course", "enrolled_at"]


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
