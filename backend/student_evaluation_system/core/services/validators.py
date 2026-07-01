"""
Input validation and sanitization utilities for the Student Evaluation System.

This module provides validation functions to ensure data integrity and prevent
security issues like injection attacks, XSS, and malformed data.
"""

import re
from typing import Optional

from django.core.exceptions import ValidationError


class InputValidator:
    """Input validation and sanitization utilities."""

    # Constants for validation limits
    MAX_STRING_LENGTH = 255
    MAX_TEXT_LENGTH = 10000
    MAX_FILE_SIZE_MB = 10
    ALLOWED_FILE_EXTENSIONS = [".xlsx", ".xls", ".csv"]

    # Regex patterns for sanitization
    # Allow alphanumeric, spaces, and common punctuation for names
    SAFE_STRING_PATTERN = re.compile(r"^[\w\s\-\'\.(),:@/]+$")

    # Course code pattern: alphanumeric with optional spaces and hyphens
    COURSE_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9 \-]*$", re.IGNORECASE)

    # Student ID pattern: alphanumeric with optional leading zeros
    STUDENT_ID_PATTERN = re.compile(r"^[A-Z0-9\-]+$", re.IGNORECASE)

    # Assessment name pattern
    ASSESSMENT_NAME_PATTERN = re.compile(r"^[\w\s\-\'\.()%]+$")

    @classmethod
    def sanitize_string(cls, value: str, max_length: int = MAX_STRING_LENGTH, allow_unicode: bool = False) -> str:
        """
        Sanitize a string input.

        Args:
            value: The input string to sanitize
            max_length: Maximum allowed length
            allow_unicode: Whether to allow non-ASCII characters

        Returns:
            Sanitized string

        Raises:
            ValidationError: If input is invalid
        """
        if not isinstance(value, str):
            raise ValidationError(f"Expected string, got {type(value).__name__}")
        value = value.strip()
        return value

    @classmethod
    def validate_course_code(cls, code: str) -> str:
        """
        Validate and sanitize a course code.

        Args:
            code: The course code to validate

        Returns:
            Sanitized course code in uppercase

        Raises:
            ValidationError: If course code is invalid
        """
        if not isinstance(code, str):
            raise ValidationError("Course code must be a string")

        code = code.strip().upper()

        if not code:
            raise ValidationError("Course code cannot be empty")

        if len(code) > 20:
            raise ValidationError("Course code too long (max 20 characters)")

        if not cls.COURSE_CODE_PATTERN.match(code):
            raise ValidationError("Course code contains invalid characters. Use only letters, numbers, spaces, and hyphens.")

        return code

    @classmethod
    def validate_student_id(cls, student_id: str) -> str:
        """
        Validate and sanitize a student ID.

        Args:
            student_id: The student ID to validate

        Returns:
            Sanitized student ID

        Raises:
            ValidationError: If student ID is invalid
        """
        if not isinstance(student_id, str):
            raise ValidationError("Student ID must be a string")

        student_id = student_id.strip()

        if not student_id:
            raise ValidationError("Student ID cannot be empty")

        if len(student_id) > 50:
            raise ValidationError("Student ID too long (max 50 characters)")

        if not cls.STUDENT_ID_PATTERN.match(student_id):
            raise ValidationError("Student ID contains invalid characters")

        return student_id

    @classmethod
    def validate_assessment_name(cls, name: str) -> str:
        """
        Validate and sanitize an assessment name.

        Args:
            name: The assessment name to validate

        Returns:
            Sanitized assessment name

        Raises:
            ValidationError: If assessment name is invalid
        """
        if not isinstance(name, str):
            raise ValidationError("Assessment name must be a string")

        name = name.strip()

        if not name:
            raise ValidationError("Assessment name cannot be empty")

        if len(name) > 100:
            raise ValidationError("Assessment name too long (max 100 characters)")

        if not cls.ASSESSMENT_NAME_PATTERN.match(name):
            raise ValidationError("Assessment name contains invalid characters")

        return name

    @classmethod
    def validate_file_extension(cls, filename: str) -> None:
        """
        Validate that a file has an allowed extension.

        Args:
            filename: The filename to validate

        Raises:
            ValidationError: If file extension is not allowed
        """
        if not isinstance(filename, str):
            raise ValidationError("Filename must be a string")

        filename = filename.lower().strip()

        # Check for path traversal attempts
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValidationError("Invalid filename: path traversal detected")

        # Check extension
        has_valid_ext = any(filename.endswith(ext) for ext in cls.ALLOWED_FILE_EXTENSIONS)
        if not has_valid_ext:
            raise ValidationError(f"Invalid file extension. Allowed: {', '.join(cls.ALLOWED_FILE_EXTENSIONS)}")

    @classmethod
    def validate_score(cls, score, max_score: Optional[float] = None) -> float:
        """
        Validate a numeric score.

        Args:
            score: The score value to validate
            max_score: Optional maximum allowed score

        Returns:
            Validated score as float

        Raises:
            ValidationError: If score is invalid
        """
        try:
            score_float = float(score)
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid score value: {score}")

        if score_float < 0:
            raise ValidationError("Score cannot be negative")

        if max_score is not None and score_float > max_score:
            raise ValidationError(f"Score {score_float} exceeds maximum {max_score}")

        return score_float

    @classmethod
    def validate_weight(cls, weight: float) -> float:
        """
        Validate a weight value (should be between 0 and 1).

        Args:
            weight: The weight value to validate

        Returns:
            Validated weight

        Raises:
            ValidationError: If weight is invalid
        """
        try:
            weight_float = float(weight)
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid weight value: {weight}")

        if weight_float < 0 or weight_float > 1:
            raise ValidationError("Weight must be between 0 and 1")

        return weight_float

    @classmethod
    def sanitize_column_name(cls, column_name: str) -> str:
        """
        Sanitize a column name from Excel/CSV files.

        Args:
            column_name: The column name to sanitize

        Returns:
            Sanitized column name
        """
        if not isinstance(column_name, str):
            return str(column_name)

        # Remove null bytes and control characters
        column_name = re.sub(r"[\x00-\x1f\x7f]", "", column_name)

        # Strip whitespace
        column_name = column_name.strip()

        # Limit length
        if len(column_name) > 200:
            column_name = column_name[:200]

        return column_name


class FileValidator:
    """File validation utilities."""

    MAX_FILE_SIZE_MB = 10

    @classmethod
    def validate_file_size(cls, file_size: int) -> None:
        """
        Validate file size.

        Args:
            file_size: Size of the file in bytes

        Raises:
            ValidationError: If file is too large
        """
        max_size = cls.MAX_FILE_SIZE_MB * 1024 * 1024

        if file_size > max_size:
            human_size = file_size / (1024 * 1024)
            raise ValidationError(f"File size must be less than {cls.MAX_FILE_SIZE_MB}MB (got {human_size:.2f}MB)")
