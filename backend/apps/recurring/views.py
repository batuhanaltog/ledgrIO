from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import RecurringTemplateInvalidError, RecurringTemplateNotFoundError

from . import selectors, services
from .serializers import (
    RecurringTemplateCreateSerializer,
    RecurringTemplateListSerializer,
    RecurringTemplateSerializer,
    RecurringTemplateUpdateSerializer,
)


class RecurringTemplatePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class RecurringTemplateListCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        filters: dict = {}
        if type_ := request.query_params.get("type"):
            filters["type"] = type_
        if account_id := request.query_params.get("account_id"):
            import contextlib
            with contextlib.suppress(ValueError):
                filters["account_id"] = int(account_id)
        if frequency := request.query_params.get("frequency"):
            filters["frequency"] = frequency
        if request.query_params.get("is_active") in ("1", "true", "True"):
            filters["is_active"] = True
        elif request.query_params.get("is_active") in ("0", "false", "False"):
            filters["is_active"] = False

        qs = selectors.get_recurring_template_list(user=user, filters=filters)
        paginator = RecurringTemplatePagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = RecurringTemplateListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        serializer = RecurringTemplateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            template = services.create_recurring_template(
                user=user, **serializer.validated_data
            )
        except RecurringTemplateInvalidError as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        detail = selectors.get_recurring_template_detail(
            template_id=template.pk, user=user
        )
        return Response(
            RecurringTemplateSerializer(detail).data,
            status=status.HTTP_201_CREATED,
        )


class RecurringTemplateDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def _get_or_404(self, pk: int, user: AbstractBaseUser) -> object:
        try:
            return selectors.get_recurring_template_detail(template_id=pk, user=user)
        except RecurringTemplateNotFoundError as exc:
            from rest_framework.exceptions import NotFound

            raise NotFound(detail=str(exc)) from exc

    def get(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        template = self._get_or_404(pk, user)
        return Response(RecurringTemplateSerializer(template).data)

    def patch(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        template = self._get_or_404(pk, user)
        serializer = RecurringTemplateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated = services.update_recurring_template(
                template=template,  # type: ignore[arg-type]
                **serializer.validated_data,
            )
        except RecurringTemplateInvalidError as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        detail = selectors.get_recurring_template_detail(
            template_id=updated.pk, user=user
        )
        return Response(RecurringTemplateSerializer(detail).data)

    def delete(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        template = self._get_or_404(pk, user)
        services.soft_delete_recurring_template(template=template)  # type: ignore[arg-type]
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecurringTemplateMaterializeNowView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        try:
            template = selectors.get_recurring_template_detail(
                template_id=pk, user=user
            )
        except RecurringTemplateNotFoundError as exc:
            from rest_framework.exceptions import NotFound

            raise NotFound(detail=str(exc)) from exc

        from datetime import date

        from apps.recurring.services import compute_next_due_date, materialize_template_for_date

        target_date = date.today()
        next_due = compute_next_due_date(template=template)

        if next_due is None or next_due > target_date:
            return Response(
                {
                    "detail": "No transaction due today or template is inactive/expired.",
                    "next_due_date": next_due,
                },
                status=status.HTTP_200_OK,
            )

        transaction = materialize_template_for_date(
            template=template, target_date=next_due
        )
        if transaction is None:
            return Response(
                {"detail": "Already materialized for this date."},
                status=status.HTTP_200_OK,
            )

        from apps.transactions.serializers import TransactionSerializer

        return Response(
            TransactionSerializer(transaction).data,
            status=status.HTTP_201_CREATED,
        )
