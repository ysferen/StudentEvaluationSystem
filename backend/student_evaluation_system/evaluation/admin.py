from django.contrib import admin
from .models import Assessment, AssessmentLearningOutcomeMapping, StudentGrade, CourseEnrollment, ScoreRecomputeJob


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


@admin.register(ScoreRecomputeJob)
class ScoreRecomputeJobAdmin(admin.ModelAdmin):
    list_display = ["id", "task_type", "status", "course", "triggered_by", "created_at", "started_at", "finished_at"]
    list_filter = ["task_type", "status", "created_at"]
    search_fields = ["celery_task_id", "course__code", "course__name", "triggered_by__username"]
