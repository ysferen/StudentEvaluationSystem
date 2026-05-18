from django.contrib import admin
from core.models import (
    AuditLog,
    Term,
    Program,
    Department,
    University,
    ProgramOutcome,
    ProgramOutcomeTemplate,
    Course,
    CourseTemplate,
    CourseTemplateAssessment,
    CourseTemplateAssessmentLOMapping,
    CourseTemplateLearningOutcome,
    CourseTemplateLOPOMapping,
    LearningOutcome,
    LearningOutcomeProgramOutcomeMapping,
    DegreeLevel,
    StudentLearningOutcomeScore,
    StudentProgramOutcomeScore,
    InstructorPermission,
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


@admin.register(ProgramOutcomeTemplate)
class ProgramOutcomeTemplateAdmin(admin.ModelAdmin):
    list_display = ["code", "short_description", "program"]
    list_filter = ["program"]
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


@admin.register(InstructorPermission)
class InstructorPermissionAdmin(admin.ModelAdmin):
    list_display = ("instructor", "resource_area", "permission_tier", "program_head")
    list_filter = ("resource_area", "permission_tier")
    search_fields = ("instructor__user__username", "instructor__user__first_name", "instructor__user__last_name")


@admin.register(CourseTemplate)
class CourseTemplateAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "credits", "program"]
    list_filter = ["program"]
    search_fields = ["code", "name"]


@admin.register(CourseTemplateLearningOutcome)
class CourseTemplateLearningOutcomeAdmin(admin.ModelAdmin):
    list_display = ["code", "description", "course_template"]
    list_filter = ["course_template__program"]
    search_fields = ["code", "description"]


@admin.register(CourseTemplateAssessment)
class CourseTemplateAssessmentAdmin(admin.ModelAdmin):
    list_display = ["name", "assessment_type", "total_score", "weight", "course_template"]
    list_filter = ["assessment_type", "course_template"]
    search_fields = ["name"]


@admin.register(CourseTemplateAssessmentLOMapping)
class CourseTemplateAssessmentLOMappingAdmin(admin.ModelAdmin):
    list_display = ["template_assessment", "template_learning_outcome", "weight"]
    list_filter = ["template_assessment__course_template"]


@admin.register(CourseTemplateLOPOMapping)
class CourseTemplateLOPOMappingAdmin(admin.ModelAdmin):
    list_display = ["template_learning_outcome", "program_outcome", "weight"]
    list_filter = ["template_learning_outcome__course_template"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "user", "action", "model_name", "object_id"]
    list_filter = ["action", "model_name", "timestamp"]
    search_fields = ["user__username", "model_name", "metadata"]
    readonly_fields = [
        "user",
        "action",
        "model_name",
        "object_id",
        "before_snapshot",
        "after_snapshot",
        "metadata",
        "ip_address",
        "user_agent",
        "timestamp",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
