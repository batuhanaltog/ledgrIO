from __future__ import annotations

from datetime import date as date_type

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Currency, FxRate
from .serializers import CurrencySerializer, FxQuerySerializer, FxResponseSerializer


class CurrencyListView(generics.ListAPIView):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = PageNumberPagination
    pagination_class.page_size = 100


class FxRateView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[
            OpenApiParameter("base", str, required=True, description="ISO 4217 code"),
            OpenApiParameter("quote", str, required=True, description="ISO 4217 code"),
            OpenApiParameter("date", str, required=False, description="YYYY-MM-DD"),
        ],
        responses={200: FxResponseSerializer, 404: None, 400: None},
    )
    def get(self, request: Request) -> Response:
        query = FxQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        base: str = query.validated_data["base"]
        quote: str = query.validated_data["quote"]
        at: date_type = query.validated_data.get("date") or date_type.today()

        row = (
            FxRate.objects.filter(base_code=base, quote_code=quote, rate_date__lte=at)
            .order_by("-rate_date")
            .first()
        )
        if row is None:
            return Response(
                {"detail": f"No rate for {base}->{quote} on or before {at}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = FxResponseSerializer(
            {"base": base, "quote": quote, "rate": row.rate, "rate_date": row.rate_date}
        ).data
        return Response(payload)
