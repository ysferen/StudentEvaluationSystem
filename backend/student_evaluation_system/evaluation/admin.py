from django.contrib import admin
from .models import Assessment, AssessmentLearningOutcomeMapping, StudentGrade, CourseEnrollment


@admin.register(StudentGrade)
class StudentGradeAdmin(admin.ModelAdmin):
    list_display = ["student", "assessment", "score"]
    list_filter = ["assessment__course", "score"]
    search_fields = ["student__username", "assessment__name"]


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ["student", "course", "enrolled_at"]
    list_filter = ["course__term", "course__program"]
    search_fields = ["student__username", "course__code", "course__name"]


class AssessmentLearningOutcomeMappingInline(admin.TabularInline):
    model = AssessmentLearningOutcomeMapping
    extra = 1


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ["name", "course", "date", "total_score", "weight"]
    list_filter = ["course", "date"]
    search_fields = ["name", "course__code", "course__name"]
    inlines = [AssessmentLearningOutcomeMappingInline]
