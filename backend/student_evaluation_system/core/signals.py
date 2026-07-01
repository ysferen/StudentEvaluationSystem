from django.db.models.signals import m2m_changed, post_save, post_delete
from django.dispatch import receiver
import logging

from core.models import Course, InstructorPermission, ResourceArea, PermissionTier
from core.services.audit import log_audit
from evaluation.models import StudentGrade

logger = logging.getLogger(__name__)


# Resource areas where course instructors get full CRUD access (since they teach the course).
COURSE_LEVEL_FULL_AREAS = [
    ResourceArea.COURSES,
    ResourceArea.LEARNING_OUTCOMES,
    ResourceArea.LO_PO_WEIGHTS,
    ResourceArea.ASSESSMENT_LO_WEIGHTS,
    ResourceArea.ASSESSMENTS,
    ResourceArea.COURSE_TEMPLATES,
]

# Resource areas where course instructors get view-only access.
VIEW_ONLY_AREAS = [
    ResourceArea.PROGRAMS,
    ResourceArea.PROGRAM_OUTCOMES,
    ResourceArea.STUDENTS,
]


def _ensure_permissions(instructor_profile, program_head):
    for area in COURSE_LEVEL_FULL_AREAS:
        permission, _ = InstructorPermission.objects.get_or_create(
            instructor=instructor_profile,
            resource_area=area,
            defaults={"program_head": program_head, "permission_tier": PermissionTier.FULL},
        )
        if permission.program_head_id is None and program_head is not None:
            permission.program_head = program_head
            permission.save(update_fields=["program_head", "updated_at"])
    for area in VIEW_ONLY_AREAS:
        permission, _ = InstructorPermission.objects.get_or_create(
            instructor=instructor_profile,
            resource_area=area,
            defaults={"program_head": program_head, "permission_tier": PermissionTier.VIEW},
        )
        if permission.program_head_id is None and program_head is not None:
            permission.program_head = program_head
            permission.save(update_fields=["program_head", "updated_at"])


@receiver(m2m_changed, sender=Course.instructors.through)
def create_instructor_permissions_on_course_add(sender, instance, action, pk_set, **kwargs):
    if action != "post_add":
        return

    course = instance
    if not course.program_id:
        return

    program_head = None
    try:
        program_head = course.program.program_head_profile
    except Exception:
        logger.warning("Could not resolve program head for course %s", course.id)

    from users.models import InstructorProfile

    for user_id in pk_set:
        try:
            instructor_profile = InstructorProfile.objects.get(user_id=user_id)
        except InstructorProfile.DoesNotExist:
            continue
        _ensure_permissions(instructor_profile, program_head)


@receiver(post_save, sender=StudentGrade)
def audit_grade_save(sender, instance, created, **kwargs):
    user = getattr(instance, "_audit_user", None)
    if not user:
        return

    if created:
        after = {
            "score": instance.score,
            "total_score": instance.assessment.total_score,
            "assessment_id": instance.assessment_id,
            "student_id": instance.student_id,
        }
        log_audit(user, "CREATE", "StudentGrade", instance.id, before=None, after=after)


@receiver(post_delete, sender=StudentGrade)
def audit_grade_delete(sender, instance, **kwargs):
    user = getattr(instance, "_audit_user", None)
    if not user:
        return

    before = {
        "score": instance.score,
        "total_score": instance.assessment.total_score,
        "assessment_id": instance.assessment_id,
        "student_id": instance.student_id,
    }
    log_audit(user, "DELETE", "StudentGrade", instance.id, before=before, after=None)
