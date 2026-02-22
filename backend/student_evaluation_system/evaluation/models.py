from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from core.models import LearningOutcome, TimeStampedModel


class Assessment(TimeStampedModel):
    ASSESSMENT_TYPES = [
        ("midterm", "Midterm"),
        ("final", "Final Exam"),
        ("homework", "Homework"),
        ("project", "Project"),
        ("quiz", "Quiz"),
        ("attendance", "Attendance"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=255)
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES, default="homework")
    course = models.ForeignKey("core.Course", on_delete=models.CASCADE, related_name="assessments")
    # Use localdate to avoid DateField receiving a datetime
    date = models.DateField(default=timezone.localdate)
    total_score = models.PositiveIntegerField(default=100)
    weight = models.FloatField(
        help_text="0.0 to 1.0",
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.0,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_assessments"
    )

    class Meta:
        ordering = ["course", "date"]
        verbose_name = "Assessment"
        verbose_name_plural = "Assessments"

    def __str__(self):
        return f"{self.name} ({self.course.code})"


class AssessmentLearningOutcomeMapping(models.Model):
    """
    Renamed from Assessment_CO_Mapping for better readability.
    Maps assessments to learning outcomes with weights.
    """

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="lo_mappings")
    learning_outcome = models.ForeignKey(LearningOutcome, on_delete=models.CASCADE, related_name="assessment_mappings")
    weight = models.FloatField(help_text="0.0 to 1.0", validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])

    class Meta:
        ordering = ["assessment", "learning_outcome"]
        constraints = [models.UniqueConstraint(fields=["assessment", "learning_outcome"], name="unique_assessment_lo")]
        verbose_name = "Assessment to Learning Outcome Mapping"
        verbose_name_plural = "Assessment-LO Mappings"

    def __str__(self):
        return f"{self.assessment.name} → {self.learning_outcome.code} ({self.weight:.2f})"


class StudentGrade(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="grades")
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="student_grades")
    score = models.FloatField(validators=[MinValueValidator(0.0)])

    class Meta:
        ordering = ["assessment", "student"]
        constraints = [
            models.UniqueConstraint(fields=["student", "assessment"], name="unique_student_grade"),
            models.CheckConstraint(check=models.Q(score__gte=0), name="score_non_negative"),
        ]
        verbose_name = "Student Grade"
        verbose_name_plural = "Student Grades"

    def clean(self):
        """Validate that score doesn't exceed assessment total."""
        super().clean()
        if self.score > self.assessment.total_score:
            raise ValidationError({"score": f"Score cannot exceed {self.assessment.total_score}"})

        # Ensure student is enrolled in the course
        if not self.assessment.course.enrollments.filter(student=self.student).exists():
            raise ValidationError({"student": "Student must be enrolled in the course"})

    @property
    def percentage(self):
        """Calculate percentage score."""
        if self.assessment.total_score > 0:
            return (self.score / self.assessment.total_score) * 100
        return 0

    def __str__(self):
        return f"{self.student.username}: {self.assessment.name} - {self.score}/{self.assessment.total_score}"


class CourseEnrollment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="course_enrollments")
    course = models.ForeignKey("core.Course", on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    STATUS_CHOICES = (
        ("active", "Active"),
        ("pending", "Pending"),
        ("dropped", "Dropped"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    class Meta:
        ordering = ["course", "student"]
        constraints = [models.UniqueConstraint(fields=["student", "course"], name="unique_enrollment")]
        verbose_name = "Course Enrollment"
        verbose_name_plural = "Course Enrollments"

    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.code}"
