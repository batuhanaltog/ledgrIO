from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import (
    DebtBalanceUnderflowError,
    DebtCategoryCycleError,
    DebtCategoryHasChildrenError,
    DebtCategoryNotFoundError,
    DebtNotFoundError,
)

from . import selectors, services
from .models import Debt, DebtCategory, DebtPayment
from .serializers import (
    DebtCategoryCreateSerializer,
    DebtCategorySerializer,
    DebtCategoryUpdateSerializer,
    DebtCreateSerializer,
    DebtMonthlySummarySerializer,
    DebtPaymentCreateSerializer,
    DebtPaymentSerializer,
    DebtSerializer,
    DebtUpdateSerializer,
)


class DebtPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class DebtCategoryListCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        tree = selectors.get_debt_categories_tree(user=user)
        return Response(tree)

    def post(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        serializer = DebtCategoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            category = services.create_debt_category(
                user=user, **serializer.validated_data
            )
        except DebtCategoryNotFoundError as exc:
            raise NotFound(detail=str(exc)) from exc
        except (ValueError, Exception) as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            DebtCategorySerializer(category).data, status=status.HTTP_201_CREATED
        )


class DebtCategoryDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def _get_or_404(self, pk: int, user: AbstractBaseUser) -> DebtCategory:
        from typing import cast as _cast
        try:
            return _cast(DebtCategory, DebtCategory.objects.get(pk=pk, user=user))
        except DebtCategory.DoesNotExist:
            raise NotFound(detail=f"Debt category {pk} not found.") from None

    def patch(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        category = self._get_or_404(pk, user)
        serializer = DebtCategoryUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated = services.update_debt_category(
                category=category, **serializer.validated_data
            )
        except DebtCategoryNotFoundError as exc:
            raise NotFound(detail=str(exc)) from exc
        except DebtCategoryCycleError as exc:
            return Response(
                {"error": {"type": "CONFLICT", "detail": str(exc), "status": 409}},
                status=status.HTTP_409_CONFLICT,
            )
        except ValueError as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(DebtCategorySerializer(updated).data)

    def delete(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        category = self._get_or_404(pk, user)
        try:
            services.soft_delete_debt_category(category=category)
        except DebtCategoryHasChildrenError as exc:
            return Response(
                {"error": {"type": "CONFLICT", "detail": str(exc), "status": 409}},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class DebtListCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        filters: dict = {}
        if cat_id := request.query_params.get("category_id"):
            filters["category_id"] = cat_id
        if currency := request.query_params.get("currency"):
            filters["currency"] = currency
        if (is_settled := request.query_params.get("is_settled")) is not None:
            filters["is_settled"] = is_settled in ("1", "true", "True")

        qs = selectors.get_debt_list(user=user, filters=filters)
        paginator = DebtPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = DebtSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        serializer = DebtCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            debt = services.create_debt(user=user, **serializer.validated_data)
        except DebtCategoryNotFoundError as exc:
            raise NotFound(detail=str(exc)) from exc
        except ValueError as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(DebtSerializer(debt).data, status=status.HTTP_201_CREATED)


class DebtDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def _get_or_404(self, pk: int, user: AbstractBaseUser) -> Debt:
        try:
            return selectors.get_debt_with_payments(debt_id=pk, user=user)
        except DebtNotFoundError as exc:
            raise NotFound(detail=str(exc)) from exc

    def get(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        debt = self._get_or_404(pk, user)
        return Response(DebtSerializer(debt).data)

    def patch(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        debt = self._get_or_404(pk, user)
        serializer = DebtUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated = services.update_debt(debt=debt, **serializer.validated_data)
        except DebtCategoryNotFoundError as exc:
            raise NotFound(detail=str(exc)) from exc
        except ValueError as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(DebtSerializer(updated).data)

    def delete(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        debt = self._get_or_404(pk, user)
        try:
            services.soft_delete_debt(debt=debt)
        except ValidationError as exc:
            return Response(
                {"error": {"type": "CONFLICT", "detail": str(exc), "status": 409}},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class DebtPaymentCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def _get_debt_or_404(self, debt_pk: int, user: AbstractBaseUser) -> Debt:
        from typing import cast as _cast
        try:
            return _cast(Debt, Debt.objects.get(pk=debt_pk, user=user))
        except Debt.DoesNotExist:
            raise NotFound(detail=f"Debt {debt_pk} not found.") from None

    def post(self, request: Request, debt_pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        debt = self._get_debt_or_404(debt_pk, user)
        serializer = DebtPaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account_id: int = serializer.validated_data["account_id"]
        try:
            from apps.accounts.models import Account

            account = Account.objects.get(pk=account_id, user=user)
        except Exception:
            raise NotFound(detail=f"Account {account_id} not found.") from None

        try:
            payment = services.record_debt_payment(
                debt=debt,
                account=account,
                amount=serializer.validated_data["amount"],
                paid_at=serializer.validated_data["paid_at"],
                user=user,
                description=serializer.validated_data.get("description", ""),
            )
        except DebtBalanceUnderflowError as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(DebtPaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class DebtPaymentDeleteView(APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request: Request, debt_pk: int, payment_pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        try:
            payment = DebtPayment.objects.select_related("debt").get(
                pk=payment_pk, debt__pk=debt_pk, debt__user=user  # type: ignore[misc]
            )
        except DebtPayment.DoesNotExist:
            raise NotFound(detail=f"Payment {payment_pk} not found.") from None

        services.reverse_debt_payment(payment=payment)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DebtMonthlySummaryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        raw_year = request.query_params.get("year")
        raw_month = request.query_params.get("month")

        if not raw_year or not raw_month:
            return Response(
                {
                    "error": {
                        "type": "VALIDATION_ERROR",
                        "detail": "year and month query parameters are required.",
                        "status": 400,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            year = int(raw_year)
            month = int(raw_month)
            if not (1 <= month <= 12):
                raise ValueError("month must be 1–12")
        except ValueError as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = selectors.get_debt_monthly_summary(user=user, year=year, month=month)
        serializer = DebtMonthlySummarySerializer(data)
        return Response(serializer.data)
