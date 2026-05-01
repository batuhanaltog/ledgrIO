from __future__ import annotations

from django.urls import path

from .views import (
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    RegisterView,
    VerifyEmailView,
)

auth_urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
]

user_urlpatterns = [
    path("users/me/", MeView.as_view(), name="users-me"),
]

urlpatterns = auth_urlpatterns + user_urlpatterns
