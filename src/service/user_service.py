from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from modules.tools.logger import logger
from src.models._init_database import Rumor, User, UserUploadRumor
from src.utils.security import get_password_hash, needs_password_upgrade, verify_password
from src.utils.rumor_merge import (
    RumorMergeFeatures,
    build_rumor_merge_features,
    should_auto_merge,
    should_mark_pending,
)

DIRECT_OFFICIAL_MATCH_THRESHOLD = 0.56
PENDING_OFFICIAL_MATCH_THRESHOLD = 0.32


def serialize_user(user: User) -> dict:
    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "avatar": user.avatar,
        "role": user.role,
        "gender": user.gender,
        "province": user.province,
        "city": user.city,
        "birthday": user.birthday.isoformat() if user.birthday else None,
        "status": user.status,
        "create_time": user.create_time.isoformat() if user.create_time else None,
        "update_time": user.update_time.isoformat() if user.update_time else None,
    }


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.user_id == user_id).first()


def _password_matches(db: Session, db_user: User, plain_password: str) -> bool:
    if verify_password(plain_password, db_user.password):
        if needs_password_upgrade(db_user.password):
            db_user.password = get_password_hash(plain_password)
            db.commit()
            db.refresh(db_user)
        return True

    # 兼容历史明文密码账号，并在首次成功登录后自动升级为哈希密码。
    if db_user.password == plain_password:
        db_user.password = get_password_hash(plain_password)
        db.commit()
        db.refresh(db_user)
        return True

    return False


def login(db: Session, account: str, password: str):
    logger.request(f"收到登录请求=>用户：{account}")

    db_user = db.query(User).filter(
        or_(
            User.username == account,
            User.email == account,
            User.phone == account,
        )
    ).first()

    if not db_user:
        logger.request(f"用户：{account} 登录失败！用户不存在或账号未注册")
        return False, "用户不存在或账号未注册"

    if not _password_matches(db, db_user, password):
        logger.request(f"用户：{account} 登录失败！该账号密码错误")
        return False, "密码错误"

    if db_user.status == "禁用":
        logger.request(f"用户：{account} 登录失败！该账号已被禁用")
        return False, "该账号已被禁用，请联系管理员"
    if db_user.status == "未激活":
        logger.request(f"用户：{account} 登录失败！该账号未激活")
        return False, "该账号未激活"

    logger.request(f"用户：{account} 登录成功！")
    return True, db_user


def create_user(db: Session, user_data: dict):
    logger.request(f"{user_data['phone']} 意图创建用户")

    if db.query(User).filter(User.username == user_data["username"]).first():
        logger.request(f"{user_data['phone']} 创建用户失败！因为用户名已存在")
        return None, "用户名已存在"
    if db.query(User).filter(User.email == user_data["email"]).first():
        logger.request(f"{user_data['phone']} 创建用户失败！因为邮箱已被注册")
        return None, "邮箱已被注册"
    if db.query(User).filter(User.phone == user_data["phone"]).first():
        logger.request(f"{user_data['phone']} 创建用户失败！因为手机号已被注册")
        return None, "手机号已被注册"

    user_data["password"] = get_password_hash(user_data["password"])

    admin_exists = db.query(User.user_id).filter(User.role == "admin").first() is not None
    user_data.setdefault("role", "user")
    user_data.setdefault("status", "正常")

    if not admin_exists:
        user_data["role"] = "admin"

    new_user = User(**user_data)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.business(
        f"创建用户成功 => user_id={new_user.user_id}, role={new_user.role}, username={new_user.username}"
    )
    return new_user, None


def update_user_profile(db: Session, user: User, update_data: dict):
    mutable_fields = ["avatar", "gender", "province", "city", "birthday", "phone", "email"]

    if "email" in update_data and update_data["email"] != user.email:
        existing_email = db.query(User).filter(User.email == update_data["email"]).first()
        if existing_email and existing_email.user_id != user.user_id:
            return None, "邮箱已被注册"

    if "phone" in update_data and update_data["phone"] != user.phone:
        existing_phone = db.query(User).filter(User.phone == update_data["phone"]).first()
        if existing_phone and existing_phone.user_id != user.user_id:
            return None, "手机号已被注册"

    for field in mutable_fields:
        if field in update_data and update_data[field] is not None:
            setattr(user, field, update_data[field])

    db.commit()
    db.refresh(user)
    return user, None


def list_users(
    db: Session,
    search: str | None = None,
    role: str | None = None,
    status: str | None = None,
    *,
    page: int | None = None,
    page_size: int | None = None,
):
    query = db.query(User)

    if search:
        keyword = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.username.like(keyword),
                User.email.like(keyword),
                User.phone.like(keyword),
            )
        )

    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)

    ordered_query = query.order_by(User.create_time.desc())

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


def update_user_by_admin(
    db: Session,
    *,
    current_user: User,
    target_user_id: int,
    role: str | None = None,
    status: str | None = None,
):
    target_user = get_user_by_id(db, target_user_id)
    if not target_user:
        return None, "用户不存在"

    if role is not None:
        if current_user.user_id == target_user.user_id and role != "admin":
            return None, "不能取消自己的管理员权限"

        if target_user.role == "admin" and role != "admin":
            admin_count = db.query(func.count(User.user_id)).filter(User.role == "admin").scalar() or 0
            if admin_count <= 1:
                return None, "系统至少需要保留一名管理员"

        target_user.role = role

    if status is not None:
        if current_user.user_id == target_user.user_id and status != "正常":
            return None, "不能修改自己的账号状态为不可用"
        target_user.status = status

    db.commit()
    db.refresh(target_user)
    return target_user, None


def delete_users_by_admin(db: Session, *, current_user: User, user_ids: list[int]):
    target_ids = sorted({int(user_id) for user_id in user_ids if user_id is not None})
    if not target_ids:
        return 0, "请选择需要删除的用户"

    if current_user.user_id in target_ids:
        return 0, "不能删除当前登录的管理员账号"

    targets = db.query(User).filter(User.user_id.in_(target_ids)).all()
    found_ids = {user.user_id for user in targets}
    missing_ids = [str(user_id) for user_id in target_ids if user_id not in found_ids]
    if missing_ids:
        return 0, f"以下用户不存在：{', '.join(missing_ids)}"

    admin_count = db.query(func.count(User.user_id)).filter(User.role == "admin").scalar() or 0
    deleting_admin_count = sum(1 for user in targets if user.role == "admin")
    if admin_count - deleting_admin_count <= 0:
        return 0, "系统至少需要保留一名管理员"

    try:
        deleted_count = len(targets)
        for user in targets:
            db.delete(user)
        db.commit()
        return deleted_count, None
    except Exception as exc:
        db.rollback()
        logger.error(f"管理员批量删除用户失败: {exc}", exc_info=True)
        return 0, "批量删除用户失败，请稍后重试"


def get_admin_overview(db: Session) -> dict:
    total_users = db.query(func.count(User.user_id)).scalar() or 0
    admin_users = db.query(func.count(User.user_id)).filter(User.role == "admin").scalar() or 0
    active_users = db.query(func.count(User.user_id)).filter(User.status == "正常").scalar() or 0
    disabled_users = db.query(func.count(User.user_id)).filter(User.status == "禁用").scalar() or 0
    pending_users = db.query(func.count(User.user_id)).filter(User.status == "未激活").scalar() or 0

    rumor_total = 0
    approved_rumors = 0
    pending_rumors = 0
    system_rumors = 0
    user_rumors = 0
    rumor_ratio = {"rumor": 0, "normal": 0}

    try:
        rumor_total = db.query(func.count(Rumor.rumor_id)).scalar() or 0
        approved_rumors = (
            db.query(func.count(Rumor.rumor_id)).filter(Rumor.status == "pass").scalar() or 0
        )
        pending_rumors = (
            db.query(func.count(Rumor.rumor_id)).filter(Rumor.status == "not_pass").scalar() or 0
        )
        system_rumors = (
            db.query(func.count(Rumor.rumor_id)).filter(Rumor.source_type == "system").scalar() or 0
        )
        user_rumors = (
            db.query(func.count(Rumor.rumor_id)).filter(Rumor.source_type == "user").scalar() or 0
        )

        rumor_ratio["rumor"] = db.query(func.count(Rumor.rumor_id)).filter(Rumor.label == 1).scalar() or 0
        rumor_ratio["normal"] = db.query(func.count(Rumor.rumor_id)).filter(Rumor.label == 0).scalar() or 0
    except Exception as exc:
        logger.error(f"统计谣言数据失败: {exc}")

    latest_users = [
        serialize_user(user)
        for user in db.query(User).order_by(User.create_time.desc()).limit(6).all()
    ]

    upload_review_total = db.query(func.count(UserUploadRumor.upload_id)).scalar() or 0
    upload_review_pending = (
        db.query(func.count(UserUploadRumor.upload_id))
        .filter(UserUploadRumor.status == "待合并")
        .scalar()
        or 0
    )
    upload_review_merged = (
        db.query(func.count(UserUploadRumor.upload_id))
        .filter(UserUploadRumor.status == "已合并")
        .scalar()
        or 0
    )
    upload_review_invalid = (
        db.query(func.count(UserUploadRumor.upload_id))
        .filter(UserUploadRumor.status == "无效")
        .scalar()
        or 0
    )
    upload_review_high_risk_pending = (
        db.query(func.count(UserUploadRumor.upload_id))
        .filter(
            UserUploadRumor.status == "待合并",
            UserUploadRumor.result_risk_level == "high",
        )
        .scalar()
        or 0
    )

    return {
        "user_stats": {
            "total": total_users,
            "admin": admin_users,
            "active": active_users,
            "disabled": disabled_users,
            "pending": pending_users,
        },
        "rumor_stats": {
            "total": rumor_total,
            "approved": approved_rumors,
            "pending": pending_rumors,
            "system": system_rumors,
            "user": user_rumors,
            "ratio": rumor_ratio,
        },
        "upload_review_stats": {
            "total": upload_review_total,
            "pending": upload_review_pending,
            "merged": upload_review_merged,
            "invalid": upload_review_invalid,
            "high_risk_pending": upload_review_high_risk_pending,
        },
        "latest_users": latest_users,
    }


def get_bootstrap_status(db: Session) -> dict:
    user_count = db.query(func.count(User.user_id)).scalar() or 0
    admin_exists = db.query(User.user_id).filter(User.role == "admin").first() is not None
    return {"user_count": user_count, "admin_exists": admin_exists}


def _build_prediction_summary(rumor_probability: float | None, predicted_label: int | None = None) -> dict:
    if rumor_probability is None:
        rumor_probability = 1.0 if predicted_label == 1 else 0.0

    rumor_probability = max(0.0, min(float(rumor_probability), 1.0))
    credible_probability = 1 - rumor_probability

    if rumor_probability >= 0.75:
        risk_level = "high"
        verdict = "高度疑似谣言"
    elif rumor_probability >= 0.45:
        risk_level = "medium"
        verdict = "存在较高风险，建议继续核查"
    else:
        risk_level = "low"
        verdict = "当前更接近真实或中性信息"

    return {
        "verdict": verdict,
        "risk_level": risk_level,
        "rumor_probability": rumor_probability,
        "credible_probability": credible_probability,
        "label": "rumor" if rumor_probability >= 0.5 else "normal",
    }


def _normalize_rumor_text(text: str) -> str:
    return " ".join(text.split()).strip()


def _strip_unsupported_db_chars(value: str | None) -> str | None:
    if value is None:
        return None
    return "".join(char for char in str(value) if ord(char) <= 0xFFFF)


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _truncate_text(value: str | None, limit: int = 320) -> str | None:
    normalized = _strip_unsupported_db_chars(value)
    if not normalized:
        return None
    normalized = " ".join(normalized.split()).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(1, limit - 1)].rstrip() + "…"


def _compact_related_candidate(item: dict) -> dict | None:
    title = _truncate_text(item.get("title") or item.get("content"), 180)
    content = _truncate_text(item.get("content"), 220)
    truth_text = _truncate_text(item.get("truth_text"), 240)
    if not any((title, content, truth_text)):
        return None

    payload = {
        "rumor_id": item.get("rumor_id"),
        "event_id": item.get("event_id"),
        "title": title,
        "content": content,
        "truth_text": truth_text,
        "source_name": _truncate_text(item.get("source_name"), 80),
        "publish_time": _truncate_text(item.get("publish_time"), 40),
        "article_url": _truncate_text(item.get("article_url"), 300),
        "match_score": round(_safe_float(item.get("match_score")), 6),
        "pair_score": round(_safe_float(item.get("pair_score")), 6),
        "lexical_score": round(_safe_float(item.get("lexical_score")), 6),
        "match_hint": _truncate_text(item.get("match_hint"), 120),
        "candidate_source": _truncate_text(item.get("candidate_source"), 32),
        "matched_text": _truncate_text(item.get("matched_text"), 200),
        "matched_view": _truncate_text(item.get("matched_view"), 32),
        "coherence_score": round(_safe_float(item.get("coherence_score")), 6),
    }
    return {key: value for key, value in payload.items() if value not in (None, "", [])}


def _compact_related_rumors(prediction_result: dict, *, limit: int = 5) -> list[dict]:
    compacted: list[dict] = []
    seen: set[tuple[str | None, str | None, str | None]] = set()

    for item in prediction_result.get("related_rumors", [])[: max(1, limit)]:
        compacted_item = _compact_related_candidate(item)
        if compacted_item is None:
            continue
        signature = (
            compacted_item.get("event_id"),
            str(compacted_item.get("rumor_id")) if compacted_item.get("rumor_id") is not None else None,
            compacted_item.get("title") or compacted_item.get("content"),
        )
        if signature in seen:
            continue
        seen.add(signature)
        compacted.append(compacted_item)

    return compacted


def _find_rumor_by_id(db: Session, rumor_id: int | None) -> Rumor | None:
    if rumor_id is None:
        return None
    return db.query(Rumor).filter(Rumor.rumor_id == rumor_id).first()


def _pick_top_official_candidate(db: Session, related_rumors: list[dict]) -> tuple[Rumor | None, dict | None]:
    for candidate in related_rumors:
        rumor_id = candidate.get("rumor_id")
        if rumor_id is None:
            continue
        rumor = _find_rumor_by_id(db, int(rumor_id))
        if rumor is not None:
            return rumor, candidate
    return None, None


def _build_prediction_storage_plan(
    db: Session,
    *,
    features: RumorMergeFeatures,
    prediction_result: dict,
    predicted_label: int,
    related_rumors: list[dict],
) -> dict:
    rumor_probability = _safe_float(prediction_result.get("rumor_probability"))
    official_rumor, official_candidate = _pick_top_official_candidate(db, related_rumors)
    official_match_score = _safe_float(official_candidate.get("match_score")) if official_candidate else 0.0

    if official_rumor is not None:
        if official_match_score >= DIRECT_OFFICIAL_MATCH_THRESHOLD or (
            rumor_probability >= 0.82 and official_match_score >= 0.42
        ):
            return {
                "action": "merge",
                "candidate": official_rumor,
                "confidence": max(official_match_score, rumor_probability),
                "reason": "命中平台主谣言候选，已直接绑定到官方主谣言",
                "strategy": "official_match",
            }

        if official_match_score >= PENDING_OFFICIAL_MATCH_THRESHOLD or (
            rumor_probability >= 0.58 and official_match_score >= 0.22
        ):
            return {
                "action": "pending",
                "candidate": official_rumor,
                "confidence": max(official_match_score, rumor_probability * 0.9),
                "reason": "存在较接近的官方主谣言候选，保留为待复核记录",
                "strategy": "official_candidate",
            }

    if predicted_label == 1:
        legacy_target = _find_merge_target(db, features, predicted_label)
        if legacy_target["action"] in {"merge", "pending"} and legacy_target["candidate"] is not None:
            return legacy_target

    unmatched_status = "待合并" if rumor_probability >= 0.45 else "无效"
    unmatched_reason = "未匹配到已知主谣言，建议人工复核" if rumor_probability >= 0.45 else "未匹配到已知主谣言，作为普通查询历史保留"
    return {
        "action": "unmatched",
        "candidate": None,
        "confidence": rumor_probability,
        "reason": unmatched_reason,
        "strategy": "history_only",
        "status": unmatched_status,
    }


def _load_related_rumors_snapshot(raw_json: str | None) -> list[dict]:
    if not raw_json:
        return []
    try:
        payload = json.loads(raw_json)
    except (TypeError, ValueError):
        return []
    return payload if isinstance(payload, list) else []


def _apply_merge_features_to_rumor(rumor: Rumor, features: RumorMergeFeatures) -> None:
    rumor.normalized_content = features.normalized_text
    rumor.merge_key_hash = features.merge_key_hash
    rumor.fact_signature = features.fact_signature


def _hydrate_rumor_merge_features(rumor: Rumor) -> RumorMergeFeatures:
    features = build_rumor_merge_features(rumor.content)
    if (
        rumor.normalized_content != features.normalized_text
        or rumor.merge_key_hash != features.merge_key_hash
        or rumor.fact_signature != features.fact_signature
    ):
        _apply_merge_features_to_rumor(rumor, features)
    return features


def _build_upload_record(
    *,
    user: User,
    raw_text: str,
    features: RumorMergeFeatures,
    prediction_result: dict,
    upload_time: datetime,
    merged_rumor_id: int | None,
    status: str,
    merge_strategy: str,
    merge_confidence: float,
    merge_reason: str,
    candidate_rumor_id: int | None = None,
    base_model_probability: float | None = None,
    event_match_probability: float | None = None,
    result_risk_level: str | None = None,
    result_verdict: str | None = None,
    related_rumors_json: str | None = None,
):
    return UserUploadRumor(
        user_id=user.user_id,
        upload_content=raw_text,
        normalized_content=features.normalized_text,
        merge_key_hash=features.merge_key_hash,
        fact_signature=features.fact_signature,
        merged_rumor_id=merged_rumor_id,
        candidate_rumor_id=candidate_rumor_id,
        upload_time=upload_time,
        predicted_label=1 if prediction_result.get("label") == "rumor" else 0,
        rumor_probability=prediction_result.get("rumor_probability"),
        base_model_probability=base_model_probability,
        event_match_probability=event_match_probability,
        result_risk_level=_truncate_text(result_risk_level, 16),
        result_verdict=_truncate_text(result_verdict, 120),
        related_rumors_json=related_rumors_json,
        status=status,
        merge_strategy=merge_strategy,
        merge_confidence=merge_confidence,
        merge_reason=merge_reason[:255] if merge_reason else None,
    )


def _find_merge_target(db: Session, features: RumorMergeFeatures, predicted_label: int):
    checked_ids: set[int] = set()
    pending_candidate: tuple[Rumor, float, str] | None = None

    exact_candidates = (
        db.query(Rumor)
        .filter(Rumor.merge_key_hash == features.merge_key_hash)
        .order_by(Rumor.latest_upload_time.desc(), Rumor.create_time.desc())
        .all()
    )

    for candidate in exact_candidates:
        checked_ids.add(candidate.rumor_id)
        candidate_features = _hydrate_rumor_merge_features(candidate)
        should_merge, confidence, reason = should_auto_merge(features, candidate_features)
        if should_merge:
            return {
                "action": "merge",
                "candidate": candidate,
                "confidence": confidence,
                "reason": reason,
                "strategy": "exact" if features.normalized_text == candidate_features.normalized_text else "merge_key",
            }

        should_pending, pending_confidence, pending_reason = should_mark_pending(features, candidate_features)
        if should_pending and (
            pending_candidate is None or pending_confidence > pending_candidate[1]
        ):
            pending_candidate = (candidate, pending_confidence, pending_reason)

    candidate_query = db.query(Rumor).filter(Rumor.label == predicted_label)
    if features.fact_signature:
        candidate_query = candidate_query.filter(Rumor.fact_signature == features.fact_signature)

    similar_candidates = (
        candidate_query
        .order_by(Rumor.latest_upload_time.desc(), Rumor.create_time.desc())
        .limit(80)
        .all()
    )

    for candidate in similar_candidates:
        if candidate.rumor_id in checked_ids:
            continue

        candidate_features = _hydrate_rumor_merge_features(candidate)
        should_merge, confidence, reason = should_auto_merge(features, candidate_features)
        if should_merge:
            return {
                "action": "merge",
                "candidate": candidate,
                "confidence": confidence,
                "reason": reason,
                "strategy": "similarity",
            }

        should_pending, pending_confidence, pending_reason = should_mark_pending(features, candidate_features)
        if should_pending and (
            pending_candidate is None or pending_confidence > pending_candidate[1]
        ):
            pending_candidate = (candidate, pending_confidence, pending_reason)

    if pending_candidate is not None:
        candidate, confidence, reason = pending_candidate
        return {
            "action": "pending",
            "candidate": candidate,
            "confidence": confidence,
            "reason": reason,
            "strategy": "pending_review",
        }

    return {
        "action": "new",
        "candidate": None,
        "confidence": 1.0,
        "reason": "未找到满足自动归并条件的主谣言，创建新主记录",
        "strategy": "new_rumor",
    }


def _serialize_upload_history_record(upload: UserUploadRumor) -> dict:
    prediction_summary = _build_prediction_summary(upload.rumor_probability, upload.predicted_label)
    related_rumors = _load_related_rumors_snapshot(upload.related_rumors_json)
    return {
        "id": upload.upload_id,
        "upload_id": upload.upload_id,
        "text": upload.upload_content,
        "createdAt": upload.upload_time.isoformat() if upload.upload_time else None,
        "label": prediction_summary["label"],
        "verdict": upload.result_verdict or prediction_summary["verdict"],
        "risk_level": upload.result_risk_level or prediction_summary["risk_level"],
        "rumor_probability": prediction_summary["rumor_probability"],
        "credible_probability": prediction_summary["credible_probability"],
        "base_model_probability": upload.base_model_probability,
        "event_match_probability": upload.event_match_probability,
        "predicted_label": upload.predicted_label,
        "upload_status": upload.status,
        "merge_strategy": upload.merge_strategy,
        "merge_confidence": upload.merge_confidence,
        "merge_reason": upload.merge_reason,
        "merged_rumor_id": upload.merged_rumor_id,
        "candidate_rumor_id": upload.candidate_rumor_id,
        "related_rumors": related_rumors,
    }


def _serialize_rumor_brief(rumor: Rumor | None) -> dict | None:
    if rumor is None:
        return None
    return {
        "rumor_id": rumor.rumor_id,
        "title": rumor.title or rumor.content,
        "content": rumor.content,
        "truth_text": rumor.truth_text,
        "source_name": rumor.source_name,
        "publish_time": rumor.publish_time.isoformat(sep=" ") if rumor.publish_time else None,
        "status": rumor.status,
        "source_type": rumor.source_type,
    }


def _resolve_review_target_rumor_id(upload: UserUploadRumor) -> int | None:
    if upload.candidate_rumor_id is not None:
        return int(upload.candidate_rumor_id)

    for item in _load_related_rumors_snapshot(upload.related_rumors_json):
        rumor_id = item.get("rumor_id")
        if rumor_id is not None:
            return int(rumor_id)

    if upload.merged_rumor_id is not None:
        return int(upload.merged_rumor_id)

    return None


def _serialize_admin_upload_review_record(
    upload: UserUploadRumor,
    *,
    username: str | None = None,
    email: str | None = None,
    rumor_map: dict[int, Rumor] | None = None,
) -> dict:
    payload = _serialize_upload_history_record(upload)
    rumor_map = rumor_map or {}

    merged_rumor = rumor_map.get(upload.merged_rumor_id) if upload.merged_rumor_id else None
    candidate_rumor = rumor_map.get(upload.candidate_rumor_id) if upload.candidate_rumor_id else None

    payload.update(
        {
            "user_id": upload.user_id,
            "username": username,
            "email": email,
            "merged_rumor": _serialize_rumor_brief(merged_rumor),
            "candidate_rumor": _serialize_rumor_brief(candidate_rumor),
            "review_target_rumor_id": _resolve_review_target_rumor_id(upload),
        }
    )
    return payload


def _refresh_rumor_upload_stats(db: Session, rumor_ids: set[int]) -> None:
    for rumor_id in rumor_ids:
        rumor = db.query(Rumor).filter(Rumor.rumor_id == rumor_id).first()
        if rumor is None:
            continue

        upload_count, latest_upload_time = (
            db.query(
                func.count(UserUploadRumor.upload_id),
                func.max(UserUploadRumor.upload_time),
            )
            .filter(UserUploadRumor.merged_rumor_id == rumor_id)
            .one()
        )

        rumor.upload_count = int(upload_count or 0)
        rumor.latest_upload_time = latest_upload_time


def save_user_prediction_record(
    db: Session,
    *,
    user: User,
    raw_text: str,
    prediction_result: dict,
):
    raw_text_for_storage = _strip_unsupported_db_chars(raw_text or "") or ""
    normalized_text = _normalize_rumor_text(raw_text_for_storage)
    if not normalized_text:
        return None, "待识别文本不能为空"

    predicted_label = 1 if prediction_result.get("label") == "rumor" else 0
    merge_features = build_rumor_merge_features(normalized_text)
    upload_time = datetime.now()
    related_rumors = _compact_related_rumors(prediction_result)
    related_rumors_json = json.dumps(related_rumors, ensure_ascii=False) if related_rumors else None
    base_model_probability = _safe_float(prediction_result.get("base_model_probability"), None)
    event_match_probability = _safe_float(prediction_result.get("event_match_probability"), None)
    result_risk_level = _truncate_text(prediction_result.get("risk_level"), 16)
    result_verdict = _truncate_text(prediction_result.get("verdict"), 120)

    try:
        merge_target = _build_prediction_storage_plan(
            db,
            features=merge_features,
            prediction_result=prediction_result,
            predicted_label=predicted_label,
            related_rumors=related_rumors,
        )
        linked_rumor = merge_target["candidate"]
        merged_rumor_id = linked_rumor.rumor_id if merge_target["action"] == "merge" and linked_rumor else None
        candidate_rumor_id = linked_rumor.rumor_id if merge_target["action"] == "pending" and linked_rumor else None
        upload_status = merge_target.get("status") or ("已合并" if merged_rumor_id else "待合并")

        upload_record = _build_upload_record(
            user=user,
            raw_text=raw_text_for_storage,
            features=merge_features,
            prediction_result=prediction_result,
            upload_time=upload_time,
            merged_rumor_id=merged_rumor_id,
            status=upload_status,
            merge_strategy=merge_target["strategy"],
            merge_confidence=merge_target["confidence"],
            merge_reason=merge_target["reason"],
            candidate_rumor_id=candidate_rumor_id,
            base_model_probability=base_model_probability,
            event_match_probability=event_match_probability,
            result_risk_level=result_risk_level,
            result_verdict=result_verdict,
            related_rumors_json=related_rumors_json,
        )

        db.add(upload_record)
        db.flush()
        impacted_rumor_ids = {merged_rumor_id} if merged_rumor_id else set()
        if impacted_rumor_ids:
            _refresh_rumor_upload_stats(db, impacted_rumor_ids)
        db.commit()
        db.refresh(upload_record)
        if linked_rumor is not None:
            db.refresh(linked_rumor)

        logger.business(
            "识别结果已写入数据库 => "
            f"user_id={user.user_id}, rumor_id={linked_rumor.rumor_id if linked_rumor else 'none'}, "
            f"upload_id={upload_record.upload_id}, action={merge_target['action']}, "
            f"strategy={merge_target['strategy']}"
        )

        return {
            "rumor_id": merged_rumor_id,
            "upload_id": upload_record.upload_id,
            "upload_time": upload_record.upload_time.isoformat() if upload_record.upload_time else None,
            "candidate_rumor_id": upload_record.candidate_rumor_id,
            "created_new_rumor": False,
            "stored_label": linked_rumor.label if linked_rumor and merged_rumor_id else None,
            "rumor_status": linked_rumor.status if linked_rumor and merged_rumor_id else None,
            "upload_status": upload_record.status,
            "merge_strategy": upload_record.merge_strategy,
            "merge_confidence": upload_record.merge_confidence,
            "merge_reason": upload_record.merge_reason,
            "related_rumors": related_rumors,
        }, None
    except Exception as exc:
        db.rollback()
        logger.error(f"识别结果写入数据库失败: {exc}", exc_info=True)
        return None, "识别结果写入数据库失败，请稍后重试"


def list_user_prediction_history(
    db: Session,
    *,
    user: User,
    limit: int = 100,
) -> list[dict]:
    safe_limit = max(1, min(limit, 200))
    records = (
        db.query(UserUploadRumor)
        .filter(UserUploadRumor.user_id == user.user_id)
        .order_by(UserUploadRumor.upload_time.desc(), UserUploadRumor.upload_id.desc())
        .limit(safe_limit)
        .all()
    )
    return [_serialize_upload_history_record(record) for record in records]


def list_admin_upload_reviews(
    db: Session,
    *,
    search: str | None = None,
    status: str | None = "all",
    risk_level: str | None = None,
    page: int = 1,
    page_size: int = 10,
):
    query = (
        db.query(
            UserUploadRumor,
            User.username.label("username"),
            User.email.label("email"),
        )
        .join(User, User.user_id == UserUploadRumor.user_id)
    )

    if search:
        keyword = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.username.like(keyword),
                User.email.like(keyword),
                UserUploadRumor.upload_content.like(keyword),
                UserUploadRumor.merge_reason.like(keyword),
            )
        )

    if status and status != "all":
        query = query.filter(UserUploadRumor.status == status)

    if risk_level and risk_level != "all":
        query = query.filter(UserUploadRumor.result_risk_level == risk_level)

    ordered_query = query.order_by(UserUploadRumor.upload_time.desc(), UserUploadRumor.upload_id.desc())
    safe_page = max(1, int(page))
    safe_page_size = max(1, min(int(page_size), 100))
    total = ordered_query.order_by(None).count()
    rows = (
        ordered_query
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )

    rumor_ids: set[int] = set()
    for upload, *_ in rows:
        if upload.merged_rumor_id is not None:
            rumor_ids.add(int(upload.merged_rumor_id))
        if upload.candidate_rumor_id is not None:
            rumor_ids.add(int(upload.candidate_rumor_id))

    rumor_map: dict[int, Rumor] = {}
    if rumor_ids:
        rumor_map = {
            rumor.rumor_id: rumor
            for rumor in db.query(Rumor).filter(Rumor.rumor_id.in_(rumor_ids)).all()
        }

    items = [
        _serialize_admin_upload_review_record(
            upload,
            username=username,
            email=email,
            rumor_map=rumor_map,
        )
        for upload, username, email in rows
    ]

    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


def review_prediction_record_by_admin(
    db: Session,
    *,
    upload_id: int,
    action: str,
    rumor_id: int | None = None,
    reason: str | None = None,
):
    upload = (
        db.query(UserUploadRumor)
        .filter(UserUploadRumor.upload_id == upload_id)
        .first()
    )
    if upload is None:
        return None, "待复核记录不存在"

    impacted_rumor_ids = {
        rumor_id
        for rumor_id in (upload.merged_rumor_id, upload.candidate_rumor_id)
        if rumor_id is not None
    }

    normalized_reason = _truncate_text(reason, 255)
    review_action = (action or "").strip().lower()

    try:
        if review_action == "merge":
            target_rumor_id = rumor_id or _resolve_review_target_rumor_id(upload)
            if target_rumor_id is None:
                return None, "当前记录没有可用的主谣言候选，请先指定 rumor_id"

            target_rumor = _find_rumor_by_id(db, int(target_rumor_id))
            if target_rumor is None:
                return None, "指定的主谣言不存在"

            upload.merged_rumor_id = target_rumor.rumor_id
            upload.candidate_rumor_id = target_rumor.rumor_id
            upload.status = "已合并"
            upload.merge_strategy = "admin_review"
            upload.merge_confidence = max(
                _safe_float(upload.merge_confidence),
                _safe_float(upload.event_match_probability),
                _safe_float(upload.rumor_probability),
            )
            upload.merge_reason = normalized_reason or f"管理员审核后并入主谣言 #{target_rumor.rumor_id}"
            impacted_rumor_ids.add(target_rumor.rumor_id)
        elif review_action == "invalid":
            upload.merged_rumor_id = None
            upload.status = "无效"
            upload.merge_strategy = "admin_invalid"
            upload.merge_reason = normalized_reason or "管理员审核后标记为无效记录"
        elif review_action == "pending":
            upload.merged_rumor_id = None
            upload.status = "待合并"
            upload.merge_strategy = "admin_pending"
            upload.merge_reason = normalized_reason or "管理员重新退回待复核"
        else:
            return None, "仅支持 merge、invalid 或 pending 三种审核动作"

        db.flush()
        _refresh_rumor_upload_stats(db, impacted_rumor_ids)
        db.commit()
        db.refresh(upload)

        rumor_map: dict[int, Rumor] = {}
        final_rumor_ids = {
            rumor_id
            for rumor_id in (upload.merged_rumor_id, upload.candidate_rumor_id)
            if rumor_id is not None
        }
        if final_rumor_ids:
            rumor_map = {
                rumor.rumor_id: rumor
                for rumor in db.query(Rumor).filter(Rumor.rumor_id.in_(final_rumor_ids)).all()
            }

        user = get_user_by_id(db, upload.user_id)
        return _serialize_admin_upload_review_record(
            upload,
            username=user.username if user else None,
            email=user.email if user else None,
            rumor_map=rumor_map,
        ), None
    except Exception as exc:
        db.rollback()
        logger.error(f"管理员审核待复核记录失败: {exc}", exc_info=True)
        return None, "审核失败，请稍后重试"


def delete_user_prediction_record(
    db: Session,
    *,
    user: User,
    upload_id: int,
):
    record = (
        db.query(UserUploadRumor)
        .filter(
            UserUploadRumor.upload_id == upload_id,
            UserUploadRumor.user_id == user.user_id,
        )
        .first()
    )
    if record is None:
        return False, "记录不存在或无权操作"

    impacted_rumor_ids = {record.merged_rumor_id} if record.merged_rumor_id else set()

    try:
        db.delete(record)
        db.flush()
        _refresh_rumor_upload_stats(db, impacted_rumor_ids)
        db.commit()
        return True, None
    except Exception as exc:
        db.rollback()
        logger.error(f"删除识别历史失败: {exc}", exc_info=True)
        return False, "删除识别历史失败，请稍后重试"


def clear_user_prediction_history(db: Session, *, user: User):
    records = (
        db.query(UserUploadRumor)
        .filter(UserUploadRumor.user_id == user.user_id)
        .all()
    )
    if not records:
        return 0, None

    impacted_rumor_ids = {
        record.merged_rumor_id
        for record in records
        if record.merged_rumor_id is not None
    }

    try:
        deleted_count = len(records)
        for record in records:
            db.delete(record)

        db.flush()
        _refresh_rumor_upload_stats(db, impacted_rumor_ids)
        db.commit()
        return deleted_count, None
    except Exception as exc:
        db.rollback()
        logger.error(f"清空识别历史失败: {exc}", exc_info=True)
        return 0, "清空识别历史失败，请稍后重试"
