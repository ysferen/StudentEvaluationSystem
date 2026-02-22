from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from typing import Optional
import secrets


User = get_user_model()


class TimeStampedModel(models.Model):
    """
    Abstract base class that provides self-updating created_at and updated_at fields.

    Inherit from this class to automatically track when records are created
    and last modified.

    Attributes:
        created_at (DateTimeField): Timestamp when the record was created.
        updated_at (DateTimeField): Timestamp when the record was last updated.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Term(models.Model):
    """
    Represents an academic term/semester (e.g., Fall 2025, Spring 2026).

    Only one term can be active at a time. When a term is set to active,
    all other terms are automatically deactivated.

    Attributes:
        name (str): Display name of the term (e.g., "Fall 2025").
        is_active (bool): Whether this is the currently active term.
    """
    name = models.CharField(max_length=100, help_text="e.g., Fall 2025")
    is_active = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-is_active', '-name']
        indexes = [
            models.Index(fields=['-is_active', '-name']),
        ]
        verbose_name = "Academic Term"
        verbose_name_plural = "Academic Terms"

    def save(self, *args, **kwargs) -> None:
        """
        Save the term instance.

        If this term is being set to active, automatically deactivate
        all other terms to maintain single active term constraint.
        """
        if self.is_active:
            Term.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Return string representation showing term name and active status."""
        return f"{self.name} {'(Active)' if self.is_active else ''}"

def generate_unique_code() -> str:
    """
    Generate a random unique code for University instances.

    Returns:
        str: A 10-character alphanumeric code starting with 'U'.
    """
    return f"U{secrets.token_hex(4).upper()}"[:10]


class University(models.Model):
    """
    Represents a university institution in the system.

    Universities contain multiple departments and serve as the top-level
    organizational unit.

    Attributes:
        name (str): Full name of the university.
        code (str): Unique short code identifier (auto-generated if not provided).
    """
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=10, unique=True, db_index=True, default=generate_unique_code)

    class Meta:
        ordering = ['name']
        verbose_name = "University"
        verbose_name_plural = "Universities"

    def save(self, *args, **kwargs) -> None:
        """
        Save the university instance.

        Ensures code is always populated and handles rare collisions
        from auto-generated values by regenerating until unique.
        """
        if not self.code or not str(self.code).strip():
            self.code = generate_unique_code()

        # Handle rare collisions from generated values
        while University.objects.exclude(pk=self.pk).filter(code=self.code).exists():
            self.code = generate_unique_code()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Return the university name."""
        return self.name

class Department(models.Model):
    """
    Represents an academic department within a university.

    Departments contain multiple programs and are associated with
    a single university.

    Attributes:
        name (str): Full name of the department.
        code (str): Unique department code (e.g., "CS", "MATH").
        university (University): The university this department belongs to.
    """
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

    def __str__(self) -> str:
        """Return formatted string with code and name."""
        return f"{self.code} - {self.name}"

class DegreeLevel(models.Model):
    """
    Represents a degree level (e.g., Bachelor's, Master's, PhD).

    The level field allows for hierarchical ordering of degrees.

    Attributes:
        name (str): Name of the degree level (e.g., "Bachelor of Science").
        level (int): Numeric level for ordering (higher = more advanced).
    """
    name = models.CharField(max_length=100, unique=True)
    level = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['name']
        verbose_name = "Degree Level"
        verbose_name_plural = "Degree Levels"

    def __str__(self) -> str:
        """Return the degree level name."""
        return self.name

class Program(models.Model):
    """
    Represents an academic program (e.g., Computer Science BS, Mathematics MS).

    Programs belong to a department and have a specific degree level.
    They contain multiple courses and define program outcomes.

    Attributes:
        name (str): Full name of the program.
        code (str): Unique program code (e.g., "CS-BS", "MATH-MS").
        degree_level (DegreeLevel): The degree level offered.
        department (Department): The department offering this program.
    """
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

    def __str__(self) -> str:
        """Return formatted string with code, name, and degree level."""
        return f"{self.code}: {self.name} ({self.degree_level})"

class ProgramOutcome(TimeStampedModel):
    """
    Represents a Program Outcome (PO) - high-level learning goals for a program.

    Program outcomes are defined at the program level and can vary by term.
    They are mapped to Learning Outcomes through LO-PO mappings.

    Attributes:
        description (str): Detailed description of the outcome.
        code (str): Short code identifier (e.g., "PO1", "PO2").
        weight (float): Relative weight of this outcome (0.0 to 1.0).
        program (Program): The program this outcome belongs to.
        term (Term): The academic term this outcome is defined for.
        created_by (User): User who created this outcome.
    """
    description = models.TextField()
    code = models.CharField(max_length=10)
    weight = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="0.0 to 1.0",
    )
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

    def __str__(self) -> str:
        """Return formatted string with code and truncated description."""
        return f"{self.code}: {self.description[:50]}"

class Course(TimeStampedModel):
    """
    Represents a course offering within a program for a specific term.

    Courses have instructors, learning outcomes, and assessments.
    The same course code can exist in different terms or programs.

    Attributes:
        name (str): Full course name.
        code (str): Course code (e.g., "CS101").
        credits (int): Number of credit hours.
        program (Program): The program this course belongs to.
        term (Term): The term this course is offered in.
        instructors (ManyToManyField): Instructors teaching this course.

    Properties:
        total_assessments: Number of assessments in this course.
        enrolled_students_count: Number of students enrolled.
    """
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
    def total_assessments(self) -> int:
        """
        Get the total number of assessments for this course.

        Returns:
            int: Count of associated Assessment objects.
        """
        return self.assessments.count()

    @property
    def enrolled_students_count(self) -> int:
        """
        Get the number of students enrolled in this course.

        Returns:
            int: Count of associated CourseEnrollment objects.
        """
        return self.enrollments.count()

    def __str__(self) -> str:
        """Return formatted string with course code and name."""
        return f"{self.code}: {self.name}"

class LearningOutcome(TimeStampedModel):
    """
    Represents a Learning Outcome (LO) - specific goals for a course.

    Learning outcomes are course-level objectives that map to Program Outcomes.
    Student performance is measured against these outcomes through assessments.

    Attributes:
        description (str): Detailed description of what students should achieve.
        code (str): Short code identifier (e.g., "LO1", "LO2").
        course (Course): The course this outcome belongs to.
        created_by (User): User who created this outcome.
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

    def __str__(self) -> str:
        """Return formatted string with code and truncated description."""
        return f"{self.code}: {self.description[:50]}"

class LearningOutcomeProgramOutcomeMapping(models.Model):
    """
    Maps Learning Outcomes to Program Outcomes with contribution weights.

    This mapping defines how much each Learning Outcome contributes to
    achieving a Program Outcome. Weights are used in score calculations
    to aggregate student performance.

    Attributes:
        course (Course): The course this mapping applies to.
        learning_outcome (LearningOutcome): The source learning outcome.
        program_outcome (ProgramOutcome): The target program outcome.
        weight (float): Contribution weight from 0.0 to 1.0.
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

    def clean(self) -> None:
        """
        Validate that the learning outcome belongs to the specified course.

        Raises:
            ValidationError: If learning outcome's course doesn't match mapping's course.
        """
        super().clean()
        if self.learning_outcome.course != self.course:
            raise ValidationError({
                'learning_outcome': 'Learning outcome must belong to the selected course'
            })

class StudentLearningOutcomeScore(models.Model):
    """
    Stores the calculated score for a student in a specific Learning Outcome.

    These scores are computed from assessment grades using the assessment-LO
    weight mappings. They represent student achievement at the course level.

    Attributes:
        student (User): The student who earned this score.
        learning_outcome (LearningOutcome): The learning outcome being measured.
        score (float): Calculated score (typically 0-100).
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

    def __str__(self) -> str:
        """Return formatted string showing student, outcome, and score."""
        return f"{self.student.username} - {self.learning_outcome.code}: {self.score:.2f}"

class StudentProgramOutcomeScore(models.Model):
    """
    Stores the calculated score for a student in a specific Program Outcome.

    These scores are aggregated across all courses in a program using the
    LO-PO weight mappings. They represent overall student achievement toward
    program-level goals.

    Attributes:
        student (User): The student who earned this score.
        program_outcome (ProgramOutcome): The program outcome being measured.
        score (float): Calculated aggregate score (typically 0-100).
        term (Term): The term for which this score was calculated.
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
    # Track which term this calculation is for
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

    def __str__(self) -> str:
        """Return formatted string showing student, outcome, and score."""
        return f"{self.student.username} - {self.program_outcome.code}: {self.score:.2f}"
