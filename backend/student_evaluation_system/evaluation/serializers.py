from rest_framework import serializers
from .models import Assessment, AssessmentLearningOutcomeMapping, StudentGrade, CourseEnrollment
from core.models import Course, LearningOutcome
from users.models import CustomUser

class EvaluationLearningOutcomeSerializer(serializers.ModelSerializer):
    """Learning Outcome serializer for evaluation app to avoid conflicts"""
    course = serializers.StringRelatedField()

    class Meta:
        model = LearningOutcome
        fields = ['id', 'code', 'description', 'course', 'created_at']


class AssessmentLearningOutcomeMappingListSerializer(serializers.ListSerializer):
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
                    'weights': f"Learning Outcome weights must sum to 1.0, but got {total_weight:.4f}. "
                              f"Please adjust the weights so they total exactly 1.0."
                }
            )
        return attrs


class AssessmentLearningOutcomeMappingSerializer(serializers.ModelSerializer):
    """Nested inside AssessmentSerializer"""
    learning_outcome = EvaluationLearningOutcomeSerializer(read_only=True)
    learning_outcome_id = serializers.PrimaryKeyRelatedField(
        queryset=LearningOutcome.objects.all(),
        source='learning_outcome',
        write_only=True
    )

    class Meta:
        model = AssessmentLearningOutcomeMapping
        fields = ['id', 'learning_outcome', 'learning_outcome_id', 'weight']
        list_serializer_class = AssessmentLearningOutcomeMappingListSerializer

    def validate_weight(self, value):
        """Validate individual weight is between 0 and 1"""
        if not (0 <= value <= 1):
            raise serializers.ValidationError(
                "Weight must be between 0 and 1 (representing percentage as decimal)"
            )
        return value


class AssessmentSerializer(serializers.ModelSerializer):
    course = serializers.StringRelatedField(read_only=True)
    lo_mappings = AssessmentLearningOutcomeMappingSerializer(many=True, read_only=True)

    class Meta:
        model = Assessment
        fields = ['id', 'name', 'course', 'date', 'total_score', 'weight',
                  'lo_mappings', 'created_at']


class AssessmentCreateSerializer(serializers.ModelSerializer):
    """For creating/updating assessments"""
    class Meta:
        model = Assessment
        fields = ['id', 'name', 'course', 'date', 'total_score', 'weight', 'assessment_type']


class StudentGradeSerializer(serializers.ModelSerializer):
    student = serializers.StringRelatedField()
    assessment = AssessmentSerializer(read_only=True)

    class Meta:
        model = StudentGrade
        fields = ['id', 'student', 'assessment', 'score']


class StudentGradeCreateSerializer(serializers.ModelSerializer):
    """For creating/updating grades"""
    class Meta:
        model = StudentGrade
        fields = ['id', 'student', 'assessment', 'score']


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    from core.serializers import CourseSerializer

    student = serializers.StringRelatedField()
    course = CourseSerializer(read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = ['id', 'student', 'course', 'enrolled_at']


class MyGradesSerializer(serializers.ModelSerializer):
    """Custom serializer for students to view their grades"""
    assessment_name = serializers.CharField(source='assessment.name')
    course_name = serializers.CharField(source='assessment.course.name')
    course_code = serializers.CharField(source='assessment.course.code')
    total_score = serializers.IntegerField(source='assessment.total_score')
    percentage = serializers.SerializerMethodField()

    class Meta:
        model = StudentGrade
        fields = ['id', 'course_code', 'course_name', 'assessment_name',
                  'score', 'total_score', 'percentage']

    def get_percentage(self, obj):
        return (obj.score / obj.assessment.total_score) * 100 if obj.assessment.total_score > 0 else 0
