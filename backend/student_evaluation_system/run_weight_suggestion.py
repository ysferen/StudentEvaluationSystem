"""
Celery-based weight suggestion test script.

Usage:
    cd backend/student_evaluation_system
    uv run python run_weight_suggestion.py [course_id]

    If no course_id is provided, picks the first course with LOs from the DB.
    If no assessments exist in DB for the course, the task uses the assessment
    names and types from the DB directly.

Prerequisites:
    - Django DB accessible
    - Redis running (Celery broker)
    - Celery worker running (docker compose up celery_worker)
"""

import json
import os
import sys
import time


def _resolve_course_id():
    """Resolve course_id from CLI arg or auto-pick first course with LOs."""
    from core.models import Course

    if len(sys.argv) > 1:
        return int(sys.argv[1])

    course = Course.objects.filter(learning_outcomes__isnull=False).distinct().first()
    if course is None:
        print("ERROR: No course with learning outcomes found in DB.")
        print("Create a course with LOs first, or provide a course_id argument.")
        sys.exit(1)
    return course.id


def _print_summary_table(mappings):
    """Print a formatted summary table of assessment-to-LO weight mappings."""
    if not mappings:
        print("\nNo assessment_lo mappings returned (empty result).")
        return

    lo_count = len(next(iter(mappings.values())))
    lo_keys = [f"LO{i + 1}" for i in range(lo_count)]
    print("\n" + "-" * 50)
    header = f"{'Assessment':<20}" + "".join(f"{lo:>6}" for lo in lo_keys)
    print(header)
    print("-" * 50)
    for assessment, weights in mappings.items():
        short_name = assessment[:20]
        row = f"{short_name:<20}"
        for lo_key in lo_keys:
            row += f"{weights.get(lo_key, '?'):>6}"
        print(row)
    print("-" * 50)


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "student_evaluation_system.settings")

    import django

    django.setup()

    from core.models import Course, ProgramOutcome

    course_id = _resolve_course_id()
    course = Course.objects.get(id=course_id)
    pos = list(ProgramOutcome.objects.filter(term=course.term))
    print("=" * 70)
    print(f"Course: {course.name} (ID: {course.id})")
    print(f"POs: {len(pos)}")
    for po in pos:
        print(f"  {po.code}: {po.description}")
    print(f"LOs: {course.learning_outcomes.count()}")
    for lo in course.learning_outcomes.all():
        print(f"  {lo.code}: {lo.description}")
    print(f"Assessments in DB: {course.assessments.count()}")
    for a in course.assessments.all():
        desc = (a.description or "").strip() or f"({a.get_assessment_type_display()})"
        print(f"  {a.name}: {desc}")
    print("=" * 70)

    # --- Queue the Celery task ---
    print("\nDispatching Celery task...")

    try:
        from core.tasks import suggest_assessment_lo_weights_task

        async_result = suggest_assessment_lo_weights_task.delay(course_id=course.id)
    except Exception as e:
        print(f"ERROR: Could not dispatch task. Is Celery/Redis running?\n{e}")
        sys.exit(1)

    # --- Poll for result ---
    print(f"Task ID: {async_result.id}")
    print("Waiting for result", end="", flush=True)

    timeout = 120
    poll_interval = 0.5
    start = time.monotonic()
    while not async_result.ready():
        elapsed = time.monotonic() - start
        if elapsed > timeout:
            print(f"\nERROR: Task timed out after {timeout}s.")
            print("Check Celery worker logs for errors.")
            sys.exit(1)
        print(".", end="", flush=True)
        time.sleep(poll_interval)

    print(f" done ({time.monotonic() - start:.1f}s)")

    # --- Print result ---
    if async_result.failed():
        print(f"\nERROR: Task failed.\n{async_result.traceback}")
        sys.exit(1)

    result = async_result.result
    print("\nResponse:")
    print(json.dumps(result, indent=4))

    _print_summary_table(result.get("assessment_lo", {}))


if __name__ == "__main__":
    main()
