from django.urls import path
from .views import (
    login_view, register_view, dashboard_view,
    appointments_view, reports_view, medications_view,
    upload_view, doctors_view, health_view
)

urlpatterns = [
    # REST modern endpoints
    path('auth/login', login_view, name='api_login'),
    path('auth/login/', login_view, name='api_login_slash'),
    path('auth/register', register_view, name='api_register'),
    path('auth/register/', register_view, name='api_register_slash'),
    path('dashboard', dashboard_view, name='api_dashboard'),
    path('dashboard/', dashboard_view, name='api_dashboard_slash'),
    path('appointments', appointments_view, name='api_appointments'),
    path('appointments/', appointments_view, name='api_appointments_slash'),
    path('reports', reports_view, name='api_reports'),
    path('reports/', reports_view, name='api_reports_slash'),
    path('medications', medications_view, name='api_medications'),
    path('medications/', medications_view, name='api_medications_slash'),
    path('upload', upload_view, name='api_upload'),
    path('upload/', upload_view, name='api_upload_slash'),
    path('documents', upload_view, name='api_documents'),
    path('documents/', upload_view, name='api_documents_slash'),
    path('doctors', doctors_view, name='api_doctors'),
    path('doctors/', doctors_view, name='api_doctors_slash'),
    path('health', health_view, name='api_health'),

    # PHP backward compatibility aliases
    path('auth/login.php', login_view, name='php_login'),
    path('auth/register.php', register_view, name='php_register'),
    path('api/dashboard.php', dashboard_view, name='php_dashboard'),
    path('api/appointments.php', appointments_view, name='php_appointments'),
    path('api/reports.php', reports_view, name='php_reports'),
    path('api/medications.php', medications_view, name='php_medications'),
    path('api/upload.php', upload_view, name='php_upload'),
]
