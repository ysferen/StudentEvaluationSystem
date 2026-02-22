from django.contrib import admin
from .models import (
    Term,
    Program,
    Department,
    University,
    ProgramOutcome,
    Course,
    LearningOutcome,
    LearningOutcomeProgramOutcomeMapping,
    DegreeLevel,
    StudentLearningOutcomeScore,
    StudentProgramOutcomeScore,
)


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "university"]
    list_filter = ["university"]
    search_fields = ["name", "code"]


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(DegreeLevel)
class DegreeLevelAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "degree_level", "department"]
    list_filter = ["degree_level", "department"]
    search_fields = ["name", "code"]


@admin.register(ProgramOutcome)
class ProgramOutcomeAdmin(admin.ModelAdmin):
    list_display = ["code", "short_description", "program", "term"]
    list_filter = ["program", "term"]
    search_fields = ["code", "description"]

    def short_description(self, obj):
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description


@admin.register(LearningOutcome)
class LearningOutcomeAdmin(admin.ModelAdmin):
    list_display = ["code", "short_description", "course"]
    list_filter = ["course__program", "course__term"]
    search_fields = ["code", "description", "course__code", "course__name"]

    def short_description(self, obj):
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description


@admin.register(StudentLearningOutcomeScore)
class StudentLearningOutcomeScoreAdmin(admin.ModelAdmin):
    list_display = ["student", "learning_outcome", "score"]
    list_filter = ["learning_outcome__course", "score"]
    search_fields = ["student__username", "learning_outcome__code"]


@admin.register(StudentProgramOutcomeScore)
class StudentProgramOutcomeScoreAdmin(admin.ModelAdmin):
    list_display = ["student", "program_outcome", "term", "score"]
    list_filter = ["term", "program_outcome"]
    search_fields = ["student__username", "program_outcome__code"]


class LearningOutcomeProgramOutcomeMappingInline(admin.TabularInline):
    model = LearningOutcomeProgramOutcomeMapping
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "program", "term"]
    list_filter = ["program", "term"]
    search_fields = ["code", "name"]
    filter_horizontal = ["instructors"]
    inlines = [LearningOutcomeProgramOutcomeMappingInline]
