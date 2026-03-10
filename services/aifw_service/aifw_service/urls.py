"""URL configuration for aifw-service."""
from django.urls import path

from aifw_service import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("nl2sql/query", views.nl2sql_query, name="nl2sql_query"),
    path("nl2sql/examples/", views.nl2sql_examples, name="nl2sql_examples"),
    path("nl2sql/feedback/", views.nl2sql_feedback_list, name="nl2sql_feedback_list"),
    path(
        "nl2sql/feedback/<int:feedback_id>/promote/",
        views.nl2sql_feedback_promote,
        name="nl2sql_feedback_promote",
    ),
]
