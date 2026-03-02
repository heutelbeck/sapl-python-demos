"""Root URL configuration for the SAPL Django demo project."""
from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("api/", include("medical.urls")),
]
