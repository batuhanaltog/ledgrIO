from __future__ import annotations

from django.urls import path

from apps.accounts.views import AccountDetailView, AccountListCreateView, AccountSummaryView

urlpatterns = [
    path("accounts/", AccountListCreateView.as_view(), name="account-list-create"),
    path("accounts/summary/", AccountSummaryView.as_view(), name="account-summary"),
    path("accounts/<int:pk>/", AccountDetailView.as_view(), name="account-detail"),
]
