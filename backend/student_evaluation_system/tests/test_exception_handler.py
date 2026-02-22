"""
Tests for the global exception handler.

These tests verify standardized error responses and custom exception classes.
"""

from unittest.mock import Mock, patch
from rest_framework.exceptions import ValidationError, APIException
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import IntegrityError
from django.conf import settings

from student_evaluation_system.exception_handler import (
    APIError,
    NotFoundError,
    PermissionError,
    ValidationAPIError,
    custom_exception_handler,
    get_error_code,
    get_error_message,
    ExceptionMiddleware,
)


class TestAPIErrorClasses:
    """Test custom API error exception classes."""

    def test_api_error_basic(self):
        """Test basic APIError creation."""
        error = APIError("Something went wrong")
        assert error.message == "Something went wrong"
        assert error.code == "error"
        assert error.status_code == 400
        assert error.details == {}

    def test_api_error_with_all_params(self):
        """Test APIError with all parameters."""
        error = APIError(message="Custom error", code="custom_code", status_code=500, details={"field": "value"})
        assert error.message == "Custom error"
        assert error.code == "custom_code"
        assert error.status_code == 500
        assert error.details == {"field": "value"}

    def test_not_found_error_basic(self):
        """Test NotFoundError with minimal parameters."""
        error = NotFoundError()
        assert error.message == "Resource not found"
        assert error.code == "not_found"
        assert error.status_code == 404

    def test_not_found_error_with_resource(self):
        """Test NotFoundError with resource name."""
        error = NotFoundError(resource="Student")
        assert error.message == "Student not found"

    def test_not_found_error_with_resource_and_identifier(self):
        """Test NotFoundError with resource and identifier."""
        error = NotFoundError(resource="Course", identifier="CS101")
        assert error.message == "Course not found: CS101"

    def test_permission_error_default_message(self):
        """Test PermissionError with default message."""
        error = PermissionError()
        assert error.message == "You don't have permission to perform this action"
        assert error.code == "permission_denied"
        assert error.status_code == 403

    def test_permission_error_custom_message(self):
        """Test PermissionError with custom message."""
        error = PermissionError("Admin access required")
        assert error.message == "Admin access required"

    def test_validation_api_error(self):
        """Test ValidationAPIError."""
        error = ValidationAPIError("Invalid input", details={"field": "required"})
        assert error.message == "Invalid input"
        assert error.code == "validation_error"
        assert error.status_code == 400
        assert error.details == {"field": "required"}


class TestGetErrorCode:
    """Test the get_error_code function."""

    def test_validation_error_code(self):
        """Test code for ValidationError."""
        exc = ValidationError("test")
        assert get_error_code(exc) == "validation_error"

    def test_permission_denied_code(self):
        """Test code for PermissionDenied."""
        exc = PermissionDenied()
        assert get_error_code(exc) == "permission_denied"

    def test_status_code_mapping(self):
        """Test mapping of status codes to error codes."""
        test_cases = [
            (400, "bad_request"),
            (401, "unauthorized"),
            (403, "forbidden"),
            (404, "not_found"),
            (405, "method_not_allowed"),
            (429, "rate_limited"),
            (500, "internal_error"),
        ]
        for status_code, expected_code in test_cases:
            exc = Mock()
            exc.status_code = status_code
            assert get_error_code(exc) == expected_code

    def test_unknown_status_code(self):
        """Test code for unknown status code."""
        exc = Mock()
        exc.status_code = 418  # I'm a teapot
        assert get_error_code(exc) == "error"

    def test_no_status_code_attribute(self):
        """Test code for exception without status_code."""
        exc = Exception("test")
        assert get_error_code(exc) == "error"


class TestGetErrorMessage:
    """Test the get_error_message function."""

    def test_exception_without_detail(self):
        """Test message for exception without detail."""
        exc = Exception("Simple error")
        assert get_error_message(exc) == "Simple error"

    def test_validation_error_with_dict_detail(self):
        """Test message formatting for dict detail."""
        exc = Mock()
        exc.detail = {"username": ["This field is required"], "email": ["Invalid email"]}
        message = get_error_message(exc)
        assert "username: This field is required" in message
        assert "email: Invalid email" in message

    def test_validation_error_with_list_detail(self):
        """Test message formatting for list detail."""
        exc = Mock()
        exc.detail = ["Error 1", "Error 2"]
        message = get_error_message(exc)
        assert message == "Error 1; Error 2"

    def test_validation_error_with_string_detail(self):
        """Test message formatting for string detail."""
        exc = Mock()
        exc.detail = "Simple detail message"
        message = get_error_message(exc)
        assert message == "Simple detail message"

    def test_validation_error_with_non_list_non_string_errors(self):
        """Test message formatting when errors are not strings."""
        exc = Mock()
        exc.detail = {"field": 123}  # Non-string error
        message = get_error_message(exc)
        assert "field: 123" in message


class TestCustomExceptionHandler:
    """Test the custom_exception_handler function."""

    def test_handles_drf_validation_error(self):
        """Test handler for DRF ValidationError."""
        exc = ValidationError({"field": ["This field is required"]})
        context = {"request": Mock(), "view": Mock()}

        response = custom_exception_handler(exc, context)

        assert response is not None
        assert response.status_code == 400
        assert "error" in response.data
        assert response.data["error"]["code"] == "validation_error"
        assert "details" in response.data["error"]

    def test_handles_permission_denied(self):
        """Test handler for Django PermissionDenied."""
        exc = PermissionDenied()
        context = {"request": Mock(), "view": Mock()}

        response = custom_exception_handler(exc, context)

        assert response is not None
        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    @patch("student_evaluation_system.exception_handler.exception_handler")
    def test_handles_permission_denied_when_drf_returns_none(self, mock_drf_handler):
        """Test handler for PermissionDenied when DRF doesn't handle it."""
        mock_drf_handler.return_value = None  # DRF doesn't handle it
        exc = PermissionDenied()
        context = {"request": Mock(), "view": Mock()}

        response = custom_exception_handler(exc, context)

        assert response is not None
        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"
        assert "You do not have permission" in response.data["error"]["message"]

    def test_handles_object_does_not_exist(self):
        """Test handler for ObjectDoesNotExist."""
        exc = ObjectDoesNotExist("Object not found")
        context = {"request": Mock(), "view": Mock()}

        response = custom_exception_handler(exc, context)

        assert response is not None
        assert response.status_code == 404
        assert response.data["error"]["code"] == "not_found"

    def test_handles_integrity_error_debug(self):
        """Test handler for IntegrityError in DEBUG mode."""
        with patch.object(settings, "DEBUG", True):
            exc = IntegrityError("Duplicate key")
            context = {"request": Mock(), "view": Mock()}

            response = custom_exception_handler(exc, context)

            assert response is not None
            assert response.status_code == 400
            assert response.data["error"]["code"] == "integrity_error"
            assert "details" in response.data["error"]
            assert "Duplicate key" in response.data["error"]["details"]["detail"]

    def test_handles_integrity_error_production(self):
        """Test handler for IntegrityError in production (no details)."""
        with patch.object(settings, "DEBUG", False):
            exc = IntegrityError("Duplicate key")
            context = {"request": Mock(), "view": Mock()}

            response = custom_exception_handler(exc, context)

            assert response is not None
            assert response.status_code == 400
            assert response.data["error"]["code"] == "integrity_error"
            assert response.data["error"].get("details") == {}

    @patch("student_evaluation_system.exception_handler.logger")
    def test_handles_unhandled_exception_debug(self, mock_logger):
        """Test handler for unhandled exceptions in DEBUG mode."""
        with patch.object(settings, "DEBUG", True):
            exc = Exception("Unexpected error")
            context = {"request": Mock(), "view": Mock()}

            response = custom_exception_handler(exc, context)

            assert response is not None
            assert response.status_code == 500
            assert response.data["error"]["code"] == "internal_error"
            assert "Unexpected error" in response.data["error"]["details"]["detail"]
            mock_logger.exception.assert_called_once()

    @patch("student_evaluation_system.exception_handler.logger")
    def test_handles_unhandled_exception_production(self, mock_logger):
        """Test handler for unhandled exceptions in production."""
        with patch.object(settings, "DEBUG", False):
            exc = Exception("Unexpected error")
            context = {"request": Mock(), "view": Mock()}

            response = custom_exception_handler(exc, context)

            assert response is not None
            assert response.status_code == 500
            assert response.data["error"]["code"] == "internal_error"
            assert response.data["error"].get("details") == {}
            mock_logger.exception.assert_called_once()

    def test_drf_handled_exception_standardizes_format(self):
        """Test that DRF-handled exceptions get standardized format."""
        # Create a mock APIException that DRF handles
        exc = APIException("API error")
        exc.status_code = 400
        context = {"request": Mock(), "view": Mock()}

        response = custom_exception_handler(exc, context)

        assert response is not None
        assert "error" in response.data
        assert "code" in response.data["error"]
        assert "message" in response.data["error"]


class TestExceptionMiddleware:
    """Test the ExceptionMiddleware class."""

    def test_middleware_init(self):
        """Test middleware initialization."""
        get_response = Mock()
        middleware = ExceptionMiddleware(get_response)
        assert middleware.get_response == get_response

    def test_middleware_call(self):
        """Test middleware __call__ method."""
        get_response = Mock(return_value="response")
        middleware = ExceptionMiddleware(get_response)
        request = Mock()

        response = middleware(request)

        get_response.assert_called_once_with(request)
        assert response == "response"

    @patch("student_evaluation_system.exception_handler.logger")
    def test_process_exception_logs_non_api_exception(self, mock_logger):
        """Test that non-API exceptions are logged."""
        get_response = Mock()
        middleware = ExceptionMiddleware(get_response)
        request = Mock()
        request.method = "GET"
        request.path = "/api/test/"
        exception = Exception("Test error")

        result = middleware.process_exception(request, exception)

        assert result is None  # Let DRF handle it
        mock_logger.exception.assert_called_once()
        assert "GET /api/test/" in mock_logger.exception.call_args[0][0]

    def test_process_exception_does_not_log_api_exception(self):
        """Test that APIException is not logged by middleware."""
        get_response = Mock()
        middleware = ExceptionMiddleware(get_response)
        request = Mock()
        exception = APIException("API error")

        with patch("student_evaluation_system.exception_handler.logger") as mock_logger:
            result = middleware.process_exception(request, exception)

        assert result is None
        mock_logger.exception.assert_not_called()
