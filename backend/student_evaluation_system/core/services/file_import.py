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
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional

from ..models import (
    Program,
    Term,
    Course,
    LearningOutcome,
    ProgramOutcome,
    ProgramOutcomeTemplate,
    CourseTemplate,
    CourseTemplateLearningOutcome,
    CourseTemplateAssessment,
)
from evaluation.models import Assessment, StudentGrade, CourseEnrollment, ScoreRecomputeJob
from .validators import InputValidator, FileValidator, ValidationError as CustomValidationError
from .column_parsing import extract_assessment_columns, clean_assessment_name, find_student_id_column
from .validation import AssignmentScoreValidator

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
    def parse_sheet(self, file_obj, import_type: Optional[str] = None, sheet_name: Optional[str] = None) -> pd.DataFrame:
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

    SPREADSHEETML_NS = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}

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
            file_obj.seek(0)
            workbook = pd.ExcelFile(file_obj)
            return [str(sheet_name) for sheet_name in workbook.sheet_names]
        except Exception as e:
            try:
                workbook_root = self._read_spreadsheetml_root(file_obj)
                return [
                    str(sheet.attrib.get("{urn:schemas-microsoft-com:office:spreadsheet}Name", ""))
                    for sheet in workbook_root.findall("ss:Worksheet", self.SPREADSHEETML_NS)
                ]
            except Exception:
                raise FileImportError(f"Error reading Excel file: {str(e)}")

    def _read_spreadsheetml_root(self, file_obj):
        file_obj.seek(0)
        raw_content = file_obj.read()
        if isinstance(raw_content, str):
            xml_content = raw_content
        else:
            xml_content = raw_content.decode("utf-8-sig")
        return ET.fromstring(xml_content)

    def _parse_spreadsheetml_sheet(self, file_obj, sheet_name: Optional[str] = None) -> pd.DataFrame:
        workbook_root = self._read_spreadsheetml_root(file_obj)
        worksheets = workbook_root.findall("ss:Worksheet", self.SPREADSHEETML_NS)
        selected_sheet = None
        for worksheet in worksheets:
            current_name = worksheet.attrib.get("{urn:schemas-microsoft-com:office:spreadsheet}Name", "")
            if sheet_name is None or current_name == sheet_name:
                selected_sheet = worksheet
                break

        if selected_sheet is None:
            raise FileImportError(f"Sheet '{sheet_name}' not found")

        table = selected_sheet.find("ss:Table", self.SPREADSHEETML_NS)
        if table is None:
            return pd.DataFrame()

        parsed_rows = []
        for row in table.findall("ss:Row", self.SPREADSHEETML_NS):
            parsed_row = []
            current_index = 1
            for cell in row.findall("ss:Cell", self.SPREADSHEETML_NS):
                index_attr = cell.attrib.get("{urn:schemas-microsoft-com:office:spreadsheet}Index")
                if index_attr:
                    target_index = int(index_attr)
                    while current_index < target_index:
                        parsed_row.append("")
                        current_index += 1

                data = cell.find("ss:Data", self.SPREADSHEETML_NS)
                parsed_row.append(data.text if data is not None and data.text is not None else "")
                current_index += 1
            parsed_rows.append(parsed_row)

        if not parsed_rows:
            return pd.DataFrame()

        max_width = max(len(row) for row in parsed_rows)
        normalized_rows = [row + [""] * (max_width - len(row)) for row in parsed_rows]
        headers = [str(value).strip() for value in normalized_rows[0]]
        data_rows = normalized_rows[1:]
        return pd.DataFrame(data_rows, columns=headers)

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

    def parse_sheet(self, file_obj, import_type: Optional[str] = None, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """
        Parse Excel sheet with proper dtype specifications.

        Args:
            file_obj: Excel file object
            import_type: Type hint for column interpretation

        Returns:
            DataFrame with properly typed columns
        """
        try:
            file_obj.seek(0)
            workbook = pd.ExcelFile(file_obj)

            # Get dtype mapping for this import type
            dtype_map = self._get_dtype_mapping(import_type) if import_type else {}

            # Read with explicit dtypes and nullable backend
            df = pd.read_excel(
                workbook,
                sheet_name=sheet_name if sheet_name else 0,
                dtype=dtype_map if dtype_map else None,
                dtype_backend="numpy_nullable",  # Better null handling
                na_values=["", "NA", "N/A", "null", "NULL", "-"],  # Standard null values
            )

            return df
        except Exception as e:
            try:
                return self._parse_spreadsheetml_sheet(file_obj, sheet_name=sheet_name)
            except FileImportError:
                raise
            except Exception:
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

    def parse_sheet(self, file_obj, import_type: Optional[str] = None, sheet_name: Optional[str] = None) -> pd.DataFrame:
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

    PROGRAM_TEMPLATE_SHEETS = {
        "Courses": ["CourseCode", "CourseTitle", "Credit", "Status"],
        "AssessmentMethods": ["CourseCode", "AssessmentType", "Quantity", "Percentage"],
        "LearningOutcomes": ["CourseCode", "OutcomeNo", "OutcomeText"],
        "ProgramOutcomes": ["ProgramOutcomeNo", "ProgramOutcomeText"],
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

    def _get_parser(self) -> FileParser:
        """Get or initialize the parser for the current file."""
        if self.parser is not None:
            return self.parser

        parser_name = self.detect_file_format()
        parser_class = self.PARSERS.get(parser_name)
        if not parser_class:
            raise FileImportError(f"No parser available for format: {parser_name}")

        self.parser = parser_class()
        return self.parser

    @staticmethod
    def _cell_value(value) -> str:
        if pd.isna(value):
            return ""
        return str(value).strip()

    @staticmethod
    def _normalize_template_code(prefix: str, value) -> str:
        raw_value = FileImportService._cell_value(value).upper()
        if raw_value.startswith(prefix):
            return raw_value
        match = re.search(r"\d+", raw_value)
        if not match:
            raise ValueError(f"Missing numeric value for {prefix} code")
        return f"{prefix}{int(match.group(0))}"

    @staticmethod
    def _parse_positive_int(value, field_name: str) -> int:
        raw_value = FileImportService._cell_value(value)
        parsed_value = int(float(raw_value))
        if parsed_value <= 0:
            raise ValueError(f"{field_name} must be positive")
        return parsed_value

    @staticmethod
    def _parse_percentage(value) -> float:
        raw_value = FileImportService._cell_value(value).replace("%", "")
        parsed_value = float(raw_value)
        if parsed_value < 0:
            raise ValueError("Percentage must not be negative")
        return parsed_value / 100

    @staticmethod
    def _normalize_assessment_type(value) -> str:
        normalized_value = FileImportService._cell_value(value).lower()
        normalized_value = re.sub(r"\s+", " ", normalized_value)
        mapping = {
            "midterm": "midterm",
            "final exam": "final",
            "final": "final",
            "homework": "homework",
            "assignment": "homework",
            "project": "project",
            "quiz": "quiz",
        }
        return mapping.get(normalized_value, "other")

    def _parse_program_template_sheets(self) -> Dict[str, pd.DataFrame]:
        parser = self._get_parser()
        available_sheets = set(parser.get_sheet_names(self.file_obj))
        missing_sheets = [sheet_name for sheet_name in self.PROGRAM_TEMPLATE_SHEETS if sheet_name not in available_sheets]
        if missing_sheets:
            raise FileImportError(f"Missing required sheets: {', '.join(missing_sheets)}")

        parsed_sheets = {}
        for sheet_name, required_columns in self.PROGRAM_TEMPLATE_SHEETS.items():
            dataframe = parser.parse_sheet(self.file_obj, import_type="program_templates", sheet_name=sheet_name)
            missing_columns = [column for column in required_columns if column not in dataframe.columns]
            if missing_columns:
                raise FileImportError(
                    f"Missing required columns for {sheet_name}: {', '.join(missing_columns)}. "
                    f"Found columns: {', '.join(str(column) for column in dataframe.columns.tolist())}"
                )
            parsed_sheets[sheet_name] = dataframe
        return parsed_sheets

    def _validate_program_template_source(self, program: Program, sheets: Dict[str, pd.DataFrame]):
        source_names = set()
        source_ids = set()
        for dataframe in sheets.values():
            if "ProgramName" in dataframe.columns:
                source_names.update(
                    self._cell_value(value) for value in dataframe["ProgramName"].tolist() if self._cell_value(value)
                )
            if "ProgramId" in dataframe.columns:
                source_ids.update(
                    self._cell_value(value) for value in dataframe["ProgramId"].tolist() if self._cell_value(value)
                )

        if len(source_names) > 1 or len(source_ids) > 1:
            raise FileImportError("File contains rows for more than one source program")

        source_name = next(iter(source_names), "")
        if source_name and source_name.lower() != program.name.lower():
            raise FileImportError(f"Source ProgramName '{source_name}' does not match selected program '{program.name}'")

        return {"program_name": source_name, "program_id": next(iter(source_ids), "")}

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
            parser = self._get_parser()
            return parser.validate_file(self.file_obj)

        except Exception as e:
            if isinstance(e, FileImportError):
                raise
            raise FileImportError(f"Invalid file: {str(e)}")

    def import_program_templates(self, program_id: int):
        """
        Import reusable program/course template data from the program SpreadsheetML workbook.

        The import creates or updates template rows only. It intentionally does not
        instantiate term-specific Course, LearningOutcome, ProgramOutcome, or
        Assessment rows.
        """
        try:
            program = Program.objects.get(pk=int(program_id))
        except (Program.DoesNotExist, ValueError, TypeError):
            raise FileImportError(f"Program with ID '{program_id}' not found")

        preview = self.preview_program_templates(program_id)
        created_counts = dict.fromkeys(preview["summary"]["created"].keys(), 0)
        updated_counts = dict.fromkeys(preview["summary"]["updated"].keys(), 0)
        deleted_counts = {"course_template_assessments": 0}

        with transaction.atomic():
            course_templates = {}
            for course_data in preview["courses"]:
                course_template, created = CourseTemplate.objects.update_or_create(
                    program=program,
                    code=course_data["code"],
                    defaults={"name": course_data["name"], "credits": course_data["credits"]},
                )
                course_templates[course_data["code"]] = course_template
                target_counts = created_counts if created else updated_counts
                target_counts["course_templates"] += 1

                for assessment_data in course_data["assessments"]:
                    _, created = CourseTemplateAssessment.objects.update_or_create(
                        course_template=course_template,
                        name=assessment_data["name"],
                        defaults={
                            "assessment_type": assessment_data["assessment_type"],
                            "total_score": assessment_data["total_score"],
                            "weight": assessment_data["weight"],
                        },
                    )
                    target_counts = created_counts if created else updated_counts
                    target_counts["course_template_assessments"] += 1

                assessment_names = [assessment_data["name"] for assessment_data in course_data["assessments"]]
                stale_assessments = course_template.assessments.exclude(name__in=assessment_names)
                deleted_counts["course_template_assessments"] += stale_assessments.count()
                stale_assessments.delete()

                for learning_outcome_data in course_data["learning_outcomes"]:
                    _, created = CourseTemplateLearningOutcome.objects.update_or_create(
                        course_template=course_template,
                        code=learning_outcome_data["code"],
                        defaults={"description": learning_outcome_data["description"]},
                    )
                    target_counts = created_counts if created else updated_counts
                    target_counts["course_template_learning_outcomes"] += 1

            for program_outcome_data in preview["program_outcomes"]:
                _, created = ProgramOutcomeTemplate.objects.update_or_create(
                    program=program,
                    code=program_outcome_data["code"],
                    defaults={"description": program_outcome_data["description"], "weight": 0.0},
                )
                target_counts = created_counts if created else updated_counts
                target_counts["program_outcome_templates"] += 1

        self.import_results["created"] = created_counts
        self.import_results["updated"] = updated_counts
        self.import_results["deleted"] = deleted_counts
        self.import_results["errors"] = preview["errors"]
        self.import_results["skipped"] = preview["skipped"]
        self.import_results["source_program"] = preview["source_program"]
        self.import_results["preview"] = preview
        self.import_results["message"] = "Program template import completed."
        return self.import_results

    def _get_program_for_template_import(self, program_id: int) -> Program:
        try:
            return Program.objects.get(pk=int(program_id))
        except (Program.DoesNotExist, ValueError, TypeError):
            raise FileImportError(f"Program with ID '{program_id}' not found")

    def _preview_course_templates(self, program: Program, courses_df: pd.DataFrame, errors: List[str]):
        courses_by_code = {}
        skipped_count = 0
        for row_offset, row in courses_df.iterrows():
            row_number = row_offset + 2
            try:
                status = self._cell_value(row["Status"]).upper()
                error_message = self._cell_value(row.get("ErrorMessage", ""))
                if status != "OK" or error_message:
                    skipped_count += 1
                    if error_message:
                        errors.append(f"Courses row {row_number}: skipped source error - {error_message}")
                    continue

                course_code = self._cell_value(row["CourseCode"]).upper()
                course_title = self._cell_value(row["CourseTitle"])
                credits = self._parse_positive_int(row["Credit"], "Credit")
                if not course_code or not course_title:
                    raise ValueError("CourseCode and CourseTitle are required")

                existing_course = CourseTemplate.objects.filter(program=program, code=course_code).first()
                courses_by_code[course_code] = {
                    "code": course_code,
                    "name": course_title,
                    "credits": credits,
                    "action": "update" if existing_course else "create",
                    "assessments": [],
                    "learning_outcomes": [],
                }
            except Exception as e:
                errors.append(f"Courses row {row_number}: {str(e)}")
        return courses_by_code, skipped_count

    def _preview_course_template_assessments(
        self,
        program: Program,
        assessments_df: pd.DataFrame,
        courses_by_code: Dict[str, Dict[str, Any]],
        errors: List[str],
    ):
        for row_offset, row in assessments_df.iterrows():
            row_number = row_offset + 2
            try:
                course_code = self._cell_value(row["CourseCode"]).upper()
                course_preview = courses_by_code.get(course_code)
                if course_preview is None:
                    raise ValueError(f"Course template '{course_code}' was not imported")

                assessment_base_name = self._cell_value(row["AssessmentType"])
                if not assessment_base_name:
                    raise ValueError("AssessmentType is required")

                total_weight = self._parse_percentage(row["Percentage"])
                assessment_type = self._normalize_assessment_type(assessment_base_name)
                existing_course = CourseTemplate.objects.filter(program=program, code=course_code).first()

                existing_assessment = None
                if existing_course is not None:
                    existing_assessment = CourseTemplateAssessment.objects.filter(
                        course_template=existing_course,
                        name=assessment_base_name,
                    ).first()
                course_preview["assessments"].append(
                    {
                        "name": assessment_base_name,
                        "assessment_type": assessment_type,
                        "total_score": 100,
                        "weight": total_weight,
                        "action": "update" if existing_assessment else "create",
                    }
                )
            except Exception as e:
                errors.append(f"AssessmentMethods row {row_number}: {str(e)}")

    def _preview_course_template_learning_outcomes(
        self,
        program: Program,
        learning_outcomes_df: pd.DataFrame,
        courses_by_code: Dict[str, Dict[str, Any]],
        errors: List[str],
    ):
        for row_offset, row in learning_outcomes_df.iterrows():
            row_number = row_offset + 2
            try:
                course_code = self._cell_value(row["CourseCode"]).upper()
                course_preview = courses_by_code.get(course_code)
                if course_preview is None:
                    raise ValueError(f"Course template '{course_code}' was not imported")

                lo_code = self._normalize_template_code("LO", row["OutcomeNo"])
                description = self._cell_value(row["OutcomeText"])
                if not description:
                    raise ValueError("OutcomeText is required")

                existing_course = CourseTemplate.objects.filter(program=program, code=course_code).first()
                existing_lo = None
                if existing_course is not None:
                    existing_lo = CourseTemplateLearningOutcome.objects.filter(
                        course_template=existing_course,
                        code=lo_code,
                    ).first()
                course_preview["learning_outcomes"].append(
                    {
                        "code": lo_code,
                        "description": description,
                        "action": "update" if existing_lo else "create",
                    }
                )
            except Exception as e:
                errors.append(f"LearningOutcomes row {row_number}: {str(e)}")

    def _preview_program_outcome_templates(
        self,
        program: Program,
        program_outcomes_df: pd.DataFrame,
        errors: List[str],
    ):
        program_outcomes = []
        for row_offset, row in program_outcomes_df.iterrows():
            row_number = row_offset + 2
            try:
                po_code = self._normalize_template_code("PO", row["ProgramOutcomeNo"])
                description = self._cell_value(row["ProgramOutcomeText"])
                if not description:
                    raise ValueError("ProgramOutcomeText is required")

                existing_po = ProgramOutcomeTemplate.objects.filter(program=program, code=po_code).first()
                program_outcomes.append(
                    {
                        "code": po_code,
                        "description": description,
                        "weight": 0.0,
                        "action": "update" if existing_po else "create",
                    }
                )
            except Exception as e:
                errors.append(f"ProgramOutcomes row {row_number}: {str(e)}")
        return program_outcomes

    def _build_program_template_preview_summary(self, courses, program_outcomes):
        return {
            "created": {
                "course_templates": sum(1 for course in courses if course["action"] == "create"),
                "course_template_assessments": sum(
                    1 for course in courses for assessment in course["assessments"] if assessment["action"] == "create"
                ),
                "course_template_learning_outcomes": sum(
                    1
                    for course in courses
                    for learning_outcome in course["learning_outcomes"]
                    if learning_outcome["action"] == "create"
                ),
                "program_outcome_templates": sum(1 for outcome in program_outcomes if outcome["action"] == "create"),
            },
            "updated": {
                "course_templates": sum(1 for course in courses if course["action"] == "update"),
                "course_template_assessments": sum(
                    1 for course in courses for assessment in course["assessments"] if assessment["action"] == "update"
                ),
                "course_template_learning_outcomes": sum(
                    1
                    for course in courses
                    for learning_outcome in course["learning_outcomes"]
                    if learning_outcome["action"] == "update"
                ),
                "program_outcome_templates": sum(1 for outcome in program_outcomes if outcome["action"] == "update"),
            },
        }

    def preview_program_templates(self, program_id: int):
        """Parse a program template workbook and return the objects that would be upserted."""
        program = self._get_program_for_template_import(program_id)
        sheets = self._parse_program_template_sheets()
        source_program = self._validate_program_template_source(program, sheets)
        errors: List[str] = []
        courses_by_code, skipped_course_count = self._preview_course_templates(program, sheets["Courses"], errors)
        self._preview_course_template_assessments(program, sheets["AssessmentMethods"], courses_by_code, errors)
        self._preview_course_template_learning_outcomes(program, sheets["LearningOutcomes"], courses_by_code, errors)
        program_outcomes = self._preview_program_outcome_templates(program, sheets["ProgramOutcomes"], errors)
        courses = list(courses_by_code.values())
        summary = self._build_program_template_preview_summary(courses, program_outcomes)

        return {
            "message": "Program template preview generated.",
            "source_program": source_program,
            "summary": summary,
            "skipped": {"course_templates": skipped_course_count},
            "errors": errors,
            "courses": courses,
            "program_outcomes": program_outcomes,
        }

    def import_assignment_scores(
        self,
        course_code: str,
        term_id: int,
        resolution_policy: Optional[Dict[str, bool]] = None,
        triggered_by=None,
    ):
        """
        Import assignment scores from Turkish Excel format.

        Args:
            course_code (str): Code of the course for which grades are being imported
            term_id (int): ID of the academic term for which grades are being imported
            resolution_policy (dict, optional): Policy dict with keys:
                - skip_missing_assessments: bool
                - skip_missing_students: bool
                - skip_unenrolled_students: bool
                - skip_invalid_scores: bool
                - clamp_scores: bool

        Returns:
            dict: Import results with created/updated counts
        """
        try:
            course_code, term_id = self._validate_assignment_import_params(course_code, term_id)

            policy = {
                "skip_missing_assessments": bool((resolution_policy or {}).get("skip_missing_assessments", False)),
                "skip_missing_students": bool((resolution_policy or {}).get("skip_missing_students", False)),
                "skip_unenrolled_students": bool((resolution_policy or {}).get("skip_unenrolled_students", False)),
                "skip_invalid_scores": bool((resolution_policy or {}).get("skip_invalid_scores", False)),
                "clamp_scores": bool((resolution_policy or {}).get("clamp_scores", False)),
            }
            (
                df,
                course,
                course_assessments,
                assessment_lookup,
                student_id_col,
                assessment_columns,
                policy_effects,
            ) = self._prepare_assignment_import_context(course_code, term_id, policy)

            self.import_results["policy_effects"] = policy_effects

            created_count = 0
            updated_count = 0
            skipped_count = (
                int(policy_effects.get("rows_dropped_missing_students", 0))
                + int(policy_effects.get("rows_dropped_unenrolled_students", 0))
                + int(policy_effects.get("scores_skipped", 0))
            )
            affected_courses = set()

            with transaction.atomic():
                for row_offset in range(len(df)):
                    row_number = row_offset + 2
                    row = df.iloc[row_offset]
                    try:
                        row_created, row_updated, row_skipped = self._process_assignment_row(
                            row=row,
                            row_number=row_number,
                            student_id_col=student_id_col,
                            assessment_columns=assessment_columns,
                            assessment_lookup=assessment_lookup,
                            affected_courses=affected_courses,
                            policy=policy,
                        )
                        created_count += row_created
                        updated_count += row_updated
                        skipped_count += row_skipped
                    except Exception as e:
                        self.import_results["errors"].append(f"Row {row_number}: Error processing row - {str(e)}")
                        continue

            self.import_results["created"]["grades"] = created_count
            self.import_results["updated"]["grades"] = updated_count
            self.import_results["skipped"] = skipped_count
            self.import_results["total_rows"] = len(df)

            recompute_jobs = self._recalculate_affected_courses(affected_courses, triggered_by=triggered_by)
            self.import_results["recompute_jobs"] = recompute_jobs
            self.import_results["message"] = "Import completed. Score recomputation queued."
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
            clean_name = clean_assessment_name(assessment_name)
            if clean_name.lower().strip() not in assessment_lookup:
                missing_assessments.append(clean_name)
        return missing_assessments

    def _prepare_assignment_import_context(
        self,
        course_code: str,
        term_id: int,
        resolution_policy: Optional[Dict[str, bool]] = None,
    ):
        df = self._get_parser().parse_sheet(self.file_obj, import_type="assignment_scores")
        course = self._get_course_by_code_and_term(course_code, term_id)
        transformed_df, policy_effects = AssignmentScoreValidator.apply_resolution_policy_to_dataframe(
            df,
            course,
            resolution_policy=resolution_policy,
        )

        course_assessments = Assessment.objects.filter(course=course)
        assessment_lookup = {assessment.name.lower().strip(): assessment for assessment in course_assessments}

        if not course_assessments.exists():
            raise FileImportError(f"No assessments found for course {course.code}. Please create assessments first.")

        self._validate_required_columns(transformed_df, "assignment_scores")

        policy = resolution_policy or {}
        if not policy.get("skip_missing_students") and not policy.get("skip_unenrolled_students"):
            self._validate_students(transformed_df, course)

        try:
            student_id_col = find_student_id_column(transformed_df.columns)
        except ValueError as e:
            raise FileImportError(str(e))
        assessment_columns = extract_assessment_columns(transformed_df.columns)
        if not assessment_columns:
            raise FileImportError("No assessment score columns found in file")

        missing_assessments = self._find_missing_assessments(assessment_columns, assessment_lookup)
        if missing_assessments:
            if policy.get("skip_missing_assessments"):
                assessment_columns = [c for c in assessment_columns if c not in set(missing_assessments)]
                if not assessment_columns:
                    raise FileImportError("All assessment columns were skipped — none found in database.")
            else:
                available = ", ".join([assessment.name for assessment in course_assessments])
                raise FileImportError(
                    f"Assessments not found in database: {', '.join(missing_assessments)}. Available assessments: {available}"
                )

        return (
            transformed_df,
            course,
            course_assessments,
            assessment_lookup,
            student_id_col,
            assessment_columns,
            policy_effects,
        )

    def _process_score_with_policy(
        self,
        score,
        assessment,
        row_number: int,
        clean_name: str,
        policy: Dict[str, bool],
    ):
        try:
            return InputValidator.validate_score(score, max_score=assessment.total_score)
        except CustomValidationError:
            if policy.get("clamp_scores"):
                try:
                    raw_score = float(score)
                    return max(0.0, min(float(assessment.total_score), raw_score))
                except (ValueError, TypeError):
                    if policy.get("skip_invalid_scores"):
                        return None
                    self.import_results["errors"].append(f"Row {row_number}: Invalid score '{score}' for {clean_name}")
                    return None
            elif policy.get("skip_invalid_scores"):
                return None
            else:
                self.import_results["errors"].append(f"Row {row_number}: Invalid score '{score}' for {clean_name}")
                return None

    def _process_assignment_row(
        self,
        row,
        row_number: int,
        student_id_col,
        assessment_columns,
        assessment_lookup,
        affected_courses,
        policy: Optional[Dict[str, bool]] = None,
    ):
        if policy is None:
            policy = {}
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

        assessment_results = self._process_row_assessments(
            row=row,
            row_number=row_number,
            student_user=student_user,
            assessment_columns=assessment_columns,
            assessment_lookup=assessment_lookup,
            affected_courses=affected_courses,
            policy=policy,
        )
        return (
            created_count + assessment_results[0],
            updated_count + assessment_results[1],
            skipped_count + assessment_results[2],
        )

    def _process_row_assessments(
        self,
        row,
        row_number: int,
        student_user,
        assessment_columns,
        assessment_lookup,
        affected_courses,
        policy: Dict[str, bool],
    ):
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for col_name, assessment_name in assessment_columns:
            score = row[col_name]
            if pd.notna(score):
                try:
                    clean_name = clean_assessment_name(assessment_name)
                    assessment = assessment_lookup[clean_name.lower().strip()]

                    score_result = self._process_score_with_policy(
                        score=score,
                        assessment=assessment,
                        row_number=row_number,
                        clean_name=clean_name,
                        policy=policy,
                    )
                    if score_result is None:
                        if policy.get("skip_invalid_scores"):
                            skipped_count += 1
                        continue

                    score_float = int(score_result + 0.5)

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

    def _recalculate_affected_courses(self, affected_courses, triggered_by=None):
        from evaluation.tasks import recompute_course_scores_task

        queued_jobs = []

        for course_id in sorted(affected_courses):
            job = ScoreRecomputeJob.objects.create(
                task_type=ScoreRecomputeJob.TASK_TYPE_COURSE_RECOMPUTE,
                status=ScoreRecomputeJob.STATUS_PENDING,
                course_id=course_id,
                triggered_by=triggered_by,
            )
            try:
                async_result = recompute_course_scores_task.delay(course_id, job.pk)  # type: ignore
                ScoreRecomputeJob.objects.filter(id=job.pk).update(celery_task_id=async_result.id)
                job.celery_task_id = async_result.id
                logger.info(f"Queued score recompute job {job.pk} for course {course_id}")
            except Exception as e:
                logger.error(f"Failed to queue score recomputation for course {course_id}: {e}")
                self.import_results["errors"].append(f"Score recomputation queue failed for course {course_id}: {str(e)}")
                job.status = ScoreRecomputeJob.STATUS_FAILED
                job.finished_at = timezone.now()
                job.error = str(e)
                job.save(update_fields=["status", "finished_at", "error"])

            queued_jobs.append(
                {
                    "id": job.pk,
                    "course_id": job.course_id,
                    "status": job.status,
                    "task_type": job.task_type,
                    "celery_task_id": job.celery_task_id,
                }
            )

        return queued_jobs

    def import_learning_outcomes(self, sheet_name: str = "learning_outcomes"):
        """
        Import learning outcome data from file sheet/section.

        Args:
            sheet_name (str): Name of sheet/section containing learning outcome data

        Returns:
            dict: Import results with created/updated counts
        """
        try:
            df = self._get_parser().parse_sheet(self.file_obj, import_type="learning_outcomes")

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
            df = self._get_parser().parse_sheet(self.file_obj, import_type="program_outcomes")

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

    def _validate_required_columns(
        self, dataframe: pd.DataFrame, sheet_type: str, assessments: Optional[Iterable[Assessment]] = None
    ):
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
            assessment_list = list(assessments)
            # Use _extract_assessment_columns to get cleaned assessment names from columns
            assessment_columns = extract_assessment_columns(dataframe.columns)
            found_assessment_names = [name for _, name in assessment_columns]

            assessment_col_found = []
            for assessment in assessment_list:
                # Check if assessment name is in the found assessment columns
                if assessment.name.lower().strip() in [name.lower().strip() for name in found_assessment_names]:
                    assessment_col_found.append(True)
                else:
                    assessment_col_found.append(False)

            if not all(assessment_col_found):
                missing_columns.extend([assessment_list[i].name for i, found in enumerate(assessment_col_found) if not found])

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
        try:
            student_id_col = find_student_id_column(dataframe.columns)
        except ValueError as e:
            raise FileImportError(str(e))

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
        try:
            student_id_col = find_student_id_column(dataframe.columns)
        except ValueError as e:
            raise FileImportError(str(e))
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
        from users.models import StudentProfile

        try:
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
