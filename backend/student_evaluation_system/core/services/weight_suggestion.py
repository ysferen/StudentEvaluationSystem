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

    def suggest_assessment_lo(self, course_name, los, assessments, assessment_keys=None, include_raw_embeddings=False):
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

            include_raw_embeddings: When True, include embedding vectors,
                cosine similarities, and normalization values under a
                "debug" key.

        Returns:
            dict with shape: {"assessment_lo": {key: {LO_key: weight}}}
        """
        if not assessments:
            result = {"assessment_lo": {}}
            if include_raw_embeddings:
                result["debug"] = {"assessment_lo": self._empty_debug_payload(assessments, los)}
            return result

        keys = assessment_keys if assessment_keys is not None else assessments
        lo_keys = [f"LO{i + 1}" for i in range(len(los))]
        weights, debug = self._similarity_weights(assessments, los, include_debug=include_raw_embeddings)

        result = {
            "assessment_lo": {
                keys[row_index]: {lo_key: weights[row_index][col_index] for col_index, lo_key in enumerate(lo_keys)}
                for row_index in range(len(keys))
            }
        }
        if include_raw_embeddings:
            debug["source_keys"] = list(keys)
            debug["target_keys"] = lo_keys
            result["debug"] = {"assessment_lo": debug}
        return result

    def suggest_lo_po(self, course_name, los, pos, include_raw_embeddings=False):
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
        weights, debug = self._similarity_weights(los, pos, include_debug=include_raw_embeddings)

        result = {
            "lo_po": {
                lo_key: {po_key: weights[row_index][col_index] for col_index, po_key in enumerate(po_keys)}
                for row_index, lo_key in enumerate(lo_keys)
            }
        }
        if include_raw_embeddings:
            debug["source_keys"] = lo_keys
            debug["target_keys"] = po_keys
            result["debug"] = {"lo_po": debug}
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _similarity_weights(self, source_texts, target_texts, include_debug=False):
        """Compute 0-5 weights from cosine similarity between text lists."""
        source_embeddings = self._encode_texts(source_texts)
        target_embeddings = self._encode_texts(target_texts)
        similarity_matrix = np.matmul(source_embeddings, target_embeddings.T)
        weights = []
        rows = []
        for row_index, row in enumerate(similarity_matrix):
            row_weights, components = self._normalize_scores_with_components(row)
            weights.append(row_weights)
            if include_debug:
                rows.append(
                    {
                        "source_index": row_index,
                        "source_text": source_texts[row_index],
                        "cosine_similarity": components["cosine_similarity"],
                        "raw_scores_0_1": components["raw_scores_0_1"],
                        "row_normalized_scores": components["row_normalized_scores"],
                        "rank_scores": components["rank_scores"],
                        "blended_scores": components["blended_scores"],
                        "weights": row_weights,
                    }
                )

        if not include_debug:
            return weights, None

        return weights, {
            "source_texts": list(source_texts),
            "target_texts": list(target_texts),
            "source_embeddings": source_embeddings.tolist(),
            "target_embeddings": target_embeddings.tolist(),
            "cosine_similarity": similarity_matrix.tolist(),
            "rows": rows,
        }

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

        Blends row-wise min/max normalization with rank-based normalization
        so that narrow cosine ranges still create useful 0-5 contrast.

        Configurable via env vars:
          WEIGHT_SUGGESTION_BLEND  — rank influence (0=raw only, 1=rank only)
                                     default 0.5 balances both.
        """
        weights, _components = WeightSuggester._normalize_scores_with_components(scores)
        return weights

    @staticmethod
    def _normalize_scores_with_components(scores):
        """Normalize scores and return the intermediate values used."""
        cosine_scores = np.asarray(scores, dtype=np.float32)
        # Cosine similarity [-1, 1] → [0, 1]
        raw_scores = (cosine_scores + 1.0) / 2.0
        raw_scores = np.clip(raw_scores, 0.0, 1.0)
        score_range = float(raw_scores.max() - raw_scores.min()) if raw_scores.size else 0.0
        if score_range > 1e-6:
            row_normalized_scores = (raw_scores - raw_scores.min()) / score_range
        else:
            row_normalized_scores = raw_scores.copy()

        # Rank scores within this row: 0 = lowest similarity, 1 = highest
        n = len(raw_scores) - 1
        if n > 0 and score_range > 1e-6:
            ranks = np.argsort(np.argsort(raw_scores)).astype(np.float32)
            rank_scores = ranks / n
        else:
            rank_scores = row_normalized_scores.copy()

        blend = float(os.getenv("WEIGHT_SUGGESTION_BLEND", "0.5"))
        blended_scores = (1.0 - blend) * row_normalized_scores + blend * rank_scores

        weights = np.rint(blended_scores * 5.0).astype(int)
        weights = np.clip(weights, 0, 5)
        return [int(weight) for weight in weights], {
            "cosine_similarity": cosine_scores.tolist(),
            "raw_scores_0_1": raw_scores.tolist(),
            "row_normalized_scores": row_normalized_scores.tolist(),
            "rank_scores": rank_scores.tolist(),
            "blended_scores": blended_scores.tolist(),
        }

    @staticmethod
    def _empty_debug_payload(source_texts, target_texts):
        return {
            "source_texts": list(source_texts),
            "target_texts": list(target_texts),
            "source_embeddings": [],
            "target_embeddings": [],
            "cosine_similarity": [],
            "rows": [],
        }
