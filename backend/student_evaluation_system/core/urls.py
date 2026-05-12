from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from core.views.sse import event_stream

router = DefaultRouter()
router.register(r"universities", views.UniversityViewSet, basename="university")
router.register(r"departments", views.DepartmentViewSet, basename="department")
router.register(r"degree-levels", views.DegreeLevelViewSet, basename="degree-level")
router.register(r"programs", views.ProgramViewSet, basename="program")
router.register(r"terms", views.TermViewSet, basename="term")
router.register(r"courses", views.CourseViewSet, basename="course")
router.register(r"program-outcomes", views.ProgramOutcomeViewSet, basename="program-outcome")
router.register(r"course-templates", views.CourseTemplateViewSet, basename="course-template")
router.register(
    r"course-template-assessment-lo-mappings",
    views.CourseTemplateAssessmentLOMappingViewSet,
    basename="course-template-assessment-lo-mapping",
)
router.register(
    r"course-template-lo-po-mappings",
    views.CourseTemplateLOPOMappingViewSet,
    basename="course-template-lo-po-mapping",
)
router.register(r"learning-outcomes", views.LearningOutcomeViewSet, basename="learning-outcome")
router.register(r"lo-po-mappings", views.LearningOutcomeProgramOutcomeMappingViewSet, basename="lo-po-mapping")
router.register(r"student-lo-scores", views.StudentLearningOutcomeScoreViewSet, basename="student-lo-score")
router.register(r"student-po-scores", views.StudentProgramOutcomeScoreViewSet, basename="student-po-score")
router.register(
    r"file-import/assignment-scores", views.AssignmentScoresImportViewSet, basename="file-import-assignment-scores"
)
router.register(
    r"file-import/learning-outcomes", views.LearningOutcomesImportViewSet, basename="file-import-learning-outcomes"
)
router.register(r"file-import/program-outcomes", views.ProgramOutcomesImportViewSet, basename="file-import-program-outcomes")
router.register(r"permissions", views.InstructorPermissionViewSet, basename="instructor-permission")
router.register(r"weight-suggestion", views.WeightSuggestionViewSet, basename="weightsuggestion")

urlpatterns = [
    path("events/", event_stream, name="event-stream"),
    path("", include(router.urls)),
    path("analytics/program-stats/", views.ProgramStatsView.as_view(), name="program-stats"),
    # Legacy endpoints for backward compatibility
    path("students/", views.StudentListView.as_view(), name="student-list-legacy"),
]
