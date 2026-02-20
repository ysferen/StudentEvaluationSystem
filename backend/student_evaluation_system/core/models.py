from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class TimeStampedModel(models.Model):
    """Abstract base class with created_at and updated_at fields."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Term(models.Model):
    name = models.CharField(max_length=100, help_text="e.g., Fall 2025")
    is_active = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-is_active', '-name']
        indexes = [
            models.Index(fields=['-is_active', '-name']),
        ]
        verbose_name = "Academic Term"
        verbose_name_plural = "Academic Terms"

    def save(self, *args, **kwargs):
        # If this term is being set to active, deactivate all other terms
        if self.is_active:
            Term.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} {'(Active)' if self.is_active else ''}"

class University(models.Model):
    name = models.CharField(max_length=255, unique=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "University"
        verbose_name_plural = "Universities"
    
    def __str__(self):
        return self.name

class Department(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=10, unique=True, db_index=True)
    university = models.ForeignKey(
        University, 
        on_delete=models.CASCADE, 
        related_name='departments',
        db_index=True
    )

    class Meta:
        ordering = ['code']
        indexes = [
            models.Index(fields=['university', 'code']),
        ]
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return f"{self.code} - {self.name}"
    
class DegreeLevel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Degree Level"
        verbose_name_plural = "Degree Levels"
    
    def __str__(self):
        return self.name

class Program(models.Model):
    name = models.CharField(max_length=255) 
    code = models.CharField(max_length=10, unique=True, db_index=True) 
    degree_level = models.ForeignKey(
        DegreeLevel, 
        on_delete=models.CASCADE, 
        related_name='programs',
        db_index=True
    )
    department = models.ForeignKey(
        Department, 
        on_delete=models.CASCADE, 
        related_name='programs',
        db_index=True
    )
    
    class Meta:
        ordering = ['code']
        indexes = [
            models.Index(fields=['department', 'degree_level']),
        ]
        verbose_name = "Program"
        verbose_name_plural = "Programs"
    
    def __str__(self):
        return f"{self.code}: {self.name} ({self.degree_level})"

class ProgramOutcome(TimeStampedModel):
    description = models.TextField()
    code = models.CharField(max_length=10)
    program = models.ForeignKey(
        Program, 
        on_delete=models.CASCADE, 
        related_name='program_outcomes'
    )
    term = models.ForeignKey(
        Term, 
        on_delete=models.CASCADE, 
        related_name='program_outcomes'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_program_outcomes'
    )

    class Meta:
        ordering = ['code']
        constraints = [
            models.UniqueConstraint(
                fields=['code', 'program', 'term'], 
                name='unique_po_code_per_program_term'
            )
        ]
        verbose_name = "Program Outcome"
        verbose_name_plural = "Program Outcomes"

    def __str__(self):
        return f"{self.code}: {self.description[:50]}"

class Course(TimeStampedModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=10, db_index=True)
    credits = models.PositiveIntegerField(default=3)
    program = models.ForeignKey(
        Program, 
        on_delete=models.CASCADE, 
        related_name='courses',
        db_index=True
    )
    term = models.ForeignKey(
        Term, 
        on_delete=models.CASCADE, 
        related_name='courses',
        db_index=True
    )
    instructors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='taught_courses',
        blank=True
    )

    class Meta:
        ordering = ['code']
        constraints = [
            models.UniqueConstraint(
                fields=['code', 'program', 'term'], 
                name='unique_course_code_per_program_term'
            )
        ]
        indexes = [
            # Composite index for common query patterns
            models.Index(fields=['program', 'term']),
        ]
        verbose_name = "Course"
        verbose_name_plural = "Courses"

    @property
    def total_assessments(self):
        """Get total number of assessments for this course."""
        return self.assessments.count()
    
    @property
    def enrolled_students_count(self):
        """Get number of enrolled students."""
        return self.enrollments.count()

    def __str__(self):
        return f"{self.code}: {self.name}"

class LearningOutcome(TimeStampedModel):
    """
    Moved from evaluation app to core to resolve circular dependency.
    Represents learning outcomes for a specific course.
    """
    description = models.TextField()
    code = models.CharField(max_length=10)
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='learning_outcomes'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_learning_outcomes'
    )

    class Meta:
        ordering = ['code']
        constraints = [
            models.UniqueConstraint(
                fields=['code', 'course'], 
                name='unique_lo_code_per_course'
            )
        ]
        verbose_name = "Learning Outcome"
        verbose_name_plural = "Learning Outcomes"

    def __str__(self):
        return f"{self.code}: {self.description[:50]}"

class LearningOutcomeProgramOutcomeMapping(models.Model):
    """
    Renamed from CO_PO_Mapping for better readability.
    Maps learning outcomes to program outcomes with weights.
    """
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='lo_po_mappings'
    )
    learning_outcome = models.ForeignKey(
        LearningOutcome, 
        on_delete=models.CASCADE, 
        related_name='po_mappings'
    )
    program_outcome = models.ForeignKey(
        ProgramOutcome, 
        on_delete=models.CASCADE, 
        related_name='lo_mappings'
    )
    weight = models.FloatField(
        help_text="0.0 to 1.0",
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )

    class Meta:
        ordering = ['course', 'learning_outcome', 'program_outcome']
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'learning_outcome', 'program_outcome'], 
                name='unique_lo_po_mapping'
            )
        ]
        verbose_name = "Learning Outcome to Program Outcome Mapping"
        verbose_name_plural = "LO-PO Mappings"
    
    def clean(self):
        """Validate that the learning outcome belongs to the course."""
        super().clean()
        if self.learning_outcome.course != self.course:
            raise ValidationError({
                'learning_outcome': 'Learning outcome must belong to the selected course'
            })

class StudentLearningOutcomeScore(models.Model):
    """
    Renamed from StudentCOScore for clarity.
    Stores the calculated score for a specific Student in a specific Learning Outcome.
    """
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='lo_scores'
    )
    learning_outcome = models.ForeignKey(
        LearningOutcome, 
        on_delete=models.CASCADE, 
        related_name='student_scores'
    )
    score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)])
    
    class Meta:
        ordering = ['student', 'learning_outcome']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'learning_outcome'], 
                name='unique_student_lo_score'
            )
        ]
        verbose_name = "Student Learning Outcome Score"
        verbose_name_plural = "Student LO Scores"
    
    def __str__(self):
        return f"{self.student.username} - {self.learning_outcome.code}: {self.score:.2f}"

class StudentProgramOutcomeScore(models.Model):
    """
    Renamed from StudentPOScore for clarity.
    Stores the calculated score for a Student in a specific Program Outcome.
    This is calculated by aggregating LO scores across ALL courses in the program.
    """
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='po_scores'
    )
    program_outcome = models.ForeignKey(
        ProgramOutcome, 
        on_delete=models.CASCADE, 
        related_name='student_scores'
    )
    score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)])
    # Optional: track which term this calculation is for
    term = models.ForeignKey(
        Term,
        on_delete=models.CASCADE,
        related_name='student_po_scores'
    )

    class Meta:
        ordering = ['student', 'program_outcome']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'program_outcome', 'term'], 
                name='unique_student_po_score'
            )
        ]
        verbose_name = "Student Program Outcome Score"
        verbose_name_plural = "Student PO Scores"
    
    def __str__(self):
        return f"{self.student.username} - {self.program_outcome.code}: {self.score:.2f}"
