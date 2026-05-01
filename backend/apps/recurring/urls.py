from django.urls import path

from apps.recurring.views import (
    RecurringTemplateDetailView,
    RecurringTemplateListCreateView,
    RecurringTemplateMaterializeNowView,
)

urlpatterns = [
    path("", RecurringTemplateListCreateView.as_view(), name="recurring-list-create"),
    path("<int:pk>/", RecurringTemplateDetailView.as_view(), name="recurring-detail"),
    path(
        "<int:pk>/materialize-now/",
        RecurringTemplateMaterializeNowView.as_view(),
        name="recurring-materialize-now",
    ),
]
