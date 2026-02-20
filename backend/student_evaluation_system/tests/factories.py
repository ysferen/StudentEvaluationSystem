"""
Test factories using factory-boy for creating test data.

These factories make it easy to create test data with sensible defaults
while allowing customization when needed.

Usage:
    user = UserFactory(role='student')
    course = CourseFactory(instructors=[user])
"""

import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from core.models import (
    University, Department, DegreeLevel, Program, Term,
    Course, LearningOutcome, ProgramOutcome,
    LearningOutcomeProgramOutcomeMapping,
    StudentLearningOutcomeScore, StudentProgramOutcomeScore
)
from evaluation.models import (
    Assessment, AssessmentLearningOutcomeMapping,
    StudentGrade, CourseEnrollment
)
from users.models import StudentProfile, InstructorProfile

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating CustomUser instances."""
    
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    role = 'student'  # Default role
    is_active = True
    
    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        """Set password after creation."""
        if not create:
            return
        password = extracted or 'testpass123'
        self.set_password(password)
        if create:
            self.save()


class StudentUserFactory(UserFactory):
    """Factory for creating student users with profiles."""
    
    role = 'student'
    
    @factory.post_generation
    def create_profile(self, create, extracted, **kwargs):
        """Create student profile."""
        if not create:
            return
        StudentProfileFactory(user=self)


class InstructorUserFactory(UserFactory):
    """Factory for creating instructor users with profiles."""
    
    role = 'instructor'
    
    @factory.post_generation
    def create_profile(self, create, extracted, **kwargs):
        """Create instructor profile."""
        if not create:
            return
        InstructorProfileFactory(user=self)


class AdminUserFactory(UserFactory):
    """Factory for creating admin users."""
    
    role = 'admin'


class StudentProfileFactory(DjangoModelFactory):
    """Factory for creating StudentProfile instances."""
    
    class Meta:
        model = StudentProfile
    
    user = factory.SubFactory(UserFactory, role='student')
    student_id = factory.Sequence(lambda n: f"STU{n:06d}")
    enrollment_term = factory.SubFactory('tests.factories.TermFactory')
    program = factory.SubFactory('tests.factories.ProgramFactory')


class InstructorProfileFactory(DjangoModelFactory):
    """Factory for creating InstructorProfile instances."""
    
    class Meta:
        model = InstructorProfile
    
    user = factory.SubFactory(UserFactory, role='instructor')
    title = factory.Faker('job')


class UniversityFactory(DjangoModelFactory):
    """Factory for creating University instances."""
    
    class Meta:
        model = University
    
    name = factory.Faker('company')


class DepartmentFactory(DjangoModelFactory):
    """Factory for creating Department instances."""
    
    class Meta:
        model = Department
    
    name = factory.Faker('job')
    code = factory.Sequence(lambda n: f"DEPT{n:02d}")
    university = factory.SubFactory(UniversityFactory)


class DegreeLevelFactory(DjangoModelFactory):
    """Factory for creating DegreeLevel instances."""
    
    class Meta:
        model = DegreeLevel
    
    name = factory.Iterator(['Bachelor', 'Master', 'PhD'])


class ProgramFactory(DjangoModelFactory):
    """Factory for creating Program instances."""
    
    class Meta:
        model = Program
    
    name = factory.Faker('job')
    code = factory.Sequence(lambda n: f"PROG{n:02d}")
    degree_level = factory.SubFactory(DegreeLevelFactory)
    department = factory.SubFactory(DepartmentFactory)


class TermFactory(DjangoModelFactory):
    """Factory for creating Term instances."""
    
    class Meta:
        model = Term
    
    name = factory.Sequence(lambda n: f"Fall {2020 + n}")
    is_active = False


class ActiveTermFactory(TermFactory):
    """Factory for creating an active term."""
    
    is_active = True


class CourseFactory(DjangoModelFactory):
    """Factory for creating Course instances."""
    
    class Meta:
        model = Course
    
    name = factory.Faker('catch_phrase')
    code = factory.Sequence(lambda n: f"CS{n:03d}")
    credits = factory.Iterator([3, 4, 5])
    program = factory.SubFactory(ProgramFactory)
    term = factory.SubFactory(TermFactory)
    
    @factory.post_generation
    def instructors(self, create, extracted, **kwargs):
        """Add instructors to the course."""
        if not create:
            return
        if extracted:
            for instructor in extracted:
                self.instructors.add(instructor)


class LearningOutcomeFactory(DjangoModelFactory):
    """Factory for creating LearningOutcome instances."""
    
    class Meta:
        model = LearningOutcome
    
    description = factory.Faker('sentence')
    code = factory.Sequence(lambda n: f"LO{n}")
    course = factory.SubFactory(CourseFactory)
    created_by = factory.SubFactory(UserFactory)


class ProgramOutcomeFactory(DjangoModelFactory):
    """Factory for creating ProgramOutcome instances."""
    
    class Meta:
        model = ProgramOutcome
    
    description = factory.Faker('sentence')
    code = factory.Sequence(lambda n: f"PO{n}")
    program = factory.SubFactory(ProgramFactory)
    term = factory.SubFactory(TermFactory)
    created_by = factory.SubFactory(UserFactory)


class AssessmentFactory(DjangoModelFactory):
    """Factory for creating Assessment instances."""
    
    class Meta:
        model = Assessment
    
    name = factory.Iterator(['Midterm', 'Final', 'Quiz 1', 'Quiz 2', 'Project'])
    assessment_type = factory.Iterator(['midterm', 'final', 'quiz', 'quiz', 'project'])
    course = factory.SubFactory(CourseFactory)
    date = factory.Faker('date_this_year')
    total_score = factory.Iterator([100, 100, 20, 20, 50])
    weight = factory.Faker('pyfloat', left_digits=0, right_digits=2, positive=True, max_value=0.5)
    created_by = factory.SubFactory(UserFactory)


class CourseEnrollmentFactory(DjangoModelFactory):
    """Factory for creating CourseEnrollment instances."""
    
    class Meta:
        model = CourseEnrollment
    
    student = factory.SubFactory(UserFactory, role='student')
    course = factory.SubFactory(CourseFactory)


class StudentGradeFactory(DjangoModelFactory):
    """Factory for creating StudentGrade instances."""
    
    class Meta:
        model = StudentGrade
    
    student = factory.SubFactory(UserFactory, role='student')
    assessment = factory.SubFactory(AssessmentFactory)
    score = factory.Faker('pyfloat', left_digits=2, right_digits=1, positive=True, max_value=100)


class StudentLearningOutcomeScoreFactory(DjangoModelFactory):
    """Factory for creating StudentLearningOutcomeScore instances."""
    
    class Meta:
        model = StudentLearningOutcomeScore
    
    student = factory.SubFactory(UserFactory, role='student')
    learning_outcome = factory.SubFactory(LearningOutcomeFactory)
    score = factory.Faker('pyfloat', left_digits=2, right_digits=1, positive=True, max_value=100)


class AssessmentLearningOutcomeMappingFactory(DjangoModelFactory):
    """Factory for creating AssessmentLearningOutcomeMapping instances."""
    
    class Meta:
        model = AssessmentLearningOutcomeMapping
    
    assessment = factory.SubFactory(AssessmentFactory)
    learning_outcome = factory.SubFactory(LearningOutcomeFactory)
    weight = factory.Faker('pyfloat', left_digits=0, right_digits=2, positive=True, max_value=1.0)


class LearningOutcomeProgramOutcomeMappingFactory(DjangoModelFactory):
    """Factory for creating LearningOutcomeProgramOutcomeMapping instances."""
    
    class Meta:
        model = LearningOutcomeProgramOutcomeMapping
    
    course = factory.SubFactory(CourseFactory)
    learning_outcome = factory.SubFactory(LearningOutcomeFactory)
    program_outcome = factory.SubFactory(ProgramOutcomeFactory)
    weight = factory.Faker('pyfloat', left_digits=0, right_digits=2, positive=True, max_value=1.0)


# Pre-built scenarios for common test setups


class CourseWithStudentsFactory(CourseFactory):
    """Factory for creating a course with enrolled students."""
    
    @factory.post_generation
    def students(self, create, extracted, **kwargs):
        """Enroll students in the course."""
        if not create:
            return
        
        count = extracted if isinstance(extracted, int) else 5
        for _ in range(count):
            student = StudentUserFactory()
            CourseEnrollmentFactory(student=student, course=self)


class CourseWithAssessmentsFactory(CourseFactory):
    """Factory for creating a course with assessments."""
    
    @factory.post_generation
    def assessments(self, create, extracted, **kwargs):
        """Create assessments for the course."""
        if not create:
            return
        
        assessment_types = ['midterm', 'final', 'homework', 'project']
        for i, assessment_type in enumerate(assessment_types):
            AssessmentFactory(
                course=self,
                name=f"{assessment_type.capitalize()} {i+1}",
                assessment_type=assessment_type
            )


class CourseWithDataFactory(CourseFactory):
    """
    Factory for creating a complete course setup with:
    - Instructors
    - Enrolled students
    - Assessments
    - Learning outcomes
    """
    
    @factory.post_generation
    def setup_course(self, create, extracted, **kwargs):
        """Set up complete course data."""
        if not create:
            return
        
        # Add instructors
        instructor = InstructorUserFactory()
        self.instructors.add(instructor)
        
        # Create learning outcomes
        los = [LearningOutcomeFactory(course=self, code=f"LO{i+1}") for i in range(3)]
        
        # Create assessments
        assessments = [
            AssessmentFactory(course=self, name="Midterm", assessment_type="midterm"),
            AssessmentFactory(course=self, name="Final", assessment_type="final"),
        ]
        
        # Enroll students and create grades
        for _ in range(5):
            student = StudentUserFactory()
            CourseEnrollmentFactory(student=student, course=self)
            
            # Create grades for each assessment
            for assessment in assessments:
                StudentGradeFactory(student=student, assessment=assessment)
            
            # Create LO scores
            for lo in los:
                StudentLearningOutcomeScoreFactory(student=student, learning_outcome=lo)
