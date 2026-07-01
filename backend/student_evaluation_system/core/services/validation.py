"""
Validation Services for File Import System.
"""

import re

import pandas as pd
from typing import Dict, Any, Optional

from ..models import Course
from evaluation.models import Assessment, CourseEnrollment
from .column_parsing import (
    extract_assessment_columns,
    clean_assessment_name,
    find_student_id_column,
    find_first_name_column,
    find_last_name_column,
)
from .validators import InputValidator, FileValidator


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

        # Validate file extension
        valid_extensions = [".xlsx", ".xls"] if import_type == "assignment_scores" else [".xlsx", ".xls", ".csv"]

        try:
            InputValidator.validate_file_extension(file_obj.name)
        except Exception:
            result.add_error(f"Invalid file format. Supported formats: {', '.join(valid_extensions)}", "file_format")
            return result

        # Validate file size (10MB limit)
        try:
            FileValidator.validate_file_size(file_obj.size)
        except Exception:
            max_mb = FileValidator.MAX_FILE_SIZE_MB
            result.add_error(
                f"File size exceeds {max_mb}MB limit. Your file is {file_obj.size / (1024 * 1024):.2f}MB",
                "file_size",
            )

        file_extension = file_obj.name.lower().split(".")[-1]
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
    def _normalize_resolution_policy(resolution_policy: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
        policy = resolution_policy or {}
        return {
            "skip_missing_assessments": bool(policy.get("skip_missing_assessments", False)),
            "skip_missing_students": bool(policy.get("skip_missing_students", False)),
            "skip_unenrolled_students": bool(policy.get("skip_unenrolled_students", False)),
            "skip_invalid_scores": bool(policy.get("skip_invalid_scores", False)),
            "clamp_scores": bool(policy.get("clamp_scores", False)),
        }

    @staticmethod
    def normalize_resolution_policy(resolution_policy: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
        """Public helper to normalize resolution policy flags."""
        return AssignmentScoreValidator._normalize_resolution_policy(resolution_policy)

    @staticmethod
    def _build_student_lookups(
        dataframe: pd.DataFrame,
        course: Course,
    ) -> tuple[Dict[str, Any], set[Any], set[str], set[str], str]:
        """Build lookups for student profiles and enrollments.

        Returns:
            Tuple of (profile_lookup, enrolled_ids_set, found_ids_set, missing_ids_set, student_id_col)
        """
        try:
            student_id_col = find_student_id_column(dataframe.columns)
        except ValueError:
            return {}, set(), set(), set(), ""

        file_student_ids = {str(sid).strip() for sid in dataframe[student_id_col] if pd.notna(sid)}

        from users.models import StudentProfile

        student_profiles = StudentProfile.objects.filter(student_id__in=file_student_ids).select_related("user")
        profile_by_student_id = {str(p.student_id).strip(): p for p in student_profiles}
        found_ids = set(profile_by_student_id.keys())
        missing_ids = file_student_ids - found_ids

        enrolled_ids: set[Any] = set()
        if found_ids:
            user_ids = [p.user.pk for p in student_profiles]
            enrolled_ids = set(
                CourseEnrollment.objects.filter(course=course, student_id__in=user_ids).values_list("student_id", flat=True)
            )

        return profile_by_student_id, enrolled_ids, found_ids, missing_ids, student_id_col

    @staticmethod
    def _filter_rows_by_policy(
        dataframe: pd.DataFrame,
        student_id_col: str,
        profile_lookup: Dict[str, Any],
        enrolled_ids: set,
        missing_ids: set,
        policy: Dict[str, bool],
    ) -> tuple[pd.DataFrame, Dict[str, int]]:
        """Filter rows based on student-level policy rules."""
        keep_rows = []
        dropped_missing = 0
        dropped_unenrolled = 0

        for student_id in dataframe[student_id_col]:
            if pd.isna(student_id):
                keep_rows.append(True)
                continue

            sid = str(student_id).strip()

            if sid in missing_ids and policy.get("skip_missing_students"):
                dropped_missing += 1
                keep_rows.append(False)
                continue

            profile = profile_lookup.get(sid)
            if profile and profile.user.pk not in enrolled_ids and policy.get("skip_unenrolled_students"):
                dropped_unenrolled += 1
                keep_rows.append(False)
                continue

            keep_rows.append(True)

        filtered_df = dataframe[keep_rows].reset_index(drop=True)
        return filtered_df, {"missing": dropped_missing, "unenrolled": dropped_unenrolled}

    @staticmethod
    def _apply_score_policies(
        dataframe: pd.DataFrame,
        course: Course,
        policy: Dict[str, bool],
    ) -> Dict[str, int]:
        """Apply score-level policy rules to assessment columns."""
        effects = {"clamped": 0, "skipped": 0}

        assessment_cols = extract_assessment_columns(dataframe.columns)
        db_assessments = {a.name.lower().strip(): a for a in Assessment.objects.filter(course=course)}

        for col_name, parsed_name in assessment_cols:
            clean_name = clean_assessment_name(parsed_name)
            db_assessment = db_assessments.get(clean_name.lower().strip())
            if not db_assessment:
                continue

            max_score = db_assessment.total_score or 100
            AssignmentScoreValidator._apply_score_policy_to_column(dataframe, col_name, max_score, policy, effects)

        return effects

    @staticmethod
    def _apply_score_policy_to_column(
        dataframe: pd.DataFrame,
        col_name: str,
        max_score: float,
        policy: Dict[str, bool],
        effects: Dict[str, int],
    ) -> None:
        """Apply score policy to a single assessment column."""
        for row_idx in range(len(dataframe)):
            value = dataframe.at[row_idx, col_name]
            if pd.isna(value):
                continue

            try:
                numeric_value = float(value)  # type: ignore[arg-type]
            except (ValueError, TypeError):
                if policy.get("skip_invalid_scores"):
                    dataframe.at[row_idx, col_name] = pd.NA
                    effects["skipped"] += 1
                continue

            is_out_of_range = numeric_value < 0 or numeric_value > max_score

            if policy.get("clamp_scores") and is_out_of_range:
                dataframe.at[row_idx, col_name] = max(0.0, min(float(max_score), numeric_value))
                effects["clamped"] += 1
            elif policy.get("skip_invalid_scores") and is_out_of_range:
                dataframe.at[row_idx, col_name] = pd.NA
                effects["skipped"] += 1

    @staticmethod
    def _apply_resolution_policy_to_dataframe(
        dataframe: pd.DataFrame,
        course: Course,
        policy: Dict[str, bool],
    ) -> tuple[pd.DataFrame, Dict[str, Any]]:
        transformed = dataframe.copy()
        effects = {
            "rows_before": len(transformed),
            "rows_dropped_missing_students": 0,
            "rows_dropped_unenrolled_students": 0,
            "scores_clamped": 0,
            "scores_skipped": 0,
        }

        # Build student lookups
        profile_lookup, enrolled_ids, found_ids, missing_ids, student_id_col = AssignmentScoreValidator._build_student_lookups(
            transformed, course
        )

        if not student_id_col:
            effects["rows_after"] = len(transformed)
            return transformed, effects

        # Filter rows based on student policy
        transformed, row_effects = AssignmentScoreValidator._filter_rows_by_policy(
            transformed, student_id_col, profile_lookup, enrolled_ids, missing_ids, policy
        )
        effects["rows_dropped_missing_students"] = row_effects["missing"]
        effects["rows_dropped_unenrolled_students"] = row_effects["unenrolled"]

        # Apply score policies
        score_effects = AssignmentScoreValidator._apply_score_policies(transformed, course, policy)
        effects["scores_clamped"] = score_effects["clamped"]
        effects["scores_skipped"] = score_effects["skipped"]

        effects["rows_after"] = len(transformed)
        return transformed, effects

    @staticmethod
    def apply_resolution_policy_to_dataframe(
        dataframe: pd.DataFrame,
        course: Course,
        resolution_policy: Optional[Dict[str, Any]] = None,
    ) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """Public helper used by resolve/upload paths to keep transformation behavior consistent."""
        policy = AssignmentScoreValidator._normalize_resolution_policy(resolution_policy)
        return AssignmentScoreValidator._apply_resolution_policy_to_dataframe(dataframe, course, policy)

    @staticmethod
    def validate_file_structure(file_obj) -> ValidationResult:
        """
        Validate file is Excel format and under 10MB.

        Args:
            file_obj: Uploaded file object

        Returns:
            ValidationResult: Validation results
        """
        return FileFormatValidator.validate_file_format(file_obj, "assignment_scores")

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
        assessment_columns = extract_assessment_columns(dataframe.columns)

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
            clean_name = clean_assessment_name(assessment_name)
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
    def _find_optional_name_columns(dataframe: pd.DataFrame) -> tuple[Optional[str], Optional[str]]:
        first_name_col: Optional[str] = None
        last_name_col: Optional[str] = None

        try:
            first_name_col = find_first_name_column(dataframe.columns)
        except ValueError:
            pass

        try:
            last_name_col = find_last_name_column(dataframe.columns)
        except ValueError:
            pass

        return first_name_col, last_name_col

    @staticmethod
    def _extract_student_ids_and_names(
        dataframe: pd.DataFrame,
        student_id_col: str,
        first_name_col: Optional[str],
        last_name_col: Optional[str],
    ) -> tuple[set[str], Dict[str, Dict[str, str]]]:
        file_student_ids: set[str] = set()
        student_names: Dict[str, Dict[str, str]] = {}

        for idx, student_id in enumerate(dataframe[student_id_col]):
            if pd.isna(student_id):
                continue

            sid = str(student_id).strip()
            file_student_ids.add(sid)

            first_name = ""
            last_name = ""

            if first_name_col is not None:
                first_name_value = dataframe.iloc[idx][first_name_col]
                if pd.notna(first_name_value):
                    first_name = str(first_name_value).strip()

            if last_name_col is not None:
                last_name_value = dataframe.iloc[idx][last_name_col]
                if pd.notna(last_name_value):
                    last_name = str(last_name_value).strip()

            student_names[sid] = {"first_name": first_name, "last_name": last_name}

        return file_student_ids, student_names

    @staticmethod
    def _collect_not_enrolled_students(student_profiles, course: Course) -> list[Dict[str, str]]:
        if not student_profiles:
            return []

        user_ids = [profile.user.pk for profile in student_profiles]
        enrolled_user_ids = set(
            CourseEnrollment.objects.filter(course=course, student_id__in=user_ids).values_list("student_id", flat=True)
        )

        not_enrolled: list[Dict[str, str]] = []
        for profile in student_profiles:
            if profile.user.pk not in enrolled_user_ids:
                not_enrolled.append(
                    {
                        "student_id": str(profile.student_id),
                        "first_name": profile.user.first_name or "",
                        "last_name": profile.user.last_name or "",
                    }
                )

        return not_enrolled

    @staticmethod
    def _build_missing_from_database(
        missing_students: set[str],
        student_names: Dict[str, Dict[str, str]],
    ) -> list[Dict[str, str]]:
        missing_from_database: list[Dict[str, str]] = []

        for sid in sorted(missing_students):
            names = student_names.get(sid, {})
            missing_from_database.append(
                {
                    "student_id": sid,
                    "first_name": names.get("first_name", ""),
                    "last_name": names.get("last_name", ""),
                }
            )

        return missing_from_database

    @staticmethod
    def validate_students(dataframe: pd.DataFrame, course: Course) -> ValidationResult:
        """
        Validate that students in file exist in database and are enrolled in course.

        Args:
            dataframe: Parsed Excel data
            course: Course context

        Returns:
            ValidationResult: Validation results with found/missing students
        """
        result = ValidationResult()

        try:
            student_id_col = find_student_id_column(dataframe.columns)
        except ValueError:
            result.add_error("Student ID column not found. Expected column containing 'öğrenci no' or 'No'", "student_column")
            return result

        first_name_col, last_name_col = AssignmentScoreValidator._find_optional_name_columns(dataframe)
        file_student_ids, student_names = AssignmentScoreValidator._extract_student_ids_and_names(
            dataframe,
            student_id_col,
            first_name_col,
            last_name_col,
        )

        if not file_student_ids:
            result.add_error("No student IDs found in file", "student_validation")
            return result

        from users.models import StudentProfile

        student_profiles = StudentProfile.objects.filter(student_id__in=file_student_ids).select_related("user")
        existing_students = [profile.student_id for profile in student_profiles]

        existing_set = set(str(sid).strip() for sid in existing_students)
        missing_students = file_student_ids - existing_set
        found_students = file_student_ids & existing_set

        not_enrolled: list[Dict[str, str]] = []
        if found_students:
            found_profiles = [profile for profile in student_profiles if str(profile.student_id).strip() in found_students]
            not_enrolled = AssignmentScoreValidator._collect_not_enrolled_students(
                found_profiles,
                course,
            )

        missing_from_database: list[Dict[str, str]] = []
        if missing_students:
            missing_from_database = AssignmentScoreValidator._build_missing_from_database(
                missing_students,
                student_names,
            )
            result.add_error(f"{len(missing_students)} students not found in database", "student_validation")
            result.add_detail("missing_students", missing_from_database[:20])

        if not_enrolled:
            sample_ids = [student["student_id"] for student in not_enrolled[:20]]
            result.add_error(
                f"The following students are not enrolled in course {course.code}: {', '.join(sample_ids)}",
                "student_validation",
            )

        result.add_detail(
            "student_validation",
            {
                "total_in_file": len(file_student_ids),
                "found_in_database": len(found_students),
                "missing_from_database": missing_from_database,
                "not_enrolled": not_enrolled,
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

        def matches_required_column(required_column: str, dataframe_column: str) -> bool:
            required_tokens = re.findall(r"[a-z0-9ğüşıöç]+", required_column.lower())
            dataframe_tokens = re.findall(r"[a-z0-9ğüşıöç]+", dataframe_column.lower())

            if not required_tokens or not dataframe_tokens:
                return False

            if len(dataframe_tokens) < len(required_tokens):
                return False

            return dataframe_tokens[: len(required_tokens)] == required_tokens

        required_cols = [
            ("öğrenci no", "Student ID"),
            ("adı", "First Name"),
            ("soyadı", "Last Name"),
        ]

        for col, label in required_cols:
            matched = any(matches_required_column(col, str(c)) for c in dataframe.columns)
            if not matched:
                result.add_error(f"{label} column not found. Expected column '{col}'", "column_structure")

        assessment_cols = extract_assessment_columns(dataframe.columns)
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

        assessment_cols = extract_assessment_columns(dataframe.columns)
        if not assessment_cols:
            result.add_detail("score_validation", {"passed": True, "invalid_scores": []})
            return result

        db_assessments = {a.name.lower().strip(): a for a in Assessment.objects.filter(course=course)}

        invalid_scores = []

        for col_name, parsed_name in assessment_cols:
            clean = clean_assessment_name(parsed_name)
            db_assessment = db_assessments.get(clean.lower().strip())

            if not db_assessment:
                continue

            max_score = db_assessment.total_score or 100

            for row_idx, value in enumerate(dataframe[col_name]):
                if pd.isna(value):
                    continue
                try:
                    score = float(value)  # type: ignore[arg-type]
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
    def validate_complete(file_obj, course: Course, resolution_policy: Optional[Dict[str, Any]] = None) -> ValidationResult:
        final_result = ValidationResult()
        checks = AssignmentScoreValidator._base_checks()
        policy = AssignmentScoreValidator._normalize_resolution_policy(resolution_policy)
        final_result.add_detail("checks", checks)
        final_result.add_detail("phase_reached", "file_structure")
        final_result.add_detail("resolution_policy", policy)

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

        transformed_dataframe, policy_effects = AssignmentScoreValidator._apply_resolution_policy_to_dataframe(
            dataframe,
            course,
            policy,
        )
        final_result.add_detail("policy_effects", policy_effects)

        final_result.validation_details["phase_reached"] = "assessment_validation"
        assessment_result = AssignmentScoreValidator.validate_assignments(transformed_dataframe, course)
        if policy.get("skip_missing_assessments") and not assessment_result.is_valid:
            remaining_errors = [err for err in assessment_result.errors if err.get("category") != "assessment_validation"]
            assessment_result.errors = remaining_errors
            assessment_result.is_valid = len(remaining_errors) == 0
        merge_phase("assessment_validation", assessment_result)

        final_result.validation_details["phase_reached"] = "student_validation"
        student_result = AssignmentScoreValidator.validate_students(transformed_dataframe, course)
        merge_phase("student_validation", student_result)

        final_result.validation_details["phase_reached"] = "score_validation"
        score_result = AssignmentScoreValidator.validate_scores(transformed_dataframe, course)
        merge_phase("score_validation", score_result)

        if final_result.is_valid:
            final_result.validation_details["phase_reached"] = "complete"

        return final_result
