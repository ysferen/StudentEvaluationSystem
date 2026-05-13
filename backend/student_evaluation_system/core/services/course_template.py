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
)
from evaluation.models import Assessment, AssessmentLearningOutcomeMapping


def clone_program_outcomes_for_term(old_term, new_term, program, user=None) -> dict[int, "ProgramOutcome"]:
    """
    Clone all ProgramOutcomes from old_term to new_term for a given program.

    Returns a mapping of old PO id → new PO instance for use in LO-PO mapping cloning.
    """
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
            },
        )
        po_map[old_po.id] = new_po
    return po_map


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

    # 5. Clone LO-PO mappings — use new-term POs when a po_map is provided
    for template_lo in template.learning_outcomes.all():
        for mapping in template_lo.po_mappings.all():
            program_outcome = po_map.get(mapping.program_outcome_id) if po_map else mapping.program_outcome
            if program_outcome is None:
                continue
            LearningOutcomeProgramOutcomeMapping.objects.create(
                course=course,
                learning_outcome=lo_map[template_lo.id],
                program_outcome=program_outcome,
                weight=mapping.weight,
            )

    return course
