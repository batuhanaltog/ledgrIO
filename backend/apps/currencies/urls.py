from __future__ import annotations

from django.urls import path

from .views import CurrencyListView, FxRateView

urlpatterns = [
    path("currencies/", CurrencyListView.as_view(), name="currencies-list"),
    path("fx/", FxRateView.as_view(), name="fx-rate"),
]
