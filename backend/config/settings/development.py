"""Development-only Django settings."""
from __future__ import annotations

from .base import *  # noqa: F403
from .base import INSTALLED_APPS

DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [*INSTALLED_APPS, "django_extensions"]

# Looser CORS in dev
CORS_ALLOW_ALL_ORIGINS = True

# Print emails to console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
