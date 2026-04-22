from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import median

from src.core.common.io_utils import ensure_directory, write_json, write_jsonl
from src.core.common.text_utils import (
    clean_result_summary,
    event_id_from_summary,
    extract_event_focus,
    normalize_rumor_text,
    simplify_event_summary,
    stable_text_hash,
)


@dataclass(slots=True)
class CleaningStats:
    total_lines: int = 0
    kept_lines: int = 0
    skipped_empty_text: int = 0
    skipped_empty_result: int = 0
    skipped_short_text: int = 0
    duplicate_variant_rows: int = 0


def iter_ndjson(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            yield line_number, json.loads(line)


def clean_weibo_rumor_dataset(
    input_path: Path,
    output_dir: Path,
    *,
    min_text_length: int = 12,
    keep_duplicate_variants: bool = False,
) -> dict[str, Path]:
    ensure_directory(output_dir)

    cleaned_records: list[dict] = []
    stats = CleaningStats()
    seen_variant_keys: set[tuple[str, str]] = set()
    normalized_text_lengths: list[int] = []
    event_counter: Counter[str] = Counter()

    for line_number, raw in iter_ndjson(input_path):
        stats.total_lines += 1
        rumor_text = normalize_rumor_text(raw.get("rumorText", ""))
        if not rumor_text:
            stats.skipped_empty_text += 1
            continue

        result_summary = clean_result_summary(raw.get("result", ""))
        if not result_summary:
            stats.skipped_empty_result += 1
            continue

        if len(rumor_text) < min_text_length:
            stats.skipped_short_text += 1
            continue

        simplified_summary = simplify_event_summary(result_summary)
        event_focus = extract_event_focus(result_summary, fallback_text=rumor_text)
        event_id = event_id_from_summary(result_summary)
        normalized_hash = stable_text_hash(rumor_text, length=20)
        variant_key = (event_id, normalized_hash)
        if variant_key in seen_variant_keys and not keep_duplicate_variants:
            stats.duplicate_variant_rows += 1
            continue
        seen_variant_keys.add(variant_key)

        normalized_text_lengths.append(len(rumor_text))
        event_counter[event_id] += 1
        cleaned_records.append(
            {
                "line_number": line_number,
                "rumor_code": raw.get("rumorCode"),
                "title": normalize_rumor_text(raw.get("title", "")),
                "rumor_text": rumor_text,
                "result_summary": result_summary,
                "event_summary": simplified_summary,
                "event_focus": event_focus,
                "event_id": event_id,
                "publish_time": raw.get("publishTime") or "",
                "visit_times": int(raw.get("visitTimes") or 0),
                "informer_name": raw.get("informerName") or "",
                "rumormonger_name": raw.get("rumormongerName") or "",
                "raw_record": raw,
            }
        )

    stats.kept_lines = len(cleaned_records)

    cleaned_path = output_dir / "cleaned_records.jsonl"
    write_jsonl(cleaned_path, cleaned_records)

    report_path = output_dir / "cleaning_report.json"
    report = {
        "input_path": str(input_path),
        "output_path": str(cleaned_path),
        "stats": {
            "total_lines": stats.total_lines,
            "kept_lines": stats.kept_lines,
            "skipped_empty_text": stats.skipped_empty_text,
            "skipped_empty_result": stats.skipped_empty_result,
            "skipped_short_text": stats.skipped_short_text,
            "duplicate_variant_rows": stats.duplicate_variant_rows,
            "unique_events": len(event_counter),
            "normalized_text_length_median": int(median(normalized_text_lengths)) if normalized_text_lengths else 0,
        },
        "top_events": event_counter.most_common(20),
    }
    write_json(report_path, report)

    return {
        "cleaned_records": cleaned_path,
        "report": report_path,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean Weibo rumor ndjson into normalized records.")
    parser.add_argument("--input", required=True, type=Path, help="Path to rumors_v170613 jsonl-like file.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for cleaned assets.")
    parser.add_argument("--min-text-length", type=int, default=12)
    parser.add_argument("--keep-duplicate-variants", action="store_true")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    outputs = clean_weibo_rumor_dataset(
        args.input,
        args.output_dir,
        min_text_length=args.min_text_length,
        keep_duplicate_variants=args.keep_duplicate_variants,
    )
    print(json.dumps({key: str(value) for key, value in outputs.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

