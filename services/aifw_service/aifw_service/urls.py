"""URL configuration for aifw-service."""
from django.urls import path

from aifw_service import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("nl2sql/query", views.nl2sql_query, name="nl2sql_query"),
]
