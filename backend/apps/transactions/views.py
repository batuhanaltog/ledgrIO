from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter

from .models import Transaction, Category
from .serializers import TransactionSerializer, CategorySerializer
from .filters import TransactionFilter
from .querysets import get_running_balance, get_transaction_summary


@extend_schema_view(
    list=extend_schema(tags=["Transactions"]),
    create=extend_schema(tags=["Transactions"]),
    retrieve=extend_schema(tags=["Transactions"]),
    update=extend_schema(tags=["Transactions"]),
    partial_update=extend_schema(tags=["Transactions"]),
    destroy=extend_schema(tags=["Transactions"]),
)
class TransactionViewSet(ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TransactionFilter

    def get_queryset(self):
        return (
            Transaction.objects
            .filter(user=self.request.user)
            .select_related("category", "asset", "portfolio")
        )

    @extend_schema(tags=["Transactions"])
    @action(detail=False, methods=["get"])
    def running_balance(self, request):
        data = get_running_balance(request.user.id)
        return Response(data)

    @extend_schema(
        tags=["Transactions"],
        parameters=[
            OpenApiParameter("date_from", str, description="Start date (YYYY-MM-DD)"),
            OpenApiParameter("date_to", str, description="End date (YYYY-MM-DD)"),
        ],
    )
    @action(detail=False, methods=["get"])
    def summary(self, request):
        date_from = request.query_params.get("date_from", "2000-01-01")
        date_to = request.query_params.get("date_to", "2099-12-31")
        data = get_transaction_summary(request.user.id, date_from, date_to)
        return Response(data)


@extend_schema_view(
    list=extend_schema(tags=["Categories"]),
    create=extend_schema(tags=["Categories"]),
    retrieve=extend_schema(tags=["Categories"]),
    update=extend_schema(tags=["Categories"]),
    partial_update=extend_schema(tags=["Categories"]),
    destroy=extend_schema(tags=["Categories"]),
)
class CategoryViewSet(ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)
