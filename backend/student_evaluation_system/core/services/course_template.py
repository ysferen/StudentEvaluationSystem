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
    ProgramOutcome,
    ProgramOutcomeTemplate,
)
from evaluation.models import Assessment, AssessmentLearningOutcomeMapping


def instantiate_program_outcomes_from_templates(new_term, program, user=None) -> dict[int, "ProgramOutcome"]:
    """
    Instantiate all ProgramOutcomeTemplate rows for a program into a term.

    Returns a mapping of template PO id to concrete ProgramOutcome instance.
    """
    po_map: dict[int, ProgramOutcome] = {}
    templates = ProgramOutcomeTemplate.objects.filter(program=program)
    for template in templates:
        po, _ = ProgramOutcome.objects.get_or_create(
            code=template.code,
            program=program,
            term=new_term,
            defaults={
                "description": template.description,
                "weight": template.weight,
                "created_by": user,
                "program_outcome_template": template,
            },
        )
        if po.program_outcome_template_id is None:
            po.program_outcome_template = template
            po.save(update_fields=["program_outcome_template"])
        po_map[template.id] = po
    return po_map


def clone_program_outcomes_for_term(old_term, new_term, program, user=None) -> dict[int, "ProgramOutcome"]:
    """
    Clone all ProgramOutcomes from old_term to new_term for a given program.

    Returns a mapping of old PO id → new PO instance for use in LO-PO mapping cloning.
    """
    template_map = instantiate_program_outcomes_from_templates(new_term, program, user=user)
    if template_map:
        return template_map

    old_pos = ProgramOutcome.objects.filter(program=program, term=old_term)
    po_map: dict[int, ProgramOutcome] = {}
    for old_po in old_pos:
        new_po, _ = ProgramOutcome.objects.get_or_create(
            code=old_po.code,
            program=program,
            term=new_term,
            defaults={
                "description": old_po.description,
                "weight": old_po.weight,
                "created_by": user,
                "program_outcome_template": old_po.program_outcome_template,
            },
        )
        po_map[old_po.id] = new_po
    return po_map


def _clone_learning_outcomes(template: CourseTemplate, course: Course, user=None) -> dict[int, LearningOutcome]:
    """Clone template learning outcomes to course learning outcomes."""
    lo_map: dict[int, LearningOutcome] = {}
    for template_lo in template.learning_outcomes.all():
        lo = LearningOutcome.objects.create(
            code=template_lo.code,
            description=template_lo.description,
            course=course,
            created_by=user,
        )
        lo_map[template_lo.id] = lo
    return lo_map


def _clone_assessments(template: CourseTemplate, course: Course, user=None) -> dict[int, Assessment]:
    """Clone template assessments to course assessments."""
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
    return assessment_map


def _clone_assessment_lo_mappings(
    template: CourseTemplate,
    assessment_map: dict[int, Assessment],
    lo_map: dict[int, LearningOutcome],
) -> None:
    """Clone assessment-learning outcome mappings."""
    for template_assessment in template.assessments.all():
        for mapping in template_assessment.lo_mappings.all():
            AssessmentLearningOutcomeMapping.objects.create(
                assessment=assessment_map[template_assessment.id],
                learning_outcome=lo_map[mapping.template_learning_outcome_id],
                weight=mapping.weight,
            )


def _clone_lo_po_mappings(
    template: CourseTemplate,
    course: Course,
    lo_map: dict[int, LearningOutcome],
    po_map: dict[int, ProgramOutcome] | None = None,
) -> None:
    """Clone learning outcome-program outcome mappings."""
    for template_lo in template.learning_outcomes.all():
        for mapping in template_lo.po_mappings.all():
            program_outcome = None
            if po_map and mapping.program_outcome_template_id:
                program_outcome = po_map.get(mapping.program_outcome_template_id)
            if program_outcome is None and po_map and mapping.program_outcome_id:
                program_outcome = po_map.get(mapping.program_outcome_id)
            if program_outcome is None:
                program_outcome = mapping.program_outcome
            if program_outcome is None:
                continue
            LearningOutcomeProgramOutcomeMapping.objects.create(
                course=course,
                learning_outcome=lo_map[template_lo.id],
                program_outcome=program_outcome,
                weight=mapping.weight,
            )


def clone_course_from_template(
    template: CourseTemplate, term, user=None, po_map: dict[int, ProgramOutcome] | None = None
) -> Course:
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
    lo_map = _clone_learning_outcomes(template, course, user)

    # 3. Clone template assessments → real Assessments
    assessment_map = _clone_assessments(template, course, user)

    # 4. Clone assessment-LO mappings
    _clone_assessment_lo_mappings(template, assessment_map, lo_map)

    # 5. Clone LO-PO mappings — use new-term POs when a po_map is provided
    _clone_lo_po_mappings(template, course, lo_map, po_map)

    return course
