from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.exceptions import (
    CategoryCycleError,
    CategoryDepthError,
    CategoryNotFoundError,
    CategoryPermissionError,
)

from . import selectors, services
from .models import Category
from .serializers import CategoryFlatSerializer, CategoryWriteSerializer


def _get_visible_category_or_404(pk: int, user: AbstractBaseUser) -> Category:
    try:
        return Category.objects.get(Q(is_system=True) | Q(owner=user), id=pk)  # type: ignore[no-any-return]
    except Category.DoesNotExist:
        raise CategoryNotFoundError(f"Category {pk} not found.") from None


class CategoryListView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[OpenApiParameter("format", str, enum=["tree", "flat"], description="Response format")],
    )
    def get(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        fmt = request.query_params.get("format", "tree")
        if fmt == "flat":
            return Response(selectors.get_category_flat(user=user))
        qs = selectors.get_visible_categories(user=user)
        return Response(selectors.build_category_tree(qs))

    def post(self, request: Request) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        serializer = CategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            category = services.create_category(user=user, **serializer.validated_data)
        except (CategoryCycleError, CategoryDepthError) as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(CategoryFlatSerializer(category).data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def patch(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        category = _get_visible_category_or_404(pk, user)
        serializer = CategoryWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            category = services.update_category(
                category=category, user=user, **serializer.validated_data
            )
        except CategoryPermissionError as exc:
            return Response(
                {"error": {"type": "CATEGORY_PERMISSION_DENIED", "detail": str(exc), "status": 403}},
                status=status.HTTP_403_FORBIDDEN,
            )
        except (CategoryCycleError, CategoryDepthError) as exc:
            return Response(
                {"error": {"type": "VALIDATION_ERROR", "detail": str(exc), "status": 400}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(CategoryFlatSerializer(category).data)

    def delete(self, request: Request, pk: int) -> Response:
        user: AbstractBaseUser = request.user  # type: ignore[assignment]
        category = _get_visible_category_or_404(pk, user)
        try:
            services.soft_delete_category(category=category, user=user)
        except CategoryPermissionError as exc:
            return Response(
                {"error": {"type": "CATEGORY_PERMISSION_DENIED", "detail": str(exc), "status": 403}},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
