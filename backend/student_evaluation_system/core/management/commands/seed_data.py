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
            university = self.create_university()
            department = self.create_department(university)
            degree_level = self.create_degree_level()
            program = self.create_program(department, degree_level)
            term = self.create_term()
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Create instructor
            step_start = time.time()
            self.stdout.write("\n[2/8] Creating instructor...")
            instructor = self.create_instructor(department, university)
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Create 6 courses
            step_start = time.time()
            self.stdout.write("\n[3/8] Creating courses...")
            courses = self.create_courses(program, term, instructor, count=6)
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # Create 10 program outcomes
            step_start = time.time()
            self.stdout.write("\n[4/8] Creating program outcomes...")
            program_outcomes = self.create_program_outcomes(program, term, count=10)
            self.stdout.write(f"  ⏱ Completed in {time.time() - step_start:.2f}s")

            # For each course: 5 LOs, 4 assessments
            step_start = time.time()
            self.stdout.write("\n[5/8] Creating learning outcomes and assessments...")
            all_assessments = []
            for i, course in enumerate(courses, 1):
                self.stdout.write(f"  → Course {i}/{len(courses)}: {course.code}")
                learning_outcomes = self.create_learning_outcomes(course, count=5)

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
            students = self.create_students(department, program, university, term, count=50)
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

    def create_university(self):
        university, _ = University.objects.get_or_create(name="Acıbadem University")
        self.stdout.write(f"  ✓ University: {university.name}")
        return university

    def create_department(self, university):
        department, _ = Department.objects.get_or_create(name="Computer Engineering", code="CSE", university=university)
        self.stdout.write(f"  ✓ Department: {department.name}")
        return department

    def create_degree_level(self):
        degree_level, _ = DegreeLevel.objects.get_or_create(name="Bachelor")
        return degree_level

    def create_program(self, department, degree_level):
        program, _ = Program.objects.get_or_create(
            name="Computer Engineering", code="CE", department=department, degree_level=degree_level
        )
        self.stdout.write(f"  ✓ Program: {program.name}")
        return program

    def create_term(self):
        term, _ = Term.objects.get_or_create(name="Fall 2025", defaults={"is_active": True})
        self.stdout.write(f"  ✓ Term: {term.name}")
        return term

    def create_instructor(self, department, university):
        user, created = CustomUser.objects.get_or_create(
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
        if created:
            user.set_password("instructor123")
            user.save()

        profile, _ = InstructorProfile.objects.get_or_create(user=user, defaults={"title": "Professor"})
        self.stdout.write(f"  ✓ Instructor: {user.get_full_name()}")
        return user

    def create_courses(self, program, term, instructor, count=6):
        course_names = [
            "Artificial Intelligence",
            "Algorithms I",
            "Data Systems",
            "Operating Systems",
            "Computer Networks",
            "Microcontrollers",
        ]
        courses = []

        for i in range(count):
            course, _ = Course.objects.get_or_create(
                code=f"CS{300 + i}",
                defaults={
                    "name": course_names[i] if i < len(course_names) else f"Course {i + 1}",
                    "credits": 3,
                    "program": program,
                    "term": term,
                },
            )
            course.instructors.add(instructor)
            courses.append(course)

        self.stdout.write(f"  ✓ Courses: {len(courses)} created")
        return courses

    def create_program_outcomes(self, program, term, count=10):
        outcomes = []
        for i in range(1, count + 1):
            po, _ = ProgramOutcome.objects.get_or_create(
                code=f"PO{i}",
                program=program,
                term=term,
                defaults={"description": f"Program Outcome {i}: Sample description for PO{i}"},
            )
            outcomes.append(po)

        self.stdout.write(f"  ✓ Program Outcomes: {len(outcomes)} created")
        return outcomes

    def create_learning_outcomes(self, course, count=5):
        outcomes = []
        for i in range(1, count + 1):
            lo, _ = LearningOutcome.objects.get_or_create(
                code=f"LO{i}", course=course, defaults={"description": f"Learning Outcome {i} for {course.code}"}
            )
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
        weight_per_lo = 1.0 / len(learning_outcomes)

        for lo in learning_outcomes:
            AssessmentLearningOutcomeMapping.objects.get_or_create(
                assessment=assessment, learning_outcome=lo, defaults={"weight": round(weight_per_lo, 3)}
            )

    def create_students(self, department, program, university, term, count=50):
        students = []

        for i in range(1, count + 1):
            username = f"student{i:03d}"
            password = f"pass{i:03d}"

            user, created = CustomUser.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "first_name": "Student",
                    "last_name": f"Number{i}",
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
                    "student_id": f"2025{i:05d}",
                    "program": program,
                    "enrollment_term": term,
                },
            )

            students.append({"user": user, "profile": profile, "password": password})

        self.stdout.write(f"  ✓ Students: {len(students)} created")
        return students

    def enroll_students(self, students, courses):
        """Enroll all students in all courses"""
        enrollments_count = 0
        for student_data in students:
            for course in courses:
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
                # Use random normal distribution centered at 75 with std dev of 12
                raw_score = random.gauss(75, 12)
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
