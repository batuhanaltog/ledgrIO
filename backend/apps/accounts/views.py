from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import (
    AccountCurrencyLockedError,
    AccountInUseError,
    AccountNotFoundError,
)

from . import selectors, services
from .serializers import (
    AccountCreateSerializer,
    AccountListSerializer,
    AccountUpdateSerializer,
    TotalAssetsSummarySerializer,
)


class AccountPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class AccountListCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        filters: dict = {}
        if account_type := request.query_params.get("account_type"):
            filters["account_type"] = account_type
        if request.query_params.get("include_archived") in ("1", "true", "True"):
            filters["include_archived"] = True
        if currency := request.query_params.get("currency"):
            filters["currency"] = currency

        qs = selectors.get_account_list_with_balance(user=user, filters=filters)
        paginator = AccountPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = AccountListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        serializer = AccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            account = services.create_account(user=user, **serializer.validated_data)
        except ValueError as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        out = selectors.get_account_with_balance(account_id=account.pk, user=user)
        return Response(AccountListSerializer(out).data, status=status.HTTP_201_CREATED)


class AccountDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def _get_or_404(self, pk: int, user: AbstractBaseUser) -> object:
        try:
            return selectors.get_account_with_balance(account_id=pk, user=user)
        except AccountNotFoundError as exc:
            from rest_framework.exceptions import NotFound

            raise NotFound(detail=str(exc)) from exc

    def get(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        account = self._get_or_404(pk, user)
        return Response(AccountListSerializer(account).data)

    def patch(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        account = self._get_or_404(pk, user)
        serializer = AccountUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated = services.update_account(account=account, **serializer.validated_data)  # type: ignore[arg-type]
        except AccountCurrencyLockedError as exc:
            return Response(
                {"error": {"type": "CONFLICT", "detail": str(exc), "status": 409}},
                status=status.HTTP_409_CONFLICT,
            )
        out = selectors.get_account_with_balance(account_id=updated.pk, user=user)
        return Response(AccountListSerializer(out).data)

    def delete(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        account = self._get_or_404(pk, user)
        try:
            services.soft_delete_account(account=account)  # type: ignore[arg-type]
        except AccountInUseError as exc:
            return Response(
                {"error": {"type": "CONFLICT", "detail": str(exc), "status": 409}},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountSummaryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        data = selectors.get_total_assets_summary(user=user)
        serializer = TotalAssetsSummarySerializer(data)
        return Response(serializer.data)
