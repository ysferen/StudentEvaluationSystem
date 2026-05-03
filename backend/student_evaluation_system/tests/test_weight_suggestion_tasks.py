"""Tests for weight suggestion Celery tasks."""

import pytest
from unittest.mock import MagicMock, patch


class TestSuggestAssessmentLOTask:
    """Tests for suggest_assessment_lo_weights_task."""

    def test_task_is_registered(self):
        """Verify the task is importable and has celery attributes."""
        from core.tasks import suggest_assessment_lo_weights_task

        assert suggest_assessment_lo_weights_task is not None
        assert hasattr(suggest_assessment_lo_weights_task, "delay")
        assert hasattr(suggest_assessment_lo_weights_task, "name")

    def test_task_returns_correct_schema(self):
        """Task result must have 'assessment_lo' key with expected structure."""
        from core.tasks import suggest_assessment_lo_weights_task

        mock_suggester = MagicMock()
        mock_suggester.suggest_assessment_lo.return_value = {
            "assessment_lo": {
                "Midterm": {"LO1": 4, "LO2": 2},
                "Final": {"LO1": 3, "LO2": 5},
            }
        }

        mock_course = MagicMock()
        mock_course.name = "Test Course"
        mock_course.learning_outcomes.values_list.return_value = [
            "LO1: desc a",
            "LO2: desc b",
        ]
        mock_course.assessments.all.return_value = []

        with patch("core.tasks._suggester", mock_suggester), patch("core.models.Course") as mock_course_model:
            mock_course_model.objects.get.return_value = mock_course

            result = suggest_assessment_lo_weights_task(course_id=42)

            assert isinstance(result, dict)
            assert "assessment_lo" in result
            weights = result["assessment_lo"]
            assert isinstance(weights, dict)
            for assessment_name, lo_weights in weights.items():
                assert isinstance(lo_weights, dict)
                for lo_key, weight in lo_weights.items():
                    assert isinstance(weight, int)
                    assert 0 <= weight <= 5

    def test_task_updates_job_status_on_success(self):
        """Task should update job to success with result."""
        from core.tasks import suggest_assessment_lo_weights_task

        mock_suggester = MagicMock()
        mock_suggester.suggest_assessment_lo.return_value = {"assessment_lo": {"Midterm": {"LO1": 3, "LO2": 4}}}

        mock_course = MagicMock()
        mock_course.name = "Test Course"
        mock_course.learning_outcomes.values_list.return_value = [
            "LO1: desc a",
            "LO2: desc b",
        ]
        mock_course.assessments.all.return_value = []

        with (
            patch("core.tasks._suggester", mock_suggester),
            patch("core.models.Course") as mock_course_model,
            patch("core.models.WeightSuggestionJob") as mock_job_model,
            patch("core.tasks.timezone") as mock_tz,
        ):
            mock_course_model.objects.get.return_value = mock_course
            mock_filter = MagicMock()
            mock_job_model.objects.filter.return_value = mock_filter
            mock_tz.now.return_value = "2025-01-01T00:00:00Z"

            suggest_assessment_lo_weights_task(course_id=42, job_id=99)

            # Verify the last update call set status=success, result, and finished_at
            last_update = mock_filter.update.call_args_list[-1]
            last_kwargs = last_update[1]
            assert last_kwargs["status"] == mock_job_model.STATUS_SUCCESS
            assert last_kwargs["result"] == {"assessment_lo": {"Midterm": {"LO1": 3, "LO2": 4}}}
            assert last_kwargs["finished_at"] == "2025-01-01T00:00:00Z"

    def test_task_updates_job_on_failure(self):
        """Task should mark job as failed on exception."""
        from core.tasks import suggest_assessment_lo_weights_task

        mock_suggester = MagicMock()
        mock_suggester.suggest_assessment_lo.side_effect = ValueError("model error")

        mock_course = MagicMock()
        mock_course.name = "Test Course"
        mock_course.learning_outcomes.values_list.return_value = [
            "LO1: desc a",
        ]
        mock_course.assessments.all.return_value = []

        with (
            patch("core.tasks._suggester", mock_suggester),
            patch("core.models.Course") as mock_course_model,
            patch("core.models.WeightSuggestionJob") as mock_job_model,
            patch("core.tasks.timezone") as mock_tz,
        ):
            mock_course_model.objects.get.return_value = mock_course
            mock_filter = MagicMock()
            mock_job_model.objects.filter.return_value = mock_filter
            mock_tz.now.return_value = "2025-01-01T00:00:00Z"

            with pytest.raises(ValueError, match="model error"):
                suggest_assessment_lo_weights_task(course_id=42, job_id=99)

            mock_filter.update.assert_called()
            update_kwargs = mock_filter.update.call_args[1]
            assert update_kwargs["status"] == mock_job_model.STATUS_FAILED

    def test_task_handles_missing_course(self):
        """Task should raise Course.DoesNotExist if course not found."""
        from core.tasks import suggest_assessment_lo_weights_task
        from core.models import Course as CourseModel

        with patch("core.models.Course") as mock_course_model:
            mock_course_model.objects.get.side_effect = CourseModel.DoesNotExist("no course")

            with pytest.raises(CourseModel.DoesNotExist):
                suggest_assessment_lo_weights_task(course_id=99999)

    def test_task_handles_no_los(self):
        """Task should succeed with empty mapping when course has no LOs."""
        from core.tasks import suggest_assessment_lo_weights_task

        mock_suggester = MagicMock()
        mock_suggester.suggest_assessment_lo.return_value = {"assessment_lo": {}}

        mock_course = MagicMock()
        mock_course.name = "Test Course"
        mock_course.learning_outcomes.values_list.return_value = []
        mock_a = MagicMock(name="Midterm", assessment_type="midterm")
        mock_a.name = "Midterm"
        mock_a.description = "tests theoretical knowledge"
        del mock_a.get_assessment_type_display  # force use of description path
        mock_course.assessments.all.return_value = [mock_a]

        with patch("core.tasks._suggester", mock_suggester), patch("core.models.Course") as mock_course_model:
            mock_course_model.objects.get.return_value = mock_course

            result = suggest_assessment_lo_weights_task(course_id=42)

            assert result == {"assessment_lo": {}}
            call_kwargs = mock_suggester.suggest_assessment_lo.call_args[1]
            assert call_kwargs["los"] == []
            assert call_kwargs["assessments"] == ["Midterm: tests theoretical knowledge"]
            assert call_kwargs["assessment_keys"] == ["Midterm"]

    def test_task_uses_description_when_present(self):
        """Task should use assessment.description for embedding text, name for key."""
        from core.tasks import suggest_assessment_lo_weights_task

        mock_suggester = MagicMock()
        mock_suggester.suggest_assessment_lo.return_value = {"assessment_lo": {"Midterm": {"LO1": 3}}}

        mock_course = MagicMock()
        mock_course.name = "Test Course"
        mock_course.learning_outcomes.values_list.return_value = ["LO1: desc"]
        # Assessment with description
        mock_a = MagicMock()
        mock_a.name = "Midterm"
        mock_a.description = "tests theoretical knowledge"
        # Assessment without description (falls back to type)
        mock_b = MagicMock()
        mock_b.name = "Final"
        mock_b.description = ""
        mock_b.get_assessment_type_display.return_value = "Final Exam"
        mock_course.assessments.all.return_value = [mock_a, mock_b]

        with patch("core.tasks._suggester", mock_suggester), patch("core.models.Course") as mock_course_model:
            mock_course_model.objects.get.return_value = mock_course

            suggest_assessment_lo_weights_task(course_id=42)

            call_kwargs = mock_suggester.suggest_assessment_lo.call_args[1]
            assert call_kwargs["assessments"] == [
                "Midterm: tests theoretical knowledge",
                "Final: Final Exam",
            ]
            assert call_kwargs["assessment_keys"] == ["Midterm", "Final"]

    def test_task_raises_when_suggester_not_initialized(self):
        """Task should raise RuntimeError when _suggester stays None after init."""
        from core.tasks import suggest_assessment_lo_weights_task

        mock_course = MagicMock()
        mock_course.name = "Test Course"
        mock_course.learning_outcomes.values_list.return_value = []
        mock_course.assessments.all.return_value = []

        with (
            patch("core.tasks._suggester", None),
            patch("core.tasks._init_weight_suggester"),
            patch("core.models.Course") as mock_course_model,
        ):
            mock_course_model.objects.get.return_value = mock_course

            with pytest.raises(RuntimeError, match="Weight suggester not initialized"):
                suggest_assessment_lo_weights_task(course_id=42)


class TestWorkerInit:
    """Tests for the worker_process_init signal handler."""

    def test_init_worker_creates_suggester(self):
        """Verify the signal handler sets _suggester."""
        import core.tasks as tasks_module

        with (
            patch("sentence_transformers.SentenceTransformer") as mock_st,
            patch("core.services.weight_suggestion.WeightSuggester") as mock_ws_cls,
            patch.object(tasks_module, "os") as mock_os,
        ):
            mock_os.getenv.return_value = "test-model"
            mock_ws_cls.return_value = "mock-suggester-instance"

            tasks_module._init_weight_suggester()

            mock_st.assert_called_once_with("test-model")
            mock_ws_cls.assert_called_once()
            call_kwargs = mock_ws_cls.call_args[1]
            assert "encoder" in call_kwargs

    def test_init_worker_default_model(self):
        """Verify default model name when env var is not set."""
        import core.tasks as tasks_module

        with (
            patch("sentence_transformers.SentenceTransformer") as mock_st,
            patch("core.services.weight_suggestion.WeightSuggester"),
            patch.object(tasks_module, "os") as mock_os,
        ):
            mock_os.getenv = lambda key, default=None: default

            tasks_module._init_weight_suggester()

            mock_st.assert_called_once_with("all-MiniLM-L6-v2")
