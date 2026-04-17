"""
Validation Services for File Import System

This module provides layered validation approach with clear separation of concerns:
- FileFormatValidator: Basic file format and structure validation
- BusinessStructureValidator: Business rules and data structure validation
- DatabaseIntegrityValidator: Database consistency and relationship validation
- DataQualityValidator: Data quality and integrity validation

Each validator focuses on specific responsibility and can be combined
to create comprehensive validation pipelines.
"""

import pandas as pd
import re
from typing import Dict, Any
from django.contrib.auth import get_user_model

from ..models import Term, Course
from evaluation.models import Assessment

User = get_user_model()


class ValidationResult:
    """
    Container for validation results with detailed error reporting.
    """

    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
        self.suggestions = []
        self.validation_details = {}

    def add_error(self, message: str, category: str = "general"):
        """Add an error to the results."""
        self.is_valid = False
        self.errors.append({"message": message, "category": category, "severity": "error"})

    def add_warning(self, message: str, category: str = "general"):
        """Add a warning to the results."""
        self.warnings.append({"message": message, "category": category, "severity": "warning"})

    def add_suggestion(self, message: str, category: str = "general"):
        """Add a suggestion to the results."""
        self.suggestions.append({"message": message, "category": category, "severity": "suggestion"})

    def add_detail(self, key: str, value: Any):
        """Add detailed validation information."""
        self.validation_details[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary format."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "validation_details": self.validation_details,
        }


class FileFormatValidator:
    """
    Handles basic file format and structure validation.
    Focus: File type, size, readability, basic structure.
    """

    # Maximum file size: 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024

    REQUIRED_COLUMNS = {
        "assessment_scores": ["student_id", "assessment_name", "score"],
        "learning_outcomes": ["code", "description", "course_code"],
        "program_outcomes": ["code", "description", "program_code", "term_name"],
        "assignment_scores": ["öğrenci no", "adı", "soyadı"],
    }

    @staticmethod
    def validate_file_format(file_obj, import_type: str) -> ValidationResult:
        """
        Validate basic file format and structure.

        Args:
            file_obj: Uploaded file object
            import_type: Type of import (assessment_scores, learning_outcomes, etc.)

        Returns:
            ValidationResult: Validation results
        """
        result = ValidationResult()

        # Validate file extension - only Excel files allowed for assignment_scores
        if import_type == "assignment_scores":
            valid_extensions = [".xlsx", ".xls"]
        else:
            valid_extensions = [".xlsx", ".xls", ".csv"]

        file_extension = file_obj.name.lower().split(".")[-1]

        if not any(file_obj.name.lower().endswith(ext) for ext in valid_extensions):
            result.add_error(f"Invalid file format. Supported formats: {', '.join(valid_extensions)}", "file_format")
            return result

        # Validate file size (10MB limit)
        max_size = FileFormatValidator.MAX_FILE_SIZE
        if file_obj.size > max_size:
            result.add_error(
                f"File size exceeds {max_size // (1024 * 1024)}MB limit. Your file is {file_obj.size / (1024 * 1024):.2f}MB",
                "file_size",
            )

        # Add file info to details
        result.add_detail(
            "file_info",
            {
                "name": file_obj.name,
                "size": file_obj.size,
                "size_mb": round(file_obj.size / (1024 * 1024), 2),
                "extension": file_extension,
            },
        )

        return result

    @staticmethod
    def validate_dataframe_structure(dataframe: pd.DataFrame, import_type: str) -> ValidationResult:
        """
        Validate dataframe structure and required columns.

        Args:
            dataframe: Pandas DataFrame to validate
            import_type: Type of import operation

        Returns:
            ValidationResult: Validation results
        """
        result = ValidationResult()

        # Check if dataframe is empty
        if dataframe.empty:
            result.add_error("File contains no data rows", "data_structure")
            return result

        # Get required columns for import type
        required_columns = FileFormatValidator.REQUIRED_COLUMNS.get(import_type, [])
        missing_columns = []

        # Check for each required column (case-insensitive partial match)
        for required_col in required_columns:
            found = False
            for df_col in dataframe.columns:
                if required_col.lower() in str(df_col).lower():
                    found = True
                    break
            if not found:
                missing_columns.append(required_col)

        if missing_columns:
            result.add_error(f"Missing required columns: {', '.join(missing_columns)}", "columns")
            result.add_suggestion(f"Required columns: {', '.join(required_columns)}", "columns")

        # Add column information
        result.add_detail(
            "columns",
            {
                "found": dataframe.columns.tolist(),
                "required": required_columns,
                "missing": missing_columns,
                "row_count": len(dataframe),
            },
        )

        return result


class BusinessStructureValidator:
    """
    Handles business rules and data structure validation.
    Focus: Data formats, business rules, logical consistency.
    """

    @staticmethod
    def _get_course_assessment_names(course: Course):
        assessments = Assessment.objects.filter(course=course)
        return assessments, list(assessments.values_list("name", flat=True))

    @staticmethod
    def _collect_file_assessment_issues(columns, assessment_names):
        file_assessment_names = set()
        invalid_assessments = set()

        for column in columns:
            if "assessment" in str(column).lower() or "score" in str(column).lower():
                assessment_name = str(column).replace("_score", "").replace("assessment_", "").strip()
                file_assessment_names.add(assessment_name)
                if assessment_name not in assessment_names:
                    invalid_assessments.add(assessment_name)

        return file_assessment_names, invalid_assessments

    @staticmethod
    def _collect_invalid_student_ids(student_ids):
        invalid_student_ids = []
        for student_id in student_ids:
            if pd.isna(student_id) or str(student_id).strip() == "":
                invalid_student_ids.append(student_id)
        return invalid_student_ids

    @staticmethod
    def _collect_invalid_scores(dataframe, score_columns):
        invalid_scores = []
        for column in score_columns:
            for score in dataframe[column]:
                if pd.notna(score):
                    try:
                        score_float = float(score)
                        if score_float < 0:
                            invalid_scores.append(f"Negative score: {score_float} in column {column}")
                    except (ValueError, TypeError):
                        invalid_scores.append(f"Invalid score format: {score} in column {column}")
        return invalid_scores

    @staticmethod
    def validate_assessment_scores_structure(dataframe: pd.DataFrame, course: Course) -> ValidationResult:
        """
        Validate assessment scores data structure and business rules.

        Args:
            dataframe: Assessment scores data
            course: Course object for context

        Returns:
            ValidationResult: Validation results
        """
        result = ValidationResult()

        assessments, assessment_names = BusinessStructureValidator._get_course_assessment_names(course)

        if not assessments:
            result.add_error(f"No assessments found for course {course.code}. Create assessments first.", "business_rules")
            return result

        file_assessment_names, invalid_assessments = BusinessStructureValidator._collect_file_assessment_issues(
            dataframe.columns, assessment_names
        )

        if invalid_assessments:
            result.add_error(f"Invalid assessment names: {', '.join(invalid_assessments)}", "assessment_validation")
            result.add_suggestion(f"Valid assessments for this course: {', '.join(assessment_names)}", "assessment_validation")

        # Validate student IDs format
        invalid_student_ids = BusinessStructureValidator._collect_invalid_student_ids(dataframe.get("student_id", []))

        if invalid_student_ids:
            result.add_error(f"Found {len(invalid_student_ids)} empty or invalid student IDs", "data_format")

        # Validate score formats and ranges
        score_columns = [col for col in dataframe.columns if "score" in str(col).lower()]
        invalid_scores = BusinessStructureValidator._collect_invalid_scores(dataframe, score_columns)

        if invalid_scores:
            result.add_error(f"Found {len(invalid_scores)} invalid scores", "score_validation")
            result.add_detail("invalid_scores_sample", invalid_scores[:5])  # Show first 5

        # Add business validation details
        result.add_detail(
            "business_validation",
            {
                "course_assessments": assessment_names,
                "file_assessments": list(file_assessment_names),
                "invalid_assessments": list(invalid_assessments),
                "student_count": len(dataframe),
                "score_columns": score_columns,
            },
        )

        return result

    @staticmethod
    def validate_assignment_scores_structure(dataframe: pd.DataFrame, course: Course) -> ValidationResult:
        """
        Validate assignment scores data structure for Turkish Excel format.

        Args:
            dataframe: Assignment scores data
            course: Course object for context

        Returns:
            ValidationResult: Validation results
        """
        result = ValidationResult()

        assessments, assessment_names = BusinessStructureValidator._get_course_assessment_names(course)

        if not assessments:
            result.add_error(f"No assessments found for course {course.code}. Create assessments first.", "business_rules")
            return result

        # Extract assessment columns from Turkish format
        assessment_columns = BusinessStructureValidator._extract_assessment_columns(dataframe.columns)

        if not assessment_columns:
            result.add_error(
                "No assessment score columns found. "
                "Expected columns like 'Midterm 1(%25)_0833AB', "
                "'Project(%40)_0833AB', etc.",
                "assignment_scores",
            )
            return result

        # Validate assessment names against database
        invalid_assessments = []
        for _, assessment_name in assessment_columns:
            # Clean assessment name by removing suffixes and weights
            clean_name = BusinessStructureValidator._clean_assessment_name(assessment_name)
            if clean_name not in assessment_names:
                invalid_assessments.append(clean_name)

        if invalid_assessments:
            result.add_error(f"Assessments not found in database: {', '.join(invalid_assessments)}", "assignment_scores")
            result.add_suggestion(f"Available assessments: {', '.join(assessment_names)}", "assignment_scores")

        # Validate student IDs (öğrenci no column)
        student_id_col = BusinessStructureValidator._find_student_id_column(dataframe.columns)
        if not student_id_col:
            result.add_error("Student ID column not found. Expected columns containing 'öğrenci no'", "assignment_scores")
            return result

        # Check for empty student IDs
        invalid_student_ids = BusinessStructureValidator._collect_invalid_student_ids(dataframe[student_id_col])

        if invalid_student_ids:
            result.add_error(f"Found {len(invalid_student_ids)} empty or invalid student IDs", "assignment_scores")

        # Validate score formats and ranges for assessment columns
        assessment_column_names = [col_name for col_name, _ in assessment_columns]
        invalid_scores = BusinessStructureValidator._collect_invalid_scores(dataframe, assessment_column_names)

        if invalid_scores:
            result.add_error(f"Found {len(invalid_scores)} invalid scores", "assignment_scores")
            result.add_detail("invalid_scores_sample", invalid_scores[:5])  # Show first 5

        # Add business validation details
        result.add_detail(
            "business_validation",
            {
                "course_assessments": assessment_names,
                "file_assessment_columns": [(col, name) for col, name in assessment_columns],
                "invalid_assessments": invalid_assessments,
                "student_count": len(dataframe),
                "student_id_column": student_id_col,
                "assessment_count": len(assessment_columns),
            },
        )

        return result

    @staticmethod
    def _extract_assessment_columns(columns):
        """
        Extract assessment columns from Turkish Excel format.

        Column format examples:
        - 'Midterm 1(%25)_0833AB' -> 'Midterm 1'
        - 'Project(%40)_0833AB' -> 'Project'
        - 'Attendance(%10)_0833AB' -> 'Attendance'

        We only look at the first word/part before any suffix like _0833AB.
        Non-assessment columns are: No, Öğrenci No, Adı, Soyadı, Snf, Girme Durum, Harf Notu
        """
        assessment_columns = []

        # Known non-assessment column prefixes (case-insensitive)
        non_assessment_prefixes = ["no", "öğrenci no", "adı", "soyadı", "snf", "girme durum", "harf notu"]

        for col in columns:
            col_str = str(col).strip()

            # Extract the first part before any suffix pattern (_XXXXXX)
            # Split by underscore and take everything before the last part if it looks like a suffix
            parts = col_str.split("_")
            if len(parts) > 1:
                # Check if last part looks like a suffix (alphanumeric code)
                last_part = parts[-1]
                if last_part.isalnum() and len(last_part) >= 4:
                    # Reconstruct without the suffix
                    base_name = "_".join(parts[:-1])
                else:
                    base_name = col_str
            else:
                base_name = col_str

            # Extract assessment name by removing weight pattern like (%25)
            import re

            assessment_name = re.sub(r"\(%?\d+%?\)", "", base_name).strip()

            # Check if this is a non-assessment column
            is_non_assessment = False
            for prefix in non_assessment_prefixes:
                if assessment_name.lower().startswith(prefix.lower()):
                    is_non_assessment = True
                    break

            if not is_non_assessment and assessment_name:
                assessment_columns.append((col_str, assessment_name))

        return assessment_columns

    @staticmethod
    def _clean_assessment_name(name):
        """Clean assessment name by removing weight information."""
        # Remove weight patterns like "(%25)", "(%40)", etc.
        cleaned = re.sub(r"\(%\d+\)", "", name).strip()
        return cleaned

    @staticmethod
    def _find_student_id_column(columns):
        """Find the student ID column from Turkish column names."""
        for col in columns:
            col_str = str(col).lower().strip()
            if "öğrenci no" in col_str:
                return col
        return None


class DatabaseIntegrityValidator:
    """
    Handles database consistency and relationship validation.
    Focus: Database lookups, relationship integrity, permission checks.
    """

    @staticmethod
    def _validate_course_for_term(result: ValidationResult, course: Course, term: Term):
        try:
            validated_course = Course.objects.get(code=course.code, term=term)
            result.add_detail("course_validated", True)
            return validated_course
        except Course.DoesNotExist:
            result.add_error(f"Course {course.code} not found for term {term.name}", "course_validation")
            available_courses = Course.objects.filter(code=course.code).select_related("term")
            if available_courses.exists():
                terms = [f"{existing_course.code} ({existing_course.term.name})" for existing_course in available_courses]
                result.add_suggestion(f"Available terms for {course.code}: {', '.join(terms)}", "course_validation")
            return None

    @staticmethod
    def _collect_student_ids(values):
        return {str(student_id).strip() for student_id in values if pd.notna(student_id)}

    @staticmethod
    def _extract_assessment_names_from_columns(columns):
        assessment_columns = [column for column in columns if "assessment" in str(column).lower()]
        return {str(column).strip() for column in assessment_columns if "score" not in str(column).lower()}

    @staticmethod
    def validate_assessment_scores_database(dataframe: pd.DataFrame, course: Course, term: Term) -> ValidationResult:
        """
        Validate database integrity for assessment scores import.

        Args:
            dataframe: Assessment scores data
            course: Course object
            term: Term object

        Returns:
            ValidationResult: Validation results
        """
        result = ValidationResult()

        course = DatabaseIntegrityValidator._validate_course_for_term(result, course, term)
        if not course:
            return result

        # Validate student enrollment
        student_ids = DatabaseIntegrityValidator._collect_student_ids(dataframe.get("student_id", []))

        # Check if students exist in database
        from users.models import StudentProfile

        existing_students = StudentProfile.objects.filter(student_id__in=student_ids).values_list("student_id", flat=True)

        missing_students = student_ids - set(existing_students)

        if missing_students:
            result.add_error(f"{len(missing_students)} students not found in database", "student_validation")
            result.add_detail("missing_students", list(missing_students)[:10])  # Show first 10

        # Validate assessments exist
        assessment_names = DatabaseIntegrityValidator._extract_assessment_names_from_columns(dataframe.columns)

        invalid_assessments = set()
        valid_assessments = set(Assessment.objects.filter(course=course).values_list("name", flat=True))

        for assessment_name in assessment_names:
            if assessment_name not in valid_assessments:
                invalid_assessments.add(assessment_name)

        if invalid_assessments:
            result.add_error(
                f"{len(invalid_assessments)} assessments not found for course {course.code}", "assessment_validation"
            )
            result.add_detail("invalid_assessments", list(invalid_assessments))

        # Add database validation details
        result.add_detail(
            "database_validation",
            {
                "course_validated": True,
                "total_students_in_file": len(student_ids),
                "valid_students_found": len(existing_students),
                "missing_students_count": len(missing_students),
                "valid_assessments_found": len(valid_assessments),
                "invalid_assessments": list(invalid_assessments),
            },
        )

        return result

    @staticmethod
    def validate_assignment_scores_database(dataframe: pd.DataFrame, course: Course, term: Term) -> ValidationResult:
        """
        Validate database integrity for assignment scores import (Turkish format).

        Args:
            dataframe: Assignment scores data
            course: Course object
            term: Term object

        Returns:
            ValidationResult: Validation results
        """
        result = ValidationResult()

        # Validate course exists for term
        try:
            course = Course.objects.get(code=course.code, term=term)
            result.add_detail("course_validated", True)
        except Course.DoesNotExist:
            result.add_error(f"Course {course.code} not found for term {term.name}", "course_validation")
            return result

        # Find student ID column
        student_id_col = BusinessStructureValidator._find_student_id_column(dataframe.columns)
        if not student_id_col:
            result.add_error("Student ID column not found", "assignment_scores")
            return result

        # Validate student enrollment
        student_ids = set()
        for student_id in dataframe[student_id_col]:
            if pd.notna(student_id):
                student_ids.add(str(student_id).strip())

        # Check if students exist in database
        from users.models import StudentProfile

        existing_students = StudentProfile.objects.filter(student_id__in=student_ids).values_list("student_id", flat=True)

        missing_students = set(student_ids) - set(existing_students)

        if missing_students:
            result.add_error(f"{len(missing_students)} students not found in database", "assignment_scores")
            result.add_detail("missing_students", list(missing_students)[:10])  # Show first 10

        # Validate assessments exist
        assessment_columns = BusinessStructureValidator._extract_assessment_columns(dataframe.columns)
        assessment_names = set()

        for col_name, assessment_name in assessment_columns:
            clean_name = BusinessStructureValidator._clean_assessment_name(assessment_name)
            assessment_names.add(clean_name)

        invalid_assessments = set()
        valid_assessments = set(Assessment.objects.filter(course=course).values_list("name", flat=True))

        for assessment_name in assessment_names:
            if assessment_name not in valid_assessments:
                invalid_assessments.add(assessment_name)

        if invalid_assessments:
            result.add_error(f"{len(invalid_assessments)} assessments not found for course {course.code}", "assignment_scores")
            result.add_detail("invalid_assessments", list(invalid_assessments))

        # Add database validation details
        result.add_detail(
            "database_validation",
            {
                "course_validated": True,
                "total_students_in_file": len(student_ids),
                "valid_students_found": len(existing_students),
                "missing_students_count": len(missing_students),
                "valid_assessments_found": len(valid_assessments),
                "invalid_assessments": list(invalid_assessments),
            },
        )

        return result


class DataQualityValidator:
    """
    Handles data quality and integrity validation.
    Focus: Data quality checks, consistency, potential issues.
    """

    @staticmethod
    def _analyze_missing_data(dataframe: pd.DataFrame, result: ValidationResult):
        missing_data_analysis = {}
        total_rows = len(dataframe)

        for column in dataframe.columns:
            missing_count = dataframe[column].isna().sum()
            if missing_count > 0:
                missing_percentage = (missing_count / total_rows) * 100
                missing_data_analysis[column] = {
                    "missing_count": int(missing_count),
                    "missing_percentage": round(missing_percentage, 2),
                }

                if missing_percentage > 50:
                    result.add_warning(f"Column {column} has {missing_percentage:.1f}% missing data", "data_quality")

        return missing_data_analysis, total_rows

    @staticmethod
    def _add_assignment_score_details(result: ValidationResult, dataframe: pd.DataFrame, assessment_columns, course: Course):
        for column_name, assessment_name in assessment_columns:
            scores = dataframe[column_name].dropna()
            if len(scores) == 0:
                continue

            min_score = scores.min()
            max_score = scores.max()
            avg_score = scores.mean()
            clean_name = BusinessStructureValidator._clean_assessment_name(assessment_name)

            try:
                assessment = Assessment.objects.get(name=clean_name, course=course)
                if max_score > assessment.total_score:
                    result.add_warning(
                        f"Max score ({max_score}) exceeds assessment total ({assessment.total_score}) in {column_name}",
                        "score_validation",
                    )

                result.add_detail(
                    f"score_stats_{column_name}",
                    {
                        "min": float(min_score),
                        "max": float(max_score),
                        "avg": float(avg_score),
                        "assessment_total": assessment.total_score,
                    },
                )
            except Assessment.DoesNotExist:
                continue

    @staticmethod
    def validate_assessment_scores_quality(dataframe: pd.DataFrame, course: Course) -> ValidationResult:
        """
        Validate data quality for assessment scores.

        Args:
            dataframe: Assessment scores data
            course: Course object

        Returns:
            ValidationResult: Validation results
        """
        result = ValidationResult()

        # Check for duplicate student IDs
        student_ids = dataframe.get("student_id", [])
        if len(student_ids) != len(set(student_ids)):
            duplicates = len(student_ids) - len(set(student_ids))
            result.add_warning(f"Found {duplicates} duplicate student IDs", "data_quality")

        # Check score distributions
        score_columns = [col for col in dataframe.columns if "score" in str(col).lower()]

        for col in score_columns:
            scores = dataframe[col].dropna()

            if len(scores) > 0:
                min_score = scores.min()
                max_score = scores.max()
                avg_score = scores.mean()

                # Get assessment total score
                assessment_name = col.replace("_score", "").replace("assessment_", "").strip()
                try:
                    assessment = Assessment.objects.get(name=assessment_name, course=course)
                    if max_score > assessment.total_score:
                        result.add_warning(
                            f"Max score ({max_score}) exceeds assessment total ({assessment.total_score}) in {col}",
                            "score_validation",
                        )

                    # Add score statistics
                    result.add_detail(
                        f"score_stats_{col}",
                        {
                            "min": float(min_score),
                            "max": float(max_score),
                            "avg": float(avg_score),
                            "assessment_total": assessment.total_score,
                        },
                    )
                except Assessment.DoesNotExist:
                    pass  # Already handled in database validation

        # Check for missing data
        missing_data_analysis = {}
        total_rows = len(dataframe)

        for col in dataframe.columns:
            missing_count = dataframe[col].isna().sum()
            if missing_count > 0:
                missing_percentage = (missing_count / total_rows) * 100
                missing_data_analysis[col] = {
                    "missing_count": int(missing_count),
                    "missing_percentage": round(missing_percentage, 2),
                }

                if missing_percentage > 50:
                    result.add_warning(f"Column {col} has {missing_percentage:.1f}% missing data", "data_quality")

        if missing_data_analysis:
            result.add_detail("missing_data_analysis", missing_data_analysis)

        # Data consistency checks
        result.add_detail(
            "data_quality",
            {
                "total_rows": total_rows,
                "duplicate_students_found": len(student_ids) != len(set(student_ids)),
                "score_columns_analyzed": len(score_columns),
                "columns_with_missing_data": len(missing_data_analysis),
            },
        )

        return result

    @staticmethod
    def validate_assignment_scores_quality(dataframe: pd.DataFrame, course: Course) -> ValidationResult:
        """
        Validate data quality for assignment scores (Turkish format).

        Args:
            dataframe: Assignment scores data
            course: Course object

        Returns:
            ValidationResult: Validation results
        """
        result = ValidationResult()

        # Find student ID column
        student_id_col = BusinessStructureValidator._find_student_id_column(dataframe.columns)
        if not student_id_col:
            result.add_error("Student ID column not found", "assignment_scores")
            return result

        # Check for duplicate student IDs
        student_ids = dataframe[student_id_col]
        if len(student_ids) != len(set(student_ids)):
            duplicates = len(student_ids) - len(set(student_ids))
            result.add_warning(f"Found {duplicates} duplicate student IDs", "data_quality")

        assessment_columns = BusinessStructureValidator._extract_assessment_columns(dataframe.columns)
        DataQualityValidator._add_assignment_score_details(result, dataframe, assessment_columns, course)

        missing_data_analysis, total_rows = DataQualityValidator._analyze_missing_data(dataframe, result)

        if missing_data_analysis:
            result.add_detail("missing_data_analysis", missing_data_analysis)

        # Data consistency checks
        result.add_detail(
            "data_quality",
            {
                "total_rows": total_rows,
                "duplicate_students_found": len(student_ids) != len(set(student_ids)),
                "score_columns_analyzed": len(assessment_columns),
                "columns_with_missing_data": len(missing_data_analysis),
            },
        )

        return result


class ValidationPipeline:
    """
    Orchestrates multiple validators to create comprehensive validation.
    """

    def __init__(self, import_type: str):
        self.import_type = import_type
        self.validators = []

    def add_validator(self, validator_class, **kwargs):
        """Add a validator to the pipeline."""
        self.validators.append((validator_class, kwargs))

    @staticmethod
    def _merge_results(target: ValidationResult, source: ValidationResult) -> None:
        if not source.is_valid:
            target.is_valid = False
        target.errors.extend(source.errors)
        target.warnings.extend(source.warnings)
        target.suggestions.extend(source.suggestions)
        target.validation_details.update(source.validation_details)

    def _run_file_format_validation(self, all_kwargs) -> ValidationResult:
        result = FileFormatValidator.validate_file_format(all_kwargs.get("file_obj"), self.import_type)
        if not result.is_valid and "dataframe" in all_kwargs:
            structure_result = FileFormatValidator.validate_dataframe_structure(all_kwargs["dataframe"], self.import_type)
            self._merge_results(result, structure_result)
        return result

    def _run_validator(self, validator_class, all_kwargs) -> ValidationResult:
        if self.import_type != "assignment_scores":
            return ValidationResult()

        if validator_class == FileFormatValidator:
            return self._run_file_format_validation(all_kwargs)
        if validator_class == BusinessStructureValidator:
            return BusinessStructureValidator.validate_assignment_scores_structure(
                all_kwargs["dataframe"], all_kwargs["course"]
            )
        if validator_class == DatabaseIntegrityValidator:
            return DatabaseIntegrityValidator.validate_assignment_scores_database(
                all_kwargs["dataframe"], all_kwargs["course"], all_kwargs["term"]
            )
        if validator_class == DataQualityValidator:
            return DataQualityValidator.validate_assignment_scores_quality(all_kwargs["dataframe"], all_kwargs["course"])
        return ValidationResult()

    def run_validation(self, **kwargs) -> ValidationResult:
        """
        Run all validators in the pipeline.

        Returns:
            ValidationResult: Combined validation results
        """
        final_result = ValidationResult()

        for validator_class, validator_kwargs in self.validators:
            all_kwargs = {**kwargs, **validator_kwargs}
            result = self._run_validator(validator_class, all_kwargs)
            self._merge_results(final_result, result)

        return final_result


class ImportType:
    """Constants for import types."""

    ASSESSMENT_SCORES = "assessment_scores"
    LEARNING_OUTCOMES = "learning_outcomes"
    PROGRAM_OUTCOMES = "program_outcomes"
    ASSIGNMENT_SCORES = "assignment_scores"


class AssignmentScoreValidator:
    """
    Comprehensive validator for Turkish Excel format assignment scores.

    Validates:
    1. File structure: Excel format, max 10MB
    2. Assignment names: Parses and checks against database
    3. Students: Checks if students exist in database
    """

    @staticmethod
    def _base_checks() -> Dict[str, Dict[str, Any]]:
        return {
            "file_structure": {"passed": False},
            "column_structure": {"passed": False},
            "assessment_validation": {"passed": False},
            "student_validation": {"passed": False},
            "score_validation": {"passed": False},
        }

    @staticmethod
    def validate_file_structure(file_obj) -> ValidationResult:
        """
        Validate file is Excel format and under 10MB.

        Args:
            file_obj: Uploaded file object

        Returns:
            ValidationResult: Validation results
        """
        return FileFormatValidator.validate_file_format(file_obj, ImportType.ASSIGNMENT_SCORES)

    @staticmethod
    def validate_assignments(dataframe: pd.DataFrame, course: Course) -> ValidationResult:
        """
        Parse and validate assessment names from columns against database.

        Args:
            dataframe: Parsed Excel data
            course: Course to check assessments against

        Returns:
            ValidationResult: Validation results with found/missing assessments
        """
        result = ValidationResult()

        # Extract assessment columns
        assessment_columns = BusinessStructureValidator._extract_assessment_columns(dataframe.columns)

        if not assessment_columns:
            result.add_error(
                "No assessment score columns found in file. "
                "Expected columns like 'Midterm 1(%25)_XXXXX', "
                "'Project(%40)_XXXXX', etc.",
                "assignment_columns",
            )
            return result

        # Get assessments from database for this course
        db_assessments = Assessment.objects.filter(course=course)
        db_assessment_names = {a.name.lower().strip(): a for a in db_assessments}

        if not db_assessments.exists():
            result.add_error(
                f"No assessments found in database for course {course.code}. Please create assessments first.", "database"
            )
            return result

        # Check each parsed assessment against database
        found_assessments = []
        missing_assessments = []

        for col_name, assessment_name in assessment_columns:
            clean_name = BusinessStructureValidator._clean_assessment_name(assessment_name)
            if clean_name.lower().strip() in db_assessment_names:
                found_assessments.append(
                    {
                        "column": col_name,
                        "parsed_name": clean_name,
                        "db_assessment": db_assessment_names[clean_name.lower().strip()].name,
                    }
                )
            else:
                missing_assessments.append({"column": col_name, "parsed_name": clean_name})

        if missing_assessments:
            missing_names = [m["parsed_name"] for m in missing_assessments]
            result.add_error(f"Assessments not found in database: {', '.join(missing_names)}", "assessment_validation")
            result.add_suggestion(
                f"Available assessments for this course: {', '.join([a.name for a in db_assessments])}",
                "assessment_validation",
            )

        result.add_detail(
            "assessment_validation",
            {
                "total_columns_found": len(assessment_columns),
                "found_assessments": found_assessments,
                "missing_assessments": missing_assessments,
                "available_in_database": [a.name for a in db_assessments],
            },
        )

        return result

    @staticmethod
    def validate_students(dataframe: pd.DataFrame, course: Course) -> ValidationResult:
        """
        Validate that students in file exist in database.

        Args:
            dataframe: Parsed Excel data
            course: Course context

        Returns:
            ValidationResult: Validation results with found/missing students
        """
        result = ValidationResult()

        # Find student ID column
        student_id_col = BusinessStructureValidator._find_student_id_column(dataframe.columns)
        if not student_id_col:
            result.add_error("Student ID column not found. Expected column containing 'öğrenci no' or 'No'", "student_column")
            return result

        # Extract student IDs from file
        file_student_ids = set()
        for student_id in dataframe[student_id_col]:
            if pd.notna(student_id):
                file_student_ids.add(str(student_id).strip())

        if not file_student_ids:
            result.add_error("No student IDs found in file", "student_validation")
            return result

        # Check students in database
        from users.models import StudentProfile

        existing_students = StudentProfile.objects.filter(student_id__in=file_student_ids).values_list("student_id", flat=True)

        existing_set = set(str(sid).strip() for sid in existing_students)
        missing_students = file_student_ids - existing_set
        found_students = file_student_ids & existing_set

        if missing_students:
            result.add_error(f"{len(missing_students)} students not found in database", "student_validation")
            result.add_detail("missing_students", list(missing_students)[:20])  # Show first 20

        result.add_detail(
            "student_validation",
            {
                "total_in_file": len(file_student_ids),
                "found_in_database": len(found_students),
                "missing_from_database": len(missing_students),
                "student_id_column": student_id_col,
            },
        )

        return result

    @staticmethod
    def validate_column_structure(dataframe: pd.DataFrame) -> ValidationResult:
        """
        Phase 2: Validate required columns are present and at least one
        assessment column exists.
        """
        result = ValidationResult()

        required_cols = [
            ("öğrenci no", "Student ID"),
            ("adı", "First Name"),
            ("soyadı", "Last Name"),
        ]

        for col, label in required_cols:
            matched = any(col.lower() == c.lower() for c in dataframe.columns)
            if not matched:
                result.add_error(f"{label} column not found. Expected column '{col}'", "column_structure")

        assessment_cols = BusinessStructureValidator._extract_assessment_columns(dataframe.columns)
        if not assessment_cols:
            result.add_error(
                "No assessment score columns found in file. "
                "Expected columns like 'Midterm 1(%25)_XXXXX', 'Project(%40)_XXXXX', etc.",
                "column_structure",
            )

        if not result.is_valid:
            result.add_detail("column_structure", {"passed": False, "columns_found": dataframe.columns.tolist()})
        else:
            result.add_detail(
                "column_structure", {"passed": True, "columns_found": dataframe.columns.tolist(), "row_count": len(dataframe)}
            )

        return result

    @staticmethod
    def validate_scores(dataframe: pd.DataFrame, course: Course) -> ValidationResult:
        """
        Phase 5: Validate all score values are numeric and within 0-100 (or 0-total_score).
        """
        result = ValidationResult()

        assessment_cols = BusinessStructureValidator._extract_assessment_columns(dataframe.columns)
        if not assessment_cols:
            result.add_detail("score_validation", {"passed": True, "invalid_scores": []})
            return result

        db_assessments = {a.name.lower().strip(): a for a in Assessment.objects.filter(course=course)}

        invalid_scores = []

        for col_name, parsed_name in assessment_cols:
            clean = BusinessStructureValidator._clean_assessment_name(parsed_name)
            db_assessment = db_assessments.get(clean.lower().strip())

            if not db_assessment:
                continue

            max_score = db_assessment.total_score or 100

            for row_idx, value in enumerate(dataframe[col_name]):
                if pd.isna(value):
                    continue
                try:
                    score = float(value)
                    if score < 0 or score > max_score:
                        invalid_scores.append(
                            {
                                "row": row_idx + 2,
                                "column": col_name,
                                "value": str(value),
                                "parsed_name": clean,
                                "max_score": max_score,
                            }
                        )
                except (ValueError, TypeError):
                    invalid_scores.append(
                        {
                            "row": row_idx + 2,
                            "column": col_name,
                            "value": str(value),
                            "parsed_name": clean,
                            "error": "non-numeric",
                        }
                    )

        if invalid_scores:
            sample = invalid_scores[:3]
            sample_values = [s["value"] for s in sample]
            result.add_error(f"Found {len(invalid_scores)} invalid score(s): values {sample_values}", "score_validation")
            result.add_detail("score_validation", {"passed": False, "invalid_scores": invalid_scores[:50]})
        else:
            result.add_detail("score_validation", {"passed": True, "invalid_scores": []})

        return result

    @staticmethod
    def validate_complete(file_obj, course: Course) -> ValidationResult:
        final_result = ValidationResult()
        checks = AssignmentScoreValidator._base_checks()
        final_result.add_detail("checks", checks)
        final_result.add_detail("phase_reached", "file_structure")

        def merge_phase(phase_key: str, result: ValidationResult):
            final_result.errors.extend(result.errors)
            final_result.warnings.extend(result.warnings)
            final_result.suggestions.extend(result.suggestions)
            final_result.validation_details.update(result.validation_details)
            checks[phase_key]["passed"] = result.is_valid
            if not result.is_valid:
                final_result.is_valid = False
                final_result.validation_details["phase_reached"] = phase_key

        file_result = AssignmentScoreValidator.validate_file_structure(file_obj)
        merge_phase("file_structure", file_result)
        if not file_result.is_valid:
            return final_result

        try:
            file_obj.seek(0)
            dataframe = pd.read_excel(file_obj)
            final_result.add_detail("file_parsed", True)
            final_result.add_detail("row_count", len(dataframe))
            final_result.add_detail("columns", dataframe.columns.tolist())
        except Exception as exc:
            final_result.add_error(f"Failed to parse Excel file: {str(exc)}", "file_parse")
            final_result.is_valid = False
            final_result.validation_details["phase_reached"] = "file_structure"
            checks["file_structure"]["passed"] = False
            return final_result

        final_result.validation_details["phase_reached"] = "column_structure"
        column_result = AssignmentScoreValidator.validate_column_structure(dataframe)
        merge_phase("column_structure", column_result)
        if not column_result.is_valid:
            return final_result

        final_result.validation_details["phase_reached"] = "assessment_validation"
        assessment_result = AssignmentScoreValidator.validate_assignments(dataframe, course)
        merge_phase("assessment_validation", assessment_result)

        final_result.validation_details["phase_reached"] = "student_validation"
        student_result = AssignmentScoreValidator.validate_students(dataframe, course)
        merge_phase("student_validation", student_result)

        final_result.validation_details["phase_reached"] = "score_validation"
        score_result = AssignmentScoreValidator.validate_scores(dataframe, course)
        merge_phase("score_validation", score_result)

        if final_result.is_valid:
            final_result.validation_details["phase_reached"] = "complete"

        return final_result
