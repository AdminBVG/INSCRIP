from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('inscripcion/<str:key>/', views.inscripcion, name='inscripcion'),
]
