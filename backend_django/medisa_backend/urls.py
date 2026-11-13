from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('medisa_api.urls')),
    path('', include('medisa_api.urls')),  # Allow root-relative calls like /auth/login, /api/dashboard.php
]

if settings.MEDIA_ROOT:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
