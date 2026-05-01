from __future__ import annotations

from typing import cast

from django.contrib.auth.models import AbstractBaseUser
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import (
    CategoryNotFoundError,
    CategoryPermissionError,
)

from . import selectors, services
from .models import Transaction
from .serializers import (
    TransactionFilterSerializer,
    TransactionSerializer,
    TransactionSummaryQuerySerializer,
    TransactionWriteSerializer,
)


class TransactionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _get_own_transaction_or_404(pk: int, user: AbstractBaseUser) -> Transaction:
    try:
        return cast(Transaction, Transaction.objects.get(id=pk, user=user))
    except Transaction.DoesNotExist:
        raise NotFound(detail=f"Transaction {pk} not found.") from None


class TransactionListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        filter_serializer = TransactionFilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        qs = selectors.get_transaction_list(user=user, filters=filter_serializer.validated_data)

        paginator = TransactionPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = TransactionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        serializer = TransactionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tx = services.create_transaction(user=user, **serializer.validated_data)
        except (CategoryNotFoundError, CategoryPermissionError) as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


class TransactionDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        tx = _get_own_transaction_or_404(pk, user)
        return Response(TransactionSerializer(tx).data)

    def patch(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        tx = _get_own_transaction_or_404(pk, user)
        serializer = TransactionWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            tx = services.update_transaction(transaction=tx, user=user, **serializer.validated_data)
        except (CategoryNotFoundError, CategoryPermissionError) as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(TransactionSerializer(tx).data)

    def delete(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        tx = _get_own_transaction_or_404(pk, user)
        services.soft_delete_transaction(transaction=tx, user=user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransactionSummaryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        query_serializer = TransactionSummaryQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        data = selectors.get_transaction_summary(user=user, **query_serializer.validated_data)
        return Response(data)
