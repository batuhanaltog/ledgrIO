from __future__ import annotations

from django.urls import URLPattern, path

from .views import CategoryDetailView, CategoryListView

urlpatterns: list[URLPattern] = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/<int:pk>/", CategoryDetailView.as_view(), name="category-detail"),
]
