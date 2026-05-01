from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from django.shortcuts import get_object_or_404

from .models import Portfolio
from .serializers import PortfolioSerializer, PortfolioAllocationSerializer, PortfolioPerformanceSerializer
from .querysets import PortfolioQuerySet, get_portfolio_allocation, get_portfolio_performance


@extend_schema_view(
    list=extend_schema(tags=["Portfolios"]),
    create=extend_schema(tags=["Portfolios"]),
    retrieve=extend_schema(tags=["Portfolios"]),
    update=extend_schema(tags=["Portfolios"]),
    partial_update=extend_schema(tags=["Portfolios"]),
    destroy=extend_schema(tags=["Portfolios"]),
)
class PortfolioViewSet(ModelViewSet):
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Portfolio.objects
            .for_user(self.request.user)
            .with_asset_count()
            .with_total_value()
        )

    @extend_schema(tags=["Portfolios"])
    @action(detail=True, methods=["get"])
    def allocation(self, request, pk=None):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        data = get_portfolio_allocation(portfolio.id)
        serializer = PortfolioAllocationSerializer(data, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["Portfolios"],
        parameters=[
            OpenApiParameter("date_from", str, description="Start date (YYYY-MM-DD)"),
            OpenApiParameter("date_to", str, description="End date (YYYY-MM-DD)"),
        ],
    )
    @action(detail=True, methods=["get"])
    def performance(self, request, pk=None):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        date_from = request.query_params.get("date_from", "2000-01-01")
        date_to = request.query_params.get("date_to", "2099-12-31")
        data = get_portfolio_performance(portfolio.id, date_from, date_to)
        serializer = PortfolioPerformanceSerializer(data, many=True)
        return Response(serializer.data)

    @extend_schema(tags=["Portfolios"])
    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        allocation = get_portfolio_allocation(portfolio.id)
        total_value = sum(float(row["current_value"] or 0) for row in allocation)
        return Response({
            "portfolio_id": str(portfolio.id),
            "name": portfolio.name,
            "total_value": round(total_value, 2),
            "currency": portfolio.currency,
            "asset_count": len(allocation),
        })
