# Core Rumor Pipeline

This folder contains the backend-oriented asset pipeline for rumor-event matching.

## Layout

- `common/`: shared text and file helpers
- `data_cleansing/`: raw dataset cleaning
- `dataset_building/`: event catalog and pair-sample generation
- `training/`: lexical index builder and BERT pair trainer
- `inference/`: lexical and hybrid matchers
- `pipeline/`: end-to-end orchestration scripts

## Recommended Commands

Run the full Weibo asset pipeline:

```bash
python -m src.core.pipeline.weibo_training_pipeline \
  --input data/rumors_v170613.json \
  --output-dir data/processed/weibo_v170613
```

Train a BERT pair classifier after installing `torch` and `transformers`:

```bash
python -m src.core.training.bert_pair_trainer \
  --train data/processed/weibo_v170613/dataset/pair_data/train.jsonl \
  --val data/processed/weibo_v170613/dataset/pair_data/val.jsonl \
  --model-name-or-path model/bert-base-chinese \
  --output-dir output/event_pair_model
```
