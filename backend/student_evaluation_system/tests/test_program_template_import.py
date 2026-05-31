"""
Tests for importing reusable program and course template data from SpreadsheetML workbooks.
"""

from xml.sax.saxutils import escape

import pytest

from core.models import (
    Course,
    CourseTemplate,
    CourseTemplateAssessment,
    CourseTemplateLearningOutcome,
    LearningOutcome,
    ProgramOutcome,
    ProgramOutcomeTemplate,
)
from core.services.file_import import ExcelParser, FileImportError, FileImportService
from evaluation.models import Assessment
from tests.upload_helpers import InMemoryUpload


def _spreadsheetml_upload(sheets, name="program_templates.xls"):
    worksheets = []
    for sheet_name, rows in sheets.items():
        xml_rows = []
        for row in rows:
            cells = "".join(f'<Cell><Data ss:Type="String">{escape(str(value))}</Data></Cell>' for value in row)
            xml_rows.append(f"<Row>{cells}</Row>")
        worksheets.append(f'<Worksheet ss:Name="{escape(sheet_name)}"><Table>{"".join(xml_rows)}</Table></Worksheet>')

    workbook = f"""<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
{"".join(worksheets)}
</Workbook>
"""
    return InMemoryUpload(workbook.encode("utf-8"), name=name)


def _valid_template_sheets(program_name="Test Program", course_title="Algorithms", po_text="Use engineering knowledge"):
    return {
        "Courses": [
            [
                "ProgramName",
                "ProgramId",
                "CourseCode",
                "CourseTitle",
                "Credit",
                "Status",
                "ErrorMessage",
            ],
            [program_name, "5", "CS101", course_title, "3", "OK", ""],
        ],
        "AssessmentMethods": [
            ["CourseCode", "AssessmentType", "Quantity", "Percentage"],
            ["CS101", "Midterm", "2", "30"],
            ["CS101", "Final Exam", "1", "40"],
        ],
        "LearningOutcomes": [
            ["CourseCode", "CourseTitle", "OutcomeNo", "OutcomeText"],
            ["CS101", course_title, "1", "Understand algorithms"],
            ["CS101", course_title, "2", "Analyze complexity"],
        ],
        "ProgramOutcomes": [
            ["ProgramName", "ProgramId", "ProgramOutcomeNo", "ProgramOutcomeText", "SourceUrl"],
            [program_name, "5", "1", po_text, "https://example.test/po"],
        ],
        "WeeklyContents": [["CourseCode", "Week"], ["CS101", "1"]],
    }


@pytest.mark.django_db
class TestProgramTemplateImport:
    def test_parses_spreadsheetml_xls_sheets(self):
        upload = _spreadsheetml_upload(_valid_template_sheets())

        parser = ExcelParser()
        sheets = parser.get_sheet_names(upload)
        courses_df = parser.parse_sheet(upload, sheet_name="Courses")

        assert {"Courses", "AssessmentMethods", "LearningOutcomes", "ProgramOutcomes"}.issubset(set(sheets))
        assert courses_df.iloc[0]["CourseCode"] == "CS101"

    def test_import_creates_templates_only(self, db_setup):
        upload = _spreadsheetml_upload(_valid_template_sheets())

        result = FileImportService(upload).import_program_templates(db_setup["program"].id)

        assert result["created"]["course_templates"] == 1
        assert result["created"]["course_template_learning_outcomes"] == 2
        assert result["created"]["program_outcome_templates"] == 1
        assert CourseTemplate.objects.filter(program=db_setup["program"], code="CS101").exists()
        assert CourseTemplateLearningOutcome.objects.count() == 2
        assert ProgramOutcomeTemplate.objects.get(code="PO1").weight == 0.0
        assert Course.objects.count() == 1
        assert LearningOutcome.objects.count() == 0
        assert ProgramOutcome.objects.count() == 0
        assert Assessment.objects.count() == 0

    def test_preview_returns_objects_without_creating_templates(self, db_setup):
        upload = _spreadsheetml_upload(_valid_template_sheets())

        preview = FileImportService(upload).preview_program_templates(db_setup["program"].id)

        assert preview["summary"]["created"]["course_templates"] == 1
        assert preview["courses"][0]["code"] == "CS101"
        assert [assessment["name"] for assessment in preview["courses"][0]["assessments"]] == [
            "Midterm 1",
            "Midterm 2",
            "Final Exam",
        ]
        assert [outcome["code"] for outcome in preview["courses"][0]["learning_outcomes"]] == ["LO1", "LO2"]
        assert preview["program_outcomes"][0]["code"] == "PO1"
        assert CourseTemplate.objects.count() == 0
        assert CourseTemplateAssessment.objects.count() == 0
        assert CourseTemplateLearningOutcome.objects.count() == 0
        assert ProgramOutcomeTemplate.objects.count() == 0

    def test_expands_assessments_and_normalizes_weights(self, db_setup):
        upload = _spreadsheetml_upload(_valid_template_sheets())

        FileImportService(upload).import_program_templates(db_setup["program"].id)

        assessments = CourseTemplateAssessment.objects.order_by("name")
        assert list(assessments.values_list("name", flat=True)) == ["Final Exam", "Midterm 1", "Midterm 2"]
        assert CourseTemplateAssessment.objects.get(name="Midterm 1").assessment_type == "midterm"
        assert CourseTemplateAssessment.objects.get(name="Final Exam").assessment_type == "final"
        assert CourseTemplateAssessment.objects.get(name="Midterm 1").weight == pytest.approx(0.15)
        assert CourseTemplateAssessment.objects.get(name="Midterm 2").weight == pytest.approx(0.15)
        assert CourseTemplateAssessment.objects.get(name="Final Exam").weight == pytest.approx(0.40)

    def test_skips_non_ok_course_rows(self, db_setup):
        sheets = _valid_template_sheets()
        sheets["Courses"].append(["Test Program", "5", "CS102", "Broken Course", "3", "ERROR", "missing details"])
        sheets["AssessmentMethods"].append(["CS102", "Quiz", "1", "10"])
        upload = _spreadsheetml_upload(sheets)

        result = FileImportService(upload).import_program_templates(db_setup["program"].id)

        assert CourseTemplate.objects.filter(code="CS102").exists() is False
        assert result["skipped"]["course_templates"] == 1
        assert any("missing details" in error for error in result["errors"])
        assert any("CS102" in error for error in result["errors"])

    def test_reimport_updates_without_duplicates(self, db_setup):
        FileImportService(_spreadsheetml_upload(_valid_template_sheets())).import_program_templates(db_setup["program"].id)
        changed_sheets = _valid_template_sheets(
            course_title="Advanced Algorithms",
            po_text="Updated program outcome",
        )

        result = FileImportService(_spreadsheetml_upload(changed_sheets)).import_program_templates(db_setup["program"].id)

        assert result["updated"]["course_templates"] == 1
        assert CourseTemplate.objects.count() == 1
        assert CourseTemplateLearningOutcome.objects.count() == 2
        assert CourseTemplateAssessment.objects.count() == 3
        assert ProgramOutcomeTemplate.objects.count() == 1
        assert CourseTemplate.objects.get(code="CS101").name == "Advanced Algorithms"
        assert ProgramOutcomeTemplate.objects.get(code="PO1").description == "Updated program outcome"

    def test_reimport_removes_stale_template_assessments(self, db_setup):
        assignment_sheets = _valid_template_sheets()
        assignment_sheets["AssessmentMethods"] = [
            ["CourseCode", "AssessmentType", "Quantity", "Percentage"],
            ["CS101", "Assignment", "10", "20"],
            ["CS101", "Final Exam", "1", "40"],
        ]
        FileImportService(_spreadsheetml_upload(assignment_sheets)).import_program_templates(db_setup["program"].id)

        result = FileImportService(_spreadsheetml_upload(_valid_template_sheets())).import_program_templates(
            db_setup["program"].id
        )

        assessments = CourseTemplateAssessment.objects.order_by("name")
        assert list(assessments.values_list("name", flat=True)) == ["Final Exam", "Midterm 1", "Midterm 2"]
        assert result["deleted"]["course_template_assessments"] == 10

    def test_rejects_missing_required_sheet(self, db_setup):
        sheets = _valid_template_sheets()
        del sheets["LearningOutcomes"]
        upload = _spreadsheetml_upload(sheets)

        with pytest.raises(FileImportError, match="Missing required sheets: LearningOutcomes"):
            FileImportService(upload).import_program_templates(db_setup["program"].id)

    def test_rejects_missing_required_column(self, db_setup):
        sheets = _valid_template_sheets()
        sheets["AssessmentMethods"][0] = ["CourseCode", "AssessmentType", "Quantity"]
        upload = _spreadsheetml_upload(sheets)

        with pytest.raises(FileImportError, match="Missing required columns for AssessmentMethods: Percentage"):
            FileImportService(upload).import_program_templates(db_setup["program"].id)
