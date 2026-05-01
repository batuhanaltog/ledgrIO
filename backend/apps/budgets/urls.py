from __future__ import annotations

from django.urls import URLPattern, path

from .views import BudgetDetailView, BudgetListCreateView

urlpatterns: list[URLPattern] = [
    path("", BudgetListCreateView.as_view(), name="budget-list-create"),
    path("<int:pk>/", BudgetDetailView.as_view(), name="budget-detail"),
]
