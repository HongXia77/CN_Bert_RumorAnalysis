from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
AT_RE = re.compile(r"@\S+")
HASHTAG_RE = re.compile(r"#([^#]+)#?")
EMOJI_BRACKET_RE = re.compile(r"\[[^\]]*]")
WHITESPACE_RE = re.compile(r"\s+")
REPEATED_PUNCT_RE = re.compile(r"([!,.?;:~\-_=+])\1+")
NON_WORD_GAP_RE = re.compile(r"^[\W_]+|[\W_]+$")
ALNUM_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)

DETAIL_MARKER = "\u8be6\u60c5"
ACCORDING_NOW_MARKER = "\u73b0\u6839\u636e"
ACCORDING_MARKER = "\u6839\u636e"
REPORTED_ACCOUNT_MARKER = "\u88ab\u4e3e\u62a5\u4eba"
ABOVE_ACTION_MARKER = "\u4e0a\u8ff0\u5904\u7406"
VERDICT_PREFIXES = (
    "\u7ecf\u67e5",
    "\u6b64\u5fae\u535a\u79f0",
    "\u8be5\u5fae\u535a\u79f0",
    "\u6b64\u5fae\u535a\u4e2d\u6240\u79f0",
    "\u6b64\u5fae\u535a\u4e2d\u79f0",
    "\u6b64\u5fae\u535a\u6240\u79f0",
    "\u6b64\u5fae\u535a\u914d\u56fe\u79f0",
    "\u8be5\u5fae\u535a\u914d\u56fe\u79f0",
)
COMMON_SEPARATORS = " \t\r\n,.;:!?~`'\"|/\\()[]{}<>-_+=\u3002\uff0c\uff1b\uff1a\uff01\uff1f\u2014\u3001"


def collapse_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def strip_social_markup(text: str) -> str:
    text = URL_RE.sub(" ", text)
    text = AT_RE.sub(" ", text)
    text = HASHTAG_RE.sub(r"\1", text)
    text = EMOJI_BRACKET_RE.sub(" ", text)
    return text


def normalize_rumor_text(text: str) -> str:
    text = strip_social_markup(text or "")
    text = text.replace("\u00a0", " ").replace("\u3000", " ")
    text = REPEATED_PUNCT_RE.sub(r"\1", text)
    text = collapse_whitespace(text)
    text = NON_WORD_GAP_RE.sub("", text)
    return text.strip(COMMON_SEPARATORS)


def clean_result_summary(text: str) -> str:
    text = (text or "").replace("\u00a0", " ").replace("\u3000", " ")

    for marker in (
        DETAIL_MARKER,
        ACCORDING_NOW_MARKER,
        ACCORDING_MARKER,
        REPORTED_ACCOUNT_MARKER,
        ABOVE_ACTION_MARKER,
    ):
        if marker in text:
            text = text.split(marker, 1)[0]

    text = URL_RE.sub(" ", text)
    text = collapse_whitespace(text)
    return text.strip(COMMON_SEPARATORS)


def simplify_event_summary(text: str) -> str:
    text = clean_result_summary(text)
    for prefix in VERDICT_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    text = text.lstrip("\uff0c,:;\u3002 ")
    return collapse_whitespace(text).strip(COMMON_SEPARATORS)


def extract_event_focus(summary: str, fallback_text: str = "") -> str:
    summary = simplify_event_summary(summary)
    quoted_segments = re.findall(r"[\u201c\"]([^\"\u201d]{4,80})[\u201d\"]", summary)
    if quoted_segments:
        return quoted_segments[0].strip(COMMON_SEPARATORS)

    first_clause = re.split(r"[\u3002\uff01\uff1f\uff1b;.!?]", summary, maxsplit=1)[0]
    first_clause = first_clause.strip(COMMON_SEPARATORS)
    if len(first_clause) >= 8:
        return first_clause[:80]

    fallback_text = normalize_rumor_text(fallback_text)
    return fallback_text[:80]


def stable_text_hash(text: str, length: int = 16) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length]


def event_id_from_summary(summary: str) -> str:
    return stable_text_hash(simplify_event_summary(summary), length=16)


def char_bigrams(text: str) -> Counter[str]:
    normalized = normalize_rumor_text(text).lower()
    if not normalized:
        return Counter()

    features: Counter[str] = Counter()
    for match in ALNUM_TOKEN_RE.finditer(normalized):
        token = match.group(0)
        if len(token) >= 2:
            features[f"tok:{token}"] += 1

    cjk_stream = ALNUM_TOKEN_RE.sub(" ", normalized)
    cjk_stream = "".join(cjk_stream.split())
    if len(cjk_stream) >= 2:
        features.update(f"bg:{cjk_stream[index:index + 2]}" for index in range(len(cjk_stream) - 1))
    elif cjk_stream:
        features[f"uni:{cjk_stream}"] += 1

    return features


def cosine_from_counters(left: Counter[str], right: Counter[str], idf: dict[str, float] | None = None) -> float:
    if not left or not right:
        return 0.0

    overlap = set(left) & set(right)
    if not overlap:
        return 0.0

    def weight(token: str) -> float:
        return idf[token] if idf and token in idf else 1.0

    numerator = sum(left[token] * right[token] * weight(token) * weight(token) for token in overlap)
    left_norm = math.sqrt(sum((count * weight(token)) ** 2 for token, count in left.items()))
    right_norm = math.sqrt(sum((count * weight(token)) ** 2 for token, count in right.items()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
