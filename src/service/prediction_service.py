import logging
import math
import os
from pathlib import Path

from src.core.common.text_utils import char_bigrams, cosine_from_counters

logger = logging.getLogger(__name__)


class PredictionConfig:
    def __init__(self):
        # 兼容 Windows + Conda 环境下常见的 OpenMP 重复加载问题，
        # 避免首次加载 PyTorch 模型时直接崩溃。
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        import torch

        project_root = Path(__file__).resolve().parents[2]
        default_model_dir = project_root / "output" / "model"
        default_event_model_dir = project_root / "output" / "event_pair_model"
        default_event_index_path = (
            project_root / "data" / "processed" / "weibo_v170613" / "index" / "lexical_event_index.json"
        )
        self.model_dir = Path(os.getenv("RUMOR_MODEL_DIR", str(default_model_dir)))
        self.event_model_dir = Path(os.getenv("RUMOR_EVENT_MODEL_DIR", str(default_event_model_dir)))
        self.event_index_path = Path(os.getenv("RUMOR_EVENT_INDEX_PATH", str(default_event_index_path)))
        self.max_seq_length = int(os.getenv("RUMOR_MAX_SEQ_LENGTH", "128"))
        self.event_candidate_pool = int(os.getenv("RUMOR_EVENT_CANDIDATE_POOL", "20"))
        self.event_topk = int(os.getenv("RUMOR_EVENT_TOPK", "5"))
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


_prediction_bundle = None
_event_bundle = None


def _validate_model_files(model_dir: Path) -> None:
    required_files = [
        "config.json",
        "model.safetensors",
        "tokenizer.json",
        "tokenizer_config.json",
    ]
    missing_files = [name for name in required_files if not (model_dir / name).exists()]
    if missing_files:
        raise FileNotFoundError(
            f"模型目录缺少必要文件: {', '.join(missing_files)} | dir={model_dir}"
        )


def _load_bundle():
    global _prediction_bundle

    if _prediction_bundle is None:
        config = PredictionConfig()
        import torch
        from transformers import BertForSequenceClassification, BertTokenizer

        _validate_model_files(config.model_dir)

        logger.info("加载谣言识别模型: %s", config.model_dir)
        tokenizer = BertTokenizer.from_pretrained(config.model_dir)
        model = BertForSequenceClassification.from_pretrained(config.model_dir)
        model.to(config.device)
        model.eval()

        _prediction_bundle = (model, tokenizer, config, torch)

    return _prediction_bundle


def _load_event_bundle():
    global _event_bundle

    if _event_bundle is None:
        config = PredictionConfig()
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        from src.core.inference.lexical_ranker import LexicalEventRanker

        _validate_model_files(config.event_model_dir)
        if not config.event_index_path.exists():
            raise FileNotFoundError(f"事件索引文件不存在: {config.event_index_path}")

        logger.info("加载主谣言事件匹配模型: %s", config.event_model_dir)
        event_tokenizer = AutoTokenizer.from_pretrained(config.event_model_dir)
        event_model = AutoModelForSequenceClassification.from_pretrained(config.event_model_dir)
        event_model.to(config.device)
        event_model.eval()
        event_ranker = LexicalEventRanker(config.event_index_path)
        _event_bundle = (event_model, event_tokenizer, event_ranker, config, torch)

    return _event_bundle


def _score_with_base_model(text: str) -> dict:
    model, tokenizer, config, torch = _load_bundle()
    normalized_text = text.strip()

    if not normalized_text:
        raise ValueError("待识别文本不能为空")

    encoding = tokenizer(
        normalized_text,
        add_special_tokens=True,
        max_length=config.max_seq_length,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )

    input_ids = encoding["input_ids"].to(config.device)
    attention_mask = encoding["attention_mask"].to(config.device)

    with torch.no_grad():
        outputs = model(input_ids, attention_mask=attention_mask)
        probabilities = torch.softmax(outputs.logits, dim=1)
        rumor_probability = float(probabilities[0][1].item())

    return {
        "text": normalized_text,
        "rumor_probability": rumor_probability,
    }


def _build_match_hint(match_score: float, pair_score: float, lexical_score: float) -> str:
    if match_score >= 0.85:
        return "与已知主谣言事件高度接近，可优先按疑似已知谣言核查"
    if pair_score >= 0.7:
        return "语义重排结果较强，建议优先查看该主事件"
    if lexical_score >= 0.3:
        return "词法表达存在较强重合，可作为候选主谣言继续核查"
    return "作为占位候选返回，供进一步核查"


def _candidate_pair_texts(candidate: dict) -> list[tuple[str, str]]:
    texts: list[tuple[str, str]] = []
    seen: set[str] = set()

    lexical_text = (candidate.get("lexical_text") or "").strip()
    if lexical_text:
        seen.add(lexical_text)
        texts.append((candidate.get("lexical_view") or "lexical_text", lexical_text))

    for field_name in ("canonical_text", "anchor_text", "representative_text"):
        value = (candidate.get(field_name) or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        texts.append((field_name, value))

    for index, value in enumerate(candidate.get("example_texts", [])[:2], start=1):
        normalized = (value or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        texts.append((f"example_{index}", normalized))

    return texts


def _official_candidate_pair_texts(candidate: dict) -> list[tuple[str, str]]:
    texts: list[tuple[str, str]] = []
    seen: set[str] = set()

    title = (candidate.get("title") or "").strip()
    claim_text = (candidate.get("claim_text") or "").strip()
    content = (candidate.get("content") or "").strip()
    truth_text = (candidate.get("truth_text") or "").strip()

    for field_name, value in (
        ("claim_text", claim_text),
        ("content", content),
        ("title", title),
    ):
        if not value or value in seen:
            continue
        seen.add(value)
        texts.append((field_name, value))

    if title and content:
        combined = f"{title} {content}".strip()
        if combined not in seen:
            seen.add(combined)
            texts.append(("title_plus_content", combined))

    if claim_text and truth_text:
        combined = f"{claim_text} {truth_text}".strip()
        if combined not in seen:
            seen.add(combined)
            texts.append(("claim_plus_truth", combined))

    return texts


def _blend_event_match_score(
    pair_score: float,
    lexical_score: float,
    *,
    coherence_score: float = 1.0,
    lexical_view: str = "",
    overlap_count: int = 0,
    sample_count: int = 0,
) -> float:
    lexical_signal = math.sqrt(max(lexical_score, 0.0))
    match_score = lexical_signal * (0.55 + 0.45 * pair_score)
    if lexical_score < 0.06:
        match_score *= 0.55
    elif lexical_score < 0.12:
        match_score *= 0.72
    if overlap_count <= 1:
        match_score *= 0.52 if lexical_score < 0.18 else 0.72
    elif overlap_count == 2 and lexical_score < 0.18:
        match_score *= 0.82
    if sample_count <= 1 and coherence_score < 0.12 and overlap_count <= 1:
        match_score *= 0.68
    if lexical_view == "anchor_text" and coherence_score < 0.22:
        match_score *= max(0.38, coherence_score * 2.0)
    return max(0.0, min(1.0, match_score))


def _blend_official_match_score(
    pair_score: float,
    lexical_score: float,
    *,
    coherence_score: float = 1.0,
    overlap_count: int = 0,
) -> float:
    pair_signal = max(pair_score, 0.0)
    lexical_signal = max(lexical_score, 0.0)
    match_score = pair_signal * 0.58 + lexical_signal * 0.42

    if overlap_count >= 5 and pair_signal >= 0.88 and lexical_signal >= 0.18:
        match_score = max(match_score, 0.8)
    elif overlap_count >= 3 and pair_signal >= 0.78 and lexical_signal >= 0.14:
        match_score = max(match_score, 0.68)
    elif overlap_count >= 2 and pair_signal >= 0.68 and lexical_signal >= 0.1:
        match_score = max(match_score, 0.54)

    if overlap_count <= 1:
        match_score = min(match_score, lexical_signal * 1.18 + 0.02)
    elif overlap_count == 2 and lexical_signal < 0.18:
        match_score = min(match_score, 0.46)

    if lexical_signal < 0.05 and pair_signal < 0.58:
        match_score *= 0.82
    if coherence_score < 0.12 and lexical_signal < 0.08:
        match_score *= max(0.72, coherence_score * 3.2)

    return max(0.0, min(1.0, match_score))


def _score_event_candidates(text: str, *, limit: int | None = None) -> list[dict]:
    event_model, event_tokenizer, event_ranker, config, torch = _load_event_bundle()
    candidate_pool = max(limit or config.event_topk, config.event_candidate_pool)
    lexical_candidates = event_ranker.rank(text, limit=candidate_pool)
    if not lexical_candidates:
        return []

    pair_views: list[tuple[dict, str, str]] = []
    for candidate in lexical_candidates:
        candidate_views = _candidate_pair_texts(candidate)
        if not candidate_views:
            candidate_views = [("canonical_text", candidate.get("canonical_text", ""))]
        for view_name, view_text in candidate_views:
            pair_views.append((candidate, view_name, view_text))

    encoded = event_tokenizer(
        [text] * len(pair_views),
        [view_text for _, _, view_text in pair_views],
        truncation=True,
        padding="max_length",
        max_length=config.max_seq_length,
        return_tensors="pt",
    )
    encoded = {key: value.to(config.device) for key, value in encoded.items()}

    with torch.no_grad():
        outputs = event_model(**encoded)
        pair_probabilities = torch.softmax(outputs.logits, dim=1)[:, 1].detach().cpu().tolist()

    per_event_views: dict[str, list[dict]] = {}
    for (candidate, view_name, view_text), pair_probability in zip(pair_views, pair_probabilities):
        per_event_views.setdefault(candidate["event_id"], []).append(
            {
                "view_name": view_name,
                "view_text": view_text,
                "pair_score": float(pair_probability),
            }
        )

    ranked_items = []
    for candidate in lexical_candidates:
        lexical_score = float(candidate["score"])
        view_scores = per_event_views.get(candidate["event_id"], [])
        best_view = max(view_scores, key=lambda item: item["pair_score"]) if view_scores else None
        pair_score = float(best_view["pair_score"]) if best_view else 0.0
        canonical_text = candidate.get("canonical_text") or candidate.get("event_focus") or ""
        anchor_text = candidate.get("anchor_text") or candidate.get("representative_text") or canonical_text
        coherence_score = cosine_from_counters(
            char_bigrams(canonical_text),
            char_bigrams(anchor_text),
            None,
        )
        matched_text = best_view["view_text"] if best_view else anchor_text or canonical_text
        overlap_count = len(set(char_bigrams(text)) & set(char_bigrams(matched_text)))
        match_score = _blend_event_match_score(
            pair_score,
            lexical_score,
            coherence_score=coherence_score,
            lexical_view=candidate.get("lexical_view", ""),
            overlap_count=overlap_count,
            sample_count=int(candidate.get("sample_count", 0) or 0),
        )
        ranked_items.append(
            {
                "rumor_id": None,
                "event_id": candidate["event_id"],
                "title": canonical_text or candidate.get("representative_title") or anchor_text,
                "content": anchor_text or canonical_text,
                "truth_text": candidate.get("event_summary") or "",
                "source_name": "微博辟谣公开数据集",
                "publish_time": "",
                "article_url": None,
                "match_score": round(match_score, 6),
                "pair_score": round(pair_score, 6),
                "lexical_score": round(lexical_score, 6),
                "match_hint": _build_match_hint(match_score, pair_score, lexical_score),
                "candidate_source": "weibo_event",
                "sample_count": candidate.get("sample_count", 0),
                "anchor_text": anchor_text,
                "matched_text": matched_text,
                "matched_view": best_view["view_name"] if best_view else "canonical_text",
                "coherence_score": round(float(coherence_score), 6),
                "overlap_count": overlap_count,
            }
        )

    ranked_items.sort(
        key=lambda item: (
            item["match_score"],
            item.get("pair_score", 0.0),
            item.get("sample_count", 0),
        ),
        reverse=True,
    )
    return ranked_items[: max(1, limit or config.event_topk)]


def _score_official_candidates(text: str, candidates: list[dict], *, limit: int | None = None) -> list[dict]:
    if not candidates:
        return []

    event_model, event_tokenizer, _, config, torch = _load_event_bundle()
    max_candidates = max(1, limit or config.event_topk)
    candidate_pool = candidates[: max(max_candidates, 12)]

    pair_views: list[tuple[dict, str, str]] = []
    for candidate in candidate_pool:
        candidate_views = _official_candidate_pair_texts(candidate)
        if not candidate_views:
            fallback_text = (
                candidate.get("claim_text")
                or candidate.get("content")
                or candidate.get("title")
                or ""
            )
            candidate_views = [("content", fallback_text)]
        for view_name, view_text in candidate_views:
            pair_views.append((candidate, view_name, view_text))

    encoded = event_tokenizer(
        [text] * len(pair_views),
        [view_text for _, _, view_text in pair_views],
        truncation=True,
        padding="max_length",
        max_length=config.max_seq_length,
        return_tensors="pt",
    )
    encoded = {key: value.to(config.device) for key, value in encoded.items()}

    with torch.no_grad():
        outputs = event_model(**encoded)
        pair_probabilities = torch.softmax(outputs.logits, dim=1)[:, 1].detach().cpu().tolist()

    per_rumor_views: dict[str, list[dict]] = {}
    for (candidate, view_name, view_text), pair_probability in zip(pair_views, pair_probabilities):
        candidate_key = str(candidate.get("rumor_id") or candidate.get("article_id") or candidate.get("title") or id(candidate))
        per_rumor_views.setdefault(candidate_key, []).append(
            {
                "view_name": view_name,
                "view_text": view_text,
                "pair_score": float(pair_probability),
            }
        )

    ranked_items = []
    for candidate in candidate_pool:
        candidate_key = str(candidate.get("rumor_id") or candidate.get("article_id") or candidate.get("title") or id(candidate))
        view_scores = per_rumor_views.get(candidate_key, [])
        best_view = max(view_scores, key=lambda item: item["pair_score"]) if view_scores else None
        pair_score = float(best_view["pair_score"]) if best_view else 0.0
        lexical_score = float(candidate.get("match_score") or 0.0)
        content_text = (candidate.get("content") or candidate.get("claim_text") or candidate.get("title") or "").strip()
        anchor_text = (candidate.get("claim_text") or candidate.get("title") or content_text).strip()
        matched_text = best_view["view_text"] if best_view else content_text
        coherence_score = cosine_from_counters(
            char_bigrams(content_text),
            char_bigrams(anchor_text),
            None,
        )
        overlap_count = len(set(char_bigrams(text)) & set(char_bigrams(matched_text)))
        match_score = _blend_official_match_score(
            pair_score,
            lexical_score,
            coherence_score=coherence_score,
            overlap_count=overlap_count,
        )
        ranked_items.append(
            {
                **candidate,
                "match_score": round(match_score, 6),
                "pair_score": round(pair_score, 6),
                "lexical_score": round(lexical_score, 6),
                "matched_text": matched_text,
                "matched_view": best_view["view_name"] if best_view else "content",
                "coherence_score": round(float(coherence_score), 6),
                "overlap_count": overlap_count,
                "candidate_source": "official_db",
                "match_hint": _build_match_hint(match_score, pair_score, lexical_score),
            }
        )

    ranked_items.sort(
        key=lambda item: (
            item["match_score"],
            item.get("pair_score", 0.0),
            item.get("lexical_score", 0.0),
            item.get("publish_time") or "",
        ),
        reverse=True,
    )
    return ranked_items[:max_candidates]


def _merge_related_rumors(
    event_candidates: list[dict],
    official_candidates: list[dict],
    *,
    limit: int = 5,
) -> list[dict]:
    merged_items: list[dict] = []
    seen: set[tuple[str | None, str | None, str | None]] = set()

    def _signature(item: dict) -> tuple[str | None, str | None, str | None]:
        return (
            str(item.get("rumor_id")) if item.get("rumor_id") is not None else None,
            item.get("event_id"),
            (item.get("title") or item.get("content") or "").strip(),
        )

    for candidate in [*official_candidates, *event_candidates]:
        signature = _signature(candidate)
        if signature in seen:
            continue
        seen.add(signature)
        merged_items.append(candidate)

    merged_items.sort(
        key=lambda item: (
            float(item.get("match_score") or 0.0) + (0.06 if item.get("candidate_source") == "official_db" else 0.0),
            1 if item.get("candidate_source") == "official_db" else 0,
            float(item.get("pair_score") or 0.0),
        ),
        reverse=True,
    )
    return merged_items[: max(1, limit)]


def _is_low_quality_candidate(item: dict) -> bool:
    match_score = float(item.get("match_score") or 0.0)
    lexical_score = float(item.get("lexical_score") or 0.0)
    pair_score = float(item.get("pair_score") or 0.0)
    overlap_count = int(item.get("overlap_count") or 0)
    coherence_score = float(item.get("coherence_score") or 0.0)
    sample_count = int(item.get("sample_count") or 0)
    source = item.get("candidate_source")

    if match_score >= 0.62:
        return False
    if match_score < 0.18 and lexical_score < 0.12:
        return True

    if source == "official_db":
        if overlap_count <= 1 and lexical_score < 0.24 and match_score < 0.34:
            return True
        if overlap_count == 0 and match_score < 0.4:
            return True
        return False

    if overlap_count <= 1 and lexical_score < 0.18 and match_score < 0.34:
        return True
    if sample_count <= 1 and coherence_score < 0.12 and match_score < 0.36:
        return True
    if pair_score < 0.12 and lexical_score < 0.18 and match_score < 0.28:
        return True
    return False


def _filter_related_rumors(candidates: list[dict], *, limit: int) -> list[dict]:
    filtered = [item for item in candidates if not _is_low_quality_candidate(item)]
    return filtered[: max(1, limit)]


def _prune_dominated_candidates(candidates: list[dict], *, limit: int) -> list[dict]:
    if not candidates:
        return []

    top_item = candidates[0]
    top_score = float(top_item.get("match_score") or 0.0)
    if top_score < 0.58:
        return candidates[: max(1, limit)]

    kept = [top_item]
    for item in candidates[1:]:
        score = float(item.get("match_score") or 0.0)
        source = item.get("candidate_source")
        if top_score >= 0.9:
            if score >= 0.6 and (top_score - score) <= 0.22:
                kept.append(item)
        elif top_score >= 0.78:
            if score >= 0.4 and (top_score - score) <= 0.32:
                kept.append(item)
        else:
            if score >= 0.28 and (top_score - score) <= 0.36:
                kept.append(item)
            elif source != top_item.get("candidate_source") and score >= 0.34 and (top_score - score) <= 0.42:
                kept.append(item)

    return kept[: max(1, limit)]


def _blend_rumor_probability(
    base_probability: float,
    event_match_probability: float,
    *,
    top_lexical_score: float = 0.0,
    official_match_probability: float = 0.0,
    official_lexical_score: float = 0.0,
) -> float:
    known_match_probability = max(event_match_probability, official_match_probability)

    if known_match_probability >= 0.78:
        blended = max(base_probability * 0.42 + known_match_probability * 0.58, 0.82)
    elif known_match_probability >= 0.58:
        blended = max(base_probability * 0.24 + known_match_probability * 0.76, 0.58)
    elif known_match_probability >= 0.4:
        blended = max(base_probability * 0.12 + known_match_probability * 0.88, 0.43)
    elif known_match_probability >= 0.25:
        blended = max(0.22 + known_match_probability * 0.38, known_match_probability * 0.78)
    else:
        blended = min(0.39, base_probability * 0.35)

    if official_match_probability >= 0.82:
        blended = max(blended, 0.86)
    elif official_match_probability >= 0.68:
        blended = max(blended, 0.74)
    elif official_match_probability >= 0.54:
        blended = max(blended, 0.6)

    if known_match_probability < 0.18 and max(top_lexical_score, official_lexical_score) < 0.14:
        blended = min(blended, 0.29)
    if max(top_lexical_score, official_lexical_score) < 0.18 and known_match_probability < 0.45:
        blended = min(blended, 0.39)
    return max(0.01, min(blended, 0.99))


def _build_verdict(rumor_probability: float, related_rumors: list[dict], known_match_probability: float) -> tuple[str, str]:
    if not related_rumors or known_match_probability < 0.2:
        if rumor_probability >= 0.45:
            return "medium", "文本呈现一定风险，但未匹配到已知主谣言，建议人工复核"
        return "low", "未匹配到已知主谣言，建议进一步核查"

    if rumor_probability >= 0.75:
        risk_level = "high"
        verdict = "高度疑似已知谣言变体" if related_rumors else "高度疑似谣言"
    elif rumor_probability >= 0.45:
        risk_level = "medium"
        verdict = "存在较高风险，建议结合候选主谣言继续核查" if related_rumors else "存在较高风险，建议继续核查"
    else:
        risk_level = "low"
        verdict = "当前未发现明显高风险匹配，可继续人工核查" if related_rumors else "当前更接近真实或中性信息"

    return risk_level, verdict


def predict_text(text: str, *, official_candidates: list[dict] | None = None) -> dict:
    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("待识别文本不能为空")

    base_payload = _score_with_base_model(normalized_text)
    base_probability = float(base_payload["rumor_probability"])

    config = PredictionConfig()
    try:
        _, _, _, config, _ = _load_event_bundle()
        related_rumors = _score_event_candidates(normalized_text)
        official_related_rumors = _score_official_candidates(
            normalized_text,
            official_candidates or [],
            limit=3,
        )
    except FileNotFoundError as exc:
        logger.warning("主谣言事件资源缺失，回退到基础二分类: %s", exc)
        related_rumors = []
        official_related_rumors = []

    event_match_probability = float(related_rumors[0]["match_score"]) if related_rumors else 0.0
    top_lexical_score = float(related_rumors[0]["lexical_score"]) if related_rumors else 0.0
    official_match_probability = float(official_related_rumors[0]["match_score"]) if official_related_rumors else 0.0
    official_lexical_score = float(official_related_rumors[0]["lexical_score"]) if official_related_rumors else 0.0
    merged_related_rumors = _merge_related_rumors(
        related_rumors,
        official_related_rumors,
        limit=max(config.event_topk, 5),
    )
    merged_related_rumors = _filter_related_rumors(
        merged_related_rumors,
        limit=max(config.event_topk, 5),
    )
    merged_related_rumors = _prune_dominated_candidates(
        merged_related_rumors,
        limit=max(config.event_topk, 5),
    )
    if merged_related_rumors:
        top_candidate = merged_related_rumors[0]
        if top_candidate.get("candidate_source") == "official_db":
            official_match_probability = float(top_candidate.get("match_score") or 0.0)
            official_lexical_score = float(top_candidate.get("lexical_score") or 0.0)
            event_match_probability = max(
                (
                    float(item.get("match_score") or 0.0)
                    for item in merged_related_rumors
                    if item.get("candidate_source") == "weibo_event"
                ),
                default=0.0,
            )
            top_lexical_score = max(
                (
                    float(item.get("lexical_score") or 0.0)
                    for item in merged_related_rumors
                    if item.get("candidate_source") == "weibo_event"
                ),
                default=0.0,
            )
        else:
            event_match_probability = float(top_candidate.get("match_score") or 0.0)
            top_lexical_score = float(top_candidate.get("lexical_score") or 0.0)
            official_match_probability = max(
                (
                    float(item.get("match_score") or 0.0)
                    for item in merged_related_rumors
                    if item.get("candidate_source") == "official_db"
                ),
                default=0.0,
            )
            official_lexical_score = max(
                (
                    float(item.get("lexical_score") or 0.0)
                    for item in merged_related_rumors
                    if item.get("candidate_source") == "official_db"
                ),
                default=0.0,
            )
    else:
        event_match_probability = 0.0
        top_lexical_score = 0.0
        official_match_probability = 0.0
        official_lexical_score = 0.0
    rumor_probability = _blend_rumor_probability(
        base_probability,
        event_match_probability,
        top_lexical_score=top_lexical_score,
        official_match_probability=official_match_probability,
        official_lexical_score=official_lexical_score,
    )
    known_match_probability = max(event_match_probability, official_match_probability)
    risk_level, verdict = _build_verdict(rumor_probability, merged_related_rumors, known_match_probability)

    return {
        "text": normalized_text,
        "label": "rumor" if rumor_probability >= 0.5 else "normal",
        "verdict": verdict,
        "risk_level": risk_level,
        "rumor_probability": rumor_probability,
        "credible_probability": 1 - rumor_probability,
        "base_model_probability": base_probability,
        "event_match_probability": event_match_probability,
        "official_match_probability": official_match_probability,
        "known_match_probability": known_match_probability,
        "related_rumors": merged_related_rumors,
    }
