from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape
from io import BytesIO
from pathlib import Path
from statistics import mean
from typing import Sequence

from django.db.models import F
from django.utils import timezone

from core.models import Course, LearningOutcome, StudentLearningOutcomeScore
from evaluation.models import Assessment, CourseEnrollment, StudentGrade


@dataclass(frozen=True)
class AssessmentReportData:
    name: str
    assessment_type: str
    weight: float
    scores: Sequence[float]


@dataclass(frozen=True)
class LearningOutcomeReportData:
    code: str
    title: str
    scores: Sequence[float]


@dataclass(frozen=True)
class StudentRiskReportData:
    name: str
    course_grade: float
    lo_scores: dict[str, float]


@dataclass(frozen=True)
class CourseReportData:
    course_code: str
    course_name: str
    term: str
    program: str
    credits: int
    instructors: Sequence[str]
    generated_on: date
    enrolled_students: int
    assessments: Sequence[AssessmentReportData]
    learning_outcomes: Sequence[LearningOutcomeReportData]
    students: Sequence[StudentRiskReportData]


class ReportDataError(ValueError):
    """Raised when report data cannot be built from the selected DB slice."""


BRAND = {
    "ink": "#172033",
    "muted": "#64748B",
    "line": "#D8E0EA",
    "panel": "#F7FAFC",
    "white": "#FFFFFF",
    "teal": "#0F9F95",
    "blue": "#2563EB",
    "amber": "#F59E0B",
    "red": "#DC2626",
    "green": "#16A34A",
}

PDF_FONT_REGULAR = "SES-DejaVuSans"
PDF_FONT_BOLD = "SES-DejaVuSans-Bold"
PDF_FONT_FAMILY = "DejaVu Sans"
_FONT_REGISTERED = False


def ensure_pdf_fonts() -> None:
    """Register a Unicode font family so Turkish characters render in PDFs."""
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("PDF reports require reportlab to be installed.") from exc

    regular_path = _find_font_path("DejaVuSans.ttf")
    bold_path = _find_font_path("DejaVuSans-Bold.ttf")
    pdfmetrics.registerFont(TTFont(PDF_FONT_REGULAR, str(regular_path)))
    pdfmetrics.registerFont(TTFont(PDF_FONT_BOLD, str(bold_path)))
    pdfmetrics.registerFontFamily(
        PDF_FONT_FAMILY,
        normal=PDF_FONT_REGULAR,
        bold=PDF_FONT_BOLD,
        italic=PDF_FONT_REGULAR,
        boldItalic=PDF_FONT_BOLD,
    )
    pdfmetrics.registerFontFamily(
        PDF_FONT_REGULAR,
        normal=PDF_FONT_REGULAR,
        bold=PDF_FONT_BOLD,
        italic=PDF_FONT_REGULAR,
        boldItalic=PDF_FONT_BOLD,
    )
    _FONT_REGISTERED = True


def _find_font_path(filename: str) -> Path:
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu") / filename,
        Path("/usr/local/share/fonts") / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise RuntimeError(f"PDF reports require {filename} to be installed.")


THEME = {
    "thresholds": {
        "danger": 60,
        "warning": 70,
        "success": 80,
    },
    "spacing": {
        "xs": 2,
        "sm": 4,
        "md": 6,
    },
}


def generate_course_report_pdf(data: CourseReportData) -> bytes:
    """Generate a two-page A4 institutional course performance report."""

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            PageBreak,
            SimpleDocTemplate,
            Spacer,
            Table,
        )
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("Course PDF reports require reportlab to be installed.") from exc

    ensure_pdf_fonts()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=f"{data.course_code} Course Performance Report",
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName=PDF_FONT_BOLD,
            fontSize=18,
            leading=22,
            textColor=colors.HexColor(BRAND["ink"]),
            alignment=TA_LEFT,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Eyebrow",
            parent=styles["Normal"],
            fontName=PDF_FONT_BOLD,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor(BRAND["teal"]),
            uppercase=True,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Meta",
            parent=styles["Normal"],
            fontName=PDF_FONT_REGULAR,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor(BRAND["muted"]),
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyTextSmall",
            parent=styles["Normal"],
            fontName=PDF_FONT_REGULAR,
            fontSize=8.4,
            leading=11.2,
            textColor=colors.HexColor(BRAND["ink"]),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CalloutTitle",
            parent=styles["Normal"],
            fontName=PDF_FONT_BOLD,
            fontSize=8.5,
            leading=10.5,
            textColor=colors.HexColor(BRAND["ink"]),
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName=PDF_FONT_BOLD,
            fontSize=11,
            leading=13,
            textColor=colors.HexColor(BRAND["ink"]),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="KpiLabel",
            parent=styles["Normal"],
            fontName=PDF_FONT_BOLD,
            fontSize=6.8,
            leading=8,
            textColor=colors.HexColor(BRAND["muted"]),
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="KpiValue",
            parent=styles["Normal"],
            fontName=PDF_FONT_BOLD,
            fontSize=17,
            leading=19,
            textColor=colors.HexColor(BRAND["ink"]),
            alignment=TA_CENTER,
        )
    )

    story = []
    story.extend(_build_header(data, styles))
    story.append(Spacer(1, THEME["spacing"]["sm"] * mm))
    story.append(_build_kpi_table(data, styles))
    story.append(Spacer(1, THEME["spacing"]["sm"] * mm))
    story.append(
        _chart_panel(
            "Learning Outcome Achievement",
            _chart_image(_lo_average_figure(data), 168 * mm, 80 * mm, pixel_width=1260, pixel_height=600),
            width=180 * mm,
            note="Outcome averages are ordered from lowest to highest. Color bands follow the institutional threshold legend.",
        )
    )
    story.append(Spacer(1, THEME["spacing"]["sm"] * mm))
    story.append(
        Table(
            [
                [
                    _chart_panel(
                        "Course Grade Distribution",
                        _chart_image(_grade_distribution_figure(data), 78 * mm, 43 * mm, pixel_width=860, pixel_height=520),
                        width=84 * mm,
                    ),
                    _build_interpretation_panel(data, styles),
                ]
            ],
            colWidths=[86 * mm, 94 * mm],
            style=_gridless_table_style(),
        )
    )
    story.append(Spacer(1, THEME["spacing"]["sm"] * mm))
    story.append(_build_insight_table(data, styles))
    story.append(PageBreak())

    story.extend(_build_page_two_header(data, styles))
    story.append(Spacer(1, THEME["spacing"]["sm"] * mm))
    diagnostic_rows = [
        [
            _chart_panel(
                "Assessment Performance",
                _chart_image(_assessment_figure(data), 82 * mm, 52 * mm, pixel_width=900, pixel_height=560),
                width=88 * mm,
            ),
            _chart_panel(
                "LO Score Spread",
                _chart_image(_lo_box_figure(data), 82 * mm, 52 * mm, pixel_width=900, pixel_height=560),
                width=88 * mm,
            ),
        ],
        [
            _chart_panel(
                "Intervention Priority Heatmap",
                _chart_image(
                    _student_heatmap_figure(data),
                    174 * mm,
                    74 * mm,
                    pixel_width=1392,
                    pixel_height=544,
                ),
                width=180 * mm,
                note=(
                    "Rows are the 10 students with the lowest course averages. "
                    "Use this view to target outcome-specific support."
                ),
            ),
            "",
        ],
        [_build_recommendations_panel(data, styles), ""],
    ]
    story.append(
        Table(
            diagnostic_rows,
            colWidths=[90 * mm, 90 * mm],
            rowHeights=[66 * mm, 94 * mm, 52 * mm],
            style=_gridless_table_style(span_rows=[1, 2]),
        )
    )

    doc.build(story, onFirstPage=_draw_page_frame, onLaterPages=_draw_page_frame)
    return buffer.getvalue()


def build_course_report_data(course_id) -> CourseReportData:
    course = Course.objects.select_related("program", "term").prefetch_related("instructors").get(pk=course_id)
    enrollments = list(CourseEnrollment.objects.filter(course=course).select_related("student").order_by("student__username"))
    assessments = list(Assessment.objects.filter(course=course).order_by("date", "id"))
    learning_outcomes = list(LearningOutcome.objects.filter(course=course).order_by("code", "id"))

    if not enrollments:
        raise ReportDataError("Course report requires at least one enrollment.")
    if not assessments:
        raise ReportDataError("Course report requires at least one assessment.")
    if not learning_outcomes:
        raise ReportDataError("Course report requires at least one learning outcome.")

    student_ids = [enrollment.student_id for enrollment in enrollments]
    student_names = {enrollment.student_id: _display_name(enrollment.student) for enrollment in enrollments}
    assessment_ids = [assessment.id for assessment in assessments]

    grade_rows = list(
        StudentGrade.objects.filter(student_id__in=student_ids, assessment_id__in=assessment_ids)
        .annotate(percentage=F("score") * 100.0 / F("assessment__total_score"))
        .values("student_id", "assessment_id", "percentage", "assessment__weight")
    )
    assessment_scores = {assessment.id: [] for assessment in assessments}
    course_grade_parts = {student_id: [0.0, 0.0] for student_id in student_ids}

    for row in grade_rows:
        percentage = float(row["percentage"] or 0)
        assessment_scores[row["assessment_id"]].append(percentage)
        weight = float(row["assessment__weight"] or 0)
        if weight > 0:
            course_grade_parts[row["student_id"]][0] += percentage * weight
            course_grade_parts[row["student_id"]][1] += weight

    lo_ids = [lo.id for lo in learning_outcomes]
    lo_score_rows = StudentLearningOutcomeScore.objects.filter(
        student_id__in=student_ids,
        learning_outcome_id__in=lo_ids,
    ).values("student_id", "learning_outcome_id", "score")
    lo_score_map = {(row["student_id"], row["learning_outcome_id"]): float(row["score"] or 0) for row in lo_score_rows}

    assessment_data = [
        AssessmentReportData(
            name=assessment.name,
            assessment_type=assessment.assessment_type,
            weight=float(assessment.weight or 0),
            scores=assessment_scores[assessment.id],
        )
        for assessment in assessments
    ]
    learning_outcome_data = [
        LearningOutcomeReportData(
            code=lo.code,
            title=lo.description,
            scores=[lo_score_map.get((student_id, lo.id), 0.0) for student_id in student_ids],
        )
        for lo in learning_outcomes
    ]
    students = []
    for student_id in student_ids:
        weighted_sum, total_weight = course_grade_parts[student_id]
        course_grade = weighted_sum / total_weight if total_weight > 0 else 0.0
        students.append(
            StudentRiskReportData(
                name=student_names[student_id],
                course_grade=round(course_grade, 1),
                lo_scores={lo.code: lo_score_map.get((student_id, lo.id), 0.0) for lo in learning_outcomes},
            )
        )

    return CourseReportData(
        course_code=course.code,
        course_name=course.name,
        term=course.term.name,
        program=course.program.name,
        credits=course.credits,
        instructors=[_display_name(instructor) for instructor in course.instructors.all()] or ["Unassigned"],
        generated_on=timezone.localdate(),
        enrolled_students=len(enrollments),
        assessments=assessment_data,
        learning_outcomes=learning_outcome_data,
        students=students,
    )


def _display_name(user) -> str:
    return user.get_full_name() or user.username


def _build_header(data, styles):
    from reportlab.platypus import Paragraph

    return [
        Paragraph("COURSE PERFORMANCE REPORT", styles["Eyebrow"]),
        Paragraph(f"{data.course_code} · {data.course_name}", styles["ReportTitle"]),
        Paragraph(
            f"{data.program} · {data.term} · {data.credits} credits · "
            f"{', '.join(data.instructors)} · Generated {data.generated_on.isoformat()}",
            styles["Meta"],
        ),
    ]


def _build_page_two_header(data, styles):
    from reportlab.platypus import Paragraph

    return [
        Paragraph("DIAGNOSTIC BREAKDOWN", styles["Eyebrow"]),
        Paragraph(f"{data.course_code} · Outcome and Assessment Detail", styles["ReportTitle"]),
        Paragraph(
            "Assessment diagnostics, student support priorities, and accreditation-ready follow-up notes.", styles["Meta"]
        ),
    ]


def _build_kpi_table(data, styles):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    avg_grade = _avg([student.course_grade for student in data.students])
    avg_lo = _avg([score for lo in data.learning_outcomes for score in lo.scores])
    at_risk = len([student for student in data.students if student.course_grade < 60])
    coverage = _grade_coverage(data)
    kpis = [
        ("ENROLLED", f"{data.enrolled_students}"),
        ("AVG COURSE GRADE", f"{avg_grade:.1f}%"),
        ("AVG LO SCORE", f"{avg_lo:.1f}%"),
        ("AT RISK", f"{at_risk}"),
        ("ASSESSMENTS", f"{len(data.assessments)}"),
        ("GRADE COVERAGE", f"{coverage:.0f}%"),
    ]
    cells = [[Paragraph(value, styles["KpiValue"]), Paragraph(label, styles["KpiLabel"])] for label, value in kpis]
    table = Table([cells], colWidths=[30 * mm for _ in cells])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(BRAND["line"])),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor(BRAND["line"])),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _build_insight_table(data, styles):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Table, TableStyle

    weakest_lo = min(data.learning_outcomes, key=lambda item: _avg(item.scores))
    difficult_assessment = min(data.assessments, key=lambda item: _avg(item.scores))
    volatile_assessment = max(data.assessments, key=lambda item: _score_range(item.scores))
    at_risk = len([student for student in data.students if student.course_grade < 60])
    rows = [
        [
            _insight(
                "Action needed",
                f"{weakest_lo.code} · {_avg(weakest_lo.scores):.1f}%",
                f"Review {weakest_lo.title.lower()} activities before final evaluation.",
                styles,
            ),
            _insight(
                "Assessment review",
                f"{difficult_assessment.name} · {_avg(difficult_assessment.scores):.1f}%",
                f"Revisit preparation and rubric clarity for this {difficult_assessment.weight:.0%} weighted item.",
                styles,
            ),
            _insight(
                "Consistency check",
                f"{volatile_assessment.name} · {_score_range(volatile_assessment.scores):.0f} pts",
                "Check rubric consistency or student segmentation",
                styles,
            ),
            _insight("Support queue", f"{at_risk} students", "Course grade below the intervention threshold.", styles),
        ]
    ]
    table = Table(rows, colWidths=[45 * mm, 45 * mm, 45 * mm, 45 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(BRAND["line"])),
                ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor(BRAND["line"])),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _insight(label, value, note, styles):
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    label_style = ParagraphStyle(f"{label}Label", parent=styles["KpiLabel"], alignment=TA_LEFT, fontSize=7.2, leading=9)
    value_style = ParagraphStyle(f"{label}Value", parent=styles["KpiValue"], alignment=TA_LEFT, fontSize=13, leading=15)
    note_style = ParagraphStyle(f"{label}Note", parent=styles["Meta"], fontSize=7.3, leading=9)
    return [Paragraph(label.upper(), label_style), Paragraph(value, value_style), Paragraph(note, note_style)]


def _build_interpretation_panel(data, styles):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table

    avg_grade = _avg([student.course_grade for student in data.students])
    weakest_lo = min(data.learning_outcomes, key=lambda item: _avg(item.scores))
    weakest_score = _avg(weakest_lo.scores)
    at_risk = sorted(
        [student for student in data.students if student.course_grade < THEME["thresholds"]["danger"]],
        key=lambda item: item.course_grade,
    )
    text = (
        f"The course average is <b>{avg_grade:.1f}%</b>. "
        f"<b>{escape(weakest_lo.code)}</b> is the weakest outcome at <b>{weakest_score:.1f}%</b>, "
        f"suggesting that {escape(weakest_lo.title.lower())} should receive additional reinforcement. "
        f"{len(at_risk)} student{'s' if len(at_risk) != 1 else ''} are below the intervention threshold."
    )
    table = Table(
        [
            [Paragraph("Summary Interpretation", styles["SectionTitle"])],
            [Paragraph(text, styles["BodyTextSmall"])],
            [_build_threshold_legend(styles)],
        ],
        colWidths=[92 * mm],
    )
    table.setStyle(_panel_style(colors))
    return table


def _build_threshold_legend(styles):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    title_style = ParagraphStyle(
        "ThresholdLegendTitle",
        parent=styles["KpiLabel"],
        alignment=TA_CENTER,
        fontSize=7.4,
        leading=9,
        textColor=colors.HexColor(BRAND["teal"]),
    )
    label_style = ParagraphStyle(
        "ThresholdLegendLabel",
        parent=styles["BodyTextSmall"],
        fontSize=7.0,
        leading=8.2,
        alignment=TA_CENTER,
    )

    items = [
        (BRAND["red"], "Danger", "&lt; 60", "Immediate action"),
        (BRAND["amber"], "Warning", "60-69", "At risk"),
        (BRAND["blue"], "Developing", "70-79", "On track"),
        (BRAND["teal"], "Success", "&gt;= 80", "Meets target"),
    ]

    item_tables = []
    for color, label, score_range, note in items:
        swatch = Table([[""]], colWidths=[3 * mm], rowHeights=[3 * mm])
        swatch.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(color)),
                    ("BOX", (0, 0), (-1, -1), 0.2, colors.HexColor(color)),
                ]
            )
        )
        item = Table(
            [
                [swatch],
                [
                    Paragraph(
                        f"<b>{label}</b><br/>{score_range}<br/><font color='{BRAND['muted']}'>{note}</font>",
                        label_style,
                    )
                ],
            ],
            colWidths=[17 * mm],
        )
        item.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 0.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0.5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0.5),
                ]
            )
        )
        item_tables.append(item)

    legend = Table(
        [
            [Paragraph("THRESHOLD LEGEND", title_style), "", "", ""],
            item_tables,
        ],
        colWidths=[19 * mm, 19 * mm, 19 * mm, 19 * mm],
    )
    legend.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor(BRAND["teal"])),
                ("INNERGRID", (0, 1), (-1, -1), 0.35, colors.HexColor(BRAND["line"])),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 0.5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0.5),
            ]
        )
    )
    return legend


def _build_recommendations_panel(data, styles):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table

    weakest_lo = min(data.learning_outcomes, key=lambda item: _avg(item.scores))
    difficult_assessment = min(data.assessments, key=lambda item: _avg(item.scores))
    at_risk = sorted(
        [student for student in data.students if student.course_grade < THEME["thresholds"]["danger"]],
        key=lambda item: item.course_grade,
    )
    support_names = ", ".join(escape(student.name) for student in at_risk[:5]) or "No students currently below threshold"
    rows = [
        [Paragraph("Recommended Actions", styles["SectionTitle"])],
        [
            Paragraph(
                f"1. Reinforce <b>{escape(weakest_lo.code)}</b> ({escape(weakest_lo.title)}) "
                "with targeted practice and a short reassessment.",
                styles["BodyTextSmall"],
            )
        ],
        [
            Paragraph(
                f"2. Review <b>{escape(difficult_assessment.name)}</b> evidence and rubric alignment "
                "before closing the course file.",
                styles["BodyTextSmall"],
            )
        ],
        [Paragraph(f"3. Prioritize support meetings for: <b>{support_names}</b>.", styles["BodyTextSmall"])],
    ]
    table = Table(rows, colWidths=[180 * mm])
    table.setStyle(_panel_style(colors))
    return table


def _chart_panel(title, image, width, note=None):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table

    title_style = ParagraphStyle(
        f"{title}Style",
        fontName=PDF_FONT_BOLD,
        fontSize=9.5,
        leading=11,
        textColor=colors.HexColor(BRAND["ink"]),
    )
    rows = [[Paragraph(title, title_style)], [Spacer(1, 1.2 * mm)], [image]]
    if note:
        note_style = ParagraphStyle(
            f"{title}Note",
            fontName=PDF_FONT_REGULAR,
            fontSize=7.3,
            leading=9,
            textColor=colors.HexColor(BRAND["muted"]),
        )
        rows.append([Paragraph(note, note_style)])
    table = Table(rows, colWidths=[width])
    table.setStyle(_panel_style(colors))
    return table


def _chart_image(fig, width, height, pixel_width=980, pixel_height=620):
    try:
        import plotly.io as pio
        from reportlab.platypus import Image
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("Course PDF charts require plotly and kaleido to be installed.") from exc

    png_bytes = pio.to_image(fig, format="png", width=pixel_width, height=pixel_height, scale=2)
    return Image(BytesIO(png_bytes), width=width, height=height)


def _grade_distribution_figure(data):
    import plotly.graph_objects as go

    buckets = [(0, 49), (50, 59), (60, 69), (70, 79), (80, 89), (90, 100)]
    labels = [f"{low}-{high}" for low, high in buckets]
    counts = [len([s for s in data.students if low <= s.course_grade <= high]) for low, high in buckets]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=counts,
            marker_color=[score_color((low + high) / 2) for low, high in buckets],
        )
    )
    return _style_fig(fig, y_title="Students", x_title="Course grade band")


def _lo_average_figure(data):
    import plotly.graph_objects as go

    values = sorted([(lo.code, _avg(lo.scores), lo.title) for lo in data.learning_outcomes], key=lambda item: item[1])
    fig = go.Figure(
        go.Bar(
            x=[item[1] for item in values],
            y=[item[0] for item in values],
            orientation="h",
            text=[f"{item[1]:.1f}%" for item in values],
            textposition="outside",
            marker_color=[score_color(item[1]) for item in values],
            hovertext=[item[2] for item in values],
        )
    )
    fig.update_traces(width=0.58, cliponaxis=False)
    fig.update_xaxes(range=[0, 104])
    fig = _style_fig(fig, x_title="Average score", y_title="", margin={"l": 86, "r": 46, "t": 24, "b": 54})
    fig.update_yaxes(ticklabelposition="outside", ticklabelstandoff=14, ticksuffix="  ")
    return fig


def _assessment_figure(data):
    import plotly.graph_objects as go

    fig = go.Figure(
        go.Bar(
            x=[assessment.name for assessment in data.assessments],
            y=[_avg(assessment.scores) for assessment in data.assessments],
            text=[f"{_avg(a.scores):.1f}% · w {a.weight:.0%}" for a in data.assessments],
            textposition="outside",
            marker_color=[score_color(_avg(assessment.scores)) for assessment in data.assessments],
        )
    )
    fig.update_yaxes(range=[0, 100])
    return _style_fig(fig, y_title="Average score", x_title="")


def _lo_box_figure(data):
    import plotly.graph_objects as go

    fig = go.Figure()
    for lo in data.learning_outcomes:
        fig.add_trace(go.Box(y=list(lo.scores), name=lo.code, boxmean=True, marker_color=score_color(_avg(lo.scores))))
    fig.update_yaxes(range=[0, 100])
    return _style_fig(fig, y_title="Score spread", x_title="")


def _student_heatmap_figure(data):
    import plotly.graph_objects as go

    weakest_students = sorted(data.students, key=lambda item: item.course_grade)[:10]
    lo_codes = [lo.code for lo in data.learning_outcomes]
    z = [[student.lo_scores.get(code, 0) for code in lo_codes] for student in weakest_students]
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=lo_codes,
            y=[student.name for student in weakest_students],
            colorscale=[
                [0.0, BRAND["red"]],
                [0.6, BRAND["amber"]],
                [0.8, BRAND["blue"]],
                [1.0, BRAND["green"]],
            ],
            zmin=0,
            zmax=100,
            colorbar={"title": "LO score"},
        )
    )
    return _style_fig(fig, x_title="", y_title="")


def _style_fig(fig, x_title="", y_title="", margin=None):
    margin = margin or {"l": 58, "r": 30, "t": 24, "b": 54}
    fig.update_layout(
        template="plotly_white",
        margin=margin,
        font={"family": PDF_FONT_FAMILY, "size": 15, "color": BRAND["ink"]},
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=False,
    )
    fig.update_xaxes(title=x_title, gridcolor="#E5EAF0", zeroline=False, title_font={"size": 15}, tickfont={"size": 14})
    fig.update_yaxes(title=y_title, gridcolor="#E5EAF0", zeroline=False, title_font={"size": 15}, tickfont={"size": 14})
    return fig


def _draw_page_frame(canvas, doc):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm

    width, height = A4
    canvas.saveState()
    canvas.setFillColor(colors.HexColor(BRAND["panel"]))
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor(BRAND["teal"]))
    canvas.rect(0, height - 5 * mm, width, 5 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor(BRAND["muted"]))
    ensure_pdf_fonts()
    canvas.setFont(PDF_FONT_REGULAR, 7)
    canvas.drawRightString(width - 12 * mm, 6 * mm, f"Page {doc.page} · SES Analytics")
    canvas.restoreState()


def _panel_style(colors):
    from reportlab.platypus import TableStyle

    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(BRAND["white"])),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(BRAND["line"])),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
    )


def _gridless_table_style(span_rows=None):
    from reportlab.lib import colors
    from reportlab.platypus import TableStyle

    span_rows = span_rows or []
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(BRAND["panel"])),
    ]
    for row in span_rows:
        commands.append(("SPAN", (0, row), (1, row)))
    return TableStyle(commands)


def score_color(score: float) -> str:
    if score < THEME["thresholds"]["danger"]:
        return BRAND["red"]
    if score < THEME["thresholds"]["warning"]:
        return BRAND["amber"]
    if score < THEME["thresholds"]["success"]:
        return BRAND["blue"]
    return BRAND["teal"]


def _avg(values: Sequence[float]) -> float:
    return float(mean(values)) if values else 0.0


def _score_range(values: Sequence[float]) -> float:
    return max(values) - min(values) if values else 0.0


def _grade_coverage(data: CourseReportData) -> float:
    expected = data.enrolled_students * len(data.assessments)
    actual = sum(len(assessment.scores) for assessment in data.assessments)
    return (actual / expected) * 100 if expected else 0.0
