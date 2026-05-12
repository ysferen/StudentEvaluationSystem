from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
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
    academic_year = models.IntegerField(
        null=True, blank=True, help_text="The calendar year the academic year starts (e.g., 2024 for AY 2024-2025)"
    )
    semester = models.CharField(
        max_length=10, choices=[("fall", "Fall"), ("spring", "Spring"), ("summer", "Summer")], default="fall"
    )

    class Meta:
        ordering = ["-is_active", "-name"]
        indexes = [
            models.Index(fields=["-is_active", "-name"]),
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
        ordering = ["name"]
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
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="departments", db_index=True)

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(fields=["university", "code"]),
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
        ordering = ["name"]
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
    degree_level = models.ForeignKey(DegreeLevel, on_delete=models.CASCADE, related_name="programs", db_index=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="programs", db_index=True)
    duration_years = models.PositiveIntegerField(
        default=4, help_text="Program duration in years, used to cap year-level calculations"
    )

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(fields=["department", "degree_level"]),
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
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="program_outcomes")
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="program_outcomes")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_program_outcomes"
    )

    class Meta:
        ordering = ["code"]
        constraints = [models.UniqueConstraint(fields=["code", "program", "term"], name="unique_po_code_per_program_term")]
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
    course_template = models.ForeignKey(
        "CourseTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instances",
        help_text="Template this course was cloned from (if any)",
    )
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="courses", db_index=True)
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="courses", db_index=True)
    instructors = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="taught_courses", blank=True)

    class Meta:
        ordering = ["code"]
        constraints = [models.UniqueConstraint(fields=["code", "program", "term"], name="unique_course_code_per_program_term")]
        indexes = [
            # Composite index for common query patterns
            models.Index(fields=["program", "term"]),
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


class CourseTemplate(TimeStampedModel):
    """
    Canonical course definition shared across terms.

    Defines the stable attributes of a course (name, code, credits,
    program) along with template-level learning outcomes, assessments,
    and outcome mappings that are cloned when creating a per-term
    Course instance via the instantiate API.
    """

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=10, db_index=True)
    credits = models.PositiveIntegerField(default=3)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="course_templates", db_index=True)

    class Meta:
        ordering = ["code"]
        constraints = [models.UniqueConstraint(fields=["code", "program"], name="unique_course_template_per_program")]
        verbose_name = "Course Template"
        verbose_name_plural = "Course Templates"

    def __str__(self):
        return f"{self.code}: {self.name} (Template)"


class CourseTemplateLearningOutcome(TimeStampedModel):
    """
    Template-level learning outcome, cloned into LearningOutcome
    when a Course is instantiated from this template.
    """

    description = models.TextField()
    code = models.CharField(max_length=10)
    course_template = models.ForeignKey(CourseTemplate, on_delete=models.CASCADE, related_name="learning_outcomes")

    class Meta:
        ordering = ["code"]
        constraints = [models.UniqueConstraint(fields=["code", "course_template"], name="unique_template_lo_code")]
        verbose_name = "Course Template Learning Outcome"
        verbose_name_plural = "Course Template Learning Outcomes"

    def __str__(self):
        return f"{self.code}: {self.description[:50]}"


class CourseTemplateAssessment(TimeStampedModel):
    """
    Template-level assessment, cloned into Assessment when a Course
    is instantiated from this template.
    """

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
    total_score = models.PositiveIntegerField(default=100)
    weight = models.FloatField(
        help_text="0.0 to 1.0",
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    course_template = models.ForeignKey(CourseTemplate, on_delete=models.CASCADE, related_name="assessments")

    class Meta:
        verbose_name = "Course Template Assessment"
        verbose_name_plural = "Course Template Assessments"

    def __str__(self):
        return f"{self.name} ({self.get_assessment_type_display()})"


class CourseTemplateAssessmentLOMapping(models.Model):
    """
    Maps template assessments to template learning outcomes.
    Cloned into AssessmentLearningOutcomeMapping on instantiation.
    """

    template_assessment = models.ForeignKey(CourseTemplateAssessment, on_delete=models.CASCADE, related_name="lo_mappings")
    template_learning_outcome = models.ForeignKey(
        CourseTemplateLearningOutcome, on_delete=models.CASCADE, related_name="assessment_mappings"
    )
    weight = models.FloatField(
        help_text="0 to 5",
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["template_assessment", "template_learning_outcome"],
                name="unique_template_assessment_lo",
            )
        ]
        verbose_name = "Course Template Assessment-LO Mapping"
        verbose_name_plural = "Course Template Assessment-LO Mappings"

    def clean(self):
        super().clean()
        if self.template_assessment_id and self.template_learning_outcome_id:
            if self.template_assessment.course_template_id != self.template_learning_outcome.course_template_id:
                raise ValidationError("Assessment and Learning Outcome must belong to the same course template")


class CourseTemplateLOPOMapping(models.Model):
    """
    Maps template learning outcomes to program outcomes.
    Cloned into LearningOutcomeProgramOutcomeMapping on instantiation.
    """

    template_learning_outcome = models.ForeignKey(
        CourseTemplateLearningOutcome, on_delete=models.CASCADE, related_name="po_mappings"
    )
    program_outcome = models.ForeignKey(ProgramOutcome, on_delete=models.CASCADE, related_name="template_lo_mappings")
    weight = models.FloatField(
        help_text="0 to 5",
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["template_learning_outcome", "program_outcome"],
                name="unique_template_lo_po_mapping",
            )
        ]
        verbose_name = "Course Template LO-PO Mapping"
        verbose_name_plural = "Course Template LO-PO Mappings"


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
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="learning_outcomes")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_learning_outcomes"
    )

    class Meta:
        ordering = ["code"]
        constraints = [models.UniqueConstraint(fields=["code", "course"], name="unique_lo_code_per_course")]
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

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lo_po_mappings")
    learning_outcome = models.ForeignKey(LearningOutcome, on_delete=models.CASCADE, related_name="po_mappings")
    program_outcome = models.ForeignKey(ProgramOutcome, on_delete=models.CASCADE, related_name="lo_mappings")
    weight = models.FloatField(help_text="0 to 5", validators=[MinValueValidator(0), MaxValueValidator(5)])

    class Meta:
        ordering = ["course", "learning_outcome", "program_outcome"]
        constraints = [
            models.UniqueConstraint(fields=["course", "learning_outcome", "program_outcome"], name="unique_lo_po_mapping")
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
            raise ValidationError({"learning_outcome": "Learning outcome must belong to the selected course"})
        if self.learning_outcome.course.term != self.program_outcome.term:
            raise ValidationError(
                {"program_outcome": "Program outcome must belong to the same term as the learning outcome's course"}
            )


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

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lo_scores")
    learning_outcome = models.ForeignKey(LearningOutcome, on_delete=models.CASCADE, related_name="student_scores")
    score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)])

    class Meta:
        ordering = ["student", "learning_outcome"]
        constraints = [models.UniqueConstraint(fields=["student", "learning_outcome"], name="unique_student_lo_score")]
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

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="po_scores")
    program_outcome = models.ForeignKey(ProgramOutcome, on_delete=models.CASCADE, related_name="student_scores")
    score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0)])
    # Track which term this calculation is for
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name="student_po_scores")

    class Meta:
        ordering = ["student", "program_outcome"]
        constraints = [models.UniqueConstraint(fields=["student", "program_outcome", "term"], name="unique_student_po_score")]
        verbose_name = "Student Program Outcome Score"
        verbose_name_plural = "Student PO Scores"

    def __str__(self) -> str:
        """Return formatted string showing student, outcome, and score."""
        return f"{self.student.username} - {self.program_outcome.code}: {self.score:.2f}"


class ResourceArea(models.TextChoices):
    COURSES = "courses", "Courses"
    PROGRAMS = "programs", "Programs"
    LEARNING_OUTCOMES = "learning_outcomes", "Learning Outcomes"
    PROGRAM_OUTCOMES = "program_outcomes", "Program Outcomes"
    STUDENTS = "students", "Students"
    LO_PO_WEIGHTS = "lo_po_weights", "LO-PO Weights"
    ASSESSMENT_LO_WEIGHTS = "assessment_lo_weights", "Assessment-LO Weights"
    ASSESSMENTS = "assessments", "Assessments"
    COURSE_TEMPLATES = "course_templates", "Course Templates"


class PermissionTier(models.TextChoices):
    VIEW = "view", "View Only"
    EDIT = "edit", "Edit"
    FULL = "full", "Full Control"


class InstructorPermission(TimeStampedModel):
    instructor = models.ForeignKey(
        "users.InstructorProfile",
        on_delete=models.CASCADE,
        related_name="permissions",
    )
    program_head = models.ForeignKey(
        "users.ProgramHeadProfile",
        on_delete=models.CASCADE,
        related_name="granted_permissions",
        null=True,
        blank=True,
    )
    resource_area = models.CharField(
        max_length=30,
        choices=ResourceArea.choices,
    )
    permission_tier = models.CharField(
        max_length=10,
        choices=PermissionTier.choices,
        default=PermissionTier.VIEW,
    )

    class Meta:
        unique_together = ("instructor", "resource_area")
        verbose_name = "Instructor Permission"
        verbose_name_plural = "Instructor Permissions"

    def __str__(self):
        return f"{self.instructor.full_name} - {self.get_resource_area_display()}: {self.get_permission_tier_display()}"


class WeightSuggestionJob(TimeStampedModel):
    """Tracks async weight suggestion tasks run via Celery."""

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    )

    course = models.ForeignKey(
        "Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weight_suggestion_jobs",
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_weight_suggestion_jobs",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    celery_task_id = models.CharField(max_length=255, blank=True)
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Weight Suggestion Job"
        verbose_name_plural = "Weight Suggestion Jobs"

    def __str__(self):
        course_id = self.course_id if self.course_id is not None else "-"
        return f"WeightSuggestionJob {self.id}: course={course_id} status={self.status}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("TRANSITION", "Term Transition"),
        ("IMPORT", "File Import"),
        ("APPROVE", "Approval"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    before_snapshot = models.JSONField(null=True, blank=True)
    after_snapshot = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["model_name", "object_id"]),
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
        ]
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log Entries"

    def __str__(self):
        return f"{self.action} {self.model_name}#{self.object_id} by {self.user} at {self.timestamp}"


class TermTransitionJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    old_term = models.ForeignKey(Term, on_delete=models.PROTECT, related_name="transitions_from")
    new_term = models.ForeignKey(Term, on_delete=models.PROTECT, related_name="transitions_to")
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="term_transitions")
    template_ids = models.JSONField(default=list)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    courses_created = models.PositiveIntegerField(default=0)
    celery_task_id = models.CharField(max_length=255, blank=True, null=True)
    error = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Term Transition Job"
        verbose_name_plural = "Term Transition Jobs"

    def __str__(self):
        return f"TermTransition {self.old_term} -> {self.new_term} ({self.status})"
