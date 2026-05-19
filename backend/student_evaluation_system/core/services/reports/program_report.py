from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape
from io import BytesIO
from statistics import mean
from typing import Sequence

from django.db.models import Count
from django.utils import timezone

from core.models import Course, LearningOutcomeProgramOutcomeMapping, Program, ProgramOutcome, StudentProgramOutcomeScore, Term
from core.services.analytics.program import get_active_term, get_student_course_grade_map
from evaluation.models import CourseEnrollment

from .course_report import (
    BRAND,
    PDF_FONT_BOLD,
    PDF_FONT_FAMILY,
    PDF_FONT_REGULAR,
    THEME,
    _avg,
    _chart_image,
    _chart_panel,
    _draw_page_frame,
    _gridless_table_style,
    _panel_style,
    ReportDataError,
    ensure_pdf_fonts,
    score_color,
)


@dataclass(frozen=True)
class ProgramOutcomeReportData:
    code: str
    description: str
    scores: Sequence[float]
    contributing_courses: int


@dataclass(frozen=True)
class ProgramCourseReportData:
    code: str
    name: str
    average_score: float
    outcome_coverage: int


@dataclass(frozen=True)
class ProgramStudentRiskReportData:
    name: str
    program_average: float
    po_scores: dict[str, float]


@dataclass(frozen=True)
class ProgramReportData:
    program_code: str
    program_name: str
    department: str
    degree_level: str
    term: str
    generated_on: date
    enrolled_students: int
    active_courses: Sequence[ProgramCourseReportData]
    program_outcomes: Sequence[ProgramOutcomeReportData]
    students: Sequence[ProgramStudentRiskReportData]


def generate_program_report_pdf(data: ProgramReportData) -> bytes:
    """Generate a two-page institutional program outcome report."""

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer, Table
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("Program PDF reports require reportlab to be installed.") from exc

    ensure_pdf_fonts()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=f"{data.program_code} Program Outcome Report",
    )

    styles = _build_styles(colors, ParagraphStyle, getSampleStyleSheet(), TA_LEFT, TA_CENTER)

    story = []
    story.extend(_build_header(data, styles))
    story.append(Spacer(1, THEME["spacing"]["sm"] * mm))
    story.append(_build_kpi_table(data, styles))
    story.append(Spacer(1, THEME["spacing"]["sm"] * mm))
    story.append(
        _chart_panel(
            "Program Outcome Achievement",
            _chart_image(
                _po_average_figure(data),
                168 * mm,
                80 * mm,
                pixel_width=1260,
                pixel_height=600,
            ),
            width=180 * mm,
            note="Program outcomes are ordered from lowest to highest. Color bands follow the institutional threshold legend.",
        )
    )
    story.append(Spacer(1, THEME["spacing"]["sm"] * mm))
    story.append(
        Table(
            [
                [
                    _chart_panel(
                        "Course Contribution Overview",
                        _chart_image(
                            _course_contribution_figure(data),
                            78 * mm,
                            43 * mm,
                            pixel_width=860,
                            pixel_height=520,
                        ),
                        width=86 * mm,
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
    story.append(
        Table(
            [
                [
                    _chart_panel(
                        "PO Score Spread",
                        _chart_image(_po_box_figure(data), 82 * mm, 52 * mm, pixel_width=900, pixel_height=560),
                        width=88 * mm,
                    ),
                    _chart_panel(
                        "Course Outcome Coverage",
                        _chart_image(_coverage_figure(data), 82 * mm, 52 * mm, pixel_width=900, pixel_height=560),
                        width=88 * mm,
                    ),
                ],
                [
                    _chart_panel(
                        "Intervention Priority Heatmap",
                        _chart_image(
                            _student_heatmap_figure(data),
                            174 * mm,
                            68 * mm,
                            pixel_width=1392,
                            pixel_height=544,
                        ),
                        width=180 * mm,
                        note=(
                            "Rows are the 10 students with the lowest program averages. "
                            "Use this view to target PO-specific support."
                        ),
                    ),
                    "",
                ],
                [_build_recommendations_panel(data, styles), ""],
            ],
            colWidths=[90 * mm, 90 * mm],
            rowHeights=[66 * mm, 94 * mm, 52 * mm],
            style=_gridless_table_style(span_rows=[1, 2]),
        )
    )

    doc.build(story, onFirstPage=_draw_page_frame, onLaterPages=_draw_page_frame)
    return buffer.getvalue()


def build_program_report_data(program_id, term_id=None) -> ProgramReportData:
    program = Program.objects.select_related("department", "degree_level").get(pk=program_id)
    try:
        term = Term.objects.filter(pk=term_id).first() if term_id else get_active_term()
    except (TypeError, ValueError):
        term = None
    if term is None:
        raise ReportDataError("Program report requires an existing term.")

    courses = list(Course.objects.filter(program=program, term=term).order_by("code", "id"))
    program_outcomes = list(ProgramOutcome.objects.filter(program=program, term=term).order_by("code", "id"))
    if not courses:
        raise ReportDataError("Program report requires at least one course in the selected term.")
    if not program_outcomes:
        raise ReportDataError("Program report requires at least one program outcome in the selected term.")

    course_ids = [course.id for course in courses]
    po_ids = [po.id for po in program_outcomes]
    enrollments = list(
        CourseEnrollment.objects.filter(course__program=program, course__term=term, status="active")
        .select_related("student")
        .order_by("student__username")
    )
    students_by_id = {}
    for enrollment in enrollments:
        students_by_id[enrollment.student_id] = enrollment.student
    student_ids = list(students_by_id)

    course_grade_map = get_student_course_grade_map(student_ids, course_ids)
    course_averages = _course_averages(course_grade_map, course_ids)
    coverage_by_course = _course_po_coverage(course_ids, po_ids)
    coverage_by_po = _po_course_coverage(course_ids, po_ids)

    po_score_rows = StudentProgramOutcomeScore.objects.filter(
        student_id__in=student_ids,
        program_outcome_id__in=po_ids,
        term=term,
    ).values("student_id", "program_outcome_id", "score")
    po_score_map = {(row["student_id"], row["program_outcome_id"]): float(row["score"] or 0) for row in po_score_rows}

    active_courses = [
        ProgramCourseReportData(
            code=course.code,
            name=course.name,
            average_score=round(course_averages.get(course.id, 0.0), 1),
            outcome_coverage=coverage_by_course.get(course.id, 0),
        )
        for course in courses
    ]
    program_outcome_data = [
        ProgramOutcomeReportData(
            code=po.code,
            description=po.description,
            scores=[po_score_map.get((student_id, po.id), 0.0) for student_id in student_ids],
            contributing_courses=coverage_by_po.get(po.id, 0),
        )
        for po in program_outcomes
    ]
    students = []
    for student_id, student in students_by_id.items():
        po_values = {po.code: po_score_map.get((student_id, po.id), 0.0) for po in program_outcomes}
        students.append(
            ProgramStudentRiskReportData(
                name=_display_name(student),
                program_average=round(mean(po_values.values()), 1) if po_values else 0.0,
                po_scores=po_values,
            )
        )

    return ProgramReportData(
        program_code=program.code,
        program_name=program.name,
        department=program.department.name,
        degree_level=program.degree_level.name,
        term=term.name,
        generated_on=timezone.localdate(),
        enrolled_students=len(students_by_id),
        active_courses=active_courses,
        program_outcomes=program_outcome_data,
        students=students,
    )


def _course_averages(course_grade_map, course_ids):
    scores_by_course = {course_id: [] for course_id in course_ids}
    for (_student_id, course_id), (weighted_sum, total_weight, _credits) in course_grade_map.items():
        if total_weight > 0:
            scores_by_course[course_id].append(weighted_sum / total_weight)
    return {course_id: mean(scores) if scores else 0.0 for course_id, scores in scores_by_course.items()}


def _course_po_coverage(course_ids, po_ids):
    rows = (
        LearningOutcomeProgramOutcomeMapping.objects.filter(course_id__in=course_ids, program_outcome_id__in=po_ids)
        .values("course_id")
        .annotate(total=Count("program_outcome_id", distinct=True))
        .values_list("course_id", "total")
    )
    return {**{course_id: 0 for course_id in course_ids}, **dict(rows)}


def _po_course_coverage(course_ids, po_ids):
    rows = (
        LearningOutcomeProgramOutcomeMapping.objects.filter(course_id__in=course_ids, program_outcome_id__in=po_ids)
        .values("program_outcome_id")
        .annotate(total=Count("course_id", distinct=True))
        .values_list("program_outcome_id", "total")
    )
    return {**{po_id: 0 for po_id in po_ids}, **dict(rows)}


def _display_name(user) -> str:
    return user.get_full_name() or user.username


def _build_styles(colors, paragraph_style_cls, styles, ta_left, ta_center):
    styles.add(
        paragraph_style_cls(
            name="ReportTitle",
            parent=styles["Title"],
            fontName=PDF_FONT_BOLD,
            fontSize=18,
            leading=22,
            textColor=colors.HexColor(BRAND["ink"]),
            alignment=ta_left,
            spaceAfter=3,
        )
    )
    styles.add(
        paragraph_style_cls(
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
        paragraph_style_cls(
            name="Meta",
            parent=styles["Normal"],
            fontName=PDF_FONT_REGULAR,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor(BRAND["muted"]),
        )
    )
    styles.add(
        paragraph_style_cls(
            name="BodyTextSmall",
            parent=styles["Normal"],
            fontName=PDF_FONT_REGULAR,
            fontSize=8.4,
            leading=11.2,
            textColor=colors.HexColor(BRAND["ink"]),
        )
    )
    styles.add(
        paragraph_style_cls(
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
        paragraph_style_cls(
            name="KpiLabel",
            parent=styles["Normal"],
            fontName=PDF_FONT_BOLD,
            fontSize=6.8,
            leading=8,
            textColor=colors.HexColor(BRAND["muted"]),
            alignment=ta_center,
        )
    )
    styles.add(
        paragraph_style_cls(
            name="KpiValue",
            parent=styles["Normal"],
            fontName=PDF_FONT_BOLD,
            fontSize=17,
            leading=19,
            textColor=colors.HexColor(BRAND["ink"]),
            alignment=ta_center,
        )
    )
    return styles


def _build_header(data, styles):
    from reportlab.platypus import Paragraph

    return [
        Paragraph("PROGRAM OUTCOME REPORT", styles["Eyebrow"]),
        Paragraph(f"{data.program_code} · {data.program_name}", styles["ReportTitle"]),
        Paragraph(
            f"{data.department} · {data.degree_level} · {data.term} · Generated {data.generated_on.isoformat()}",
            styles["Meta"],
        ),
    ]


def _build_page_two_header(data, styles):
    from reportlab.platypus import Paragraph

    return [
        Paragraph("DIAGNOSTIC BREAKDOWN", styles["Eyebrow"]),
        Paragraph(f"{data.program_code} · Program Outcome Detail", styles["ReportTitle"]),
        Paragraph(
            "Outcome spread, course contribution, student support priorities, and accreditation follow-up notes.",
            styles["Meta"],
        ),
    ]


def _build_kpi_table(data, styles):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    avg_po = _avg([score for po in data.program_outcomes for score in po.scores])
    at_risk = len([student for student in data.students if student.program_average < THEME["thresholds"]["danger"]])
    weak_pos = len([po for po in data.program_outcomes if _avg(po.scores) < THEME["thresholds"]["warning"]])
    coverage = _avg([course.outcome_coverage for course in data.active_courses])
    kpis = [
        ("ENROLLED", f"{data.enrolled_students}"),
        ("AVG PO SCORE", f"{avg_po:.1f}%"),
        ("AT RISK", f"{at_risk}"),
        ("WEAK POs", f"{weak_pos}"),
        ("ACTIVE COURSES", f"{len(data.active_courses)}"),
        ("AVG COVERAGE", f"{coverage:.1f}"),
    ]
    cells = [[Paragraph(value, styles["KpiValue"]), Paragraph(label, styles["KpiLabel"])] for label, value in kpis]
    table = Table([cells], colWidths=[30 * mm for _ in cells])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(BRAND["white"])),
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
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

    weakest_po = min(data.program_outcomes, key=lambda item: _avg(item.scores))
    weakest_course = min(data.active_courses, key=lambda item: item.average_score)
    coverage_gap = min(data.program_outcomes, key=lambda item: item.contributing_courses)
    at_risk = len([student for student in data.students if student.program_average < THEME["thresholds"]["danger"]])

    def insight(label, value, note):
        label_style = ParagraphStyle(
            f"Program{label}Label", parent=styles["KpiLabel"], alignment=TA_LEFT, fontSize=7.2, leading=9
        )
        value_style = ParagraphStyle(
            f"Program{label}Value", parent=styles["KpiValue"], alignment=TA_LEFT, fontSize=13, leading=15
        )
        note_style = ParagraphStyle(f"Program{label}Note", parent=styles["Meta"], fontSize=7.3, leading=9)
        return [Paragraph(label.upper(), label_style), Paragraph(value, value_style), Paragraph(note, note_style)]

    rows = [
        [
            insight(
                "Action needed",
                f"{weakest_po.code} · {_avg(weakest_po.scores):.1f}%",
                f"Review curriculum evidence for {weakest_po.description.lower()}.",
            ),
            insight(
                "Course review",
                f"{weakest_course.code} · {weakest_course.average_score:.1f}%",
                "Check whether assessment evidence aligns with mapped POs.",
            ),
            insight(
                "Coverage gap",
                f"{coverage_gap.code} · {coverage_gap.contributing_courses} courses",
                "Confirm this outcome is represented across the curriculum.",
            ),
            insight("Support queue", f"{at_risk} students", "Program average below the intervention threshold."),
        ]
    ]
    table = Table(rows, colWidths=[45 * mm, 45 * mm, 45 * mm, 45 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(BRAND["white"])),
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


def _build_interpretation_panel(data, styles):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table

    avg_po = _avg([score for po in data.program_outcomes for score in po.scores])
    weakest_po = min(data.program_outcomes, key=lambda item: _avg(item.scores))
    at_risk = len([student for student in data.students if student.program_average < THEME["thresholds"]["danger"]])
    text = (
        f"The program outcome average is <b>{avg_po:.1f}%</b>. "
        f"<b>{escape(weakest_po.code)}</b> is the weakest outcome at <b>{_avg(weakest_po.scores):.1f}%</b>, "
        f"suggesting that curriculum evidence for {escape(weakest_po.description.lower())} needs review. "
        f"{at_risk} student{'s' if at_risk != 1 else ''} "
        f"{'are' if at_risk != 1 else 'is'} below the intervention threshold."
    )

    table = Table(
        [
            [Paragraph("Summary Interpretation", styles["SectionTitle"])],
            [Paragraph(text, styles["BodyTextSmall"])],
            [_build_threshold_legend(styles)],
        ],
        colWidths=[94 * mm],
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

    weakest_po = min(data.program_outcomes, key=lambda item: _avg(item.scores))
    weakest_course = min(data.active_courses, key=lambda item: item.average_score)
    at_risk = sorted(
        [student for student in data.students if student.program_average < THEME["thresholds"]["danger"]],
        key=lambda item: item.program_average,
    )
    support_names = ", ".join(escape(student.name) for student in at_risk[:5]) or "No students currently below threshold"
    rows = [
        [Paragraph("Recommended Actions", styles["SectionTitle"])],
        [
            Paragraph(
                f"1. Reinforce <b>{escape(weakest_po.code)}</b> evidence across mapped courses "
                "and document corrective action.",
                styles["BodyTextSmall"],
            )
        ],
        [
            Paragraph(
                f"2. Review <b>{escape(weakest_course.code)}</b> assessment alignment before closing the program file.",
                styles["BodyTextSmall"],
            )
        ],
        [Paragraph(f"3. Prioritize program-level support for: <b>{support_names}</b>.", styles["BodyTextSmall"])],
    ]
    table = Table(rows, colWidths=[180 * mm])
    table.setStyle(_panel_style(colors))
    return table


def _po_average_figure(data):
    import plotly.graph_objects as go

    values = sorted([(po.code, _avg(po.scores), po.description) for po in data.program_outcomes], key=lambda item: item[1])
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
    fig = _style_program_fig(fig, x_title="Average score", y_title="", margin={"l": 86, "r": 46, "t": 24, "b": 54})
    fig.update_yaxes(ticklabelposition="outside", ticklabelstandoff=14, ticksuffix="  ")
    return fig


def _course_contribution_figure(data):
    import plotly.graph_objects as go

    fig = go.Figure(
        go.Bar(
            x=[course.code for course in data.active_courses],
            y=[course.average_score for course in data.active_courses],
            text=[f"{course.average_score:.1f}%" for course in data.active_courses],
            textposition="outside",
            marker_color=[score_color(course.average_score) for course in data.active_courses],
        )
    )
    fig.update_yaxes(range=[0, 100])
    return _style_program_fig(fig, y_title="Average score", x_title="")


def _po_box_figure(data):
    import plotly.graph_objects as go

    fig = go.Figure()
    for po in data.program_outcomes:
        fig.add_trace(go.Box(y=list(po.scores), name=po.code, boxmean=True, marker_color=score_color(_avg(po.scores))))
    fig.update_yaxes(range=[0, 100])
    return _style_program_fig(fig, y_title="Score spread", x_title="")


def _coverage_figure(data):
    import plotly.graph_objects as go

    fig = go.Figure(
        go.Bar(
            x=[po.code for po in data.program_outcomes],
            y=[po.contributing_courses for po in data.program_outcomes],
            marker_color=BRAND["blue"],
        )
    )
    return _style_program_fig(fig, y_title="Mapped courses", x_title="")


def _student_heatmap_figure(data):
    import plotly.graph_objects as go

    weakest_students = sorted(data.students, key=lambda item: item.program_average)[:10]
    po_codes = [po.code for po in data.program_outcomes]
    z = [[student.po_scores.get(code, 0) for code in po_codes] for student in weakest_students]
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=po_codes,
            y=[student.name for student in weakest_students],
            colorscale=[
                [0.0, BRAND["red"]],
                [0.6, BRAND["amber"]],
                [0.8, BRAND["blue"]],
                [1.0, BRAND["green"]],
            ],
            zmin=0,
            zmax=100,
            colorbar={"title": "PO score"},
        )
    )
    return _style_program_fig(fig, x_title="", y_title="")


def _style_program_fig(fig, x_title="", y_title="", margin=None):
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
