from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import BudgetInvalidError, BudgetNotFoundError

from . import selectors, services
from .serializers import BudgetCreateSerializer, BudgetSerializer, BudgetUpdateSerializer


class BudgetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class BudgetListCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        qs = selectors.get_budget_queryset(user=user)
        paginator = BudgetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(BudgetSerializer(page, many=True).data)

    def post(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        serializer = BudgetCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            budget = services.create_budget(user=user, data=dict(serializer.validated_data))
        except BudgetInvalidError as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        detail = selectors.get_budget_for_user(user=user, pk=budget.pk)
        return Response(BudgetSerializer(detail).data, status=status.HTTP_201_CREATED)


class BudgetDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def _get_or_404(self, pk: int, user: AbstractBaseUser) -> object:
        try:
            return selectors.get_budget_for_user(user=user, pk=pk)
        except BudgetNotFoundError as exc:
            raise NotFound(detail=str(exc)) from exc

    def get(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        budget = self._get_or_404(pk, user)
        return Response(BudgetSerializer(budget).data)

    def patch(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        budget = self._get_or_404(pk, user)
        serializer = BudgetUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated = services.update_budget(
                budget=budget,  # type: ignore[arg-type]
                data=dict(serializer.validated_data),
            )
        except BudgetInvalidError as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        detail = selectors.get_budget_for_user(user=user, pk=updated.pk)
        return Response(BudgetSerializer(detail).data)

    def delete(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        budget = self._get_or_404(pk, user)
        services.delete_budget(budget=budget)  # type: ignore[arg-type]
        return Response(status=status.HTTP_204_NO_CONTENT)
