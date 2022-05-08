"""gbTracker URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path

from . import views

urlpatterns = [
    path('source/<int:pk>/', views.source, name='source'),
    path('datasource/add/', views.datasource_add, name='datasource_add'),
    #path('snapshots/<int:pk>/', views.snapshot, name='snapshot'),
    path('boundaries/<int:pk>/', views.boundary, name='boundary'),
    path('api/boundaries/<int:pk>/', views.api_boundary, name='api_boundary'),
    path('api/boundaries', views.api_boundaries, name='api_boundaries'),
    path('api/snapshots/', views.api_snapshots, name='api_snapshots'),
]
