from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('guest', 'Guest'),
        ('student', 'Student'),
        ('instructor', 'Instructor'),
        ('admin', 'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='guest')
    department = models.ForeignKey(
        'core.Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='users'
    )
    university = models.ForeignKey(
        'core.University', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='users'
    )
    
    class Meta:
        ordering = ['username']
        verbose_name = "User"
        verbose_name_plural = "Users"
    
    @property
    def is_student(self):
        """Check if user has student role."""
        return self.role == 'student'
    
    @property
    def is_instructor(self):
        """Check if user has instructor role."""
        return self.role == 'instructor'
    
    @property
    def is_admin_user(self):
        """Check if user has admin role."""
        return self.role == 'admin'
    
    def __str__(self):
        full_name = self.get_full_name()
        if full_name:
            return f"{full_name} ({self.role})"
        return f"{self.username} ({self.role})"

class StudentProfile(models.Model):
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='student_profile',
        db_index=True
    )
    student_id = models.CharField(max_length=20, unique=True, db_index=True)
    enrollment_term = models.ForeignKey(
        'core.Term', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='enrolled_students',
        db_index=True
    )
    program = models.ForeignKey(
        'core.Program', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='students',
        db_index=True
    )

    class Meta:
        ordering = ['student_id']
        indexes = [
            models.Index(fields=['program', 'student_id']),
        ]
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"
    
    def clean(self):
        """Validate that user has student role."""
        super().clean()
        if self.user.role != 'student':
            raise ValidationError({
                'user': 'User must have student role'
            })
    
    @property
    def full_name(self):
        """Get student's full name."""
        return self.user.get_full_name() or self.user.username

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"

class InstructorProfile(models.Model):
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='instructor_profile'
    )
    title = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['user__last_name', 'user__first_name']
        verbose_name = "Instructor Profile"
        verbose_name_plural = "Instructor Profiles"
    
    def clean(self):
        """Validate that user has instructor role."""
        super().clean()
        if self.user.role != 'instructor':
            raise ValidationError({
                'user': 'User must have instructor role'
            })
    
    @property
    def full_name(self):
        """Get instructor's full name."""
        return self.user.get_full_name() or self.user.username

    def __str__(self):
        name = self.full_name
        if self.title:
            return f"{self.title} {name}"
        return name