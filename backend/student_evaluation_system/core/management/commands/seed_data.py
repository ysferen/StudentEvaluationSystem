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
    ProgramOutcome,
    LearningOutcome,
    LearningOutcomeProgramOutcomeMapping,
)
from evaluation.models import Assessment, AssessmentLearningOutcomeMapping, CourseEnrollment, StudentGrade
from evaluation.services import calculate_course_scores
from . import data


class Command(BaseCommand):
    help = "Seed database with sample data (50 students, courses, assessments, etc.)"

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
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding",
        )

    def handle(self, *args, **options):
        # Configuration constants
        UNIVERSITIES_DATA = [
            {"name": "Acıbadem University"},
            {"name": "Istanbul University"},
        ]
        DEPARTMENTS_DATA = [
            {"name": "Engineering and Natural Sciences", "code": "ENS"},
            {"name": "Medicine", "code": "MED"},
        ]
        DEGREE_LEVELS_DATA = [
            {"name": "Bachelor"},
            {"name": "Master"},
        ]
        PROGRAMS_DATA = [
            {"name": "Computer Engineering", "code": "CSE"},
            {"name": "Biomedical Engineering", "code": "BME"},
        ]
        ASSESSMENT_TYPES = ["midterm", "final", "attendance", "project"]
        ASSESSMENT_WEIGHTS = [0.25, 0.35, 0.15, 0.25]

        start_time = time.time()

        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            clear_start = time.time()
            self.clear_data()
            self.stdout.write(f"  ⏱ Clear completed in {time.time() - clear_start:.2f}s")

        self.stdout.write(self.style.WARNING('\n=== Starting Data Seeding ==="\n'))

        # Create superuser first (outside transaction for idempotency)
        self.create_superuser()

        with transaction.atomic():
            # Create basic structure
            step_start = time.time()
            self.stdout.write("\n[1/9] Creating academic structure...")
            universities = self._create_entities(University, UNIVERSITIES_DATA, "University")
            departments = self._create_departments(universities[0], DEPARTMENTS_DATA)
            degree_levels = self._create_entities(DegreeLevel, DEGREE_LEVELS_DATA, "Degree Level")
            programs = self._create_programs(departments[0], degree_levels[0], PROGRAMS_DATA)
            terms = self.create_terms()
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Create program head
            step_start = time.time()
            self.stdout.write("\n[2/9] Creating program head...")
            head_user, head_profile = self._create_program_head(programs[0], universities[0])
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Create instructor
            step_start = time.time()
            self.stdout.write("\n[3/9] Creating instructor...")
            instructors = self._create_instructors(departments[0], universities[0])
            self._create_instructor_permissions(instructors, head_profile)
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Create 12 courses
            step_start = time.time()
            self.stdout.write("\n[4/9] Creating courses...")
            courses = self._create_courses(programs[0], terms, instructors[0], count=6)
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Create 10 program outcomes
            step_start = time.time()
            self.stdout.write("\n[5/9] Creating program outcomes...")
            program_outcomes = self._create_program_outcomes(programs[0], terms[0], head_user, count=11)
            program_outcomes.extend(self._create_program_outcomes(programs[0], terms[2], head_user, count=11))
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # For each course: 4 assessments
            step_start = time.time()
            self.stdout.write("\n[6/9] Creating learning outcomes and assessments...")
            all_assessments = []
            for course_list in courses.values():
                for i, course in enumerate(course_list, 1):
                    self.stdout.write(f"  → Course {i}/{len(course_list)}: {course.code}")
                    learning_outcomes = self._create_learning_outcomes(course, head_user)

                    # Map LOs to POs with random weights (sum=1.0)
                    self._create_lo_po_mappings(learning_outcomes, program_outcomes)

                    # Create 4 assessments
                    assessments = self._create_assessments(
                        course, assessment_types=ASSESSMENT_TYPES, weights=ASSESSMENT_WEIGHTS, count=4
                    )
                    all_assessments.extend(assessments)

                    # Map assessments to LOs with random weights (sum=1.0)
                    for assessment in assessments:
                        self._create_assessment_lo_mappings(assessment, learning_outcomes)
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Create 50 students and enroll them
            step_start = time.time()
            self.stdout.write("\n[7/9] Creating students and enrollments...")
            students = self._create_students(departments[0], programs[0], universities[0], terms[0], count=50)
            self._enroll_students(students, courses)
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Generate grades for all students
            step_start = time.time()
            self.stdout.write("\n[8/9] Calculating scores and exporting data...")
            self._generate_student_grades(students, all_assessments)
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Export credentials to CSV
            step_start = time.time()
            self.stdout.write("\n[9/9] Calculating scores and exporting data...")
            self._calculate_all_scores(courses)
            # self._export_credentials(students)
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

        total_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS("\n=== ✓ Database Seeded Successfully! ==="))
        self.stdout.write(self.style.SUCCESS(f"Total time: {total_time:.2f}s ({total_time / 60:.1f} minutes)"))
        self.stdout.write(
            self.style.SUCCESS(f"Created {len(students)} students with grades (credentials saved to student_credentials.csv)")
        )

    def clear_data(self):
        """Clear all data except superusers"""
        CustomUser.objects.filter(is_superuser=False).delete()
        University.objects.all().delete()
        Department.objects.all().delete()
        DegreeLevel.objects.all().delete()
        Program.objects.all().delete()
        Term.objects.all().delete()
        Course.objects.all().delete()
        ProgramOutcome.objects.all().delete()
        LearningOutcome.objects.all().delete()

    def create_superuser(self):
        """Create or get admin superuser account."""
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
            self.stdout.write(self.style.SUCCESS("✓ Superuser created: admin / admin"))
        else:
            self.stdout.write("✓ Superuser already exists: admin")

    def _create_entities(self, model, data_list, entity_type):
        """Generic helper to create entities and log them."""
        entities = []
        for entity_data in data_list:
            entity, _ = model.objects.get_or_create(**entity_data)
            entities.append(entity)
            self.stdout.write(f"  ✓ {entity_type}: {entity.name}")
        return entities

    def _create_departments(self, university, departments_data):
        """Create departments linked to a university."""
        departments = []
        for department_data in departments_data:
            dept, _ = Department.objects.get_or_create(**department_data, university=university)
            departments.append(dept)
            self.stdout.write(f"  ✓ Department: {dept.name}")
        return departments

    def _create_programs(self, department, degree_level, programs_data):
        """Create programs linked to a department and degree level."""
        programs = []
        for program_data in programs_data:
            program, _ = Program.objects.get_or_create(**program_data, department=department, degree_level=degree_level)
            programs.append(program)
            self.stdout.write(f"  ✓ Program: {program.name}")
        return programs

    def create_terms(self):
        """Create academic terms."""
        term1, _ = Term.objects.get_or_create(
            name="Spring 2026", defaults={"is_active": True}, academic_year=2026, semester="spring"
        )
        term2, _ = Term.objects.get_or_create(
            name="Fall 2025", defaults={"is_active": False}, academic_year=2025, semester="fall"
        )
        term3, _ = Term.objects.get_or_create(
            name="Spring 2025", defaults={"is_active": False}, academic_year=2025, semester="spring"
        )
        term4, _ = Term.objects.get_or_create(
            name="Fall 2024", defaults={"is_active": False}, academic_year=2024, semester="fall"
        )
        self.stdout.write(f"  ✓ Term: {term1.name}")
        self.stdout.write(f"  ✓ Term: {term2.name}")
        self.stdout.write(f"  ✓ Term: {term3.name}")
        self.stdout.write(f"  ✓ Term: {term4.name}")
        return term1, term2, term3, term4

    def _create_instructors(self, department, university):
        """Create instructors with predefined credentials."""
        instructors_data = [
            {
                "username": "instructor1",
                "email": "instructor@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "password": "instructor123",
                "title": "Professor",
            },
            {
                "username": "instructor2",
                "email": "instructor2@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "password": "instructor234",
                "title": "Associate Professor",
            },
        ]
        instructors = []
        for instructor_data in instructors_data:
            instructor = self._create_user(
                instructor_data["username"],
                instructor_data["email"],
                instructor_data["first_name"],
                instructor_data["last_name"],
                instructor_data["password"],
                "instructor",
                department,
                university,
            )
            InstructorProfile.objects.get_or_create(user=instructor, defaults={"title": instructor_data["title"]})
            self.stdout.write(f"  ✓ Instructor: {instructor.get_full_name()}")
            instructors.append(instructor)
        return instructors

    def _create_instructor_permissions(self, instructors, program_head):
        """Create default instructor permissions for the seeded instructors."""
        created_count = 0

        for instructor in instructors:
            instructor_profile = getattr(instructor, "instructor_profile", None)
            if instructor_profile is None:
                continue

            for resource_area in self.RESOURCE_AREAS:
                _, created = InstructorPermission.objects.get_or_create(
                    instructor=instructor_profile,
                    program_head=program_head,
                    resource_area=resource_area,
                    defaults={"permission_tier": PermissionTier.VIEW},
                )
                if created:
                    created_count += 1

        self.stdout.write(f"  ✓ Instructor permissions: {created_count} created")

    def _create_program_head(self, program, university):
        """Create the program head user and profile."""
        head_user, created = CustomUser.objects.get_or_create(
            username="headuser",
            defaults={
                "email": "head@example.com",
                "first_name": "Program",
                "last_name": "Head",
                "role": "program_head",
                "department": program.department,
                "university": university,
            },
        )
        if created:
            head_user.set_password("head123")
            head_user.save()
        head_profile, _ = ProgramHeadProfile.objects.get_or_create(
            user=head_user,
            defaults={"program": program},
        )
        self.stdout.write(self.style.SUCCESS(f"  ✓ Program Head: {head_user.get_full_name()} ({program.name})"))
        return head_user, head_profile

    def _create_courses(self, program, terms, instructor, count=6):
        """Create courses for different academic years."""
        courses = {"2025": [], "2026": []}

        for i in range(count):
            course, _ = Course.objects.get_or_create(
                code=f"CS{300 + i}",
                defaults={
                    "name": data.COURSES_2025[i] if i < len(data.COURSES_2025) else f"Course {i + 1}",
                    "credits": 3,
                    "program": program,
                    "term": terms[2],  # Spring 2025
                },
            )
            course.instructors.add(instructor)
            courses["2025"].append(course)

        for i in range(count):
            course, _ = Course.objects.get_or_create(
                code=f"CS{400 + i}",
                defaults={
                    "name": data.COURSES_2026[i] if i < len(data.COURSES_2026) else f"Course {i + 1}",
                    "credits": 3,
                    "program": program,
                    "term": terms[0],  # Spring 2026
                },
            )
            course.instructors.add(instructor)
            courses["2026"].append(course)

        self.stdout.write(f"  ✓ Courses: {len(courses['2025']) + len(courses['2026'])} created")
        return courses

    def _create_program_outcomes(self, program, term, head_user, count=10):
        """Create program outcomes for a given program and term."""
        outcomes = []
        for i in range(0, count):
            po, _ = ProgramOutcome.objects.get_or_create(
                code=f"PO{i}",
                program=program,
                term=term,
                defaults={
                    "description": data.PROGRAM_OUTCOME_DESCRIPTIONS[i]
                    if i < len(data.PROGRAM_OUTCOME_DESCRIPTIONS)
                    else f"Program Outcome {i}: Sample description for PO{i}",
                    "created_by": head_user,
                },
            )
            outcomes.append(po)

        self.stdout.write(f"  ✓ Program Outcomes: {len(outcomes)} created")
        return outcomes

    def _create_learning_outcomes(self, course, head_user):
        """Create learning outcomes for a course."""
        outcomes = []
        descriptions = data.LEARNING_OUTCOMES.get(course.name, [])

        if not descriptions:
            self.stdout.write(
                self.style.WARNING(f"  ! No LO template found for '{course.name}'. Using generic learning outcomes.")
            )
            descriptions = [
                f"Demonstrate foundational understanding of {course.name}.",
                f"Apply {course.name} methods to solve problems.",
                f"Evaluate and communicate solutions in {course.name}.",
            ]

        for i, description in enumerate(descriptions, start=1):
            lo, _ = LearningOutcome.objects.get_or_create(
                code=f"LO{i}",
                course=course,
                defaults={"description": description, "created_by": head_user},
            )
            outcomes.append(lo)

        return outcomes

    def _create_lo_po_mappings(self, learning_outcomes, program_outcomes):
        """Map each LO to 2-3 random POs with weights summing to 1.0"""
        for lo in learning_outcomes:
            # Select 2-3 random POs
            selected_pos = random.sample(program_outcomes, k=random.randint(2, 3))
            # Generate random weights that sum to 1.0
            weights = [random.random() for _ in selected_pos]
            total = sum(weights)
            normalized_weights = [w / total for w in weights]
            for po, weight in zip(selected_pos, normalized_weights):
                LearningOutcomeProgramOutcomeMapping.objects.get_or_create(
                    course=lo.course,
                    learning_outcome=lo,
                    program_outcome=po,
                    defaults={"weight": round(weight, 3)},  # ← weight only used on INSERT
                )

    def _create_assessments(self, course, assessment_types, weights, count=4):
        """Create assessments for a course."""
        assessments = []

        for i in range(count):
            assessment, _ = Assessment.objects.get_or_create(
                name=f"{assessment_types[i].title()}",
                course=course,
                defaults={
                    "assessment_type": assessment_types[i],
                    "date": f"2025-{10 + (i // 4)}-{1 + ((i % 4) * 7):02d}",
                    "total_score": 100,
                    "weight": weights[i],
                },
            )
            assessments.append(assessment)

        return assessments

    def _create_assessment_lo_mappings(self, assessment, learning_outcomes):
        """Map assessment to all LOs with equal weights (sum=1.0)"""
        if not learning_outcomes:
            self.stdout.write(
                self.style.WARNING(
                    f"  ! Skipping LO mapping for {assessment.course.code} - {assessment.name}: no learning outcomes found"
                )
            )
            return

        weight_per_lo = 1.0 / len(learning_outcomes)

        for lo in learning_outcomes:
            AssessmentLearningOutcomeMapping.objects.get_or_create(
                assessment=assessment, learning_outcome=lo, defaults={"weight": round(weight_per_lo, 3)}
            )

    def _create_students(self, department, program, university, term, count=50):
        """Create student users and profiles."""
        students = []

        for i in range(0, count):
            username = f"student{i:03d}"
            password = f"pass{i:03d}"

            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "first_name": data.NAMES[i % len(data.NAMES)],
                    "last_name": data.SURNAMES[i % len(data.SURNAMES)],
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
                    "student_id": f"2214{i:05d}",
                    "program": program,
                    "enrollment_term": term,
                },
            )

            students.append({"user": user, "profile": profile, "password": password})

        self.stdout.write(f"  ✓ Students: {len(students)} created")
        return students

    def _enroll_students(self, students, courses):
        """Enroll half of the students in all courses, and the other half in a random subset of courses"""
        enrollments_count = 0
        for i, student_data in enumerate(students):
            # Select a random subset of courses for each student
            if i < len(students) // 2:
                student_courses = courses["2025"]  # Enroll first half of students in all courses
            else:
                student_courses = courses["2026"]  # Enroll second half of students in all courses
            for course in student_courses:
                CourseEnrollment.objects.get_or_create(student=student_data["user"], course=course)
                enrollments_count += 1

        self.stdout.write(f"  ✓ Enrollments: {enrollments_count} created")

    def _generate_student_grades(self, students, assessments):
        """Generate random grades for all students in all assessments"""

        grades_to_create = []
        total_grades = len(students) * len(assessments)

        self.stdout.write(f"  → Generating {total_grades} grades...")

        for student_data in students:
            for assessment in assessments:
                # Generate realistic grades (60-100 range with normal distribution)
                # Use random normal distribution centered at 65 with std dev of 25
                raw_score = random.gauss(65, 25)
                # Clamp to valid range and round
                score = round(max(0, min(assessment.total_score, raw_score)))

                grades_to_create.append(StudentGrade(student=student_data["user"], assessment=assessment, score=score))

        # Bulk create all grades at once (much faster than individual saves)
        self.stdout.write(f"  → Bulk inserting {len(grades_to_create)} grades...")
        StudentGrade.objects.bulk_create(
            grades_to_create,
            batch_size=1000,
        )
        self.stdout.write(f"  ✓ Generated {len(grades_to_create)} student grades")

    def _calculate_all_scores(self, courses):
        """Calculate LO and PO scores for all courses"""
        self.stdout.write(f"  → Calculating outcome scores for {len(courses)} courses...")

        for course_list in courses.values():
            self.stdout.write(f"  → Processing {len(course_list)} courses for term {course_list[0].term.name}...")
            for i, course in enumerate(course_list, 1):
                self.stdout.write(f"    • Course {i}/{len(course_list)}: {course.code}", ending="... ")
                try:
                    calculate_course_scores(course.id)
                    self.stdout.write(self.style.SUCCESS("✓"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ Error: {str(e)}"))

            self.stdout.write("  ✓ Score calculation completed")

    def _export_credentials(self, students):
        """Export student credentials to CSV"""
        import csv

        with open("student_credentials.csv", "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Username", "Password", "Email", "Student ID", "Full Name"])

            for student_data in students:
                user = student_data["user"]
                profile = student_data["profile"]
                writer.writerow(
                    [user.username, student_data["password"], user.email, profile.student_id, user.get_full_name()]
                )

        self.stdout.write("  ✓ Credentials exported to student_credentials.csv")

    def _create_user(self, username, email, first_name, last_name, password, role, department, university):
        """Helper to create a user with credentials."""
        user, created = CustomUser.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                "department": department,
                "university": university,
            },
        )
        if created:
            user.set_password(password)
            user.save()
        return user
