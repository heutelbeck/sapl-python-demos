"""Django settings for the SAPL Django demo project.

Configures SAPL PDP connection, installed apps, and middleware
for policy enforcement with the sapl_django integration.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-demo-insecure-key-do-not-use-in-production"

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "sapl_django",
    "medical",
]

MIDDLEWARE = [
    "demo_project.middleware.RuntimeErrorMiddleware",
    "sapl_django.middleware.SaplRequestMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "demo_project.urls"

WSGI_APPLICATION = "demo_project.wsgi.application"

DATABASES = {}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SAPL_CONFIG = {
    "base_url": os.getenv("SAPL_PDP_URL", "http://localhost:8443"),
    "allow_insecure_connections": True,
}
