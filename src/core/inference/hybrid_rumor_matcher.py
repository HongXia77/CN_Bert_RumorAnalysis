from __future__ import annotations

from pathlib import Path

from src.core.inference.lexical_ranker import LexicalEventRanker


class HybridRumorMatcher:
    """Combine lexical event retrieval with optional model-based probability."""

    def __init__(self, index_path: Path):
        self.ranker = LexicalEventRanker(index_path)

    def _fallback_probability(self, candidates: list[dict]) -> tuple[float, str, str]:
        top_score = candidates[0]["score"] if candidates else 0.0
        rumor_probability = max(0.05, min(0.95, 0.12 + top_score * 1.55))
        if rumor_probability >= 0.75:
            return rumor_probability, "high", "\u9ad8\u5ea6\u7591\u4f3c\u5df2\u77e5\u8c23\u8a00\u53d8\u4f53"
        if rumor_probability >= 0.45:
            return rumor_probability, "medium", "\u5b58\u5728\u8f83\u9ad8\u98ce\u9669\uff0c\u5efa\u8bae\u7ee7\u7eed\u6838\u67e5"
        return rumor_probability, "low", "\u5f53\u524d\u66f4\u63a5\u8fd1\u672a\u5339\u914d\u6216\u4f4e\u98ce\u9669\u6587\u672c"

    def predict(self, text: str, limit: int = 5) -> dict:
        candidates = self.ranker.rank(text, limit=limit)
        classifier_payload = None

        try:
            from src.service.prediction_service import predict_text

            classifier_payload = predict_text(text)
        except Exception:
            classifier_payload = None

        if classifier_payload is not None:
            rumor_probability = float(classifier_payload["rumor_probability"])
            risk_level = classifier_payload["risk_level"]
            verdict = classifier_payload["verdict"]
        else:
            rumor_probability, risk_level, verdict = self._fallback_probability(candidates)

        return {
            "text": text,
            "label": "rumor" if rumor_probability >= 0.5 else "normal",
            "verdict": verdict,
            "risk_level": risk_level,
            "rumor_probability": rumor_probability,
            "credible_probability": 1 - rumor_probability,
            "related_rumors": candidates,
        }

