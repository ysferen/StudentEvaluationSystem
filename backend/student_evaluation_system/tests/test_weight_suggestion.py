"""
Tests for the embedding-based WeightSuggester service.

These tests verify:
1. Correct JSON schema in assessment_lo responses
2. Correct JSON schema in lo_po responses
3. Similarity-driven weight scaling
"""

import pytest


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_course_name():
    return "Operating Systems"


@pytest.fixture
def sample_los():
    return [
        "LO1: Explains operating system components.",
        "LO2: Compares process management algorithms.",
    ]


@pytest.fixture
def sample_assessments():
    return ["Midterm", "Final", "Project"]


@pytest.fixture
def sample_pos():
    return [
        "PO1: Engineering Knowledge",
        "PO2: Problem Analysis",
    ]


@pytest.fixture
def dummy_encoder():
    class DummyEncoder:
        def __init__(self, embeddings):
            self.embeddings = embeddings

        def encode(self, texts, normalize_embeddings=True):
            vectors = [self.embeddings[text] for text in texts]
            return vectors

    return DummyEncoder


# ---------------------------------------------------------------------------
# Test 1: assessment_lo JSON schema conformance
# ---------------------------------------------------------------------------


def test_suggest_assessment_lo_returns_valid_json(sample_course_name, sample_los, sample_assessments, dummy_encoder):
    """
    Verify that the WeightSuggester.suggest_assessment_lo method:
    - Returns a dict, not a raw string
    - Has the top-level key 'assessment_lo'
    - Contains ALL assessment methods as keys
    - Each assessment maps to ALL learning outcomes with integer weights
    - Weights are integers between 0 and 5
    """
    from core.services.weight_suggestion import WeightSuggester

    embeddings = {
        "Midterm": [1.0, 0.0],
        "Final": [0.8, 0.2],
        "Project": [0.0, 1.0],
        sample_los[0]: [1.0, 0.0],
        sample_los[1]: [0.0, 1.0],
    }
    suggester = WeightSuggester(encoder=dummy_encoder(embeddings))
    result = suggester.suggest_assessment_lo(
        course_name=sample_course_name,
        los=sample_los,
        assessments=sample_assessments,
    )

    # Top-level structure
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "assessment_lo" in result, f"Missing 'assessment_lo' key, got keys: {list(result.keys())}"

    mappings = result["assessment_lo"]
    assert isinstance(mappings, dict), f"'assessment_lo' should be dict, got {type(mappings)}"

    # Every assessment method must be present
    for assessment in sample_assessments:
        assert assessment in mappings, f"Missing assessment '{assessment}' in response. Got: {list(mappings.keys())}"

    # Every assessment must map to EVERY learning outcome
    lo_keys = [f"LO{i + 1}" for i in range(len(sample_los))]
    for assessment in sample_assessments:
        assessment_mapping = mappings[assessment]
        assert isinstance(assessment_mapping, dict), (
            f"Mapping for '{assessment}' should be dict, got {type(assessment_mapping)}"
        )
        for lo_key in lo_keys:
            assert lo_key in assessment_mapping, (
                f"'{assessment}' missing mapping for '{lo_key}'. Got: {list(assessment_mapping.keys())}"
            )
            weight = assessment_mapping[lo_key]
            assert isinstance(weight, int), f"Weight for '{assessment}'.'{lo_key}' should be int, got {type(weight)}: {weight}"
            assert 0 <= weight <= 5, f"Weight for '{assessment}'.'{lo_key}' out of range [0,5]: {weight}"


# ---------------------------------------------------------------------------
# Test 2: lo_po JSON schema conformance
# ---------------------------------------------------------------------------


def test_suggest_lo_po_returns_valid_json(sample_course_name, sample_los, sample_pos, dummy_encoder):
    """
    Verify that the WeightSuggester.suggest_lo_po method:
    - Returns a dict, not a raw string
    - Has the top-level key 'lo_po'
    - Contains ALL learning outcomes as keys
    - Each LO maps to ALL program outcomes with integer weights
    - Weights are integers between 0 and 5
    """
    from core.services.weight_suggestion import WeightSuggester

    embeddings = {
        sample_los[0]: [1.0, 0.0],
        sample_los[1]: [0.0, 1.0],
        sample_pos[0]: [1.0, 0.0],
        sample_pos[1]: [0.0, 1.0],
    }
    suggester = WeightSuggester(encoder=dummy_encoder(embeddings))
    result = suggester.suggest_lo_po(
        course_name=sample_course_name,
        los=sample_los,
        pos=sample_pos,
    )

    # Top-level structure
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert "lo_po" in result, f"Missing 'lo_po' key, got keys: {list(result.keys())}"

    mappings = result["lo_po"]
    assert isinstance(mappings, dict), f"'lo_po' should be dict, got {type(mappings)}"

    # Every learning outcome must be present
    lo_keys = [f"LO{i + 1}" for i in range(len(sample_los))]
    for lo_key in lo_keys:
        assert lo_key in mappings, f"Missing learning outcome '{lo_key}' in response. Got: {list(mappings.keys())}"

    # Every LO must map to EVERY program outcome
    po_keys = [f"PO{i + 1}" for i in range(len(sample_pos))]
    for lo_key in lo_keys:
        lo_mapping = mappings[lo_key]
        assert isinstance(lo_mapping, dict), f"Mapping for '{lo_key}' should be dict, got {type(lo_mapping)}"
        for po_key in po_keys:
            assert po_key in lo_mapping, f"'{lo_key}' missing mapping for '{po_key}'. Got: {list(lo_mapping.keys())}"
            weight = lo_mapping[po_key]
            assert isinstance(weight, int), f"Weight for '{lo_key}'.'{po_key}' should be int, got {type(weight)}: {weight}"
            assert 0 <= weight <= 5, f"Weight for '{lo_key}'.'{po_key}' out of range [0,5]: {weight}"


def test_similarity_weights_rank_higher_for_closer_texts(sample_course_name, sample_los, sample_assessments, dummy_encoder):
    from core.services.weight_suggestion import WeightSuggester

    embeddings = {
        "Midterm": [1.0, 0.0],
        "Final": [0.5, 0.5],
        "Project": [0.0, 1.0],
        sample_los[0]: [1.0, 0.0],
        sample_los[1]: [0.0, 1.0],
    }
    suggester = WeightSuggester(encoder=dummy_encoder(embeddings))
    result = suggester.suggest_assessment_lo(
        course_name=sample_course_name,
        los=sample_los,
        assessments=sample_assessments,
    )

    midterm_weights = result["assessment_lo"]["Midterm"]
    project_weights = result["assessment_lo"]["Project"]

    assert midterm_weights["LO1"] > midterm_weights["LO2"]
    assert project_weights["LO2"] > project_weights["LO1"]


# ---------------------------------------------------------------------------
# Test: Celery model pre-loading integration
# ---------------------------------------------------------------------------


def test_suggester_accepts_external_encoder(sample_course_name, sample_los, sample_assessments, dummy_encoder):
    """
    Verify WeightSuggester works correctly when encoder is passed via
    keyword argument (as it will be from the Celery worker init).
    """
    from core.services.weight_suggestion import WeightSuggester

    embeddings = {
        "Midterm": [1.0, 0.0],
        "Final": [0.8, 0.2],
        "Project": [0.0, 1.0],
        sample_los[0]: [1.0, 0.0],
        sample_los[1]: [0.0, 1.0],
    }
    encoder = dummy_encoder(embeddings)
    suggester = WeightSuggester(encoder=encoder)

    result = suggester.suggest_assessment_lo(
        course_name=sample_course_name,
        los=sample_los,
        assessments=sample_assessments,
    )

    assert "assessment_lo" in result
    assert len(result["assessment_lo"]) == 3


def test_suggester_handles_empty_assessments(sample_course_name, sample_los, dummy_encoder):
    """WeightSuggester should return empty mapping when assessments list is empty."""
    from core.services.weight_suggestion import WeightSuggester

    embeddings = {
        sample_los[0]: [1.0, 0.0],
        sample_los[1]: [0.0, 1.0],
    }
    suggester = WeightSuggester(encoder=dummy_encoder(embeddings))
    result = suggester.suggest_assessment_lo(
        course_name=sample_course_name,
        los=sample_los,
        assessments=[],
    )

    assert result == {"assessment_lo": {}}
