"""
Global exception handler for the Student Evaluation System.

Provides standardized error responses across the API with consistent format:
{
    "error": {
        "code": "error_code",
        "message": "Human readable message",
        "details": {} (optional additional details)
    }
}
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import IntegrityError
from django.conf import settings

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base class for API errors."""

    def __init__(self, message, code=None, status_code=400, details=None):
        self.message = message
        self.code = code or "error"
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(APIError):
    """Resource not found error."""

    def __init__(self, resource=None, identifier=None):
        message = f"{resource} not found" if resource else "Resource not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message, code="not_found", status_code=404)


class PermissionError(APIError):
    """Permission denied error."""

    def __init__(self, message="You don't have permission to perform this action"):
        super().__init__(message, code="permission_denied", status_code=403)


class ValidationAPIError(APIError):
    """Validation error."""

    def __init__(self, message, details=None):
        super().__init__(message, code="validation_error", status_code=400, details=details)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that standardizes error responses.

    Args:
        exc: The exception that was raised
        context: Dictionary containing request and view information

    Returns:
        Response object with standardized error format
    """
    # Get the standard DRF response first
    response = exception_handler(exc, context)

    # If DRF handled it, standardize the format
    if response is not None:
        error_data = {
            "error": {
                "code": get_error_code(exc),
                "message": get_error_message(exc),
            }
        }

        # Add details for validation errors
        if isinstance(exc, ValidationError) and hasattr(exc, "detail"):
            error_data["error"]["details"] = exc.detail

        response.data = error_data
        return response

    # Handle Django exceptions that DRF doesn't handle
    if isinstance(exc, PermissionDenied):
        return Response(
            {"error": {"code": "permission_denied", "message": "You do not have permission to perform this action"}},
            status=status.HTTP_403_FORBIDDEN,
        )

    if isinstance(exc, ObjectDoesNotExist):
        return Response(
            {"error": {"code": "not_found", "message": "The requested resource was not found"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, IntegrityError):
        logger.error(f"Database integrity error: {str(exc)}")
        return Response(
            {
                "error": {
                    "code": "integrity_error",
                    "message": "Database integrity error. This might be due to duplicate data.",
                    "details": {"detail": str(exc)} if settings.DEBUG else {},
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Log unhandled exceptions
    logger.exception(f"Unhandled exception: {str(exc)}")

    # Return generic error for unhandled exceptions (don't expose details in production)
    return Response(
        {
            "error": {
                "code": "internal_error",
                "message": "An internal server error occurred",
                "details": {"detail": str(exc)} if settings.DEBUG else {},
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def get_error_code(exc):
    """Get error code based on exception type."""
    error_codes = {
        ValidationError: "validation_error",
        PermissionDenied: "permission_denied",
    }

    for exc_type, code in error_codes.items():
        if isinstance(exc, exc_type):
            return code

    # Map status codes to error codes
    status_codes = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        429: "rate_limited",
        500: "internal_error",
    }

    if hasattr(exc, "status_code"):
        return status_codes.get(exc.status_code, "error")

    return "error"


def get_error_message(exc):
    """Get human-readable error message."""
    if hasattr(exc, "detail"):
        if isinstance(exc.detail, dict):
            # Format validation errors
            messages = []
            for field, errors in exc.detail.items():
                if isinstance(errors, list):
                    messages.append(f"{field}: {', '.join(str(e) for e in errors)}")
                else:
                    messages.append(f"{field}: {errors}")
            return "; ".join(messages)
        elif isinstance(exc.detail, list):
            return "; ".join(str(e) for e in exc.detail)
        else:
            return str(exc.detail)

    return str(exc)


class ExceptionMiddleware:
    """
    Middleware to catch and log exceptions.

    This ensures all exceptions are logged, even if they're handled
    by DRF's exception handler.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        """Log all unhandled exceptions."""
        if not isinstance(exception, APIException):
            logger.exception(f"Unhandled exception in {request.method} {request.path}: {str(exception)}")
        return None  # Let DRF handle it
