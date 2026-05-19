from rest_framework import serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.permissions import IsAdminOrProgramHead
from core.services.analytics.program import (
    build_program_stats,
    calculate_gpa_by_year,
    calculate_year_level_breakdown,
    get_active_term,
    get_active_term_student_counts_by_program,
    get_programs_for_user,
    get_term_course_counts_by_program,
    get_term_course_ids,
    get_term_lo_counts_by_program,
    get_term_po_counts_by_program,
    get_term_po_ids,
    get_term_po_score_stats_by_program,
)


class ProgramStatSerializer(drf_serializers.Serializer):
    id = drf_serializers.IntegerField()
    code = drf_serializers.CharField()
    name = drf_serializers.CharField()
    total_students = drf_serializers.IntegerField()
    total_courses = drf_serializers.IntegerField()
    avg_score = drf_serializers.FloatField(allow_null=True)
    lo_count = drf_serializers.IntegerField()
    po_count = drf_serializers.IntegerField()


class YearLevelBreakdownSerializer(drf_serializers.Serializer):
    year = drf_serializers.IntegerField()
    student_count = drf_serializers.IntegerField()
    avg_score = drf_serializers.FloatField(allow_null=True)


class GpaByYearSerializer(drf_serializers.Serializer):
    year = drf_serializers.IntegerField()
    student_count = drf_serializers.IntegerField()
    gpa = drf_serializers.FloatField(allow_null=True)


class ProgramStatsResponseSerializer(drf_serializers.Serializer):
    programs = ProgramStatSerializer(many=True)
    year_level_breakdown = YearLevelBreakdownSerializer(many=True)
    gpa_by_year = GpaByYearSerializer(many=True)


@extend_schema(
    responses=ProgramStatsResponseSerializer,
    tags=["Analytics"],
)
class ProgramStatsView(APIView):
    """Analytics endpoint for program heads and admins."""

    permission_classes = [IsAuthenticated, IsAdminOrProgramHead]

    def get(self, request):
        """
        Return aggregated statistics scoped to the user's programs.

        Admins see all programs. Program heads see only their program.
        """
        user = request.user

        programs = get_programs_for_user(user)
        if programs is None:
            return Response({"detail": "No program head profile found."}, status=403)

        program_list = list(programs)
        program_ids = [p.id for p in program_list]

        active_term = get_active_term()
        courses_map = get_term_course_counts_by_program(program_ids, active_term)
        students_map = get_active_term_student_counts_by_program(program_ids, active_term)
        po_score_map = get_term_po_score_stats_by_program(program_ids, active_term)
        po_count_map = get_term_po_counts_by_program(program_ids, active_term)
        lo_map = get_term_lo_counts_by_program(program_ids, active_term)
        active_course_ids = get_term_course_ids(program_ids, active_term)
        active_po_ids = get_term_po_ids(program_ids, active_term)
        program_stats, max_duration_years = build_program_stats(
            program_list,
            students_map,
            courses_map,
            po_score_map,
            po_count_map,
            lo_map,
        )

        year_level_breakdown = calculate_year_level_breakdown(
            active_course_ids,
            active_po_ids,
            max_duration_years,
            active_term=active_term,
        )

        gpa_by_year = calculate_gpa_by_year(active_course_ids, max_duration_years, active_term=active_term)

        return Response(
            {
                "programs": program_stats,
                "year_level_breakdown": year_level_breakdown,
                "gpa_by_year": gpa_by_year,
            }
        )
