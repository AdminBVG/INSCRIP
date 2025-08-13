from django.contrib import admin
from django.urls import path, include
from inscripciones import views as insc_views

urlpatterns = [
    path('admin/settings', insc_views.settings_view, name='settings'),
    path('admin/', admin.site.urls),
    path('', include('inscripciones.urls')),
]
