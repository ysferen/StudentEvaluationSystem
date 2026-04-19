"""
Column parsing utilities for Turkish Excel format assignment scores.

Shared helpers used by both validation and import services.
"""

import re
from typing import List, Tuple

NON_ASSESSMENT_PREFIXES = ["no", "öğrenci no", "adı", "soyadı", "snf", "girme durum", "harf notu"]


def extract_assessment_columns(columns) -> List[Tuple[str, str]]:
    """
    Extract assessment columns from Turkish Excel format.

    Column format examples:
    - 'Midterm 1(%25)_0833AB' -> 'Midterm 1'
    - 'Project(%40)_0833AB' -> 'Project'
    - 'Attendance(%10)_0833AB' -> 'Attendance'

    Returns:
        List of (original_column_name, parsed_assessment_name) tuples.
    """
    assessment_columns = []

    for col in columns:
        col_str = str(col).strip()

        parts = col_str.split("_")
        if len(parts) > 1:
            last_part = parts[-1]
            if last_part.isalnum() and len(last_part) >= 2:
                base_name = "_".join(parts[:-1])
            else:
                base_name = col_str
        else:
            base_name = col_str

        assessment_name = re.sub(r"\(%?\d+%?\)", "", base_name).strip()

        is_non_assessment = False
        for prefix in NON_ASSESSMENT_PREFIXES:
            if assessment_name.lower().startswith(prefix.lower()):
                is_non_assessment = True
                break

        if not is_non_assessment and assessment_name:
            assessment_columns.append((col_str, assessment_name))

    return assessment_columns


def clean_assessment_name(name: str) -> str:
    """Clean assessment name by removing weight information like (%25), (%40), etc."""
    return re.sub(r"\(%\d+\)", "", name).strip()


def find_student_id_column(columns) -> str:
    """
    Find the student ID column from Turkish column names.

    Returns:
        The column name containing 'öğrenci no'.

    Raises:
        ValueError: If no student ID column found.
    """
    for col in columns:
        col_str = str(col).lower().strip()
        if "öğrenci no" in col_str:
            return col
    raise ValueError("Student ID column not found. Expected column containing 'öğrenci no'")
