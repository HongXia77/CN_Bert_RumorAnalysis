from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from src.core.common.io_utils import ensure_directory, read_jsonl, write_json, write_jsonl
from src.core.common.text_utils import char_bigrams, cosine_from_counters

GENERIC_TITLE_VALUES = {"举报 不实信息", "举报", "不实信息"}
GENERIC_FOCUS_PREFIXES = (
    "此微博",
    "该微博",
    "此图片",
    "该图片",
    "图片中",
    "视频中",
    "文章中",
    "发布不实信息",
)
NOISY_VARIANT_MARKERS = (
    "查看全文",
    "转发微博",
    "http://",
    "https://",
    "我只是",
    "出于好玩",
    "真的假的",
    "虚假消息",
    "虚假",
    "不实",
    "举报",
    "驳回",
    "标准",
    "朋友举报",
    "谣言",
)


def assign_split(event_id: str) -> str:
    bucket = int(hashlib.sha1(event_id.encode("utf-8")).hexdigest(), 16) % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "val"
    return "test"


def choose_representative(records: list[dict]) -> dict:
    focus_text = next((item.get("event_focus", "") for item in records if item.get("event_focus")), "")
    focus_counter = char_bigrams(focus_text) if focus_text else Counter()

    def score_variant(item: dict) -> tuple[float, float, int, int]:
        text = item.get("rumor_text", "")
        overlap = cosine_from_counters(char_bigrams(text), focus_counter, None) if focus_counter else 0.0
        length = len(text)
        target_length = 28
        length_score = max(0.0, 1.0 - abs(min(length, 100) - target_length) / 48)
        noise_penalty = sum(marker in text for marker in NOISY_VARIANT_MARKERS)
        visit_times = int(item.get("visit_times", 0) or 0)
        return (
            round(overlap - noise_penalty * 0.3, 6),
            round(length_score - noise_penalty * 0.18, 6),
            -abs(length - target_length),
            visit_times,
        )

    return max(records, key=score_variant)


def choose_canonical_text(event_focus: str, anchor_text: str) -> str:
    focus_text = (event_focus or "").strip()
    if not focus_text:
        return anchor_text
    if any(focus_text.startswith(prefix) for prefix in GENERIC_FOCUS_PREFIXES):
        return anchor_text or focus_text
    if len(focus_text) > 48:
        return anchor_text or focus_text
    return focus_text


def choose_display_title(title: str, canonical_text: str, anchor_text: str) -> str:
    normalized_title = (title or "").strip()
    if normalized_title and normalized_title not in GENERIC_TITLE_VALUES:
        return normalized_title
    return canonical_text or anchor_text


def choose_example_texts(rows: list[dict], anchor_text: str, limit: int = 3) -> list[str]:
    seen: set[str] = set()
    candidates: list[str] = []

    for text in [anchor_text] + [row.get("rumor_text", "") for row in rows]:
        normalized = (text or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(normalized)

    def score_text(text: str) -> tuple[float, int]:
        noise_penalty = sum(marker in text for marker in NOISY_VARIANT_MARKERS)
        length_score = min(len(text), 96)
        return (-noise_penalty, length_score)

    candidates.sort(key=score_text, reverse=True)
    return candidates[:limit]


def build_event_catalog(records: Iterable[dict], min_event_size: int = 2) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in records:
        grouped[item["event_id"]].append(item)

    catalog: list[dict] = []
    for event_id, rows in grouped.items():
        representative = choose_representative(rows)
        anchor_text = representative.get("rumor_text") or representative.get("event_focus") or ""
        canonical_text = choose_canonical_text(representative.get("event_focus", ""), anchor_text)
        example_texts = choose_example_texts(rows, anchor_text)
        publish_times = [row.get("publish_time") or "" for row in rows if row.get("publish_time")]
        catalog.append(
            {
                "event_id": event_id,
                "split": assign_split(event_id),
                "event_focus": representative.get("event_focus") or representative.get("event_summary"),
                "event_summary": representative.get("event_summary") or representative.get("result_summary"),
                "canonical_text": canonical_text,
                "anchor_text": anchor_text,
                "representative_text": anchor_text,
                "representative_title": choose_display_title(
                    representative.get("title", ""),
                    canonical_text,
                    anchor_text,
                ),
                "sample_count": len(rows),
                "variant_count": len({row["rumor_text"] for row in rows}),
                "min_event_size_pass": len(rows) >= min_event_size,
                "publish_time_min": min(publish_times) if publish_times else "",
                "publish_time_max": max(publish_times) if publish_times else "",
                "example_texts": example_texts,
            }
        )
    catalog.sort(key=lambda item: (-item["sample_count"], item["event_id"]))
    return catalog


def compute_hard_negative_map(catalog: list[dict], top_k: int = 6) -> dict[str, list[str]]:
    token_map = {
        item["event_id"]: char_bigrams(
            " ".join(
                filter(
                    None,
                    [
                        item.get("canonical_text", ""),
                        item.get("anchor_text", ""),
                        item.get("representative_text", ""),
                    ],
                )
            )
        )
        for item in catalog
    }
    negative_map: dict[str, list[str]] = {}
    for anchor in catalog:
        anchor_id = anchor["event_id"]
        scores: list[tuple[str, float]] = []
        for candidate in catalog:
            candidate_id = candidate["event_id"]
            if candidate_id == anchor_id:
                continue
            score = cosine_from_counters(token_map[anchor_id], token_map[candidate_id], None)
            if score <= 0:
                continue
            scores.append((candidate_id, score))
        scores.sort(key=lambda item: item[1], reverse=True)
        negative_map[anchor_id] = [event_id for event_id, _ in scores[:top_k]]
    return negative_map


def build_pair_samples(
    records: list[dict],
    catalog: list[dict],
    *,
    min_event_size: int = 2,
    max_variants_per_event: int = 12,
    negatives_per_positive: int = 2,
    random_seed: int = 42,
) -> dict[str, list[dict]]:
    rng = random.Random(random_seed)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in records:
        grouped[item["event_id"]].append(item)

    eligible_catalog = [item for item in catalog if item["sample_count"] >= min_event_size]
    by_id = {item["event_id"]: item for item in eligible_catalog}
    hard_negative_map = compute_hard_negative_map(eligible_catalog)

    split_samples: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    for event in eligible_catalog:
        event_id = event["event_id"]
        split = event["split"]
        canonical_text = event["canonical_text"] or event["representative_text"]
        anchor_text = event.get("anchor_text") or event["representative_text"] or canonical_text
        variants = sorted(
            {row["rumor_text"] for row in grouped[event_id]},
            key=lambda value: (-len(value), value),
        )[:max_variants_per_event]

        positive_queries = variants if variants else [anchor_text or canonical_text]
        positive_targets = [anchor_text]
        if canonical_text and canonical_text not in positive_targets:
            positive_targets.append(canonical_text)
        for variant in positive_queries:
            for target_text in positive_targets:
                split_samples[split].append(
                    {
                        "event_id": event_id,
                        "text_a": variant,
                        "text_b": target_text,
                        "label": 1,
                        "split": split,
                        "pair_type": "positive",
                    }
                )

            negative_pool = [item for item in hard_negative_map.get(event_id, []) if item in by_id]
            if len(negative_pool) < negatives_per_positive:
                remaining = [item["event_id"] for item in eligible_catalog if item["event_id"] != event_id]
                rng.shuffle(remaining)
                negative_pool.extend(remaining)

            used_negative_ids: set[str] = set()
            for negative_event_id in negative_pool:
                if negative_event_id == event_id or negative_event_id in used_negative_ids:
                    continue
                used_negative_ids.add(negative_event_id)
                negative_event = by_id.get(negative_event_id)
                if negative_event is None:
                    continue
                negative_target = (
                    negative_event.get("anchor_text")
                    or negative_event.get("canonical_text")
                    or negative_event.get("representative_text")
                )
                split_samples[split].append(
                    {
                        "event_id": event_id,
                        "negative_event_id": negative_event_id,
                        "text_a": variant,
                        "text_b": negative_target,
                        "label": 0,
                        "split": split,
                        "pair_type": "hard_negative",
                    }
                )
                if len(used_negative_ids) >= negatives_per_positive:
                    break

    return split_samples


def build_event_matching_assets(
    cleaned_records_path: Path,
    output_dir: Path,
    *,
    min_event_size: int = 2,
    max_variants_per_event: int = 12,
    negatives_per_positive: int = 2,
    random_seed: int = 42,
) -> dict[str, Path]:
    ensure_directory(output_dir)
    cleaned_records = read_jsonl(cleaned_records_path)
    event_catalog = build_event_catalog(cleaned_records, min_event_size=min_event_size)

    catalog_path = output_dir / "event_catalog.jsonl"
    write_jsonl(catalog_path, event_catalog)

    split_samples = build_pair_samples(
        cleaned_records,
        event_catalog,
        min_event_size=min_event_size,
        max_variants_per_event=max_variants_per_event,
        negatives_per_positive=negatives_per_positive,
        random_seed=random_seed,
    )

    pair_dir = ensure_directory(output_dir / "pair_data")
    pair_paths: dict[str, Path] = {}
    label_distribution = {}
    for split_name, rows in split_samples.items():
        path = pair_dir / f"{split_name}.jsonl"
        write_jsonl(path, rows)
        pair_paths[split_name] = path
        label_distribution[split_name] = Counter(row["label"] for row in rows)

    report_path = output_dir / "dataset_report.json"
    write_json(
        report_path,
        {
            "cleaned_records_path": str(cleaned_records_path),
            "catalog_size": len(event_catalog),
            "eligible_events": sum(1 for item in event_catalog if item["sample_count"] >= min_event_size),
            "split_event_counts": Counter(item["split"] for item in event_catalog),
            "pair_counts": {split_name: len(rows) for split_name, rows in split_samples.items()},
            "label_distribution": {split: dict(counter) for split, counter in label_distribution.items()},
            "min_event_size": min_event_size,
            "max_variants_per_event": max_variants_per_event,
            "negatives_per_positive": negatives_per_positive,
        },
    )

    outputs = {"catalog": catalog_path, "report": report_path}
    outputs.update({f"pairs_{split}": path for split, path in pair_paths.items()})
    return outputs


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build event catalog and pair dataset from cleaned records.")
    parser.add_argument("--input", required=True, type=Path, help="Path to cleaned_records.jsonl.")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--min-event-size", type=int, default=2)
    parser.add_argument("--max-variants-per-event", type=int, default=12)
    parser.add_argument("--negatives-per-positive", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    outputs = build_event_matching_assets(
        args.input,
        args.output_dir,
        min_event_size=args.min_event_size,
        max_variants_per_event=args.max_variants_per_event,
        negatives_per_positive=args.negatives_per_positive,
        random_seed=args.seed,
    )
    print(json.dumps({key: str(value) for key, value in outputs.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
