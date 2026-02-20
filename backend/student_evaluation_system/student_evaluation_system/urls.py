"""
URL configuration for student_evaluation_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Import: from other_app.views import Home
    2. Add a URL:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import include() function: from django.urls import include, path
    2. Add a URL:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# API Version 1 URL patterns - same as regular URLs but with version support
api_v1_patterns = [
    path("users/", include("users.urls")),
    path("core/", include("core.urls")),
    path("evaluation/", include("evaluation.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    # API with versioning (current: v1)
    # The version parameter is captured by DRF's URLPathVersioning but not passed to views
    path("api/v1/", include(api_v1_patterns)),
    # Backward compatibility - also support non-versioned URLs
    # These will use DEFAULT_VERSION from settings (v1)
    path("api/users/", include("users.urls")),
    path("api/core/", include("core.urls")),
    path("api/evaluation/", include("evaluation.urls")),
    # API Schema and Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
