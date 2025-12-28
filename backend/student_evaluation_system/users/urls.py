from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'students', views.StudentProfileViewSet, basename='student')
router.register(r'instructors', views.InstructorProfileViewSet, basename='instructor')

urlpatterns = [
    path('', include(router.urls)),
    # JWT Authentication endpoints
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.CurrentUserView.as_view(), name='current_user'),
    path('change_password/', views.ChangePasswordView.as_view(), name='change_password'),
]
