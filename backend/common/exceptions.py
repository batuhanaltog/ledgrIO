"""Custom DRF exception handler — emits a uniform error envelope."""
from __future__ import annotations

from typing import Any

from rest_framework.response import Response
from rest_framework.views import exception_handler


def drf_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = exception_handler(exc, context)
    if response is None:
        return None

    response.data = {
        "error": {
            "type": exc.__class__.__name__,
            "detail": response.data,
            "status": response.status_code,
        }
    }
    return response
