"""
Tests for file import parsing utilities.
"""

import pytest
from io import BytesIO

import pandas as pd

from core.services.file_import import ExcelParser, FileImportError


@pytest.mark.django_db
class TestExcelParser:
    """Tests for ExcelParser class."""

    def test_validate_file_valid_excel(self):
        """Test validation of valid Excel file."""
        df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        buffer = BytesIO()
        df.to_excel(buffer, engine="openpyxl")
        buffer.seek(0)
        buffer.name = "test.xlsx"
        buffer.size = buffer.getbuffer().nbytes

        parser = ExcelParser()
        assert parser.validate_file(buffer) is True

    def test_validate_file_invalid_format(self):
        """Test validation of invalid file format."""
        buffer = BytesIO()
        buffer.write(b"This is not an Excel file")
        buffer.seek(0)
        buffer.name = "test.txt"

        parser = ExcelParser()
        with pytest.raises(FileImportError):
            parser.validate_file(buffer)

    def test_get_sheet_names(self):
        """Test getting sheet names from Excel file."""
        df = pd.DataFrame({"data": [1, 2, 3]})
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Sheet1", index=False)
            df.to_excel(writer, sheet_name="Sheet2", index=False)
        buffer.seek(0)

        parser = ExcelParser()
        sheets = parser.get_sheet_names(buffer)

        assert "Sheet1" in sheets
        assert "Sheet2" in sheets

    def test_parse_sheet(self):
        """Test parsing a sheet from Excel file."""
        df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        buffer = BytesIO()
        df.to_excel(buffer, sheet_name="TestData", engine="openpyxl", index=False)
        buffer.seek(0)

        parser = ExcelParser()
        parsed_df = parser.parse_sheet(buffer)

        assert len(parsed_df) == 2
        assert "col1" in parsed_df.columns
        assert "col2" in parsed_df.columns
