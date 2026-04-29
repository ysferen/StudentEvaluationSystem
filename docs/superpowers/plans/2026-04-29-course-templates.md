# Course Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `CourseTemplate` system so canonical course definitions (LOs, assessments, LO→PO mappings) can be defined once and cloned into per-term Course instances, while keeping per-term data immutable.

**Architecture:** Five new models in `core/models.py` (CourseTemplate + 4 sub-models), an optional `course_template` FK on the existing `Course` model, a clone service in `core/services/course_template.py`, new ViewSets/Serializers in the `core` app, and API endpoint `POST /api/core/course-templates/{id}/instantiate/`.

**Tech Stack:** Django ORM, Django REST Framework, pytest + factory_boy, drf-spectacular (OpenAPI)

---

## File Structure

| Action | File | Purpose |
|--------|------|---------|
| **Modify** | `core/models.py` | Add CourseTemplate + 4 sub-models, add `course_template` FK to Course, add `COURSE_TEMPLATES` to ResourceArea |
| **Modify** | `core/serializers.py` | Add 3 new serializers (CourseTemplate, CourseTemplateLO, CourseTemplateAssessment) |
| **Create** | `core/services/course_template.py` | `clone_course_from_template()` service |
| **Create** | `core/views/course_templates.py` | CourseTemplateViewSet + mapping ViewSets |
| **Modify** | `core/views/__init__.py` | Export new ViewSets |
| **Modify** | `core/urls.py` | Register 3 new ViewSets |
| **Modify** | `core/admin.py` | Register new models |
| **Modify** | `tests/factories.py` | Add CourseTemplateFactory + sub-factories |
| **Create** | `tests/test_course_templates.py` | Unit + API tests |

---

### Task 1: Add models to core/models.py

**Files:**
- Modify: `backend/student_evaluation_system/core/models.py`

- [ ] **Step 1: Add the CourseTemplate model**

Insert after the `Course` model (after line 316, before `LearningOutcome`):

```python
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
        constraints = [
            models.UniqueConstraint(fields=["code", "program"], name="unique_course_template_per_program")
        ]
        verbose_name = "Course Template"
        verbose_name_plural = "Course Templates"

    def __str__(self):
        return f"{self.code}: {self.name} (Template)"
```

- [ ] **Step 2: Add CourseTemplateLearningOutcome model**

Insert after `CourseTemplate`:

```python
class CourseTemplateLearningOutcome(TimeStampedModel):
    """
    Template-level learning outcome, cloned into LearningOutcome
    when a Course is instantiated from this template.
    """

    description = models.TextField()
    code = models.CharField(max_length=10)
    course_template = models.ForeignKey(
        CourseTemplate, on_delete=models.CASCADE, related_name="learning_outcomes"
    )

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["code", "course_template"], name="unique_template_lo_code")
        ]
        verbose_name = "Course Template Learning Outcome"
        verbose_name_plural = "Course Template Learning Outcomes"

    def __str__(self):
        return f"{self.code}: {self.description[:50]}"
```

- [ ] **Step 3: Add CourseTemplateAssessment model**

Insert after `CourseTemplateLearningOutcome`:

```python
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
        default=0.0,
    )
    course_template = models.ForeignKey(
        CourseTemplate, on_delete=models.CASCADE, related_name="assessments"
    )

    class Meta:
        verbose_name = "Course Template Assessment"
        verbose_name_plural = "Course Template Assessments"

    def __str__(self):
        return f"{self.name} ({self.get_assessment_type_display()})"
```

- [ ] **Step 4: Add CourseTemplateAssessmentLOMapping model**

Insert after `CourseTemplateAssessment`:

```python
class CourseTemplateAssessmentLOMapping(models.Model):
    """
    Maps template assessments to template learning outcomes.
    Cloned into AssessmentLearningOutcomeMapping on instantiation.
    """

    template_assessment = models.ForeignKey(
        CourseTemplateAssessment, on_delete=models.CASCADE, related_name="lo_mappings"
    )
    template_learning_outcome = models.ForeignKey(
        CourseTemplateLearningOutcome, on_delete=models.CASCADE, related_name="assessment_mappings"
    )
    weight = models.FloatField(
        help_text="0.0 to 1.0",
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
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
                raise ValidationError(
                    "Assessment and Learning Outcome must belong to the same course template"
                )
```

- [ ] **Step 5: Add CourseTemplateLOPOMapping model**

Insert after `CourseTemplateAssessmentLOMapping`:

```python
class CourseTemplateLOPOMapping(models.Model):
    """
    Maps template learning outcomes to program outcomes.
    Cloned into LearningOutcomeProgramOutcomeMapping on instantiation.
    """

    template_learning_outcome = models.ForeignKey(
        CourseTemplateLearningOutcome, on_delete=models.CASCADE, related_name="po_mappings"
    )
    program_outcome = models.ForeignKey(
        ProgramOutcome, on_delete=models.CASCADE, related_name="template_lo_mappings"
    )
    weight = models.FloatField(
        help_text="0.0 to 1.0",
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
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
```

- [ ] **Step 6: Add course_template FK to Course model**

Add this field to the `Course` model (after `credits`, before `program`):

```python
course_template = models.ForeignKey(
    "CourseTemplate",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="instances",
    help_text="Template this course was cloned from (if any)",
)
```

Also add `course_template` to `select_related` in any view that queries courses. We'll handle that in the view task.

- [ ] **Step 7: Add COURSE_TEMPLATES to ResourceArea enum**

In the `ResourceArea` class (around line 450), add after `ASSESSMENTS`:

```python
COURSE_TEMPLATES = "course_templates", "Course Templates"
```

- [ ] **Step 8: Generate and apply migration**

Run:
```bash
workdir="backend/student_evaluation_system" python manage.py makemigrations core --name add_course_templates
```

Expected: migration file created in `core/migrations/`

Run:
```bash
workdir="backend/student_evaluation_system" python manage.py migrate
```

Expected: `Applying core.add_course_templates... OK`

---

### Task 2: Create clone service

**Files:**
- Create: `backend/student_evaluation_system/core/services/course_template.py`

- [ ] **Step 1: Write the service**

```python
"""
Service for cloning CourseTemplate data into per-term Course instances.
"""

from __future__ import annotations

from django.utils import timezone

from core.models import (
    Course,
    LearningOutcome,
    LearningOutcomeProgramOutcomeMapping,
    CourseTemplate,
    CourseTemplateAssessmentLOMapping,
    CourseTemplateLOPOMapping,
)
from evaluation.models import Assessment, AssessmentLearningOutcomeMapping


def clone_course_from_template(template: CourseTemplate, term, user=None) -> Course:
    """
    Create a new Course for the given term by cloning all data from a CourseTemplate.

    Clones: template LOs → LearningOutcome, template assessments → Assessment,
    assessment-LO mappings → AssessmentLearningOutcomeMapping,
    LO-PO mappings → LearningOutcomeProgramOutcomeMapping.

    Args:
        template: The CourseTemplate to clone from.
        term: The Term instance to assign to the new Course.
        user: Optional User instance to set as created_by on cloned objects.

    Returns:
        The newly created Course instance with all cloned data.

    Raises:
        ValueError: If template is None or term is None.
    """
    if template is None:
        raise ValueError("template is required")
    if term is None:
        raise ValueError("term is required")

    # 1. Create the Course
    course = Course.objects.create(
        name=template.name,
        code=template.code,
        credits=template.credits,
        program=template.program,
        term=term,
        course_template=template,
    )

    # 2. Clone template LOs → real LearningOutcomes
    lo_map: dict[int, LearningOutcome] = {}
    for template_lo in template.learning_outcomes.all():
        lo = LearningOutcome.objects.create(
            code=template_lo.code,
            description=template_lo.description,
            course=course,
            created_by=user,
        )
        lo_map[template_lo.id] = lo

    # 3. Clone template assessments → real Assessments
    assessment_map: dict[int, Assessment] = {}
    for template_assessment in template.assessments.all():
        assessment = Assessment.objects.create(
            name=template_assessment.name,
            assessment_type=template_assessment.assessment_type,
            course=course,
            date=timezone.localdate(),
            total_score=template_assessment.total_score,
            weight=template_assessment.weight,
            created_by=user,
        )
        assessment_map[template_assessment.id] = assessment

    # 4. Clone assessment-LO mappings
    for template_assessment in template.assessments.all():
        for mapping in template_assessment.lo_mappings.all():
            AssessmentLearningOutcomeMapping.objects.create(
                assessment=assessment_map[template_assessment.id],
                learning_outcome=lo_map[mapping.template_learning_outcome_id],
                weight=mapping.weight,
            )

    # 5. Clone LO-PO mappings
    for template_lo in template.learning_outcomes.all():
        for mapping in template_lo.po_mappings.all():
            LearningOutcomeProgramOutcomeMapping.objects.create(
                course=course,
                learning_outcome=lo_map[template_lo.id],
                program_outcome=mapping.program_outcome,
                weight=mapping.weight,
            )

    return course
```

---

### Task 3: Add serializers

**Files:**
- Modify: `backend/student_evaluation_system/core/serializers.py`

- [ ] **Step 1: Add imports at top of file**

Add after the existing `from core.models import` block (around line 20), add these models:

Inside the existing `from core.models import (` block, add these names:
```python
    CourseTemplate,
    CourseTemplateLearningOutcome,
    CourseTemplateAssessment,
    CourseTemplateAssessmentLOMapping,
    CourseTemplateLOPOMapping,
```

(Add them alphabetically within the existing import block.)

- [ ] **Step 2: Add CourseTemplateSerializer**

Insert at the end of the file (before the final blank line, around line 454):

```python
class CourseTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for CourseTemplate model.

    Provides bidirectional serialization with nested read representation
    and flat write representation for the program FK.
    """

    program = ProgramSerializer(read_only=True)
    program_id = serializers.PrimaryKeyRelatedField(
        queryset=Program.objects.all(), source="program", write_only=True
    )
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
```

- [ ] **Step 3: Add CourseTemplateLearningOutcomeSerializer**

```python
class CourseTemplateLearningOutcomeSerializer(serializers.ModelSerializer):
    """Serializer for CourseTemplateLearningOutcome."""

    class Meta:
        model = CourseTemplateLearningOutcome
        fields = ["id", "code", "description", "course_template", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
```

- [ ] **Step 4: Add CourseTemplateAssessmentSerializer**

```python
class CourseTemplateAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for CourseTemplateAssessment."""

    class Meta:
        model = CourseTemplateAssessment
        fields = [
            "id",
            "name",
            "assessment_type",
            "total_score",
            "weight",
            "course_template",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
```

- [ ] **Step 5: Add CourseTemplateAssessmentLOMappingSerializer**

```python
class CourseTemplateAssessmentLOMappingSerializer(serializers.ModelSerializer):
    """Serializer for CourseTemplateAssessmentLOMapping."""

    class Meta:
        model = CourseTemplateAssessmentLOMapping
        fields = ["id", "template_assessment", "template_learning_outcome", "weight"]
```

- [ ] **Step 6: Add CourseTemplateLOPOMappingSerializer**

```python
class CourseTemplateLOPOMappingSerializer(serializers.ModelSerializer):
    """Serializer for CourseTemplateLOPOMapping."""

    class Meta:
        model = CourseTemplateLOPOMapping
        fields = ["id", "template_learning_outcome", "program_outcome", "weight"]
```

---

### Task 4: Create views

**Files:**
- Create: `backend/student_evaluation_system/core/views/course_templates.py`

- [ ] **Step 1: Write the views module**

```python
"""
Course Template ViewSets.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from core.models import (
    Course,
    Term,
    CourseTemplate,
    CourseTemplateLearningOutcome,
    CourseTemplateAssessment,
    CourseTemplateAssessmentLOMapping,
    CourseTemplateLOPOMapping,
)
from core.serializers import (
    CourseSerializer,
    CourseTemplateSerializer,
    CourseTemplateLearningOutcomeSerializer,
    CourseTemplateAssessmentSerializer,
    CourseTemplateAssessmentLOMappingSerializer,
    CourseTemplateLOPOMappingSerializer,
)
from core.permissions import InstructorPermissionMixin
from core.services.course_template import clone_course_from_template


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="program",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter templates by program ID",
            ),
        ]
    ),
)
class CourseTemplateViewSet(viewsets.ModelViewSet):
    """CRUD operations for course templates, plus instantiate action."""

    queryset = CourseTemplate.objects.select_related("program").prefetch_related("learning_outcomes", "assessments").all()
    serializer_class = CourseTemplateSerializer
    permission_classes = [AllowAny, InstructorPermissionMixin]
    resource_area = "course_templates"

    def get_queryset(self):
        queryset = super().get_queryset()
        program_id = self.request.query_params.get("program")
        if program_id:
            queryset = queryset.filter(program_id=program_id)
        return queryset

    @extend_schema(
        description="Create a new Course by cloning all template data into the given term.",
        request={"type": "object", "properties": {"term_id": {"type": "integer"}}, "required": ["term_id"]},
        responses={201: CourseSerializer},
    )
    @action(detail=True, methods=["post"])
    def instantiate(self, request, pk=None):
        """
        POST /api/core/course-templates/{id}/instantiate/
        Body: {"term_id": 1}

        Creates a new Course by cloning all template data into the given term.
        """
        template = self.get_object()

        term_id = request.data.get("term_id")
        if not term_id:
            return Response(
                {"error": "term_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            term = Term.objects.get(pk=term_id)
        except Term.DoesNotExist:
            return Response(
                {"error": f"Term with id {term_id} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            course = clone_course_from_template(template, term, user=request.user)
        except Exception as exc:
            return Response(
                {"error": f"Failed to instantiate course: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = CourseSerializer(course)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="learning-outcomes")
    def template_learning_outcomes(self, request, pk=None):
        """
        GET/POST learning outcomes for this template.
        """
        template = self.get_object()

        if request.method == "GET":
            outcomes = template.learning_outcomes.all()
            serializer = CourseTemplateLearningOutcomeSerializer(outcomes, many=True)
            return Response(serializer.data)

        # POST
        serializer = CourseTemplateLearningOutcomeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course_template=template)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="assessments")
    def template_assessments(self, request, pk=None):
        """
        GET/POST assessments for this template.
        """
        template = self.get_object()

        if request.method == "GET":
            assessments = template.assessments.all()
            serializer = CourseTemplateAssessmentSerializer(assessments, many=True)
            return Response(serializer.data)

        # POST
        serializer = CourseTemplateAssessmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course_template=template)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CourseTemplateAssessmentLOMappingViewSet(viewsets.ModelViewSet):
    """CRUD for template assessment-to-LO mappings."""

    queryset = CourseTemplateAssessmentLOMapping.objects.all()
    serializer_class = CourseTemplateAssessmentLOMappingSerializer
    permission_classes = [AllowAny, InstructorPermissionMixin]
    resource_area = "course_templates"

    def get_queryset(self):
        queryset = super().get_queryset()
        template_assessment_id = self.request.query_params.get("template_assessment")
        template_lo_id = self.request.query_params.get("template_learning_outcome")

        if template_assessment_id:
            queryset = queryset.filter(template_assessment_id=template_assessment_id)
        if template_lo_id:
            queryset = queryset.filter(template_learning_outcome_id=template_lo_id)

        return queryset


class CourseTemplateLOPOMappingViewSet(viewsets.ModelViewSet):
    """CRUD for template LO-to-PO mappings."""

    queryset = CourseTemplateLOPOMapping.objects.all()
    serializer_class = CourseTemplateLOPOMappingSerializer
    permission_classes = [AllowAny, InstructorPermissionMixin]
    resource_area = "course_templates"

    def get_queryset(self):
        queryset = super().get_queryset()
        template_lo_id = self.request.query_params.get("template_learning_outcome")

        if template_lo_id:
            queryset = queryset.filter(template_learning_outcome_id=template_lo_id)

        return queryset
```

---

### Task 5: Register views in __init__.py and urls.py

**Files:**
- Modify: `backend/student_evaluation_system/core/views/__init__.py`
- Modify: `backend/student_evaluation_system/core/urls.py`

- [ ] **Step 1: Export new ViewSets from __init__.py**

Add import block after the `# Course & Outcomes` section:

```python
# Course Templates
from .course_templates import (
    CourseTemplateViewSet,
    CourseTemplateAssessmentLOMappingViewSet,
    CourseTemplateLOPOMappingViewSet,
)
```

And add to `__all__` list:

```python
    # Course Templates
    "CourseTemplateViewSet",
    "CourseTemplateAssessmentLOMappingViewSet",
    "CourseTemplateLOPOMappingViewSet",
```

- [ ] **Step 2: Register in urls.py**

Add after `router.register(r"program-outcomes", ...)`:

```python
router.register(r"course-templates", views.CourseTemplateViewSet, basename="course-template")
router.register(
    r"course-template-assessment-lo-mappings",
    views.CourseTemplateAssessmentLOMappingViewSet,
    basename="course-template-assessment-lo-mapping",
)
router.register(
    r"course-template-lo-po-mappings",
    views.CourseTemplateLOPOMappingViewSet,
    basename="course-template-lo-po-mapping",
)
```

---

### Task 6: Add admin registration

**Files:**
- Modify: `backend/student_evaluation_system/core/admin.py`

- [ ] **Step 1: Add imports**

Add to the existing `from .models import` block (around line 2-4):
```python
    CourseTemplate,
    CourseTemplateLearningOutcome,
    CourseTemplateAssessment,
    CourseTemplateAssessmentLOMapping,
    CourseTemplateLOPOMapping,
```

- [ ] **Step 2: Register CourseTemplate in admin**

Insert after the `CourseAdmin` class (around line 130 for that file):

```python
@admin.register(CourseTemplate)
class CourseTemplateAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "credits", "program"]
    list_filter = ["program"]
    search_fields = ["code", "name"]


@admin.register(CourseTemplateLearningOutcome)
class CourseTemplateLearningOutcomeAdmin(admin.ModelAdmin):
    list_display = ["code", "description", "course_template"]
    list_filter = ["course_template__program"]
    search_fields = ["code", "description"]


@admin.register(CourseTemplateAssessment)
class CourseTemplateAssessmentAdmin(admin.ModelAdmin):
    list_display = ["name", "assessment_type", "total_score", "weight", "course_template"]
    list_filter = ["assessment_type", "course_template"]
    search_fields = ["name"]


@admin.register(CourseTemplateAssessmentLOMapping)
class CourseTemplateAssessmentLOMappingAdmin(admin.ModelAdmin):
    list_display = ["template_assessment", "template_learning_outcome", "weight"]
    list_filter = ["template_assessment__course_template"]


@admin.register(CourseTemplateLOPOMapping)
class CourseTemplateLOPOMappingAdmin(admin.ModelAdmin):
    list_display = ["template_learning_outcome", "program_outcome", "weight"]
    list_filter = ["template_learning_outcome__course_template"]
```

- [ ] **Step 3: Verify admin loads**

Run:
```bash
workdir="backend/student_evaluation_system" python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

---

### Task 7: Add test factories

**Files:**
- Modify: `backend/student_evaluation_system/tests/factories.py`

- [ ] **Step 1: Add imports**

Add the new model names to the existing `from core.models import (` block on lines 15-26 of `tests/factories.py`:

```python
from core.models import (
    University,
    Department,
    DegreeLevel,
    Program,
    Term,
    Course,
    LearningOutcome,
    ProgramOutcome,
    LearningOutcomeProgramOutcomeMapping,
    StudentLearningOutcomeScore,
    CourseTemplate,
    CourseTemplateLearningOutcome,
    CourseTemplateAssessment,
    CourseTemplateAssessmentLOMapping,
    CourseTemplateLOPOMapping,
)
```

- [ ] **Step 2: Add CourseTemplateFactory**

Insert after `CourseFactory` (around line 199):

```python
class CourseTemplateFactory(DjangoModelFactory):
    """Factory for creating CourseTemplate instances."""

    class Meta:
        model = CourseTemplate

    name = factory.Faker("catch_phrase")
    code = factory.Sequence(lambda n: f"CS{n:03d}")
    credits = factory.Iterator([3, 4, 5])
    program = factory.SubFactory(ProgramFactory)
```

- [ ] **Step 3: Add CourseTemplateLearningOutcomeFactory**

```python
class CourseTemplateLearningOutcomeFactory(DjangoModelFactory):
    """Factory for creating CourseTemplateLearningOutcome instances."""

    class Meta:
        model = CourseTemplateLearningOutcome

    description = factory.Faker("sentence")
    code = factory.Sequence(lambda n: f"LO{n}")
    course_template = factory.SubFactory(CourseTemplateFactory)
```

- [ ] **Step 4: Add CourseTemplateAssessmentFactory**

```python
class CourseTemplateAssessmentFactory(DjangoModelFactory):
    """Factory for creating CourseTemplateAssessment instances."""

    class Meta:
        model = CourseTemplateAssessment

    name = factory.Faker("word")
    assessment_type = factory.Iterator(["midterm", "final", "homework", "quiz", "project"])
    total_score = 100
    weight = factory.LazyFunction(lambda: round(1.0 / 5, 3))
    course_template = factory.SubFactory(CourseTemplateFactory)
```

- [ ] **Step 5: Add CourseTemplateAssessmentLOMappingFactory**

```python
class CourseTemplateAssessmentLOMappingFactory(DjangoModelFactory):
    """Factory for creating CourseTemplateAssessmentLOMapping instances."""

    class Meta:
        model = CourseTemplateAssessmentLOMapping

    template_assessment = factory.SubFactory(CourseTemplateAssessmentFactory)
    template_learning_outcome = factory.SubFactory(CourseTemplateLearningOutcomeFactory)
    weight = 0.5
```

- [ ] **Step 6: Add CourseTemplateLOPOMappingFactory**

```python
class CourseTemplateLOPOMappingFactory(DjangoModelFactory):
    """Factory for creating CourseTemplateLOPOMapping instances."""

    class Meta:
        model = CourseTemplateLOPOMapping

    template_learning_outcome = factory.SubFactory(CourseTemplateLearningOutcomeFactory)
    program_outcome = factory.SubFactory(ProgramOutcomeFactory)
    weight = 0.5
```

- [ ] **Step 7: Verify factories work**

Run:
```bash
workdir="backend/student_evaluation_system" python -c "
import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_evaluation_system.settings'); django.setup()
from tests.factories import CourseTemplateFactory, CourseTemplateLearningOutcomeFactory, CourseTemplateAssessmentFactory
t = CourseTemplateFactory()
lo = CourseTemplateLearningOutcomeFactory(course_template=t)
a = CourseTemplateAssessmentFactory(course_template=t)
print(f'OK: template={t}, lo={lo}, assessment={a}')
"
```

Expected: prints `OK: template=CS000: ... (Template), lo=LO0: ..., assessment=...`

---

### Task 8: Write unit tests for clone service and models

**Files:**
- Create: `backend/student_evaluation_system/tests/test_course_templates.py`

- [ ] **Step 1: Write unit tests**

```python
"""
Tests for CourseTemplate model, clone service, and API endpoints.
"""

import pytest
from django.core.exceptions import ValidationError

from core.models import (
    CourseTemplate,
    CourseTemplateLearningOutcome,
    CourseTemplateAssessment,
    CourseTemplateAssessmentLOMapping,
    CourseTemplateLOPOMapping,
    Course,
    LearningOutcome,
    LearningOutcomeProgramOutcomeMapping,
)
from evaluation.models import Assessment, AssessmentLearningOutcomeMapping


# --- Model tests ---

@pytest.mark.django_db
class TestCourseTemplateModel:
    def test_create_template(self, db_setup):
        template = CourseTemplate.objects.create(
            name="Intro to CS",
            code="CS101",
            credits=3,
            program=db_setup["program"],
        )
        assert template.code == "CS101"
        assert str(template) == "CS101: Intro to CS (Template)"

    def test_unique_code_per_program(self, db_setup):
        CourseTemplate.objects.create(
            name="First", code="CS101", credits=3, program=db_setup["program"]
        )
        with pytest.raises(Exception):
            CourseTemplate.objects.create(
                name="Second", code="CS101", credits=4, program=db_setup["program"]
            )

    def test_string_representation(self, db_setup):
        template = CourseTemplate.objects.create(
            name="Data Structures", code="CS201", program=db_setup["program"]
        )
        assert str(template) == "CS201: Data Structures (Template)"


@pytest.mark.django_db
class TestCourseTemplateLearningOutcomeModel:
    def test_create_template_lo(self, db_setup):
        template = CourseTemplate.objects.create(
            name="Math", code="MATH101", credits=3, program=db_setup["program"]
        )
        lo = CourseTemplateLearningOutcome.objects.create(
            code="LO1",
            description="Understand basic algebra",
            course_template=template,
        )
        assert lo.course_template == template
        assert template.learning_outcomes.count() == 1

    def test_unique_lo_code_per_template(self, db_setup):
        template = CourseTemplate.objects.create(
            name="Math", code="MATH101", credits=3, program=db_setup["program"]
        )
        CourseTemplateLearningOutcome.objects.create(
            code="LO1", description="First", course_template=template
        )
        with pytest.raises(Exception):
            CourseTemplateLearningOutcome.objects.create(
                code="LO1", description="Second", course_template=template
            )


@pytest.mark.django_db
class TestCourseTemplateAssessmentModel:
    def test_create_template_assessment(self, db_setup):
        template = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        assessment = CourseTemplateAssessment.objects.create(
            name="Midterm",
            assessment_type="midterm",
            total_score=100,
            weight=0.3,
            course_template=template,
        )
        assert assessment.course_template == template
        assert template.assessments.count() == 1


@pytest.mark.django_db
class TestCourseTemplateAssessmentLOMappingModel:
    def test_valid_mapping(self, db_setup):
        template = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        lo = CourseTemplateLearningOutcome.objects.create(
            code="LO1", description="Programming basics", course_template=template
        )
        assessment = CourseTemplateAssessment.objects.create(
            name="Final", assessment_type="final", total_score=100, weight=0.5,
            course_template=template
        )
        mapping = CourseTemplateAssessmentLOMapping.objects.create(
            template_assessment=assessment,
            template_learning_outcome=lo,
            weight=1.0,
        )
        assert mapping.weight == 1.0

    def test_cross_template_validation(self, db_setup):
        template1 = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        template2 = CourseTemplate.objects.create(
            name="CS102", code="CS102", credits=3, program=db_setup["program"]
        )
        lo = CourseTemplateLearningOutcome.objects.create(
            code="LO1", description="Different template", course_template=template1
        )
        assessment = CourseTemplateAssessment.objects.create(
            name="Midterm", assessment_type="midterm", total_score=100, weight=0.5,
            course_template=template2
        )
        mapping = CourseTemplateAssessmentLOMapping(
            template_assessment=assessment,
            template_learning_outcome=lo,
            weight=0.5,
        )
        with pytest.raises(ValidationError):
            mapping.clean()


# --- Clone service tests ---

@pytest.mark.django_db
class TestCloneCourseFromTemplate:
    def test_clone_basic_course(self, db_setup):
        template = CourseTemplate.objects.create(
            name="Intro to Programming",
            code="CS100",
            credits=4,
            program=db_setup["program"],
        )
        from core.services.course_template import clone_course_from_template

        course = clone_course_from_template(template, db_setup["term"])

        assert course.name == "Intro to Programming"
        assert course.code == "CS100"
        assert course.credits == 4
        assert course.program == db_setup["program"]
        assert course.term == db_setup["term"]
        assert course.course_template == template

    def test_clone_with_learning_outcomes(self, db_setup):
        template = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        CourseTemplateLearningOutcome.objects.create(
            code="LO1", description="Understand variables", course_template=template
        )
        CourseTemplateLearningOutcome.objects.create(
            code="LO2", description="Understand loops", course_template=template
        )

        from core.services.course_template import clone_course_from_template

        course = clone_course_from_template(template, db_setup["term"])

        assert course.learning_outcomes.count() == 2
        lo_codes = set(course.learning_outcomes.values_list("code", flat=True))
        assert lo_codes == {"LO1", "LO2"}

    def test_clone_with_assessments(self, db_setup):
        template = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        CourseTemplateAssessment.objects.create(
            name="Midterm", assessment_type="midterm", total_score=100, weight=0.3,
            course_template=template,
        )
        CourseTemplateAssessment.objects.create(
            name="Final", assessment_type="final", total_score=100, weight=0.7,
            course_template=template,
        )

        from core.services.course_template import clone_course_from_template

        course = clone_course_from_template(template, db_setup["term"])

        assert course.assessments.count() == 2
        assessment_names = set(course.assessments.values_list("name", flat=True))
        assert assessment_names == {"Midterm", "Final"}

    def test_clone_with_assessment_lo_mappings(self, db_setup):
        template = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        lo = CourseTemplateLearningOutcome.objects.create(
            code="LO1", description="Coding basics", course_template=template,
        )
        assessment = CourseTemplateAssessment.objects.create(
            name="Homework", assessment_type="homework", total_score=50,
            weight=0.5, course_template=template,
        )
        CourseTemplateAssessmentLOMapping.objects.create(
            template_assessment=assessment,
            template_learning_outcome=lo,
            weight=1.0,
        )

        from core.services.course_template import clone_course_from_template

        course = clone_course_from_template(template, db_setup["term"])

        cloned_assessment = course.assessments.first()
        cloned_lo = course.learning_outcomes.first()
        mapping = AssessmentLearningOutcomeMapping.objects.get(
            assessment=cloned_assessment, learning_outcome=cloned_lo
        )
        assert mapping.weight == 1.0

    def test_clone_with_lo_po_mappings(self, db_setup):
        from core.models import ProgramOutcome
        template = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        lo = CourseTemplateLearningOutcome.objects.create(
            code="LO1", description="Coding basics", course_template=template,
        )
        po = ProgramOutcome.objects.create(
            code="PO1", description="Problem solving",
            program=db_setup["program"], term=db_setup["term"],
        )
        CourseTemplateLOPOMapping.objects.create(
            template_learning_outcome=lo,
            program_outcome=po,
            weight=0.5,
        )

        from core.services.course_template import clone_course_from_template

        course = clone_course_from_template(template, db_setup["term"])

        cloned_lo = course.learning_outcomes.first()
        mapping = LearningOutcomeProgramOutcomeMapping.objects.get(
            learning_outcome=cloned_lo, program_outcome=po,
        )
        assert mapping.weight == 0.5
        assert mapping.course == course

    def test_clone_preserves_term_independence(self, db_setup):
        """Two clones from the same template should be independent."""
        from core.models import Term
        template = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        CourseTemplateLearningOutcome.objects.create(
            code="LO1", description="Basics", course_template=template,
        )

        term_fall = db_setup["term"]
        term_spring = Term.objects.create(name="Spring 2025", is_active=True)

        from core.services.course_template import clone_course_from_template

        course_fall = clone_course_from_template(template, term_fall)
        course_spring = clone_course_from_template(template, term_spring)

        assert course_fall.learning_outcomes.count() == 1
        assert course_spring.learning_outcomes.count() == 1
        assert course_fall.learning_outcomes.first().id != course_spring.learning_outcomes.first().id

    def test_clone_raises_on_none_template(self, db_setup):
        from core.services.course_template import clone_course_from_template

        with pytest.raises(ValueError, match="template is required"):
            clone_course_from_template(None, db_setup["term"])

    def test_clone_raises_on_none_term(self, db_setup):
        template = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        from core.services.course_template import clone_course_from_template

        with pytest.raises(ValueError, match="term is required"):
            clone_course_from_template(template, None)
```

- [ ] **Step 2: Run clone service tests**

Run:
```bash
workdir="backend/student_evaluation_system" pytest tests/test_course_templates.py -v
```

All tests should pass.

---

### Task 9: Write API tests

**Files:**
- Modify: `backend/student_evaluation_system/tests/test_course_templates.py` (append)

- [ ] **Step 1: Add API test class**

Append to the same test file:

```python
# --- API tests ---

@pytest.mark.django_db
class TestCourseTemplateAPI:
    def test_list_templates(self, api_client, db_setup):
        CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        response = api_client.get("/api/core/course-templates/")
        assert response.status_code == 200
        assert len(response.data) >= 1

    def test_create_template(self, api_client, db_setup, fb_admin_factory):
        admin = fb_admin_factory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            "/api/core/course-templates/",
            {
                "name": "New Template",
                "code": "NT101",
                "credits": 3,
                "program_id": db_setup["program"].id,
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["code"] == "NT101"
        assert response.data["name"] == "New Template"

    def test_get_template_learning_outcomes(self, api_client, db_setup):
        template = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        CourseTemplateLearningOutcome.objects.create(
            code="LO1", description="Basics", course_template=template
        )
        response = api_client.get(
            f"/api/core/course-templates/{template.id}/learning-outcomes/"
        )
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["code"] == "LO1"

    def test_add_learning_outcome_to_template(self, api_client, db_setup, fb_admin_factory):
        admin = fb_admin_factory()
        api_client.force_authenticate(user=admin)
        template = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        response = api_client.post(
            f"/api/core/course-templates/{template.id}/learning-outcomes/",
            {"code": "LO1", "description": "New outcome"},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["code"] == "LO1"
        assert template.learning_outcomes.count() == 1

    def test_get_template_assessments(self, api_client, db_setup):
        template = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        CourseTemplateAssessment.objects.create(
            name="Midterm", assessment_type="midterm", total_score=100,
            weight=0.3, course_template=template,
        )
        response = api_client.get(
            f"/api/core/course-templates/{template.id}/assessments/"
        )
        assert response.status_code == 200
        assert len(response.data) == 1

    def test_instantiate_creates_course(self, api_client, db_setup, fb_admin_factory):
        admin = fb_admin_factory()
        api_client.force_authenticate(user=admin)
        template = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=4, program=db_setup["program"]
        )
        CourseTemplateLearningOutcome.objects.create(
            code="LO1", description="Basics", course_template=template,
        )
        CourseTemplateAssessment.objects.create(
            name="Final", assessment_type="final", total_score=100,
            weight=0.5, course_template=template,
        )

        response = api_client.post(
            f"/api/core/course-templates/{template.id}/instantiate/",
            {"term_id": db_setup["term"].id},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["code"] == "CS101"
        assert response.data["credits"] == 4

        # Verify the course was created with cloned data
        course = Course.objects.get(id=response.data["id"])
        assert course.course_template == template
        assert course.learning_outcomes.count() == 1
        assert course.assessments.count() == 1

    def test_instantiate_missing_term_id(self, api_client, db_setup, fb_admin_factory):
        admin = fb_admin_factory()
        api_client.force_authenticate(user=admin)
        template = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        response = api_client.post(
            f"/api/core/course-templates/{template.id}/instantiate/",
            {},
            format="json",
        )
        assert response.status_code == 400
        assert "term_id" in str(response.data)

    def test_instantiate_invalid_term_id(self, api_client, db_setup, fb_admin_factory):
        admin = fb_admin_factory()
        api_client.force_authenticate(user=admin)
        template = CourseTemplate.objects.create(
            name="CS101", code="CS101", credits=3, program=db_setup["program"]
        )
        response = api_client.post(
            f"/api/core/course-templates/{template.id}/instantiate/",
            {"term_id": 99999},
            format="json",
        )
        assert response.status_code == 404
```

- [ ] **Step 2: Run API tests**

Run:
```bash
workdir="backend/student_evaluation_system" pytest tests/test_course_templates.py -v -k TestCourseTemplateAPI
```

All API tests should pass.

---

### Task 10: Run full test suite and commit

- [ ] **Step 1: Run the full test suite**

```bash
workdir="backend/student_evaluation_system" python manage.py test tests.test_course_templates -v 2
```

Also run existing tests to make sure nothing broke:
```bash
workdir="backend/student_evaluation_system" pytest tests/ -x --tb=short -q
```

Expected: all tests pass, no regressions.

- [ ] **Step 2: Commit**

```bash
git add backend/student_evaluation_system/core/models.py
git add backend/student_evaluation_system/core/serializers.py
git add backend/student_evaluation_system/core/services/course_template.py
git add backend/student_evaluation_system/core/views/course_templates.py
git add backend/student_evaluation_system/core/views/__init__.py
git add backend/student_evaluation_system/core/urls.py
git add backend/student_evaluation_system/core/admin.py
git add backend/student_evaluation_system/core/migrations/
git add backend/student_evaluation_system/tests/factories.py
git add backend/student_evaluation_system/tests/test_course_templates.py
git commit -m "feat: add CourseTemplate system with instantiate API for per-term course cloning"
```
