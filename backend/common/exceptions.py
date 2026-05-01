"""Custom DRF exception handler — emits a uniform error envelope."""
from __future__ import annotations

from typing import Any, Final

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django_ratelimit.exceptions import Ratelimited
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


class CategoryNotFoundError(LookupError):
    """Requested category does not exist or is not visible to the user."""


class CategoryPermissionError(PermissionError):
    """User attempted to modify a system category or another user's category."""


class CategoryCycleError(ValueError):
    """Setting this parent would create a cycle in the category tree."""


class CategoryDepthError(ValueError):
    """Category hierarchy would exceed the maximum allowed depth (10)."""


class TransactionNotFoundError(LookupError):
    """Requested transaction does not exist or belongs to another user."""


class AccountNotFoundError(LookupError):
    """Requested account does not exist or belongs to another user."""


class AccountInUseError(Exception):
    """Account cannot be deleted because it has linked transactions."""


class AccountCurrencyLockedError(Exception):
    """Account currency cannot be changed once transactions exist."""


class DebtNotFoundError(LookupError):
    """Requested debt does not exist or belongs to another user."""


class DebtBalanceUnderflowError(ValueError):
    """Payment amount exceeds current debt balance."""


class DebtCategoryNotFoundError(LookupError):
    """Requested debt category does not exist or belongs to another user."""


class DebtCategoryHasChildrenError(Exception):
    """Debt category cannot be deleted because it has child categories."""


class DebtCategoryCycleError(ValueError):
    """Setting this parent would create a cycle in the debt category tree."""


class RecurringTemplateNotFoundError(LookupError):
    """Requested recurring template does not exist or belongs to another user."""


class RecurringTemplateInvalidError(ValueError):
    """Recurring template configuration is invalid (e.g. currency mismatch with account)."""


# Map DRF status codes to a stable, framework-agnostic taxonomy clients can branch on.
# Adding a new error type? Add it here, not by leaking exc.__class__.__name__.
_TYPE_BY_STATUS: Final[dict[int, str]] = {
    status.HTTP_400_BAD_REQUEST: "VALIDATION_ERROR",
    status.HTTP_401_UNAUTHORIZED: "AUTHENTICATION_FAILED",
    status.HTTP_403_FORBIDDEN: "PERMISSION_DENIED",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "UNSUPPORTED_MEDIA_TYPE",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
}


def drf_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    # django-ratelimit raises Ratelimited (subclass of PermissionDenied) which
    # DRF would otherwise render as 403; we want a real 429.
    if isinstance(exc, Ratelimited):
        return Response(
            {
                "error": {
                    "type": "RATE_LIMITED",
                    "detail": "Too many requests. Slow down.",
                    "status": status.HTTP_429_TOO_MANY_REQUESTS,
                }
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    response = exception_handler(exc, context)
    if response is None:
        return None

    error_type = _TYPE_BY_STATUS.get(response.status_code, "INTERNAL_ERROR")
    payload: dict[str, Any] = {
        "error": {
            "type": error_type,
            "detail": response.data,
            "status": response.status_code,
        }
    }
    # Only expose framework class names in DEBUG to aid local debugging.
    if settings.DEBUG:
        payload["error"]["debug_class"] = exc.__class__.__name__
    response.data = payload
    return response


def ratelimited_view(request: HttpRequest, exception: Exception) -> JsonResponse:
    """Custom handler for django-ratelimit's Ratelimited exception → 429."""
    return JsonResponse(
        {
            "error": {
                "type": "RATE_LIMITED",
                "detail": "Too many requests. Slow down.",
                "status": status.HTTP_429_TOO_MANY_REQUESTS,
            }
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
