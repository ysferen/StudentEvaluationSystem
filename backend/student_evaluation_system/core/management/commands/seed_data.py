import random
import time
from django.core.management.base import BaseCommand
from django.db import transaction
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

    def handle(self, *args, **options):
        start_time = time.time()

        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            self.clear_data()

        self.stdout.write(self.style.WARNING("\n=== Starting Data Seeding ===\n"))

        self.create_superuser()

        with transaction.atomic():
            # ── Academic structure ──
            self.stdout.write("\n[1/9] Creating academic structure...")
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
            self.stdout.write("\n[2/9] Creating program head...")
            head_user, head_profile = self._create_program_head(program, uni, dept)

            # ── Instructors ──
            self.stdout.write("\n[3/9] Creating instructors...")
            instructors = self._create_instructors(dept, uni)
            self._create_instructor_permissions(instructors, head_profile)
            self.stdout.write(f"  ✓ {len(instructors)} instructors with full permissions")

            # ── Course templates + instantiate into terms ──
            self.stdout.write("\n[4/9] Creating CourseTemplates and instantiating courses...")
            all_courses = self._build_curriculum(program, terms, instructors, head_user)

            # ── Program outcomes ──
            self.stdout.write("\n[5/9] Creating program outcomes...")
            pos = []
            for term in terms:
                pos.extend(self._create_program_outcomes(program, term, head_user))

            # ── LOs, assessments, mappings ──
            self.stdout.write("\n[6/9] Creating learning outcomes, assessments, and mappings...")
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

            # ── Students (4 cohorts × 20) ──
            self.stdout.write("\n[7/9] Creating students and enrollments...")
            all_students = self._create_student_cohorts(dept, program, uni, terms, all_courses)

            # ── Grades ──
            self.stdout.write("\n[8/9] Generating grades...")
            self._generate_student_grades(all_students, all_assessments)

            # ── Scores ──
            self.stdout.write("\n[9/9] Calculating scores...")
            self._calculate_all_scores(all_courses)

        total = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(
                f"\n=== ✓ Done in {total:.1f}s — {len(all_students)} students, "
                f"{len(all_courses)} courses, {len(all_assessments)} assessments ==="
            )
        )

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

    def _create_terms(self):
        """Create 8 terms (4 years, Fall + Spring)"""
        terms = []
        for year in [2024, 2025, 2026, 2027]:
            for sem, name in [("fall", f"Güz {year - 1}-{year}"), ("spring", f"Bahar {year - 1}-{year}")]:
                t, _ = Term.objects.get_or_create(
                    name=name,
                    defaults={"is_active": (year == 2027 and sem == "spring"), "academic_year": year, "semester": sem},
                )
                terms.append(t)
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

    def _build_curriculum(self, program, terms, instructors, head_user):
        """Create CourseTemplates from CURRICULUM, instantiate into appropriate terms."""
        all_courses = []
        semester_keys = sorted(data.CURRICULUM.keys())
        # Map: semester index → which terms to instantiate into
        semester_term_map = {
            0: terms[0],  # sem1 → Fall 2024
            1: terms[1],  # sem2 → Spring 2025
            2: terms[2],  # sem3 → Fall 2025
            3: terms[3],  # sem4 → Spring 2026
            4: terms[4],  # sem5 → Fall 2026
            5: terms[5],  # sem6 → Spring 2027
            6: terms[6],  # sem7 → Fall 2027
            7: terms[7],  # sem8 → Spring 2028
        }

        for idx, sem_key in enumerate(semester_keys):
            term = semester_term_map[idx]
            for course_info in data.CURRICULUM[sem_key]:
                code, name, credits, ctype, los, assessments = course_info

                # Create or get CourseTemplate
                template, _ = CourseTemplate.objects.get_or_create(
                    code=code,
                    program=program,
                    defaults={"name": name, "credits": credits},
                )

                # Add template LOs if missing
                if template.learning_outcomes.count() == 0:
                    for i, lo_desc in enumerate(los, 1):
                        CourseTemplateLearningOutcome.objects.get_or_create(
                            code=f"LO{i}",
                            course_template=template,
                            defaults={"description": lo_desc},
                        )

                # Add template assessments if missing
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
                        # Map to all template LOs
                        for tlo in template.learning_outcomes.all():
                            CourseTemplateAssessmentLOMapping.objects.get_or_create(
                                template_assessment=ta,
                                template_learning_outcome=tlo,
                                defaults={"weight": round(1.0 / template.learning_outcomes.count(), 3)},
                            )

                # Clone into this term
                instructor = random.choice(instructors)
                course = clone_course_from_template(template, term, user=head_user)
                course.instructors.add(instructor)
                all_courses.append(course)

                self.stdout.write(f"  ✓ {code} — {name} ({term.name})")

        self.stdout.write(f"  ✓ {len(all_courses)} courses instantiated")
        return all_courses

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
        for lo in learning_outcomes:
            selected = random.sample(program_outcomes, k=random.randint(2, 4))
            weights = [random.random() for _ in selected]
            total = sum(weights)
            for po, w in zip(selected, [round(x / total, 3) for x in weights]):
                LearningOutcomeProgramOutcomeMapping.objects.get_or_create(
                    course=lo.course,
                    learning_outcome=lo,
                    program_outcome=po,
                    defaults={"weight": w},
                )

    def _create_assessment_lo_mappings(self, assessment, learning_outcomes):
        if not learning_outcomes:
            return
        w = round(1.0 / len(learning_outcomes), 3)
        for lo in learning_outcomes:
            AssessmentLearningOutcomeMapping.objects.get_or_create(
                assessment=assessment,
                learning_outcome=lo,
                defaults={"weight": w},
            )

    def _create_student_cohorts(self, department, program, university, terms, all_courses):
        """Create 4 cohorts of 20 students, each starting in a different year."""
        all_students = []

        # Cohort definitions: (start_year, which terms their courses cover)
        cohorts = [
            ("2021", terms[0:8], "4. Sınıf"),  # Seniors — enrolled Fall 2021, take all 8 terms
            ("2022", terms[2:8], "3. Sınıf"),  # Juniors — enrolled Fall 2022, take sem3-8
            ("2023", terms[4:8], "2. Sınıf"),  # Sophomores — enrolled Fall 2023, take sem5-8
            ("2024", terms[6:8], "1. Sınıf"),  # Freshmen — enrolled Fall 2024, take sem7-8
        ]

        offset = 0
        for start_year, cohort_terms, label in cohorts:
            for i in range(20):
                idx = offset + i
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
                        "student_id": f"{start_year}{i + 1:04d}",
                        "program": program,
                        "enrollment_term": cohort_terms[0] if cohort_terms else terms[0],
                    },
                )

                # Enroll in courses that belong to this cohort's terms
                enrolled = 0
                for course in all_courses:
                    if course.term in cohort_terms:
                        CourseEnrollment.objects.get_or_create(student=user, course=course)
                        enrolled += 1

                all_students.append({"user": user, "profile": profile, "password": password})

            self.stdout.write(f"  ✓ {label} ({start_year}): 20 students, {enrolled} enrollments each")
            offset += 20

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
