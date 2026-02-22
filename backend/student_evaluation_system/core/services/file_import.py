"""
File Import Service for Student Evaluation System

This service handles server-side processing of various file formats for bulk data import.
It validates file format, parses data, and creates database records.

Supported import types:
- Students
- Courses
- Assessments
- Student Grades
- Learning Outcomes
- Program Outcomes
- Assignment Scores (Turkish Excel format)

Supported file formats:
- Excel (.xlsx, .xls) - Current implementation
- CSV (.csv) - Future extension
- JSON (.json) - Future extension
"""

import pandas as pd
import re
from django.db import transaction
from django.contrib.auth import get_user_model
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any

from ..models import Program, Term, Course, LearningOutcome, ProgramOutcome
from evaluation.models import Assessment, StudentGrade, CourseEnrollment
from evaluation.services import calculate_course_scores
from .validators import InputValidator, FileValidator, ValidationError as CustomValidationError

User = get_user_model()
logger = logging.getLogger(__name__)


class FileImportError(Exception):
    """Custom exception for file import errors."""

    pass


class FileParser(ABC):
    """
    Abstract base class for file parsers.

    This allows for modular extension to support different file formats.
    Each parser implements specific logic for reading its file type.
    """

    @abstractmethod
    def validate_file(self, file_obj) -> bool:
        """
        Validate if the file can be parsed by this parser.

        Args:
            file_obj: Uploaded file object

        Returns:
            bool: True if file is valid for this parser
        """
        pass

    @abstractmethod
    def get_sheet_names(self, file_obj) -> List[str]:
        """
        Get list of available sheets/data sections in file.

        Args:
            file_obj: Uploaded file object

        Returns:
            List[str]: Available sheet/section names
        """
        pass

    @abstractmethod
    def parse_sheet(self, file_obj, sheet_name: str) -> pd.DataFrame:
        """
        Parse a specific sheet/section from the file.

        Args:
            file_obj: Uploaded file object
            sheet_name (str): Name of sheet/section to parse

        Returns:
            pd.DataFrame: Parsed data
        """
        pass


class ExcelParser(FileParser):
    """Parser for Excel files (.xlsx, .xls)."""

    def validate_file(self, file_obj) -> bool:
        """Validate Excel file format."""
        # Validate file extension
        try:
            InputValidator.validate_file_extension(file_obj.name)
        except CustomValidationError as e:
            raise FileImportError(str(e))

        # Validate file size
        try:
            FileValidator.validate_file_size(file_obj.size)
        except CustomValidationError as e:
            raise FileImportError(str(e))

        if file_obj.size == 0:
            raise FileImportError("File is empty")

        return True

    def get_sheet_names(self, file_obj) -> List[str]:
        """Get Excel sheet names."""
        try:
            workbook = pd.ExcelFile(file_obj)
            return workbook.sheet_names
        except Exception as e:
            raise FileImportError(f"Error reading Excel file: {str(e)}")

    def _get_dtype_mapping(self, import_type: str) -> Dict[str, Any]:
        """
        Get appropriate dtype mapping for import type.

        Args:
            import_type: Type of data being imported

        Returns:
            Dict mapping column names to pandas dtypes
        """
        dtype_mappings = {
            "assignment_scores": {
                # Preserve leading zeros in student IDs
                # Let Pandas infer score columns (dynamic names)
            },
            "learning_outcomes": {"code": "str", "description": "str", "course_code": "str"},
            "program_outcomes": {"code": "str", "description": "str", "program_code": "str", "term_name": "str"},
        }

        return dtype_mappings.get(import_type, {})

    def parse_sheet(self, file_obj, import_type: str = None) -> pd.DataFrame:
        """
        Parse Excel sheet with proper dtype specifications.

        Args:
            file_obj: Excel file object
            import_type: Type hint for column interpretation

        Returns:
            DataFrame with properly typed columns
        """
        try:
            workbook = pd.ExcelFile(file_obj)

            # Get dtype mapping for this import type
            dtype_map = self._get_dtype_mapping(import_type) if import_type else {}

            # Read with explicit dtypes and nullable backend
            df = pd.read_excel(
                workbook,
                dtype=dtype_map if dtype_map else None,
                dtype_backend="numpy_nullable",  # Better null handling
                na_values=["", "NA", "N/A", "null", "NULL", "-"],  # Standard null values
            )

            return df
        except Exception as e:
            raise FileImportError(f"Error parsing file: {str(e)}")


class CSVParser(FileParser):
    """Parser for CSV files - Future implementation."""

    def validate_file(self, file_obj) -> bool:
        """Validate CSV file format."""
        # Validate file extension
        try:
            InputValidator.validate_file_extension(file_obj.name)
        except CustomValidationError as e:
            raise FileImportError(str(e))

        # Validate file size
        try:
            FileValidator.validate_file_size(file_obj.size)
        except CustomValidationError as e:
            raise FileImportError(str(e))

        return True

    def get_sheet_names(self, file_obj) -> List[str]:
        """CSV files have single sheet."""
        return ["data"]

    def parse_sheet(self, file_obj, sheet_name: str = None, import_type: str = None) -> pd.DataFrame:
        """Parse CSV into DataFrame with proper dtypes."""
        try:
            return pd.read_csv(file_obj, dtype_backend="numpy_nullable", na_values=["", "NA", "N/A", "null", "NULL", "-"])
        except Exception as e:
            raise FileImportError(f"Error parsing CSV file: {str(e)}")


class FileImportService:
    """
    Main service for handling file imports.

    This service coordinates file parsing, validation, and database operations.
    It uses a modular parser system to support multiple file formats.
    """

    # Expected column mappings for different data types
    REQUIRED_COLUMNS = {
        "learning_outcomes": ["code", "description", "course_code"],
        "program_outcomes": ["code", "description", "program_code", "term_name"],
        "assignment_scores": ["öğrenci no", "adı", "soyadı"],
    }

    # Available parsers for different file formats
    PARSERS = {"excel": ExcelParser, "csv": CSVParser}

    def __init__(self, file_obj):
        """
        Initialize service with an uploaded file.

        Args:
            file_obj: Uploaded file object containing data
        """
        self.file_obj = file_obj
        self.parser = None
        self.import_results = {"created": {}, "updated": {}, "errors": []}

    def detect_file_format(self) -> str:
        """
        Detect the file format and return appropriate parser name.

        Returns:
            str: Parser name ('excel', 'csv', etc.)
        """
        file_extension = self.file_obj.name.lower().split(".")[-1]

        if file_extension in ["xlsx", "xls"]:
            return "excel"
        elif file_extension == "csv":
            return "csv"
        else:
            raise FileImportError(f"Unsupported file format: {file_extension}")

    def validate_file(self) -> bool:
        """
        Validate uploaded file format and structure.

        Returns:
            bool: True if file is valid

        Raises:
            FileImportError: If file format is invalid
        """
        try:
            # Detect file format
            parser_name = self.detect_file_format()

            # Get appropriate parser
            parser_class = self.PARSERS.get(parser_name)
            if not parser_class:
                raise FileImportError(f"No parser available for format: {parser_name}")

            self.parser = parser_class()

            # Validate file with parser
            return self.parser.validate_file(self.file_obj)

        except Exception as e:
            if isinstance(e, FileImportError):
                raise
            raise FileImportError(f"Invalid file: {str(e)}")

    def import_assignment_scores(self, course_code: str, term_id: int):
        """
        Import assignment scores from Turkish Excel format.

        Args:
            course_code (str): Code of the course for which grades are being imported
            term_id (int): ID of the academic term for which grades are being imported

        Returns:
            dict: Import results with created/updated counts
        """
        try:
            course_code, term_id = self._validate_assignment_import_params(course_code, term_id)
            (
                df,
                course,
                course_assessments,
                assessment_lookup,
                student_id_col,
                assessment_columns,
            ) = self._prepare_assignment_import_context(course_code, term_id)

            created_count = 0
            updated_count = 0
            skipped_count = 0
            affected_courses = set()

            with transaction.atomic():
                for idx, row in df.iterrows():
                    try:
                        row_created, row_updated, row_skipped = self._process_assignment_row(
                            row=row,
                            row_number=idx + 2,
                            student_id_col=student_id_col,
                            assessment_columns=assessment_columns,
                            assessment_lookup=assessment_lookup,
                            affected_courses=affected_courses,
                        )
                        created_count += row_created
                        updated_count += row_updated
                        skipped_count += row_skipped
                    except Exception as e:
                        self.import_results["errors"].append(f"Row {idx + 2}: Error processing row - {str(e)}")
                        continue

            self.import_results["created"]["grades"] = created_count
            self.import_results["updated"]["grades"] = updated_count
            self.import_results["skipped"] = skipped_count
            self.import_results["total_rows"] = len(df)

            self._recalculate_affected_courses(affected_courses)
            return self.import_results

        except Exception as e:
            if isinstance(e, FileImportError):
                raise
            raise FileImportError(f"Error importing assignment scores: {str(e)}")

    def _validate_assignment_import_params(self, course_code: str, term_id: int):
        try:
            validated_course_code = InputValidator.validate_course_code(course_code)
            validated_term_id = int(term_id)
            if validated_term_id <= 0:
                raise ValueError("Term ID must be positive")
            return validated_course_code, validated_term_id
        except (ValueError, CustomValidationError) as e:
            raise FileImportError(f"Invalid input parameters: {str(e)}")

    def _find_missing_assessments(self, assessment_columns, assessment_lookup):
        missing_assessments = []
        for _, assessment_name in assessment_columns:
            clean_name = self._clean_assessment_name(assessment_name)
            if clean_name.lower().strip() not in assessment_lookup:
                missing_assessments.append(clean_name)
        return missing_assessments

    def _prepare_assignment_import_context(self, course_code: str, term_id: int):
        df = self.parser.parse_sheet(self.file_obj, import_type="assignment_scores")
        course = self._get_course_by_code_and_term(course_code, term_id)

        course_assessments = Assessment.objects.filter(course=course)
        assessment_lookup = {assessment.name.lower().strip(): assessment for assessment in course_assessments}

        if not course_assessments.exists():
            raise FileImportError(f"No assessments found for course {course.code}. Please create assessments first.")

        self._validate_assignment_scores(df, course, course.term)

        student_id_col = self._find_student_id_column(df.columns)
        assessment_columns = self._extract_assessment_columns(df.columns)
        if not assessment_columns:
            raise FileImportError("No assessment score columns found in file")

        missing_assessments = self._find_missing_assessments(assessment_columns, assessment_lookup)
        if missing_assessments:
            available = ", ".join([assessment.name for assessment in course_assessments])
            raise FileImportError(
                f"Assessments not found in database: {', '.join(missing_assessments)}. Available assessments: {available}"
            )

        return df, course, course_assessments, assessment_lookup, student_id_col, assessment_columns

    def _process_assignment_row(
        self,
        row,
        row_number: int,
        student_id_col,
        assessment_columns,
        assessment_lookup,
        affected_courses,
    ):
        created_count = 0
        updated_count = 0
        skipped_count = 0

        raw_student_id = str(row[student_id_col]).strip()
        if not raw_student_id or raw_student_id.lower() == "nan":
            return created_count, updated_count, skipped_count + 1

        try:
            student_id = InputValidator.validate_student_id(raw_student_id)
        except CustomValidationError as e:
            self.import_results["errors"].append(f"Row {row_number}: Invalid student ID '{raw_student_id}': {str(e)}")
            return created_count, updated_count, skipped_count

        try:
            student_user = self._get_student_by_id(student_id)
        except FileImportError:
            self.import_results["errors"].append(f"Row {row_number}: Student '{student_id}' not found in database")
            return created_count, updated_count, skipped_count

        for col_name, assessment_name in assessment_columns:
            score = row[col_name]
            if pd.notna(score):
                try:
                    clean_name = self._clean_assessment_name(assessment_name)
                    assessment = assessment_lookup[clean_name.lower().strip()]

                    try:
                        score_float = InputValidator.validate_score(score, max_score=assessment.total_score)
                    except CustomValidationError as e:
                        self.import_results["errors"].append(f"Row {row_number}: {str(e)} for {clean_name}")
                        continue

                    _, created = StudentGrade.objects.update_or_create(
                        student=student_user,
                        assessment=assessment,
                        defaults={"score": score_float},
                    )

                    affected_courses.add(assessment.course_id)

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except (ValueError, TypeError):
                    self.import_results["errors"].append(f"Row {row_number}: Invalid score '{score}' for {assessment_name}")
                    continue

        return created_count, updated_count, skipped_count

    def _recalculate_affected_courses(self, affected_courses):
        for course_id in affected_courses:
            try:
                calculate_course_scores(course_id)
                logger.info(f"Recalculated scores for course {course_id} after import")
            except Exception as e:
                logger.error(f"Failed to recalculate scores for course {course_id}: {e}")
                self.import_results["errors"].append(f"Score recalculation failed for course {course_id}: {str(e)}")

    def import_learning_outcomes(self, sheet_name: str = "learning_outcomes"):
        """
        Import learning outcome data from file sheet/section.

        Args:
            sheet_name (str): Name of sheet/section containing learning outcome data

        Returns:
            dict: Import results with created/updated counts
        """
        try:
            df = self.parser.parse_sheet(self.file_obj, import_type="learning_outcomes")

            # Validate required columns
            self._validate_required_columns(df, "learning_outcomes")

            created_count = 0
            updated_count = 0

            with transaction.atomic():
                for _, row in df.iterrows():
                    try:
                        # Get course
                        course = self._get_course_by_code(str(row["course_code"]).strip())

                        # Clean data
                        code = str(row["code"]).strip().upper()
                        description = str(row["description"]).strip()

                        # Create or update learning outcome
                        lo, created = LearningOutcome.objects.get_or_create(
                            code=code, course=course, defaults={"description": description}
                        )

                        if not created:
                            # Update existing learning outcome
                            lo.description = description
                            lo.save()
                            updated_count += 1
                        else:
                            created_count += 1

                    except Exception as e:
                        self.import_results["errors"].append(
                            f"Error importing learning outcome {row.get('code', 'unknown')}: {str(e)}"
                        )
                        continue

            self.import_results["created"]["learning_outcomes"] = created_count
            self.import_results["updated"]["learning_outcomes"] = updated_count

            return self.import_results

        except Exception as e:
            raise FileImportError(f"Error importing learning outcomes: {str(e)}")

    def import_program_outcomes(self, sheet_name: str = "program_outcomes"):
        """
        Import program outcome data from file sheet/section.

        Args:
            sheet_name (str): Name of sheet/section containing program outcome data

        Returns:
            dict: Import results with created/updated counts
        """
        try:
            df = self.parser.parse_sheet(self.file_obj, import_type="program_outcomes")

            # Validate required columns
            self._validate_required_columns(df, "program_outcomes")

            created_count = 0
            updated_count = 0

            with transaction.atomic():
                for _, row in df.iterrows():
                    try:
                        # Get related objects
                        program = self._get_program_by_code(str(row["program_code"]).strip())
                        term = self._get_term_by_name(str(row["term_name"]).strip())

                        # Clean data
                        code = str(row["code"]).strip().upper()
                        description = str(row["description"]).strip()

                        # Create or update program outcome
                        po, created = ProgramOutcome.objects.get_or_create(
                            code=code, program=program, term=term, defaults={"description": description}
                        )

                        if not created:
                            # Update existing program outcome
                            po.description = description
                            po.save()
                            updated_count += 1
                        else:
                            created_count += 1

                    except Exception as e:
                        self.import_results["errors"].append(
                            f"Error importing program outcome {row.get('code', 'unknown')}: {str(e)}"
                        )
                        continue

            self.import_results["created"]["program_outcomes"] = created_count
            self.import_results["updated"]["program_outcomes"] = updated_count

            return self.import_results

        except Exception as e:
            raise FileImportError(f"Error importing program outcomes: {str(e)}")

    def _extract_assessment_columns(self, columns):
        """
        Extract assessment columns from Excel format.

        Column format examples:
        - 'Midterm 1(%25)_XXX' -> 'Midterm 1'
        - 'Project(%40)_XXX' -> 'Project'
        - 'Attendance(%10)_XXX' -> 'Attendance'

        We only look at the first word/part before any suffix like _XXX.
        Non-assessment columns are: No, Öğrenci No, Adı, Soyadı, Snf, Girme Durum, Harf Notu
        """
        assessment_columns = []

        # Known non-assessment column prefixes (case-insensitive)
        non_assessment_prefixes = ["no", "öğrenci no", "adı", "soyadı", "snf", "girme durum", "harf notu"]

        for col in columns:
            # Sanitize column name
            col_str = InputValidator.sanitize_column_name(str(col))

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

    def _clean_assessment_name(self, name):
        """Clean assessment name by removing weight information."""
        # Remove weight patterns like "(%25)", "(%40)", etc.
        cleaned = re.sub(r"\(%\d+\)", "", name).strip()
        return cleaned

    def _find_student_id_column(self, columns):
        """Find the student ID column from Turkish column names."""
        for col in columns:
            col_str = str(col).lower().strip()
            if "öğrenci no" in col_str:
                return col
        raise FileImportError("Student ID column not found. Expected columns containing 'öğrenci no'")

    def _validate_assignment_scores(self, dataframe: pd.DataFrame, course: Course, term: Term):
        """
        Validate that all required columns are present in dataframe for assessment scores.

        Args:
            dataframe (pd.DataFrame): Data to validate
            course (Course): Course to check assessments against
            term (Term): Term to check assessments against
        Raises:
            FileImportError: If required columns are missing
        """
        try:
            self._validate_required_columns(
                dataframe, "assignment_scores", assessments=self._get_assessments_by_course(course)
            )
            self._validate_students(dataframe, course)
        except Exception as e:
            raise FileImportError(f"Validation error: {str(e)}")

    def _validate_required_columns(self, dataframe: pd.DataFrame, sheet_type: str, assessments: List[Assessment] = None):
        """
        Validate that all required columns are present in dataframe.

        Args:
            dataframe (pd.DataFrame): Data to validate
            sheet_type (str): Type of sheet to validate against
            assessments (List[Assessment], optional): List of assessments to validate against
        Raises:
            FileImportError: If required columns are missing
        """
        required_columns = self.REQUIRED_COLUMNS.get(sheet_type, [])
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

        # Check for assessment names if applicable
        if assessments:
            # Use _extract_assessment_columns to get cleaned assessment names from columns
            assessment_columns = self._extract_assessment_columns(dataframe.columns)
            found_assessment_names = [name for _, name in assessment_columns]

            assessment_col_found = []
            for assessment in assessments:
                # Check if assessment name is in the found assessment columns
                if assessment.name.lower().strip() in [name.lower().strip() for name in found_assessment_names]:
                    assessment_col_found.append(True)
                else:
                    assessment_col_found.append(False)

            if not all(assessment_col_found):
                missing_columns.extend([assessments[i].name for i, found in enumerate(assessment_col_found) if not found])

        if missing_columns:
            raise FileImportError(
                f"Missing required columns for {sheet_type}: {', '.join(missing_columns)}. "
                f"Found columns: {', '.join(dataframe.columns.tolist())}"
            )

    def _validate_students(self, dataframe: pd.DataFrame, course: Course):
        """
        Validate that all students in the dataframe are enrolled in the course.

        Args:
            dataframe (pd.DataFrame): Data to validate
            course (Course): Course to check enrollments against

        Raises:
            FileImportError: If any student is not enrolled in the course
        """
        student_id_col = self._find_student_id_column(dataframe.columns)

        student_ids = [str(sid).strip() for sid in dataframe[student_id_col]]
        enrolled_students = CourseEnrollment.objects.filter(
            course=course, student__student_profile__student_id__in=student_ids
        ).values_list("student__student_profile__student_id", flat=True)

        enrolled_student_ids = set(str(sid).strip() for sid in enrolled_students)
        missing_students = [sid for sid in student_ids if sid not in enrolled_student_ids]

        if missing_students:
            raise FileImportError(
                f"The following students are not enrolled in course {course.code}: {', '.join(missing_students)}"
            )

    def _validate_assignment_students(self, dataframe: pd.DataFrame, course: Course):
        """
        Validate that all students in the assignment dataframe are enrolled in the course.

        Args:
            dataframe (pd.DataFrame): Data to validate
            course (Course): Course to check enrollments against

        Raises:
            FileImportError: If any student is not enrolled in the course
        """
        student_id_col = self._find_student_id_column(dataframe.columns)
        student_ids = [str(sid).strip() for sid in dataframe[student_id_col].tolist()]
        enrolled_students = CourseEnrollment.objects.filter(
            course=course, student__student_profile__student_id__in=student_ids
        ).values_list("student__student_profile__student_id", flat=True)

        enrolled_student_ids = set(str(sid).strip() for sid in enrolled_students)
        missing_students = [sid for sid in student_ids if sid not in enrolled_student_ids]

        if missing_students:
            raise FileImportError(
                f"The following students are not enrolled in course {course.code}: {', '.join(missing_students)}"
            )

    def _get_program_by_code(self, code: str):
        """Get program by code, raise error if not found."""
        try:
            return Program.objects.get(code=code)
        except Program.DoesNotExist:
            raise FileImportError(f"Program with code '{code}' not found")

    def _get_term_by_name(self, name: str):
        """Get term by name, create if doesn't exist."""
        term, created = Term.objects.get_or_create(name=name, defaults={"is_active": False})
        return term

    def _get_course_by_code(self, code: str):
        """Get course by code, raise error if not found."""
        try:
            return Course.objects.get(code=code)
        except Course.DoesNotExist:
            raise FileImportError(f"Course with code '{code}' not found")

    def _get_course_by_code_and_term(self, course_code: str, term_id: int):
        """
        Get course by code and term with proper error handling.

        Args:
            course_code (str): Course code
            term_id (int): Term ID

        Returns:
            Course: Course object

        Raises:
            FileImportError: If course not found
        """
        try:
            return Course.objects.get(code=course_code, term_id=term_id)
        except Course.DoesNotExist:
            # Check if course exists with different terms
            available_courses = Course.objects.filter(code=course_code).select_related("term")
            if available_courses.exists():
                terms = [f"{course.code} ({course.term.name})" for course in available_courses]
                raise FileImportError(
                    f"Course with code '{course_code}' found but not for specified term. "
                    f"Available terms: {', '.join(terms)}. "
                    f"Please check the term_id parameter."
                )
            else:
                raise FileImportError(f"Course with code '{course_code}' not found")

    def _get_student_by_id(self, student_id: str):
        """Get student user by student_id, raise error if not found."""
        try:
            from users.models import StudentProfile

            student_profile = StudentProfile.objects.select_related("user").get(student_id=student_id)
            return student_profile.user
        except StudentProfile.DoesNotExist:
            raise FileImportError(f"Student with ID '{student_id}' not found")

    def _get_assessment_by_name(self, assessment_name: str):
        """Get assessment by name, raise error if not found."""
        try:
            return Assessment.objects.get(name=assessment_name)
        except Assessment.DoesNotExist:
            raise FileImportError(f"Assessment with name '{assessment_name}' not found")

    def _get_assessments_by_course(self, course: Course):
        """Get all assessments for a course."""
        return Assessment.objects.filter(course=course)

    def get_import_summary(self) -> Dict[str, Any]:
        """
        Get summary of import operations.

        Returns:
            dict: Summary with counts and errors
        """
        return self.import_results
