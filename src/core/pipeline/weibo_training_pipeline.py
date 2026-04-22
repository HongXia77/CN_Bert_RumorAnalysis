from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.core.data_cleansing.weibo_rumor_cleaner import clean_weibo_rumor_dataset
from src.core.dataset_building.event_dataset_builder import build_event_matching_assets
from src.core.training.lexical_event_index_builder import build_lexical_index


def run_pipeline(
    input_path: Path,
    output_dir: Path,
    *,
    min_text_length: int = 12,
    min_event_size: int = 2,
    max_variants_per_event: int = 12,
    negatives_per_positive: int = 2,
) -> dict[str, str]:
    cleaned_dir = output_dir / "cleaned"
    dataset_dir = output_dir / "dataset"
    index_dir = output_dir / "index"

    cleaning_outputs = clean_weibo_rumor_dataset(
        input_path,
        cleaned_dir,
        min_text_length=min_text_length,
    )
    dataset_outputs = build_event_matching_assets(
        Path(cleaning_outputs["cleaned_records"]),
        dataset_dir,
        min_event_size=min_event_size,
        max_variants_per_event=max_variants_per_event,
        negatives_per_positive=negatives_per_positive,
    )
    lexical_index_path = build_lexical_index(
        Path(dataset_outputs["catalog"]),
        index_dir / "lexical_event_index.json",
    )

    combined = {
        "cleaned_records": str(cleaning_outputs["cleaned_records"]),
        "cleaning_report": str(cleaning_outputs["report"]),
        "event_catalog": str(dataset_outputs["catalog"]),
        "dataset_report": str(dataset_outputs["report"]),
        "pair_train": str(dataset_outputs["pairs_train"]),
        "pair_val": str(dataset_outputs["pairs_val"]),
        "pair_test": str(dataset_outputs["pairs_test"]),
        "lexical_index": str(lexical_index_path),
    }
    with (output_dir / "pipeline_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(combined, handle, ensure_ascii=False, indent=2)
    return combined


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the full Weibo rumor asset pipeline.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--min-text-length", type=int, default=12)
    parser.add_argument("--min-event-size", type=int, default=2)
    parser.add_argument("--max-variants-per-event", type=int, default=12)
    parser.add_argument("--negatives-per-positive", type=int, default=2)
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    outputs = run_pipeline(
        args.input,
        args.output_dir,
        min_text_length=args.min_text_length,
        min_event_size=args.min_event_size,
        max_variants_per_event=args.max_variants_per_event,
        negatives_per_positive=args.negatives_per_positive,
    )
    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
