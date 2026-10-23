from django.urls import path

from planner.views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view()),
]
