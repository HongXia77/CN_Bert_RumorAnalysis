from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from modules.tools.logger import logger
from src.models._init_database import Rumor
from src.utils.rumor_merge import build_rumor_merge_features, compare_rumor_features


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PIYAO_JSONL_PATH = PROJECT_ROOT / "data" / "piyao_platform" / "raw_piyao_articles.jsonl"
DEFAULT_NHC_JSONL_PATH = PROJECT_ROOT / "data" / "platform_feeds" / "nhc_kppypt" / "current" / "articles.jsonl"

VALID_SOURCE_TYPES = {"system", "user"}
VALID_STATUSES = {"pass", "not_pass"}
VALID_LABELS = {0, 1}
DATETIME_INPUT_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
)
WECHAT_URL_RE = re.compile(r"https?://mp\.weixin\.qq\.com/s/[A-Za-z0-9\-_]+")
NHC_URL_RE = re.compile(r"https?://www\.nhc\.gov\.cn/[^\s\"']+?\.shtml")
GENERIC_URL_RE = re.compile(r"https?://[^\s\"']+")


def _strip_unsupported_mysql_chars(value: str) -> str:
    return "".join(char for char in value if ord(char) <= 0xFFFF)


def _clean_text(value) -> str | None:
    if value is None:
        return None

    text = _strip_unsupported_mysql_chars(str(value)).strip()
    return text or None


def _parse_datetime_input(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value

    raw_value = str(value).strip()
    if not raw_value:
        return None

    normalized_value = raw_value.replace("Z", "").replace("/", "-")
    for fmt in DATETIME_INPUT_FORMATS:
        try:
            return datetime.strptime(normalized_value, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(normalized_value)
    except ValueError:
        raise ValueError(f"无法解析发布时间: {raw_value}") from None


def _clean_imported_text(value) -> str | None:
    text = _clean_text(value)
    if not text:
        return None

    text = re.sub(r"^\s*[×✕✖]\s*\n*", "", text)
    text = re.sub(r"^点击(?:下方)?\s*\n*", "", text)
    text = re.sub(r"^查看答案\s*\n*", "", text)
    text = re.sub(r"^[▼▽]\s*\n*", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() or None


def _normalize_article_url(*values) -> str | None:
    candidates: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if cleaned:
            candidates.append(cleaned)

    for candidate in candidates:
        for pattern in (WECHAT_URL_RE, NHC_URL_RE):
            match = pattern.search(candidate)
            if match:
                return match.group(0)

        generic_match = GENERIC_URL_RE.search(candidate)
        if generic_match:
            candidate = generic_match.group(0)

        try:
            parts = urlsplit(candidate)
        except ValueError:
            continue

        if parts.scheme in {"http", "https"} and parts.netloc:
            return candidate

    return None


def _fit_url_for_storage(value: str | None, *, max_length: int) -> str | None:
    if not value:
        return None

    candidate = value
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return candidate[:max_length]

    candidate = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
    if len(candidate) <= max_length:
        return candidate

    if parts.netloc == "mp.weixin.qq.com" and parts.path == "/s" and parts.query:
        core_keys = {"__biz", "mid", "idx", "sn", "chksm"}
        filtered_query = urlencode(
            [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=False) if key in core_keys]
        )
        compact_candidate = urlunsplit((parts.scheme, parts.netloc, parts.path, filtered_query, ""))
        if len(compact_candidate) <= max_length:
            return compact_candidate
        candidate = compact_candidate

    no_query_candidate = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    if len(no_query_candidate) <= max_length:
        return no_query_candidate

    return candidate[:max_length]


def _normalize_article_id(value, *, fallback_url: str | None = None) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        if fallback_url:
            return hashlib.md5(fallback_url.encode("utf-8")).hexdigest()
        return None
    if len(cleaned) <= 64:
        return cleaned
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def _derive_primary_content(*, title: str | None, claim_text: str | None, raw_content: str | None) -> str:
    for candidate in (claim_text, title, raw_content):
        cleaned = _clean_text(candidate)
        if cleaned:
            return cleaned
    return ""


def _apply_merge_features(rumor: Rumor, content: str) -> None:
    features = build_rumor_merge_features(content)
    rumor.normalized_content = features.normalized_text
    rumor.merge_key_hash = features.merge_key_hash
    rumor.fact_signature = features.fact_signature


def serialize_rumor(rumor: Rumor) -> dict:
    return {
        "rumor_id": rumor.rumor_id,
        "title": rumor.title,
        "content": rumor.content,
        "claim_text": rumor.claim_text,
        "truth_text": rumor.truth_text,
        "raw_content": rumor.raw_content,
        "source_name": rumor.source_name,
        "article_id": rumor.article_id,
        "article_url": rumor.article_url,
        "publish_time": rumor.publish_time.isoformat(sep=" ") if rumor.publish_time else None,
        "label": rumor.label,
        "status": rumor.status,
        "source_type": rumor.source_type,
        "upload_user_id": rumor.upload_user_id,
        "upload_count": rumor.upload_count,
        "latest_upload_time": rumor.latest_upload_time.isoformat(sep=" ") if rumor.latest_upload_time else None,
        "refute_link": rumor.refute_link,
        "raw_source_name": rumor.source_name,
        "raw_publish_time": rumor.publish_time.isoformat(sep=" ") if rumor.publish_time else None,
        "create_time": rumor.create_time.isoformat(sep=" ") if rumor.create_time else None,
        "update_time": rumor.update_time.isoformat(sep=" ") if rumor.update_time else None,
    }


def list_rumors(
    db: Session,
    *,
    search: str | None = None,
    source_type: str | None = None,
    status: str | None = None,
    source_name: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
):
    query = db.query(Rumor)

    if search:
        keyword = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Rumor.title.like(keyword),
                Rumor.content.like(keyword),
                Rumor.claim_text.like(keyword),
                Rumor.truth_text.like(keyword),
                Rumor.source_name.like(keyword),
            )
        )

    if source_type:
        query = query.filter(Rumor.source_type == source_type)
    if status:
        query = query.filter(Rumor.status == status)
    if source_name:
        query = query.filter(Rumor.source_name.like(f"%{source_name.strip()}%"))

    ordered_query = query.order_by(
        case((Rumor.publish_time.is_(None), 1), else_=0).asc(),
        Rumor.publish_time.desc(),
        Rumor.create_time.desc(),
        Rumor.rumor_id.desc(),
    )

    if page is None or page_size is None:
        return ordered_query.all()

    safe_page = max(1, int(page))
    safe_page_size = max(1, min(int(page_size), 100))
    total = ordered_query.order_by(None).count()
    items = (
        ordered_query
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


def get_rumor_by_id(db: Session, rumor_id: int) -> Rumor | None:
    return db.query(Rumor).filter(Rumor.rumor_id == rumor_id).first()


def get_public_rumor_by_id(db: Session, rumor_id: int) -> Rumor | None:
    return (
        db.query(Rumor)
        .filter(
            Rumor.rumor_id == rumor_id,
            Rumor.source_type == "system",
            Rumor.status == "pass",
        )
        .first()
    )


def list_public_rumors(
    db: Session,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 12,
):
    return list_rumors(
        db,
        search=search,
        source_type="system",
        status="pass",
        page=page,
        page_size=page_size,
    )


def find_related_rumors(
    db: Session,
    *,
    text: str,
    limit: int = 5,
) -> list[dict]:
    normalized_text = _clean_text(text)
    if not normalized_text:
        return []

    source_features = build_rumor_merge_features(normalized_text)
    candidates = (
        db.query(Rumor)
        .filter(
            Rumor.source_type == "system",
            Rumor.status == "pass",
            Rumor.label == 1,
        )
        .all()
    )

    scored_candidates: list[tuple[float, Rumor, str]] = []
    for rumor in candidates:
        candidate_text = rumor.claim_text or rumor.content or rumor.title
        if not candidate_text:
            continue

        candidate_features = build_rumor_merge_features(candidate_text)
        comparison = compare_rumor_features(source_features, candidate_features)
        base_score = comparison.sequence_ratio * 0.68 + comparison.bigram_jaccard * 0.32

        if source_features.merge_key_hash == candidate_features.merge_key_hash:
            base_score = max(base_score, 0.94)

        if source_features.fact_signature and candidate_features.fact_signature:
            if source_features.fact_signature == candidate_features.fact_signature:
                base_score += 0.05
            elif comparison.hard_fact_conflict:
                base_score *= 0.72

        match_score = round(min(max(base_score, 0.0), 1.0), 4)
        if source_features.normalized_text == candidate_features.normalized_text:
            match_hint = "文本表达高度一致"
        elif source_features.merge_key_hash == candidate_features.merge_key_hash:
            match_hint = "核心断言接近，命中同一主谣言表达"
        elif comparison.hard_fact_conflict:
            match_hint = "语义接近，但存在部分硬事实差异"
        else:
            match_hint = "作为占位候选返回，供进一步核查"

        scored_candidates.append((match_score, rumor, match_hint))

    scored_candidates.sort(
        key=lambda item: (
            item[0],
            item[1].publish_time or item[1].create_time,
            item[1].rumor_id,
        ),
        reverse=True,
    )

    results = []
    for match_score, rumor, match_hint in scored_candidates[: max(1, limit)]:
        payload = serialize_rumor(rumor)
        payload["match_score"] = match_score
        payload["match_hint"] = match_hint
        results.append(payload)
    return results


def _validate_rumor_payload(db: Session, *, rumor_id: int | None = None, payload: dict) -> tuple[dict, str | None]:
    normalized_payload = dict(payload)

    normalized_payload["title"] = _clean_text(normalized_payload.get("title"))
    normalized_payload["claim_text"] = _clean_text(normalized_payload.get("claim_text"))
    normalized_payload["truth_text"] = _clean_text(normalized_payload.get("truth_text"))
    normalized_payload["raw_content"] = _clean_text(normalized_payload.get("raw_content"))
    normalized_payload["source_name"] = _clean_text(normalized_payload.get("source_name"))
    normalized_payload["article_id"] = _clean_text(normalized_payload.get("article_id"))
    normalized_payload["article_url"] = _clean_text(
        normalized_payload.get("article_url") or normalized_payload.get("refute_link")
    )

    if "publish_time" in normalized_payload:
        try:
            normalized_payload["publish_time"] = _parse_datetime_input(normalized_payload.get("publish_time"))
        except ValueError as exc:
            return normalized_payload, str(exc)

    source_type = normalized_payload.get("source_type") or "system"
    if source_type not in VALID_SOURCE_TYPES:
        return normalized_payload, "来源类型仅支持 system 或 user"
    normalized_payload["source_type"] = source_type

    status = normalized_payload.get("status") or ("pass" if source_type == "system" else "not_pass")
    if status not in VALID_STATUSES:
        return normalized_payload, "审核状态仅支持 pass 或 not_pass"
    normalized_payload["status"] = status

    label = normalized_payload.get("label", 1)
    try:
        label = int(label)
    except (TypeError, ValueError):
        return normalized_payload, "标签仅支持 0 或 1"
    if label not in VALID_LABELS:
        return normalized_payload, "标签仅支持 0 或 1"
    normalized_payload["label"] = label

    content = _derive_primary_content(
        title=normalized_payload.get("title"),
        claim_text=normalized_payload.get("claim_text"),
        raw_content=normalized_payload.get("raw_content"),
    )
    if not content:
        return normalized_payload, "至少需要提供标题、核心断言或正文中的一项"
    normalized_payload["content"] = content

    article_id = normalized_payload.get("article_id")
    if article_id:
        query = db.query(Rumor).filter(Rumor.article_id == article_id)
        if rumor_id is not None:
            query = query.filter(Rumor.rumor_id != rumor_id)
        if query.first():
            return normalized_payload, "该 article_id 已存在"

    article_url = normalized_payload.get("article_url")
    if article_url:
        query = db.query(Rumor).filter(
            or_(
                Rumor.article_url == article_url,
                Rumor.refute_link == article_url,
            )
        )
        if rumor_id is not None:
            query = query.filter(Rumor.rumor_id != rumor_id)
        if query.first():
            return normalized_payload, "该文章链接已存在"

    return normalized_payload, None


def create_rumor_by_admin(db: Session, payload: dict):
    normalized_payload, error = _validate_rumor_payload(db, payload=payload)
    if error:
        return None, error

    rumor = Rumor(
        title=normalized_payload["title"],
        content=normalized_payload["content"],
        claim_text=normalized_payload["claim_text"],
        truth_text=normalized_payload["truth_text"],
        raw_content=normalized_payload["raw_content"],
        source_name=normalized_payload["source_name"],
        article_id=normalized_payload["article_id"],
        article_url=normalized_payload["article_url"],
        publish_time=normalized_payload.get("publish_time"),
        label=normalized_payload["label"],
        status=normalized_payload["status"],
        source_type=normalized_payload["source_type"],
        upload_user_id=None,
        refute_link=normalized_payload["article_url"],
    )
    _apply_merge_features(rumor, rumor.content)

    try:
        db.add(rumor)
        db.commit()
        db.refresh(rumor)
        return rumor, None
    except Exception as exc:
        db.rollback()
        logger.error(f"管理员创建谣言失败: {exc}", exc_info=True)
        return None, "创建谣言失败，请稍后重试"


def update_rumor_by_admin(db: Session, *, rumor_id: int, payload: dict):
    rumor = get_rumor_by_id(db, rumor_id)
    if rumor is None:
        return None, "谣言不存在"

    merged_payload = {
        "title": rumor.title,
        "content": rumor.content,
        "claim_text": rumor.claim_text,
        "truth_text": rumor.truth_text,
        "raw_content": rumor.raw_content,
        "source_name": rumor.source_name,
        "article_id": rumor.article_id,
        "article_url": rumor.article_url,
        "publish_time": rumor.publish_time,
        "label": rumor.label,
        "status": rumor.status,
        "source_type": rumor.source_type,
        **payload,
    }

    normalized_payload, error = _validate_rumor_payload(db, rumor_id=rumor_id, payload=merged_payload)
    if error:
        return None, error

    for field in (
        "title",
        "content",
        "claim_text",
        "truth_text",
        "raw_content",
        "source_name",
        "article_id",
        "article_url",
        "publish_time",
        "label",
        "status",
        "source_type",
    ):
        setattr(rumor, field, normalized_payload.get(field))

    rumor.refute_link = normalized_payload.get("article_url")
    _apply_merge_features(rumor, rumor.content)

    try:
        db.commit()
        db.refresh(rumor)
        return rumor, None
    except Exception as exc:
        db.rollback()
        logger.error(f"管理员更新谣言失败: {exc}", exc_info=True)
        return None, "更新谣言失败，请稍后重试"


def delete_rumors_by_admin(db: Session, *, rumor_ids: list[int]):
    target_ids = sorted({int(rumor_id) for rumor_id in rumor_ids if rumor_id is not None})
    if not target_ids:
        return 0, "请选择需要删除的谣言"

    targets = db.query(Rumor).filter(Rumor.rumor_id.in_(target_ids)).all()
    found_ids = {rumor.rumor_id for rumor in targets}
    missing_ids = [str(rumor_id) for rumor_id in target_ids if rumor_id not in found_ids]
    if missing_ids:
        return 0, f"以下谣言不存在：{', '.join(missing_ids)}"

    try:
        deleted_count = len(targets)
        for rumor in targets:
            db.delete(rumor)
        db.commit()
        return deleted_count, None
    except Exception as exc:
        db.rollback()
        logger.error(f"管理员删除谣言失败: {exc}", exc_info=True)
        return 0, "删除谣言失败，请稍后重试"


def _upsert_imported_rumor(db: Session, *, existing_rumor: Rumor | None, record: dict) -> tuple[Rumor, str]:
    title = _clean_imported_text(record.get("title"))
    claim_text = _clean_imported_text(record.get("claim_text"))
    truth_text = _clean_imported_text(record.get("truth_text"))
    raw_content = _clean_imported_text(record.get("content"))
    source_name = _clean_imported_text(record.get("source_name") or record.get("site_name"))
    raw_article_url = _normalize_article_url(record.get("url"), record.get("snapshot_url"), record.get("article_url"))
    article_url = _fit_url_for_storage(raw_article_url, max_length=500)
    refute_link = _fit_url_for_storage(raw_article_url, max_length=300)
    article_id = _normalize_article_id(record.get("article_id"), fallback_url=article_url or raw_article_url)
    publish_time = _parse_datetime_input(record.get("publish_time"))
    primary_content = _derive_primary_content(
        title=title,
        claim_text=claim_text,
        raw_content=raw_content,
    )
    if not primary_content:
        raise ValueError("缺少可用的主谣言文本")

    rumor = existing_rumor or Rumor(
        label=1,
        status="pass",
        source_type="system",
        upload_user_id=None,
        upload_count=0,
    )
    rumor.title = title
    rumor.content = primary_content
    rumor.claim_text = claim_text
    rumor.truth_text = truth_text
    rumor.raw_content = raw_content
    rumor.source_name = source_name
    rumor.article_id = article_id
    rumor.article_url = article_url
    rumor.publish_time = publish_time
    rumor.label = 1
    rumor.status = "pass"
    rumor.source_type = "system"
    rumor.refute_link = refute_link

    _apply_merge_features(rumor, rumor.content)

    if existing_rumor is None:
        db.add(rumor)
        return rumor, "created"
    return rumor, "updated"


def import_rumors_from_jsonl_file(db: Session, *, file_path: str | None = None):
    target_path = Path(file_path).expanduser() if file_path else DEFAULT_PIYAO_JSONL_PATH
    if not target_path.is_absolute():
        target_path = (PROJECT_ROOT / target_path).resolve()

    if not target_path.exists():
        return None, f"未找到待导入文件: {target_path}"

    existing_rumors = db.query(Rumor).all()
    rumors_by_article_id = {rumor.article_id: rumor for rumor in existing_rumors if rumor.article_id}
    rumors_by_article_url = {rumor.article_url: rumor for rumor in existing_rumors if rumor.article_url}

    summary = {
        "file_path": target_path.as_posix(),
        "total_rows": 0,
        "created": 0,
        "updated": 0,
        "failed": 0,
        "errors": [],
    }

    try:
        with target_path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue

                summary["total_rows"] += 1
                try:
                    record = json.loads(line)
                    article_url = _fit_url_for_storage(
                        _normalize_article_url(
                            record.get("url"),
                            record.get("snapshot_url"),
                            record.get("article_url"),
                        ),
                        max_length=500,
                    )
                    article_id = _normalize_article_id(record.get("article_id"), fallback_url=article_url)
                    existing_rumor = None
                    if article_id:
                        existing_rumor = rumors_by_article_id.get(article_id)
                    if existing_rumor is None and article_url:
                        existing_rumor = rumors_by_article_url.get(article_url)

                    rumor, action = _upsert_imported_rumor(
                        db,
                        existing_rumor=existing_rumor,
                        record=record,
                    )
                    if rumor.article_id:
                        rumors_by_article_id[rumor.article_id] = rumor
                    if rumor.article_url:
                        rumors_by_article_url[rumor.article_url] = rumor
                    summary[action] += 1
                except Exception as exc:
                    summary["failed"] += 1
                    if len(summary["errors"]) < 20:
                        summary["errors"].append(f"第 {line_number} 行导入失败: {exc}")

        db.commit()
        logger.business(
            "平台谣言数据导入完成 => "
            f"file={target_path}, total={summary['total_rows']}, created={summary['created']}, "
            f"updated={summary['updated']}, failed={summary['failed']}"
        )
        return summary, None
    except Exception as exc:
        db.rollback()
        logger.error(f"平台谣言数据导入失败: {exc}", exc_info=True)
        return None, "平台谣言数据导入失败，请稍后重试"


def import_rumors_from_piyao_file(db: Session, *, file_path: str | None = None):
    return import_rumors_from_jsonl_file(db, file_path=file_path or str(DEFAULT_PIYAO_JSONL_PATH))


def import_rumors_from_nhc_file(db: Session, *, file_path: str | None = None):
    return import_rumors_from_jsonl_file(db, file_path=file_path or str(DEFAULT_NHC_JSONL_PATH))
