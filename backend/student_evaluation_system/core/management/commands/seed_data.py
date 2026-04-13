import random
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import CustomUser, StudentProfile, InstructorProfile
from core.models import (
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

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding",
        )

    def handle(self, *args, **options):
        start_time = time.time()

        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            clear_start = time.time()
            self.clear_data()
            self.stdout.write(f"  ⏱ Clear completed in {time.time() - clear_start:.2f}s")

        self.stdout.write(self.style.WARNING('\n=== Starting Data Seeding ==="\n'))

        with transaction.atomic():
            # Create basic structure
            step_start = time.time()
            self.stdout.write("\n[1/8] Creating academic structure...")
            universities = self.create_universities()
            departments = self.create_departments(universities[0])
            degree_levels = self.create_degree_levels()
            programs = self.create_programs(departments[0], degree_levels[0])
            terms = self.create_terms()
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Create instructor
            step_start = time.time()
            self.stdout.write("\n[2/8] Creating instructor...")
            instructors = self.create_instructors(departments[0], universities[0])
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Create 6 courses
            step_start = time.time()
            self.stdout.write("\n[3/8] Creating courses...")
            courses = self.create_courses(programs[0], terms[0], instructors[0], count=6)
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Create 10 program outcomes
            step_start = time.time()
            self.stdout.write("\n[4/8] Creating program outcomes...")
            program_outcomes = self.create_program_outcomes(programs[0], terms[0], count=10)
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # For each course: 5 LOs, 4 assessments
            step_start = time.time()
            self.stdout.write("\n[5/8] Creating learning outcomes and assessments...")
            all_assessments = []
            for i, course in enumerate(courses, 1):
                self.stdout.write(f"  → Course {i}/{len(courses)}: {course.code}")
                learning_outcomes = self.create_learning_outcomes(course)

                # Map LOs to POs with random weights (sum=1.0)
                self.create_lo_po_mappings(learning_outcomes, program_outcomes)

                # Create 4 assessments
                assessments = self.create_assessments(course, count=4)
                all_assessments.extend(assessments)

                # Map assessments to LOs with random weights (sum=1.0)
                for assessment in assessments:
                    self.create_assessment_lo_mappings(assessment, learning_outcomes)
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Create 50 students and enroll them
            step_start = time.time()
            self.stdout.write("\n[6/8] Creating students and enrollments...")
            students = self.create_students(departments[0], programs[0], universities[0], terms[0], count=50)
            self.enroll_students(students, courses)
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Generate grades for all students
            step_start = time.time()
            self.stdout.write("\n[7/8] Generating student grades...")
            self.generate_student_grades(students, all_assessments)
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Export credentials to CSV
            step_start = time.time()
            self.stdout.write("\n[8/8] Calculating scores and exporting data...")
            self.calculate_all_scores(courses)
            self.export_credentials(students)
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

    def create_universities(self):
        universities = []
        university1, _ = University.objects.get_or_create(name="Acıbadem University")
        university2, _ = University.objects.get_or_create(name="Istanbul University")
        universities.append(university1)
        universities.append(university2)
        self.stdout.write(f"  ✓ University: {university1.name}")
        self.stdout.write(f"  ✓ University: {university2.name}")
        return universities

    def create_departments(self, university):
        departments = []
        department1, _ = Department.objects.get_or_create(
            name="Engineering and Natural Sciences", code="ENS", university=university
        )
        department2, _ = Department.objects.get_or_create(name="Medicine", code="MED", university=university)
        departments.append(department1)
        departments.append(department2)
        self.stdout.write(f"  ✓ Department: {department1.name}")
        self.stdout.write(f"  ✓ Department: {department2.name}")
        return departments

    def create_degree_levels(self):
        degrees = []
        degree_level1, _ = DegreeLevel.objects.get_or_create(name="Bachelor")
        degree_level2, _ = DegreeLevel.objects.get_or_create(name="Master")
        degrees.append(degree_level1)
        degrees.append(degree_level2)
        self.stdout.write(f"  ✓ Degree Level: {degree_level1.name}")
        self.stdout.write(f"  ✓ Degree Level: {degree_level2.name}")
        return degrees

    def create_programs(self, department, degree_level):
        programs = []
        program1, _ = Program.objects.get_or_create(
            name="Computer Engineering", code="CSE", department=department, degree_level=degree_level
        )
        program2, _ = Program.objects.get_or_create(
            name="Biomedical Engineering", code="BME", department=department, degree_level=degree_level
        )
        programs.append(program1)
        programs.append(program2)
        self.stdout.write(f"  ✓ Program: {program1.name}")
        self.stdout.write(f"  ✓ Program: {program2.name}")
        return programs

    def create_terms(self):
        term1, _ = Term.objects.get_or_create(name="Fall 2025", defaults={"is_active": False})
        term2, _ = Term.objects.get_or_create(name="Spring 2026", defaults={"is_active": True})
        self.stdout.write(f"  ✓ Term: {term1.name}")
        self.stdout.write(f"  ✓ Term: {term2.name}")
        return term1, term2

    def create_instructors(self, department, university):
        instructors = []
        user1, created1 = CustomUser.objects.get_or_create(
            username="instructor1",
            defaults={
                "email": "instructor@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "role": "instructor",
                "department": department,
                "university": university,
            },
        )
        if created1:
            user1.set_password("instructor123")
            user1.save()

        profile1, _ = InstructorProfile.objects.get_or_create(user=user1, defaults={"title": "Professor"})
        self.stdout.write(f"  ✓ Instructor: {user1.get_full_name()}")
        instructors.append(user1)

        user2, created2 = CustomUser.objects.get_or_create(
            username="instructor2",
            defaults={
                "email": "instructor2@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "role": "instructor",
                "department": department,
                "university": university,
            },
        )
        if created2:
            user2.set_password("instructor234")
            user2.save()

        profile2, _ = InstructorProfile.objects.get_or_create(user=user2, defaults={"title": "Associate Professor"})
        self.stdout.write(f"  ✓ Instructor: {user2.get_full_name()}")
        instructors.append(user2)

        return instructors

    def create_courses(self, program, term, instructor, count=6):
        fall_courses = [
            "Artificial Intelligence",
            "Algorithms I",
            "Data Systems",
            "Operating Systems",
            "Computer Networks",
            "Microcontrollers",
        ]

        spring_courses = [
            "Machine Learning",
            "Algorithms II",
            "Cloud Computing",
            "Distributed Systems",
            "Computer Security",
            "Embedded Systems",
        ]
        courses = []

        for i in range(count):
            course, _ = Course.objects.get_or_create(
                code=f"CS{300 + i}",
                defaults={
                    "name": fall_courses[i] if i < len(fall_courses) else f"Course {i + 1}",
                    "credits": 3,
                    "program": program,
                    "term": term,
                },
            )
            course.instructors.add(instructor)
            courses.append(course)

        for i in range(count):
            course, _ = Course.objects.get_or_create(
                code=f"CS{400 + i}",
                defaults={
                    "name": spring_courses[i] if i < len(spring_courses) else f"Course {i + 1}",
                    "credits": 3,
                    "program": program,
                    "term": term,
                },
            )
            course.instructors.add(instructor)
            courses.append(course)

        self.stdout.write(f"  ✓ Courses: {len(courses)} created")
        return courses

    def create_program_outcomes(self, program, term, count=11):
        outcomes = []
        for i in range(0, count):
            po, _ = ProgramOutcome.objects.get_or_create(
                code=f"PO{i}",
                program=program,
                term=term,
                defaults={
                    "description": data.PROGRAM_OUTCOME_DESCRIPTIONS[i]
                    if i < len(data.PROGRAM_OUTCOME_DESCRIPTIONS)
                    else f"Program Outcome {i}: Sample description for PO{i}"
                },
            )
            outcomes.append(po)

        self.stdout.write(f"  ✓ Program Outcomes: {len(outcomes)} created")
        return outcomes

    def create_learning_outcomes(self, course):
        outcomes = []
        descriptions = data.LEARNING_OUTCOMES.get(course.name, [])

        if not descriptions:
            self.stdout.write(
                self.style.WARNING(f"  ! No LO template found for '{course.name}'. Using generic learning outcomes.")
            )
            descriptions = [
                f"Demonstrate foundational understanding of {course.name} concepts.",
                f"Apply {course.name} methods to solve practical problems.",
                f"Evaluate and communicate solutions in the context of {course.name}.",
            ]

        for i, description in enumerate(descriptions, start=1):
            lo, _ = LearningOutcome.objects.get_or_create(code=f"LO{i}", course=course, defaults={"description": description})
            outcomes.append(lo)

        return outcomes

    def create_lo_po_mappings(self, learning_outcomes, program_outcomes):
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
                    course=lo.course, learning_outcome=lo, program_outcome=po, weight=round(weight, 3)
                )

    def create_assessments(self, course, count=4):
        assessment_types = ["midterm", "final", "attendance", "project"]
        assessments = []

        # Weights must sum to 1.0
        weights = [0.25, 0.35, 0.15, 0.25]  # Midterm, Final, Attendance, Project

        for i in range(count):
            assessment, _ = Assessment.objects.get_or_create(
                name=f"{assessment_types[i].title()}",
                course=course,
                defaults={
                    "assessment_type": assessment_types[i],
                    "date": f"2025-{10 + i // 4}-{1 + (i % 4) * 7:02d}",
                    "total_score": 100,
                    "weight": weights[i],
                },
            )
            assessments.append(assessment)

        return assessments

    def create_assessment_lo_mappings(self, assessment, learning_outcomes):
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

    def create_students(self, department, program, university, term, count=50):
        students = []

        for i in range(0, count):
            username = f"student{i:03d}"
            password = f"pass{i:03d}"

            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "first_name": data.NAMES[i % len(data.NAMES)],
                    "last_name": data.SURNAMES[
                        i % len(data.SURNAMES) if i < len(data.SURNAMES) else (i + 1) % len(data.SURNAMES)
                    ],
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

    def enroll_students(self, students, courses):
        """Enroll half of the students in all courses, and the other half in a random subset of courses"""
        enrollments_count = 0
        for i, student_data in enumerate(students):
            # Select a random subset of courses for each student
            student_courses = random.sample(courses, k=len(courses) // 2)
            if i < len(students) // 2:
                student_courses = courses  # Enroll first half of students in all courses
            for course in student_courses:
                CourseEnrollment.objects.get_or_create(student=student_data["user"], course=course)
                enrollments_count += 1

        self.stdout.write(f"  ✓ Enrollments: {enrollments_count} created")

    def generate_student_grades(self, students, assessments):
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
        StudentGrade.objects.bulk_create(grades_to_create, batch_size=1000)
        self.stdout.write(f"  ✓ Generated {len(grades_to_create)} student grades")

    def calculate_all_scores(self, courses):
        """Calculate LO and PO scores for all courses"""
        self.stdout.write(f"  → Calculating outcome scores for {len(courses)} courses...")

        for i, course in enumerate(courses, 1):
            self.stdout.write(f"    • Course {i}/{len(courses)}: {course.code}", ending="... ")
            try:
                calculate_course_scores(course.id)
                self.stdout.write(self.style.SUCCESS("✓"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error: {str(e)}"))

        self.stdout.write("  ✓ Score calculation completed")

    def export_credentials(self, students):
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
