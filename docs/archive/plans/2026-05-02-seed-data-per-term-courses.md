# Seed Data: Per-Term Course Model Fix

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix seed data so each CourseTemplate is cloned into multiple terms (one per cohort that takes that semester), and each cohort is enrolled only in courses matching their actual semester progress. Make all year/term computation derive from a single configuration point in `data.py`.

**Architecture:** Add a `FIRST_COHORT_START_YEAR` constant to `data.py`. All term generation, cohort offsets, course instantiation, and enrollment logic derive from it via a `_semester_to_term_key` helper. The active term is Spring of the freshman cohort's first year, giving correct year-level calculations across all cohorts.

**Tech Stack:** Django 5.2, Django ORM

---

### Task 1: Add seed configuration to data.py

**Files:**
- Modify: `backend/student_evaluation_system/core/management/commands/data.py` (append at end)

- [ ] **Step 1: Append configuration constants**

At the end of `data.py`, append:

```python
# ── Seed configuration ──────────────────────────────────────────────────

# Calendar year when the newest (first-year) cohort starts their first fall
# semester. All term generation and cohort offsets are derived from this.
FIRST_COHORT_START_YEAR = 2024

# Number of cohorts to generate. Cohorts are spaced one year apart; the
# oldest cohort starts (NUM_COHORTS - 1) calendar years before
# FIRST_COHORT_START_YEAR.
NUM_COHORTS = 4

STUDENTS_PER_COHORT = 20
```

- [ ] **Step 2: Verify file is valid Python**

Run: `python -c "from core.management.commands import data; print(data.FIRST_COHORT_START_YEAR)"`
Expected: prints `2024`

- [ ] **Step 3: Commit**

```bash
git add backend/student_evaluation_system/core/management/commands/data.py
git commit -m "feat: add seed configuration constants for data-driven cohort generation"
```

---

### Task 2: Add semester-to-term-key helper to seed_data.py

**Files:**
- Modify: `backend/student_evaluation_system/core/management/commands/seed_data.py` (add static method)

- [ ] **Step 1: Add `_semester_to_term_key` as a static method**

Insert the following static method inside the `Command` class, before `_create_terms`:

```python
@staticmethod
def _semester_to_term_key(cohort_start_cal_year, semester_num):
    """
    Map a cohort's semester number to the (academic_year, semester) key
    used to look up Term objects created by _create_terms.

    Args:
        cohort_start_cal_year: Calendar year the cohort began (e.g., 2024).
        semester_num: 1-8, where 1 = first fall, 2 = first spring, etc.

    Returns:
        Tuple of (academic_year, semester) matching Term fields.
    """
    offset = (semester_num - 1) // 2
    is_fall = (semester_num % 2) == 1
    cal_year = cohort_start_cal_year + offset + (0 if is_fall else 1)
    acad_year = cal_year + 1 if is_fall else cal_year
    sem = "fall" if is_fall else "spring"
    return (acad_year, sem)
```

- [ ] **Step 2: Verify the helper with a quick Python check**

Run:
```bash
python -c "
from core.management.commands.seed_data import Command
# Verify key mappings
assert Command._semester_to_term_key(2024, 1) == (2025, 'fall'), 'sem1 fail'
assert Command._semester_to_term_key(2024, 2) == (2025, 'spring'), 'sem2 fail'
assert Command._semester_to_term_key(2024, 8) == (2028, 'spring'), 'sem8 fail'
assert Command._semester_to_term_key(2021, 1) == (2022, 'fall'), 'oldest sem1 fail'
print('All assertions passed')
"
```

- [ ] **Step 3: Commit**

```bash
git add backend/student_evaluation_system/core/management/commands/seed_data.py
git commit -m "feat: add _semester_to_term_key helper for data-driven term mapping"
```

---

### Task 3: Rewrite _create_terms to be data-driven

**Files:**
- Modify: `backend/student_evaluation_system/core/management/commands/seed_data.py` — replace `_create_terms` method (lines 170-180)

- [ ] **Step 1: Replace `_create_terms` method**

Replace the entire method with:

```python
def _create_terms(self):
    """Create terms covering all cohorts' complete 8-semester curriculum.

    Terms span from the oldest cohort's sem1 to the newest cohort's sem8.
    The active term is Spring of the freshman cohort's first year,
    ensuring year_level = 1 for freshmen and 4 for seniors.
    """
    oldest_start = data.FIRST_COHORT_START_YEAR - (data.NUM_COHORTS - 1)
    min_acad_year = oldest_start + 1        # oldest cohort's sem1 academic_year
    max_acad_year = data.FIRST_COHORT_START_YEAR + 4  # newest cohort's sem8
    active_acad_year = data.FIRST_COHORT_START_YEAR + 1

    terms = []
    for year in range(min_acad_year, max_acad_year + 1):
        for sem, name in [("fall", f"Güz {year - 1}-{year}"), ("spring", f"Bahar {year - 1}-{year}")]:
            t, _ = Term.objects.get_or_create(
                name=name,
                defaults={"is_active": False, "academic_year": year, "semester": sem},
            )
            terms.append(t)

    # Ensure exactly one active term (handles re-runs)
    active_term = next(
        t for t in terms
        if t.academic_year == active_acad_year and t.semester == "spring"
    )
    if not active_term.is_active:
        active_term.is_active = True
        active_term.save()  # Term.save() auto-deactivates all others

    return terms
```

- [ ] **Step 2: Commit**

```bash
git add backend/student_evaluation_system/core/management/commands/seed_data.py
git commit -m "refactor: make _create_terms data-driven, derive range from FIRST_COHORT_START_YEAR"
```

---

### Task 4: Rewrite _build_curriculum to clone into multiple terms

**Files:**
- Modify: `backend/student_evaluation_system/core/management/commands/seed_data.py` — replace `_build_curriculum` method (lines 239-305)

- [ ] **Step 1: Replace `_build_curriculum` method**

Replace the entire method with:

```python
def _build_curriculum(self, program, terms, instructors, head_user):
    """Create CourseTemplates from CURRICULUM, clone into every term
    where ANY cohort takes that semester."""
    from django.db import IntegrityError

    all_courses = []
    semester_keys = sorted(data.CURRICULUM.keys())
    terms_by_key = {(t.academic_year, t.semester): t for t in terms}

    for sem_idx, sem_key in enumerate(semester_keys):
        semester_num = sem_idx + 1  # 1-8

        for course_info in data.CURRICULUM[sem_key]:
            code, name, credits, ctype, los, assessments = course_info

            # ── Create / get template (shared across all terms) ──
            template, _ = CourseTemplate.objects.get_or_create(
                code=code, program=program,
                defaults={"name": name, "credits": credits},
            )

            # Template LOs
            if template.learning_outcomes.count() == 0:
                for i, lo_desc in enumerate(los, 1):
                    CourseTemplateLearningOutcome.objects.get_or_create(
                        code=f"LO{i}", course_template=template,
                        defaults={"description": lo_desc},
                    )

            # Template assessments & LO mappings
            if template.assessments.count() == 0:
                for i, (aname, weight) in enumerate(assessments):
                    atypes = ["midterm", "final", "project", "quiz", "homework"]
                    atype = atypes[i % len(atypes)] if i < 4 else "other"
                    ta = CourseTemplateAssessment.objects.create(
                        name=aname, assessment_type=atype,
                        total_score=100, weight=weight,
                        course_template=template,
                    )
                    for tlo in template.learning_outcomes.all():
                        CourseTemplateAssessmentLOMapping.objects.get_or_create(
                            template_assessment=ta,
                            template_learning_outcome=tlo,
                            defaults={"weight": round(1.0 / template.learning_outcomes.count(), 3)},
                        )

            # ── Clone into each cohort's term for this semester ──
            for cohort_idx in range(data.NUM_COHORTS):
                cohort_start = data.FIRST_COHORT_START_YEAR - (data.NUM_COHORTS - 1 - cohort_idx)
                key = self._semester_to_term_key(cohort_start, semester_num)
                term = terms_by_key.get(key)
                if term is None:
                    continue

                # Guard against duplicate clones (clone_course_from_template uses create())
                existing = Course.objects.filter(
                    code=code, program=program, term=term
                ).first()
                if existing is not None:
                    course = existing
                else:
                    try:
                        course = clone_course_from_template(template, term, user=head_user)
                    except IntegrityError:
                        course = Course.objects.get(
                            code=code, program=program, term=term
                        )

                instructor = random.choice(instructors)
                course.instructors.add(instructor)
                if course not in all_courses:
                    all_courses.append(course)

                self.stdout.write(f"  ✓ {code} — {name} ({term.name})")

        self.stdout.write(
            f"  ✓ Semester {semester_num}: cloned into {data.NUM_COHORTS} terms"
        )

    self.stdout.write(f"  ✓ {len(all_courses)} total course instances")
    return all_courses
```

- [ ] **Step 2: Commit**

```bash
git add backend/student_evaluation_system/core/management/commands/seed_data.py
git commit -m "refactor: clone courses into per-cohort terms, derive from FIRST_COHORT_START_YEAR"
```

---

### Task 5: Rewrite _create_student_cohorts to enroll per actual progress

**Files:**
- Modify: `backend/student_evaluation_system/core/management/commands/seed_data.py` — replace `_create_student_cohorts` method (lines 351-406)

- [ ] **Step 1: Replace `_create_student_cohorts` method**

Replace the entire method with:

```python
def _create_student_cohorts(self, department, program, university, terms, all_courses):
    """Create cohorts and enroll each student in courses matching their
    actual semester progress up to the active term snapshot."""
    all_students = []
    terms_by_key = {(t.academic_year, t.semester): t for t in terms}
    active_term = next(t for t in terms if t.is_active)

    for cohort_idx in range(data.NUM_COHORTS):
        # cohort_idx 0 = oldest, NUM_COHORTS-1 = newest (freshman)
        cohort_start = data.FIRST_COHORT_START_YEAR - (data.NUM_COHORTS - 1 - cohort_idx)
        label = f"{data.NUM_COHORTS - cohort_idx}. Sınıf"

        # Build list of terms this cohort participates in
        # (sem1 through whichever semester falls in the active term)
        cohort_terms = []
        for sem_num in range(1, 9):
            key = self._semester_to_term_key(cohort_start, sem_num)
            term = terms_by_key.get(key)
            if term is None:
                continue
            cohort_terms.append(term)
            if term.pk == active_term.pk:
                break  # stop at active term (snapshot boundary)

        # The cohort's actual first term (used for enrollment_term on profile)
        enrollment_key = self._semester_to_term_key(cohort_start, 1)
        enrollment_term = terms_by_key.get(enrollment_key)

        cohort_total_enrolled = 0

        for i in range(data.STUDENTS_PER_COHORT):
            idx = cohort_idx * data.STUDENTS_PER_COHORT + i
            username = f"student{idx:03d}"
            password = f"pass{idx:03d}"

            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "first_name": data.NAMES[idx % len(data.NAMES)],
                    "last_name": data.SURNAMES[idx % len(data.SURNAMES)],
                    "role": "student",
                    "department": department,
                    "university": university,
                },
            )
            if created:
                user.set_password(password)
                user.save()

            profile, _ = StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    "student_id": f"{cohort_start}{i + 1:04d}",
                    "program": program,
                    "enrollment_term": enrollment_term,
                },
            )

            # Enroll only in courses offered in this cohort's terms
            enrolled = 0
            for course in all_courses:
                if course.term in cohort_terms:
                    CourseEnrollment.objects.get_or_create(
                        student=user, course=course
                    )
                    enrolled += 1

            cohort_total_enrolled += enrolled
            all_students.append({
                "user": user, "profile": profile, "password": password,
            })

        per_student = cohort_total_enrolled // data.STUDENTS_PER_COHORT
        self.stdout.write(
            f"  ✓ {label} (start {cohort_start}): "
            f"{data.STUDENTS_PER_COHORT} students, "
            f"~{per_student} enrollments each"
        )

    return all_students
```

- [ ] **Step 2: Commit**

```bash
git add backend/student_evaluation_system/core/management/commands/seed_data.py
git commit -m "refactor: enroll cohorts by actual semester progress, derive from FIRST_COHORT_START_YEAR"
```

---

### Task 6: Validate — run seed and verify

- [ ] **Step 1: Clear and re-seed**

```bash
cd backend/student_evaluation_system && python manage.py seed_data --clear
```
Expected: Completes without IntegrityError or other exceptions. Output shows multiple course instances per code, sensible enrollment counts.

- [ ] **Step 2: Verify year levels via Django shell**

```bash
cd backend/student_evaluation_system && python manage.py shell -c "
from core.models import Term
from users.models import StudentProfile
active = Term.objects.get(is_active=True)
for sp in StudentProfile.objects.select_related('enrollment_term').order_by('enrollment_term__academic_year')[:4]:
    yl = min(active.academic_year - sp.enrollment_term.academic_year + 1, 4)
    print(f'{sp.student_id}: enrollment_ay={sp.enrollment_term.academic_year}, active_ay={active.academic_year}, year_level={yl}')
"
```
Expected: Four distinct year levels (1,2,3,4).

- [ ] **Step 3: Verify per-term course model**

```bash
cd backend/student_evaluation_system && python manage.py shell -c "
from core.models import Course
from collections import Counter
counts = Counter(Course.objects.values_list('code', flat=True))
for code, cnt in counts.most_common(5):
    print(f'{code}: {cnt} instances')
"
```
Expected: Each course code appears multiple times (once per term/cohort).

- [ ] **Step 4: Commit verification results**

```bash
git add -A
git commit -m "test: verify seed data produces correct year levels and per-term courses"
```
