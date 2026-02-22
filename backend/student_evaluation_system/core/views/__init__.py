"""
Core app views organized by domain.

This package splits the large views.py into focused modules:
- academic_structure: Universities, Departments, DegreeLevels, Programs, Terms
- course: Courses, ProgramOutcomes, LearningOutcomes, Mappings
- scores: StudentLearningOutcomeScore, StudentProgramOutcomeScore
- file_import: File import ViewSets

For backwards compatibility, all ViewSets are exported from this module.
"""

# Academic Structure
from .academic_structure import (
    UniversityViewSet,
    DepartmentViewSet,
    DegreeLevelViewSet,
    ProgramViewSet,
    TermViewSet,
    StudentListView,
    StudentDetailView,
    CourseListView,
    CourseDetailView,
    ProgramOutcomeListView,
    ProgramOutcomeDetailView,
)

# Course & Outcomes
from .course import (
    CourseViewSet,
    ProgramOutcomeViewSet,
    LearningOutcomeViewSet,
    LearningOutcomeProgramOutcomeMappingViewSet,
)

# Scores
from .scores import (
    StudentLearningOutcomeScoreViewSet,
    StudentProgramOutcomeScoreViewSet,
)

# File Import
from .file_import import (
    AssignmentScoresImportViewSet,
    LearningOutcomesImportViewSet,
    ProgramOutcomesImportViewSet,
    FileUploadRateThrottle,
)

__all__ = [
    # Academic Structure
    "UniversityViewSet",
    "DepartmentViewSet",
    "DegreeLevelViewSet",
    "ProgramViewSet",
    "TermViewSet",
    "StudentListView",
    "StudentDetailView",
    "CourseListView",
    "CourseDetailView",
    "ProgramOutcomeListView",
    "ProgramOutcomeDetailView",
    # Course & Outcomes
    "CourseViewSet",
    "ProgramOutcomeViewSet",
    "LearningOutcomeViewSet",
    "LearningOutcomeProgramOutcomeMappingViewSet",
    # Scores
    "StudentLearningOutcomeScoreViewSet",
    "StudentProgramOutcomeScoreViewSet",
    # File Import
    "AssignmentScoresImportViewSet",
    "LearningOutcomesImportViewSet",
    "ProgramOutcomesImportViewSet",
    "FileUploadRateThrottle",
]
