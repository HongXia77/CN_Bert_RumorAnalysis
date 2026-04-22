from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher


LEADING_WRAPPER_PATTERNS = [
    r"^\s*网传[:：]?\s*",
    r"^\s*传言[:：]?\s*",
    r"^\s*消息称[:：]?\s*",
    r"^\s*有消息称[:：]?\s*",
    r"^\s*有人说[:：]?\s*",
    r"^\s*听说[:：]?\s*",
    r"^\s*据说[:：]?\s*",
    r"^\s*所谓[:：]?\s*",
    r"^\s*辟谣[:：]?\s*",
    r"^\s*详情[:：]?\s*",
]

TRAILING_WRAPPER_PATTERNS = [
    r"\s*系谣言\s*$",
    r"\s*属谣言\s*$",
    r"\s*为谣言\s*$",
    r"\s*不实\s*$",
    r"\s*纯属谣言\s*$",
    r"\s*来源[:：].*$",
]

GLOBAL_NOISE_PATTERNS = [
    r"互联网联合辟谣平台",
    r"中国互联网联合辟谣平台",
    r"联合辟谣平台",
    r"不信谣不传谣",
]

PUNCTUATION_PATTERN = re.compile(r"[\"'“”‘’`~!@#$%^&*()_\-+=|\\/:;,.?，。？！；：（）【】《》、·\[\]{}<>]+")
WHITESPACE_PATTERN = re.compile(r"\s+")
FACT_TOKEN_PATTERN = re.compile(
    r"(?:\d+(?:\.\d+)?)"
    r"(?:年|月|日|号|天|小时|分钟|秒|人|个|次|岁|级|公里|千米|米|万|亿|吨|斤|克|千克|公斤|%"
    r"|％)?"
)


@dataclass(frozen=True)
class RumorMergeFeatures:
    original_text: str
    normalized_text: str
    merge_text: str
    merge_key_hash: str
    fact_signature: str
    char_bigrams: frozenset[str]


@dataclass(frozen=True)
class RumorMergeComparison:
    sequence_ratio: float
    bigram_jaccard: float
    hard_fact_conflict: bool


def normalize_rumor_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.replace("\u3000", " ").strip().lower()
    normalized = WHITESPACE_PATTERN.sub(" ", normalized)
    return normalized


def build_rumor_merge_features(text: str) -> RumorMergeFeatures:
    normalized_text = normalize_rumor_text(text)
    merge_text = _build_merge_text(normalized_text)
    merge_key_hash = hashlib.sha1(merge_text.encode("utf-8")).hexdigest()
    fact_signature = _build_fact_signature(normalized_text)
    char_bigrams = frozenset(_build_char_bigrams(merge_text))
    return RumorMergeFeatures(
        original_text=text,
        normalized_text=normalized_text,
        merge_text=merge_text,
        merge_key_hash=merge_key_hash,
        fact_signature=fact_signature,
        char_bigrams=char_bigrams,
    )


def compare_rumor_features(source: RumorMergeFeatures, target: RumorMergeFeatures) -> RumorMergeComparison:
    hard_fact_conflict = bool(
        source.fact_signature
        and target.fact_signature
        and source.fact_signature != target.fact_signature
    )
    sequence_ratio = SequenceMatcher(None, source.merge_text, target.merge_text).ratio()
    bigram_jaccard = _jaccard_similarity(source.char_bigrams, target.char_bigrams)
    return RumorMergeComparison(
        sequence_ratio=sequence_ratio,
        bigram_jaccard=bigram_jaccard,
        hard_fact_conflict=hard_fact_conflict,
    )


def should_auto_merge(source: RumorMergeFeatures, target: RumorMergeFeatures) -> tuple[bool, float, str]:
    comparison = compare_rumor_features(source, target)
    if comparison.hard_fact_conflict:
        return False, 0.0, "硬事实冲突，禁止自动归并"

    if source.normalized_text == target.normalized_text:
        return True, 1.0, "原文标准化后完全一致"

    if source.merge_key_hash != target.merge_key_hash:
        return False, 0.0, "归并键不同"

    if comparison.sequence_ratio >= 0.96 and comparison.bigram_jaccard >= 0.92:
        confidence = round((comparison.sequence_ratio + comparison.bigram_jaccard) / 2, 4)
        return True, confidence, "归并键一致且相似度达到自动归并阈值"

    return False, 0.0, "相似度不足以自动归并"


def should_mark_pending(source: RumorMergeFeatures, target: RumorMergeFeatures) -> tuple[bool, float, str]:
    comparison = compare_rumor_features(source, target)
    if comparison.hard_fact_conflict:
        return False, 0.0, "硬事实冲突，直接视为不同谣言"

    if source.fact_signature and target.fact_signature and source.fact_signature == target.fact_signature:
        if comparison.sequence_ratio >= 0.62 or comparison.bigram_jaccard >= 0.3:
            confidence = round(max(comparison.sequence_ratio, comparison.bigram_jaccard), 4)
            return True, confidence, "硬事实一致但表达不够接近，进入待合并队列"

    if comparison.sequence_ratio >= 0.9 and comparison.bigram_jaccard >= 0.8:
        confidence = round((comparison.sequence_ratio + comparison.bigram_jaccard) / 2, 4)
        return True, confidence, "文本非常相似，但缺少足够硬事实支撑，进入待合并队列"

    return False, 0.0, "与现有主谣言差异较大"


def _build_merge_text(text: str) -> str:
    merge_text = text
    for pattern in LEADING_WRAPPER_PATTERNS:
        merge_text = re.sub(pattern, "", merge_text)

    for pattern in TRAILING_WRAPPER_PATTERNS:
        merge_text = re.sub(pattern, "", merge_text)

    for pattern in GLOBAL_NOISE_PATTERNS:
        merge_text = re.sub(pattern, " ", merge_text)

    merge_text = merge_text.replace("“", " ").replace("”", " ").replace("‘", " ").replace("’", " ")
    merge_text = PUNCTUATION_PATTERN.sub(" ", merge_text)
    merge_text = WHITESPACE_PATTERN.sub(" ", merge_text).strip()
    return merge_text or text


def _build_fact_signature(text: str) -> str:
    tokens = []
    for token in FACT_TOKEN_PATTERN.findall(text):
        normalized = token.strip()
        if not normalized:
            continue
        if normalized.isdigit() and len(normalized) == 1:
            continue
        tokens.append(normalized)
    return "|".join(sorted(set(tokens)))


def _build_char_bigrams(text: str) -> set[str]:
    compact = WHITESPACE_PATTERN.sub("", text)
    if len(compact) < 2:
        return {compact} if compact else set()
    return {compact[index:index + 2] for index in range(len(compact) - 1)}


def _jaccard_similarity(source: frozenset[str], target: frozenset[str]) -> float:
    if not source and not target:
        return 1.0
    union_size = len(source | target)
    if union_size == 0:
        return 0.0
    return len(source & target) / union_size
