"""
Embedding-based weight suggestion service.

Provides a class-based interface for generating two types of mappings:
- assessment_lo: maps assessment methods to learning outcomes (0-5 weights)
- lo_po: maps learning outcomes to program outcomes (0-5 weights)

Weights are derived from sentence-embedding cosine similarity.
"""

import os
import numpy as np


class WeightSuggester:
    """Suggests assessment-to-LO and LO-to-PO weights via embeddings."""

    def __init__(self, model_name=os.getenv("SENTENCE_TRANSFORMER_MODEL"), encoder=None):
        """
        Initialize the suggester.

        Args:
            model_name: Sentence-transformer model name to use.
            encoder: Optional encoder instance for testing.
        """
        self.model_name = model_name or "all-MiniLM-L6-v2"
        self.encoder = encoder

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def suggest_assessment_lo(self, course_name, los, assessments, assessment_keys=None):
        """
        Suggest weights mapping assessment methods to learning outcomes.

        Args:
            course_name: Name of the course (e.g. "Operating Systems").
            los: List of learning outcome descriptions.
                 e.g. ["LO1: Explains OS components.", "LO2: Compares algorithms."]
            assessments: List of assessment descriptive texts used for
                         embedding similarity (e.g. "Midterm: tests theory").
            assessment_keys: Optional list of short names for response keys.
                             If None, uses `assessments` as the keys.
                             e.g. ["Midterm", "Final", "Project"]

        Returns:
            dict with shape: {"assessment_lo": {key: {LO_key: weight}}}
        """
        if not assessments:
            return {"assessment_lo": {}}

        keys = assessment_keys if assessment_keys is not None else assessments
        lo_keys = [f"LO{i + 1}" for i in range(len(los))]
        weights = self._similarity_weights(assessments, los)

        return {
            "assessment_lo": {
                keys[row_index]: {lo_key: weights[row_index][col_index] for col_index, lo_key in enumerate(lo_keys)}
                for row_index in range(len(keys))
            }
        }

    def suggest_lo_po(self, course_name, los, pos):
        """
        Suggest weights mapping learning outcomes to program outcomes.

        Args:
            course_name: Name of the course.
            los: List of learning outcome descriptions.
            pos: List of program outcome descriptions.
                 e.g. ["PO1: Engineering Knowledge", "PO2: Problem Analysis"]

        Returns:
            dict with shape: {"lo_po": {LO: {PO: weight}}}
        """
        lo_keys = [f"LO{i + 1}" for i in range(len(los))]
        po_keys = [f"PO{i + 1}" for i in range(len(pos))]
        weights = self._similarity_weights(los, pos)

        return {
            "lo_po": {
                lo_key: {po_key: weights[row_index][col_index] for col_index, po_key in enumerate(po_keys)}
                for row_index, lo_key in enumerate(lo_keys)
            }
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _similarity_weights(self, source_texts, target_texts):
        """Compute 0-5 weights from cosine similarity between text lists."""
        source_embeddings = self._encode_texts(source_texts)
        target_embeddings = self._encode_texts(target_texts)
        similarity_matrix = np.matmul(source_embeddings, target_embeddings.T)
        return [self._normalize_scores(row) for row in similarity_matrix]

    def _encode_texts(self, texts):
        """Encode texts and return normalized embeddings as a NumPy array."""
        embeddings = self.encoder.encode(texts, normalize_embeddings=True)
        embeddings = np.asarray(embeddings, dtype=np.float32)

        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        return embeddings

    @staticmethod
    def _normalize_scores(scores):
        """Normalize similarity scores to 0-5 integer weights.

        Blends raw cosine similarity with rank-based normalization so that
        the relative ordering within each assessment/LO creates contrast,
        while the absolute similarity still anchors the general level.

        Configurable via env vars:
          WEIGHT_SUGGESTION_BLEND  — rank influence (0=raw only, 1=rank only)
                                     default 0.5 balances both.
        """
        scores = np.asarray(scores, dtype=np.float32)
        # Cosine similarity [-1, 1] → [0, 1]
        raw_scores = (scores + 1.0) / 2.0
        raw_scores = np.clip(raw_scores, 0.0, 1.0)

        # Rank scores within this row: 0 = lowest similarity, 1 = highest
        n = len(raw_scores) - 1
        if n > 0:
            ranks = np.argsort(np.argsort(raw_scores)).astype(np.float32)
            rank_scores = ranks / n
        else:
            rank_scores = np.zeros_like(raw_scores)

        blend = float(os.getenv("WEIGHT_SUGGESTION_BLEND", "0.5"))
        scores = (1.0 - blend) * raw_scores + blend * rank_scores

        weights = np.rint(scores * 5.0).astype(int)
        weights = np.clip(weights, 0, 5)
        return [int(weight) for weight in weights]
