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


def test_assessment_keys_separates_descriptions_from_response_keys(
    sample_course_name,
    sample_los,
    dummy_encoder,
):
    """Response keys should use assessment_keys when provided, not assessment texts."""
    from core.services.weight_suggestion import WeightSuggester

    descriptive_texts = [
        "Midterm: tests theoretical understanding",
        "Final: comprehensive evaluation",
        "Project: practical implementation",
    ]
    short_keys = ["Midterm", "Final", "Project"]

    embeddings = {
        descriptive_texts[0]: [1.0, 0.0],
        descriptive_texts[1]: [0.8, 0.2],
        descriptive_texts[2]: [0.0, 1.0],
        sample_los[0]: [1.0, 0.0],
        sample_los[1]: [0.0, 1.0],
    }
    suggester = WeightSuggester(encoder=dummy_encoder(embeddings))
    result = suggester.suggest_assessment_lo(
        course_name=sample_course_name,
        los=sample_los,
        assessments=descriptive_texts,
        assessment_keys=short_keys,
    )

    assert len(result["assessment_lo"]) == 3
    # Keys should be the short names, not the descriptive texts
    for key in short_keys:
        assert key in result["assessment_lo"], f"Missing key '{key}'"
    # No descriptive text should appear as a key
    for text in descriptive_texts:
        if text not in short_keys:
            assert text not in result["assessment_lo"], f"Descriptive text '{text}' leaked into response key"


def test_raw_embedding_debug_payload_includes_similarity_components(
    sample_course_name,
    sample_los,
    dummy_encoder,
):
    """Debug mode should expose the values used to turn embeddings into weights."""
    from core.services.weight_suggestion import WeightSuggester

    assessments = ["Midterm: tests theoretical knowledge"]
    embeddings = {
        assessments[0]: [1.0, 0.0],
        sample_los[0]: [1.0, 0.0],
        sample_los[1]: [0.0, 1.0],
    }
    suggester = WeightSuggester(encoder=dummy_encoder(embeddings))

    result = suggester.suggest_assessment_lo(
        course_name=sample_course_name,
        los=sample_los,
        assessments=assessments,
        assessment_keys=["Midterm"],
        include_raw_embeddings=True,
    )

    debug = result["debug"]["assessment_lo"]
    assert debug["source_keys"] == ["Midterm"]
    assert debug["target_keys"] == ["LO1", "LO2"]
    assert debug["source_embeddings"] == [[1.0, 0.0]]
    assert debug["target_embeddings"] == [[1.0, 0.0], [0.0, 1.0]]
    assert debug["cosine_similarity"] == [[1.0, 0.0]]
    assert debug["rows"][0]["cosine_similarity"] == [1.0, 0.0]
    assert debug["rows"][0]["row_normalized_scores"] == [1.0, 0.0]
    assert debug["rows"][0]["weights"] == list(result["assessment_lo"]["Midterm"].values())


def test_narrow_cosine_range_still_uses_full_weight_scale():
    """Rows with close cosine values should not collapse into only 2-4 weights."""
    from core.services.weight_suggestion import WeightSuggester

    cosine_scores = [
        0.42571017146110535,
        0.35203468799591064,
        0.24981698393821716,
        0.3938533365726471,
        0.3333739638328552,
        0.3489070236682892,
        0.3085215091705322,
        0.23956027626991272,
        0.24618500471115112,
        0.4000246524810791,
        0.20198729634284973,
    ]

    weights, components = WeightSuggester._normalize_scores_with_components(cosine_scores)

    assert min(weights) == 0
    assert max(weights) == 5
    assert components["row_normalized_scores"][0] == 1.0
    assert components["row_normalized_scores"][-1] == 0.0
