from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from src.core.common.io_utils import ensure_directory, read_jsonl, write_json
from src.core.common.text_utils import char_bigrams


def build_lexical_index(event_catalog_path: Path, output_path: Path) -> Path:
    events = read_jsonl(event_catalog_path)
    tokenized_events = []
    document_frequency: Counter[str] = Counter()

    for item in events:
        view_payloads = []
        seen_texts: set[str] = set()
        for view_name, text in [
            ("canonical_text", item.get("canonical_text", "")),
            ("anchor_text", item.get("anchor_text", "")),
            ("representative_text", item.get("representative_text", "")),
            *[(f"example_{index}", text) for index, text in enumerate(item.get("example_texts", [])[:2], start=1)],
        ]:
            normalized = (text or "").strip()
            if not normalized or normalized in seen_texts:
                continue
            seen_texts.add(normalized)
            token_counts = char_bigrams(normalized)
            if not token_counts:
                continue
            view_payloads.append(
                {
                    "view_name": view_name,
                    "text": normalized,
                    "token_counts": dict(token_counts),
                }
            )

        merged_counts: Counter[str] = Counter()
        for view in view_payloads:
            merged_counts.update(view["token_counts"])

        tokenized_events.append((item, view_payloads, merged_counts))
        document_frequency.update(merged_counts.keys())

    total_documents = max(len(tokenized_events), 1)
    idf = {
        token: math.log((1 + total_documents) / (1 + df)) + 1.0
        for token, df in document_frequency.items()
    }

    payload = {
        "meta": {
            "event_count": len(events),
            "token_count": len(idf),
            "builder": "char_bigram_tfidf",
        },
        "idf": idf,
        "events": [
            {
                "event_id": item["event_id"],
                "event_focus": item.get("event_focus", ""),
                "event_summary": item.get("event_summary", ""),
                "canonical_text": item.get("canonical_text", ""),
                "anchor_text": item.get("anchor_text", ""),
                "representative_text": item.get("representative_text", ""),
                "representative_title": item.get("representative_title", ""),
                "example_texts": item.get("example_texts", []),
                "sample_count": item.get("sample_count", 0),
                "split": item.get("split", ""),
                "token_counts": dict(tokens),
                "text_views": view_payloads,
            }
            for item, view_payloads, tokens in tokenized_events
        ],
    }

    ensure_directory(output_path.parent)
    write_json(output_path, payload)
    return output_path


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a lexical retrieval index from event catalog.")
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    output = build_lexical_index(args.catalog, args.output)
    print(json.dumps({"index": str(output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
