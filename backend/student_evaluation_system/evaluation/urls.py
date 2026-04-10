from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"assessments", views.AssessmentViewSet, basename="assessment")
router.register(r"assessment-lo-mappings", views.AssessmentLearningOutcomeMappingViewSet, basename="assessment-lo-mapping")
router.register(r"grades", views.StudentGradeViewSet, basename="grade")
router.register(r"enrollments", views.CourseEnrollmentViewSet, basename="enrollment")
router.register(r"score-recompute-jobs", views.ScoreRecomputeJobViewSet, basename="score-recompute-job")

urlpatterns = [
    path("", include(router.urls)),
    # Legacy endpoints for backward compatibility
    path("evaluation/", views.EvaluationListView.as_view(), name="evaluation-list-legacy"),
    path("evaluation/<int:pk>/", views.EvaluationDetailView.as_view(), name="evaluation-detail-legacy"),
    path("evaluation/create/", views.EvaluationCreateView.as_view(), name="evaluation-create-legacy"),
]
