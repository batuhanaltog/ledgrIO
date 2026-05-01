from __future__ import annotations

from django.urls import URLPattern, path

from .views import TransactionDetailView, TransactionListView, TransactionSummaryView

urlpatterns: list[URLPattern] = [
    path("transactions/", TransactionListView.as_view(), name="transaction-list"),
    path("transactions/summary/", TransactionSummaryView.as_view(), name="transaction-summary"),
    path("transactions/<int:pk>/", TransactionDetailView.as_view(), name="transaction-detail"),
]
