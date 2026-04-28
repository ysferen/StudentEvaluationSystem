from django.db import migrations


def backfill_instructor_permissions(apps, schema_editor):
    Course = apps.get_model("core", "Course")
    InstructorPermission = apps.get_model("core", "InstructorPermission")
    InstructorProfile = apps.get_model("users", "InstructorProfile")

    RESOURCE_AREAS = [
        "courses",
        "programs",
        "learning_outcomes",
        "program_outcomes",
        "students",
        "lo_po_weights",
        "assessment_lo_weights",
        "assessments",
    ]

    created_count = 0

    for course in Course.objects.select_related("program").prefetch_related("instructors"):
        try:
            program_head = course.program.program_head_profile
        except Exception:
            continue

        for user in course.instructors.all():
            try:
                instructor_profile = InstructorProfile.objects.get(user=user)
            except InstructorProfile.DoesNotExist:
                continue

            for area in RESOURCE_AREAS:
                _, created = InstructorPermission.objects.get_or_create(
                    instructor=instructor_profile,
                    program_head=program_head,
                    resource_area=area,
                    defaults={"permission_tier": "view"},
                )
                if created:
                    created_count += 1

    if created_count:
        print(f"  Created {created_count} instructor permissions from existing course assignments.")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0013_program_duration_years_term_academic_year_and_more"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_instructor_permissions, migrations.RunPython.noop),
    ]
