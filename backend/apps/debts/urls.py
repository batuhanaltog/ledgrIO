from django.urls import path

from apps.debts.views import (
    DebtCategoryDetailView,
    DebtCategoryListCreateView,
    DebtDetailView,
    DebtListCreateView,
    DebtMonthlySummaryView,
    DebtPaymentCreateView,
    DebtPaymentDeleteView,
)

urlpatterns = [
    path("categories/", DebtCategoryListCreateView.as_view(), name="debt-category-list-create"),
    path("categories/<int:pk>/", DebtCategoryDetailView.as_view(), name="debt-category-detail"),
    path("", DebtListCreateView.as_view(), name="debt-list-create"),
    path("monthly-summary/", DebtMonthlySummaryView.as_view(), name="debt-monthly-summary"),
    path("<int:pk>/", DebtDetailView.as_view(), name="debt-detail"),
    path("<int:debt_pk>/payments/", DebtPaymentCreateView.as_view(), name="debt-payment-create"),
    path(
        "<int:debt_pk>/payments/<int:payment_pk>/",
        DebtPaymentDeleteView.as_view(),
        name="debt-payment-delete",
    ),
]
