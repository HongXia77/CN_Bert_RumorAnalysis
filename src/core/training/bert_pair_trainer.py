from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def _load_optional_dependencies():
    try:
        import torch
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            get_linear_schedule_with_warmup,
        )
        from torch.optim import AdamW
    except ImportError as exc:
        raise RuntimeError(
            "bert_pair_trainer requires torch and transformers. "
            "Install them inside the project environment before running training."
        ) from exc

    return torch, AutoTokenizer, AutoModelForSequenceClassification, AdamW, get_linear_schedule_with_warmup


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def set_seed(seed: int, torch_module) -> None:
    random.seed(seed)
    torch_module.manual_seed(seed)
    if torch_module.cuda.is_available():
        torch_module.cuda.manual_seed_all(seed)


def train_pair_classifier(
    train_path: Path,
    val_path: Path,
    model_name_or_path: str,
    output_dir: Path,
    *,
    epochs: int = 1,
    batch_size: int = 8,
    max_length: int = 128,
    learning_rate: float = 2e-5,
    seed: int = 42,
) -> dict:
    torch, AutoTokenizer, AutoModelForSequenceClassification, AdamW, get_linear_schedule_with_warmup = (
        _load_optional_dependencies()
    )
    from torch.utils.data import DataLoader, Dataset

    class PairDataset(Dataset):
        def __init__(self, rows: list[dict], tokenizer):
            self.rows = rows
            self.tokenizer = tokenizer

        def __len__(self) -> int:
            return len(self.rows)

        def __getitem__(self, index: int) -> dict:
            row = self.rows[index]
            encoded = self.tokenizer(
                row["text_a"],
                row["text_b"],
                truncation=True,
                padding="max_length",
                max_length=max_length,
                return_tensors="pt",
            )
            item = {key: value.squeeze(0) for key, value in encoded.items()}
            item["labels"] = torch.tensor(int(row["label"]), dtype=torch.long)
            return item

    def build_loader(rows: list[dict], tokenizer, shuffle: bool) -> DataLoader:
        return DataLoader(PairDataset(rows, tokenizer), batch_size=batch_size, shuffle=shuffle)

    set_seed(seed, torch)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_rows = read_jsonl(train_path)
    val_rows = read_jsonl(val_path)
    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_name_or_path, num_labels=2)
    model.to(device)

    train_loader = build_loader(train_rows, tokenizer, shuffle=True)
    val_loader = build_loader(val_rows, tokenizer, shuffle=False)

    optimizer = AdamW(model.parameters(), lr=learning_rate)
    total_steps = max(len(train_loader) * epochs, 1)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(total_steps // 10, 1),
        num_training_steps=total_steps,
    )

    best_val_accuracy = 0.0
    best_epoch = 0
    epoch_metrics: list[dict] = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for epoch in range(epochs):
        model.train()
        for batch in train_loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for batch in val_loader:
                labels = batch["labels"]
                batch = {key: value.to(device) for key, value in batch.items()}
                outputs = model(**batch)
                predictions = torch.argmax(outputs.logits, dim=1).cpu()
                correct += int((predictions == labels).sum().item())
                total += int(labels.size(0))
        val_accuracy = correct / total if total else 0.0
        epoch_metrics.append(
            {
                "epoch": epoch + 1,
                "val_accuracy": round(val_accuracy, 6),
            }
        )
        if val_accuracy >= best_val_accuracy:
            best_val_accuracy = val_accuracy
            best_epoch = epoch + 1
            model.save_pretrained(output_dir)

    tokenizer.save_pretrained(output_dir)

    metrics = {
        "train_rows": len(train_rows),
        "val_rows": len(val_rows),
        "epochs": epochs,
        "batch_size": batch_size,
        "max_length": max_length,
        "learning_rate": learning_rate,
        "best_val_accuracy": round(best_val_accuracy, 6),
        "best_epoch": best_epoch,
        "epoch_metrics": epoch_metrics,
        "device": str(device),
        "model_name_or_path": model_name_or_path,
    }
    with (output_dir / "training_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, ensure_ascii=False, indent=2)

    return metrics


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a BERT pair classifier for rumor-event matching.")
    parser.add_argument("--train", required=True, type=Path)
    parser.add_argument("--val", required=True, type=Path)
    parser.add_argument("--model-name-or-path", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    metrics = train_pair_classifier(
        args.train,
        args.val,
        args.model_name_or_path,
        args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        max_length=args.max_length,
        learning_rate=args.learning_rate,
        seed=args.seed,
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
