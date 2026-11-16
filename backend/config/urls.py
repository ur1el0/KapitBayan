"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from config.media_views import ProtectedMediaView
from django.contrib import admin
from django.urls import path, include, re_path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from config.health_views import HealthCheckView, LivenessCheckView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('gridy_auth.urls')),
    path('api/v1/', include('gridy_services.urls')),
    path('api/services/', include('gridy_services.urls')),
    path('api/v1/', include('gridy_reports.urls')),
    path('api/v1/', include('gridy_communications.urls')),
    path('api/v1/health/live/', LivenessCheckView.as_view(), name='health_live'),
    path('api/v1/health/ready/', HealthCheckView.as_view(), name='health_ready'),
    path('api/v1/health/', HealthCheckView.as_view(), name='health_check'),

    # OpenAPI Schema Views
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # Secure Media Serving (Overrides public Django static serving)
    re_path(r'^media/(?P<path>.*)$', ProtectedMediaView.as_view(), name='protected_media'),
]
