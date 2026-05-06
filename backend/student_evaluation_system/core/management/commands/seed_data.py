import random
import time
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from users.models import CustomUser, StudentProfile, InstructorProfile, ProgramHeadProfile
from core.models import (
    InstructorPermission,
    PermissionTier,
    ResourceArea,
    University,
    Department,
    DegreeLevel,
    Program,
    Term,
    Course,
    CourseTemplate,
    CourseTemplateLearningOutcome,
    CourseTemplateAssessment,
    CourseTemplateAssessmentLOMapping,
    LearningOutcome,
    LearningOutcomeProgramOutcomeMapping,
    ProgramOutcome,
)
from core.services.course_template import clone_course_from_template
from evaluation.models import AssessmentLearningOutcomeMapping, CourseEnrollment, StudentGrade
from evaluation.services import calculate_course_scores
from . import data


class Command(BaseCommand):
    help = "Seed database with a realistic Computer Engineering curriculum (4 cohorts × 20 students)."

    RESOURCE_AREAS = (
        ResourceArea.COURSES,
        ResourceArea.PROGRAMS,
        ResourceArea.LEARNING_OUTCOMES,
        ResourceArea.PROGRAM_OUTCOMES,
        ResourceArea.STUDENTS,
        ResourceArea.LO_PO_WEIGHTS,
        ResourceArea.ASSESSMENT_LO_WEIGHTS,
        ResourceArea.ASSESSMENTS,
        ResourceArea.COURSE_TEMPLATES,
    )

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")
        parser.add_argument("--skip-students", action="store_true", help="Skip student/grades/scores (steps 7-9)")

    def handle(self, *args, **options):
        start_time = time.time()
        skip_students = options["skip_students"]

        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            self.clear_data()

        step_count = "[6/6]" if skip_students else "[9/9]"
        self.stdout.write(self.style.WARNING(f"\n=== Starting Data Seeding ({'light' if skip_students else 'full'}) ===\n"))

        self.create_superuser()

        all_students = []
        with transaction.atomic():
            # ── Academic structure ──
            self.stdout.write(f"\n[1/{step_count}] Creating academic structure...")
            uni = University.objects.get_or_create(name="Acıbadem University")[0]
            dept = Department.objects.get_or_create(
                name="Mühendislik ve Doğa Bilimleri Fakültesi", code="ENS", university=uni
            )[0]
            degree = DegreeLevel.objects.get_or_create(name="Lisans")[0]
            program = Program.objects.get_or_create(
                name="Bilgisayar Mühendisliği (İngilizce)", code="CSE", department=dept, degree_level=degree
            )[0]
            terms = self._create_terms()
            self.stdout.write(f"  ✓ {len(terms)} terms created")

            # ── Program head ──
            self.stdout.write(f"\n[2/{step_count}] Creating program head...")
            head_user, head_profile = self._create_program_head(program, uni, dept)

            # ── Instructors ──
            self.stdout.write(f"\n[3/{step_count}] Creating instructors...")
            instructors = self._create_instructors(dept, uni)
            self._create_instructor_permissions(instructors, head_profile)
            self.stdout.write(f"  ✓ {len(instructors)} instructors with full permissions")

            # ── Course templates + instantiate into terms ──
            self.stdout.write(f"\n[4/{step_count}] Creating CourseTemplates and instantiating courses...")
            all_courses, courses_by_sem_cohort = self._build_curriculum(program, terms, instructors, head_user)

            # ── Program outcomes ──
            self.stdout.write(f"\n[5/{step_count}] Creating program outcomes...")
            pos = []
            for term in terms:
                pos.extend(self._create_program_outcomes(program, term, head_user))

            # ── LOs, assessments, mappings ──
            self.stdout.write(f"\n[6/{step_count}] Creating learning outcomes, assessments, and mappings...")
            all_assessments = []
            for course in all_courses:
                template = course.course_template
                if template is None:
                    continue

                # Clone the template LOs as real LOs for this course offering
                los = list(course.learning_outcomes.all())
                if not los:
                    continue

                # Map LOs to random POs
                self._create_lo_po_mappings(los, pos)

                # Assessments were already cloned from template — map them to LOs
                for assessment in course.assessments.all():
                    self._create_assessment_lo_mappings(assessment, los)
                    all_assessments.append(assessment)

            self.stdout.write(f"  ✓ {len(all_assessments)} assessments mapped")

            if not skip_students:
                # ── Students (4 cohorts × 20) ──
                self.stdout.write("\n[7/9] Creating students and enrollments...")
                all_students = self._create_student_cohorts(dept, program, uni, terms, all_courses, courses_by_sem_cohort)

                # ── Grades ──
                self.stdout.write("\n[8/9] Generating grades...")
                self._generate_student_grades(all_students, all_assessments)

                # ── Scores ──
                self.stdout.write("\n[9/9] Calculating scores...")
                self._calculate_all_scores(all_courses)

        total = time.time() - start_time
        summary_parts = [f"{len(all_courses)} courses", f"{len(all_assessments)} assessments"]
        if all_students:
            summary_parts.insert(0, f"{len(all_students)} students")
        self.stdout.write(self.style.SUCCESS(f"\n=== ✓ Done in {total:.1f}s — {', '.join(summary_parts)} ==="))

    # ── helpers ──────────────────────────────────────────────────────

    def clear_data(self):
        CustomUser.objects.filter(is_superuser=False).delete()
        University.objects.all().delete()
        Department.objects.all().delete()
        DegreeLevel.objects.all().delete()
        Program.objects.all().delete()
        Term.objects.all().delete()
        CourseTemplate.objects.all().delete()
        Course.objects.all().delete()
        ProgramOutcome.objects.all().delete()
        LearningOutcome.objects.all().delete()

    def create_superuser(self):
        admin, created = CustomUser.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "first_name": "Admin",
                "last_name": "User",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        if created:
            admin.set_password("admin")
            admin.save()
            self.stdout.write(self.style.SUCCESS("✓ Superuser: admin / admin"))

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

    def _create_terms(self):
        """Create terms from the oldest cohort's sem1 up to the active term.

        No future terms are created — the active term is the boundary.
        Year levels: 4/3/2/1 for senior/junior/sophomore/freshman.
        """
        oldest_start = data.FIRST_COHORT_START_YEAR - (data.NUM_COHORTS - 1)
        min_acad_year = oldest_start + 1  # oldest cohort's sem1 academic_year
        active_acad_year = data.FIRST_COHORT_START_YEAR + 1
        max_acad_year = active_acad_year  # stop at the active term

        terms = []
        for year in range(min_acad_year, max_acad_year + 1):
            for sem, name in [("fall", f"Güz {year - 1}-{year}"), ("spring", f"Bahar {year - 1}-{year}")]:
                t, _ = Term.objects.get_or_create(
                    name=name,
                    defaults={"is_active": False, "academic_year": year, "semester": sem},
                )
                terms.append(t)

        # Ensure exactly one active term (handles re-runs)
        active_term = next(t for t in terms if t.academic_year == active_acad_year and t.semester == "spring")
        if not active_term.is_active:
            active_term.is_active = True
            active_term.save()  # Term.save() auto-deactivates all others

        return terms

    def _create_program_head(self, program, university, department):
        head_user, created = CustomUser.objects.get_or_create(
            username="headuser",
            defaults={
                "email": "head@example.com",
                "first_name": "Program",
                "last_name": "Head",
                "role": "program_head",
                "department": department,
                "university": university,
            },
        )
        if created:
            head_user.set_password("head123")
            head_user.save()
        head_profile, _ = ProgramHeadProfile.objects.get_or_create(user=head_user, defaults={"program": program})
        self.stdout.write(f"  ✓ Program Head: {head_user.get_full_name()}")
        return head_user, head_profile

    def _create_instructors(self, department, university):
        instructors = []
        for inst_data in data.INSTRUCTORS:
            user, created = CustomUser.objects.get_or_create(
                username=inst_data["username"],
                defaults={
                    "email": inst_data["email"],
                    "first_name": inst_data["first_name"],
                    "last_name": inst_data["last_name"],
                    "role": "instructor",
                    "department": department,
                    "university": university,
                },
            )
            if created:
                user.set_password(inst_data["password"])
                user.save()
            InstructorProfile.objects.get_or_create(user=user, defaults={"title": inst_data["title"]})
            instructors.append(user)
        return instructors

    def _create_instructor_permissions(self, instructors, program_head):
        created = 0
        for user in instructors:
            profile = getattr(user, "instructor_profile", None)
            if profile is None:
                continue
            for area in self.RESOURCE_AREAS:
                _, c = InstructorPermission.objects.get_or_create(
                    instructor=profile,
                    program_head=program_head,
                    resource_area=area,
                    defaults={"permission_tier": PermissionTier.FULL},
                )
                if c:
                    created += 1
        self.stdout.write(f"  ✓ {created} permissions")

    @staticmethod
    def _ensure_template_data(template, los, assessments):
        """Create template LOs and assessments if not already present."""
        if template.learning_outcomes.count() == 0:
            for i, lo_desc in enumerate(los, 1):
                CourseTemplateLearningOutcome.objects.get_or_create(
                    code=f"LO{i}",
                    course_template=template,
                    defaults={"description": lo_desc},
                )

        if template.assessments.count() == 0:
            for i, (aname, weight) in enumerate(assessments):
                atypes = ["midterm", "final", "project", "quiz", "homework"]
                atype = atypes[i % len(atypes)] if i < 4 else "other"
                ta = CourseTemplateAssessment.objects.create(
                    name=aname,
                    assessment_type=atype,
                    total_score=100,
                    weight=weight,
                    course_template=template,
                )
                for tlo in template.learning_outcomes.all():
                    CourseTemplateAssessmentLOMapping.objects.get_or_create(
                        template_assessment=ta,
                        template_learning_outcome=tlo,
                        defaults={"weight": 3},
                    )

    def _build_curriculum(self, program, terms, instructors, head_user):
        """Create CourseTemplates from CURRICULUM, clone into every term
        where ANY cohort takes that semester."""
        all_courses = []
        courses_by_sem_cohort = {}  # (semester_num, cohort_start) -> list of Course
        semester_keys = sorted(data.CURRICULUM.keys())
        terms_by_key = {(t.academic_year, t.semester): t for t in terms}

        for sem_idx, sem_key in enumerate(semester_keys):
            semester_num = sem_idx + 1  # 1-8

            for course_info in data.CURRICULUM[sem_key]:
                code, name, credits, ctype, los, assessments = course_info

                template, _ = CourseTemplate.objects.get_or_create(
                    code=code,
                    program=program,
                    defaults={"name": name, "credits": credits},
                )
                self._ensure_template_data(template, los, assessments)

                # Clone into each cohort's term for this semester
                for cohort_idx in range(data.NUM_COHORTS):
                    cohort_start = data.FIRST_COHORT_START_YEAR - (data.NUM_COHORTS - 1 - cohort_idx)
                    key = self._semester_to_term_key(cohort_start, semester_num)
                    term = terms_by_key.get(key)
                    if term is None:
                        continue

                    existing = Course.objects.filter(code=code, program=program, term=term).first()
                    if existing is not None:
                        course = existing
                    else:
                        try:
                            course = clone_course_from_template(template, term, user=head_user)
                        except IntegrityError:
                            course = Course.objects.get(code=code, program=program, term=term)

                    instructor = random.choice(instructors)
                    course.instructors.add(instructor)
                    sem_cohort_key = (semester_num, cohort_start)
                    courses_by_sem_cohort.setdefault(sem_cohort_key, []).append(course)
                    if course not in all_courses:
                        all_courses.append(course)

                    self.stdout.write(f"  ✓ {code} — {name} ({term.name})")

            self.stdout.write(f"  ✓ Semester {semester_num}: cloned into {data.NUM_COHORTS} terms")

        self.stdout.write(f"  ✓ {len(all_courses)} total course instances")
        return all_courses, courses_by_sem_cohort

    def _create_program_outcomes(self, program, term, head_user):
        outcomes = []
        for i, desc in enumerate(data.PROGRAM_OUTCOME_DESCRIPTIONS):
            po, _ = ProgramOutcome.objects.get_or_create(
                code=f"PO{i + 1}",
                program=program,
                term=term,
                defaults={"description": desc, "created_by": head_user},
            )
            outcomes.append(po)
        self.stdout.write(f"  ✓ {len(outcomes)} program outcomes")
        return outcomes

    def _create_lo_po_mappings(self, learning_outcomes, program_outcomes):
        """Map each LO to 2-4 POs from the SAME TERM as the course."""
        for lo in learning_outcomes:
            course_term = lo.course.term
            # Only consider POs belonging to this course's term
            term_pos = [po for po in program_outcomes if po.term_id == course_term.id]
            if not term_pos:
                continue
            k = min(random.randint(2, 4), len(term_pos))
            selected = random.sample(term_pos, k=k)
            for po in selected:
                w = random.randint(1, 5)
                LearningOutcomeProgramOutcomeMapping.objects.get_or_create(
                    course=lo.course,
                    learning_outcome=lo,
                    program_outcome=po,
                    defaults={"weight": w},
                )

    def _create_assessment_lo_mappings(self, assessment, learning_outcomes):
        if not learning_outcomes:
            return
        for lo in learning_outcomes:
            AssessmentLearningOutcomeMapping.objects.get_or_create(
                assessment=assessment,
                learning_outcome=lo,
                defaults={"weight": 3},
            )

    def _create_student_cohorts(self, department, program, university, terms, all_courses, courses_by_sem_cohort):
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

                # Enroll only in courses belonging to this cohort's semesters
                enrolled = 0
                for sem_num in range(1, len(cohort_terms) + 1):
                    key = (sem_num, cohort_start)
                    for course in courses_by_sem_cohort.get(key, []):
                        CourseEnrollment.objects.get_or_create(student=user, course=course)
                        enrolled += 1

                cohort_total_enrolled += enrolled
                all_students.append(
                    {
                        "user": user,
                        "profile": profile,
                        "password": password,
                    }
                )

            per_student = cohort_total_enrolled // data.STUDENTS_PER_COHORT
            self.stdout.write(
                f"  ✓ {label} (start {cohort_start}): {data.STUDENTS_PER_COHORT} students, ~{per_student} enrollments each"
            )

        return all_students

    def _generate_student_grades(self, students, assessments):
        grades_to_create = []
        total = len(students) * len(assessments)
        self.stdout.write(f"  → Generating {total} grades...")

        for student_data in students:
            for assessment in assessments:
                # Only grade if the student is enrolled in the assessment's course
                student = student_data["user"]
                if not CourseEnrollment.objects.filter(student=student, course=assessment.course).exists():
                    continue
                raw = random.gauss(65, 25)
                score = round(max(0, min(assessment.total_score, raw)))
                grades_to_create.append(StudentGrade(student=student, assessment=assessment, score=score))

        StudentGrade.objects.bulk_create(grades_to_create, batch_size=1000)
        self.stdout.write(f"  ✓ {len(grades_to_create)} grades")

    def _calculate_all_scores(self, courses):
        for i, course in enumerate(courses, 1):
            try:
                calculate_course_scores(course.id)
            except Exception:
                pass
        self.stdout.write(f"  ✓ Scores calculated for {len(courses)} courses")
