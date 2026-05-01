"""Liveness / readiness endpoints."""
from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.db import DatabaseError, connection
from django.db.utils import OperationalError
from drf_spectacular.utils import extend_schema
from redis.exceptions import RedisError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Returns service health: DB + Redis connectivity."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        summary="Service health check",
        responses={200: {"type": "object"}, 503: {"type": "object"}},
    )
    def get(self, request: Request) -> Response:
        checks: dict[str, str] = {}
        ok = True

        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            checks["database"] = "ok"
        except (OperationalError, DatabaseError) as exc:
            checks["database"] = f"error: {exc.__class__.__name__}"
            ok = False

        try:
            cache.set("health:ping", "pong", timeout=5)
            checks["redis"] = "ok" if cache.get("health:ping") == "pong" else "error"
            ok = ok and checks["redis"] == "ok"
        except (RedisError, ConnectionError, TimeoutError) as exc:
            checks["redis"] = f"error: {exc.__class__.__name__}"
            ok = False

        payload: dict[str, Any] = {"status": "ok" if ok else "degraded", "checks": checks}
        http_status = status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(payload, status=http_status)
