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
)

# Course & Outcomes
from .course import (
    CourseViewSet,
    ProgramOutcomeViewSet,
    LearningOutcomeViewSet,
    LearningOutcomeProgramOutcomeMappingViewSet,
)

# Course Templates
from .course_templates import (
    CourseTemplateViewSet,
    CourseTemplateAssessmentLOMappingViewSet,
    CourseTemplateLOPOMappingViewSet,
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

# Permissions
from .permissions import InstructorPermissionViewSet

# Weight Suggestion
from .weight_suggestion import WeightSuggestionViewSet

# Analytics
from .analytics import ProgramStatsView

__all__ = [
    # Academic Structure
    "UniversityViewSet",
    "DepartmentViewSet",
    "DegreeLevelViewSet",
    "ProgramViewSet",
    "TermViewSet",
    "StudentListView",
    # Course & Outcomes
    "CourseViewSet",
    "ProgramOutcomeViewSet",
    "LearningOutcomeViewSet",
    "LearningOutcomeProgramOutcomeMappingViewSet",
    # Course Templates
    "CourseTemplateViewSet",
    "CourseTemplateAssessmentLOMappingViewSet",
    "CourseTemplateLOPOMappingViewSet",
    # Scores
    "StudentLearningOutcomeScoreViewSet",
    "StudentProgramOutcomeScoreViewSet",
    # File Import
    "AssignmentScoresImportViewSet",
    "LearningOutcomesImportViewSet",
    "ProgramOutcomesImportViewSet",
    "FileUploadRateThrottle",
    # Permissions
    "InstructorPermissionViewSet",
    # Weight Suggestion
    "WeightSuggestionViewSet",
    # Analytics
    "ProgramStatsView",
]
