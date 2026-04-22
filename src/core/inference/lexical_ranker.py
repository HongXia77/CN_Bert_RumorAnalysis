from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from src.core.common.text_utils import char_bigrams, cosine_from_counters


class LexicalEventRanker:
    def __init__(self, index_path: Path):
        with index_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.idf: dict[str, float] = payload["idf"]
        self.events = payload["events"]
        self.event_views = {
            item["event_id"]: [
                {
                    "view_name": view.get("view_name", ""),
                    "text": view.get("text", ""),
                    "token_counts": Counter(view.get("token_counts", {})),
                }
                for view in item.get("text_views", [])
            ]
            for item in self.events
        }

    def rank(self, text: str, limit: int = 5) -> list[dict]:
        query_counter = char_bigrams(text)
        scored_rows = []
        for item in self.events:
            event_id = item["event_id"]
            best_view = None
            for view in self.event_views.get(event_id, []):
                score = cosine_from_counters(query_counter, view["token_counts"], self.idf)
                if score <= 0:
                    continue
                if best_view is None or score > best_view["score"]:
                    best_view = {
                        "view_name": view["view_name"],
                        "text": view["text"],
                        "score": float(score),
                    }
            if best_view is None:
                continue
            scored_rows.append(
                {
                    "event_id": event_id,
                    "score": round(best_view["score"], 6),
                    "event_focus": item.get("event_focus", ""),
                    "event_summary": item.get("event_summary", ""),
                    "canonical_text": item.get("canonical_text", ""),
                    "anchor_text": item.get("anchor_text", ""),
                    "representative_text": item.get("representative_text", ""),
                    "representative_title": item.get("representative_title", ""),
                    "example_texts": item.get("example_texts", []),
                    "sample_count": item.get("sample_count", 0),
                    "lexical_view": best_view["view_name"],
                    "lexical_text": best_view["text"],
                }
            )
        scored_rows.sort(key=lambda row: row["score"], reverse=True)
        return scored_rows[:limit]
