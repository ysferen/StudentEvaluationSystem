from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StudentProfile, InstructorProfile


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Academic Info", {"fields": ("role", "university", "department")}),)
    list_display = ("username", "first_name", "last_name", "email", "role", "department", "university")
    list_filter = ("role", "department", "university", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "student_id", "program", "enrollment_term")
    list_filter = ("program", "enrollment_term")
    search_fields = ("user__username", "user__first_name", "user__last_name", "student_id")


@admin.register(InstructorProfile)
class InstructorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "title")
    search_fields = ("user__username", "user__first_name", "user__last_name", "title")
