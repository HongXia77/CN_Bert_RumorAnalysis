from __future__ import annotations

import json
import re
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from modules.tools.logger import logger
from src.models._init_database import QuickSourceCreator, QuickSourcePlatform


VALID_PLATFORM_TYPES = {"official", "creator"}
VALID_ENTRY_STATUSES = {"active", "inactive"}

SLUG_RE = re.compile(r"[^a-z0-9]+")
GENERIC_URL_RE = re.compile(r"https?://[^\s\"']+")


DEFAULT_PLATFORM_SEED = [
    {
        "name": "中国互联网联合辟谣平台",
        "slug": "piyao-national",
        "platform_type": "official",
        "short_label": "PIYAO",
        "badge_text": "国家级",
        "subtitle": "中央重点辟谣平台",
        "description": "适合核查社会热点、公共事件与网络传言，是当前系统最核心的权威来源之一。",
        "scene_hint": "适合政策、民生、突发事件与社会热点核查",
        "url": "https://www.piyao.org.cn/",
        "theme_token": "blue",
        "sort_order": 10,
        "status": "active",
    },
    {
        "name": "国家卫生健康委健康科普辟谣平台",
        "slug": "nhc-kppypt",
        "platform_type": "official",
        "short_label": "NHC",
        "badge_text": "健康",
        "subtitle": "国家卫健委健康科普平台",
        "description": "适合医疗、保健、养生和生活健康误区核查，可作为健康类文本的优先权威入口。",
        "scene_hint": "适合医学保健、营养养生与健康常识核查",
        "url": "https://www.nhc.gov.cn/kppypt/index.shtml",
        "theme_token": "blue",
        "sort_order": 20,
        "status": "active",
    },
    {
        "name": "湖南省互联网联合辟谣平台",
        "slug": "hn-piyao",
        "platform_type": "official",
        "short_label": "HN",
        "badge_text": "地方",
        "subtitle": "湖南地方辟谣入口",
        "description": "适合观察地方平台如何对区域性民生、灾害和社会热点进行核查与发布。",
        "scene_hint": "适合区域性热点、地方民生和灾害预警核查",
        "url": "https://www.hnpiyao.cn/",
        "theme_token": "blue",
        "sort_order": 30,
        "status": "active",
    },
    {
        "name": "陕西省互联网联合辟谣平台",
        "slug": "sn-piyao",
        "platform_type": "official",
        "short_label": "SN",
        "badge_text": "地方",
        "subtitle": "陕西地方辟谣入口",
        "description": "适合扩充地区类权威机构入口，辅助用户对区域传言与地方消息进行交叉核查。",
        "scene_hint": "适合本地谣言、区域民生与短视频转述核查",
        "url": "https://www.shaanxipiyao.cn/",
        "theme_token": "blue",
        "sort_order": 40,
        "status": "active",
    },
    {
        "name": "哔哩哔哩",
        "slug": "bilibili",
        "platform_type": "creator",
        "short_label": "BILI",
        "badge_text": "创作者平台",
        "subtitle": "长视频 / 专栏",
        "description": "更适合展示系统讲解型创作者账号，后续可以补充更完整的专题拆解型内容入口。",
        "scene_hint": "适合系统讲解、专题拆解与长内容复核",
        "url": "https://www.bilibili.com/",
        "theme_token": "warm",
        "sort_order": 10,
        "status": "active",
    },
    {
        "name": "抖音",
        "slug": "douyin",
        "platform_type": "creator",
        "short_label": "DOUYIN",
        "badge_text": "创作者平台",
        "subtitle": "短视频 / 切片",
        "description": "更适合展示高触达、短内容传播型创作者账号，便于观察短视频场景下的辅助核查入口。",
        "scene_hint": "适合短视频转述、热点切片与快核查",
        "url": "https://www.douyin.com/",
        "theme_token": "warm",
        "sort_order": 20,
        "status": "active",
    },
]

DEFAULT_CREATOR_SEED = [
    {
        "platform_slug": "bilibili",
        "display_name": "示例创作者 Alpha",
        "slug": "creator-alpha",
        "avatar_url": None,
        "follower_text": "98.6 万关注",
        "positioning": "科学拆解向占位信息",
        "description": "用于观察哔哩哔哩创作者卡在双列布局下的标题长度、摘要承载和头像位置。",
        "tags": ["长视频", "专题拆解", "示例资料"],
        "profile_url": "https://example.com/creator/bilibili-alpha",
        "sort_order": 10,
        "status": "active",
    },
    {
        "platform_slug": "bilibili",
        "display_name": "示例创作者 Beta",
        "slug": "creator-beta",
        "avatar_url": None,
        "follower_text": "42.3 万关注",
        "positioning": "公共事件梳理向占位信息",
        "description": "用于观察同类卡片在真实数据接入前的版式密度、标签数量和链接层级。",
        "tags": ["事件时间线", "核查梳理", "示例资料"],
        "profile_url": "https://example.com/creator/bilibili-beta",
        "sort_order": 20,
        "status": "active",
    },
    {
        "platform_slug": "bilibili",
        "display_name": "示例创作者 Gamma",
        "slug": "creator-gamma",
        "avatar_url": None,
        "follower_text": "13.5 万关注",
        "positioning": "生活误区辨析向占位信息",
        "description": "用于观察较短粉丝文本、较长定位文案与默认头像占位组合时的视觉平衡。",
        "tags": ["生活常识", "误区辨析", "示例资料"],
        "profile_url": "https://example.com/creator/bilibili-gamma",
        "sort_order": 30,
        "status": "active",
    },
    {
        "platform_slug": "douyin",
        "display_name": "示例创作者 Delta",
        "slug": "creator-delta",
        "avatar_url": None,
        "follower_text": "210.4 万粉丝",
        "positioning": "短视频快核查向占位信息",
        "description": "用于观察抖音平台创作者卡在更强平台感和短摘要样式下的展示效果。",
        "tags": ["短视频", "快核查", "示例资料"],
        "profile_url": "https://example.com/creator/douyin-delta",
        "sort_order": 10,
        "status": "active",
    },
    {
        "platform_slug": "douyin",
        "display_name": "示例创作者 Epsilon",
        "slug": "creator-epsilon",
        "avatar_url": None,
        "follower_text": "66.8 万粉丝",
        "positioning": "热点跟进向占位信息",
        "description": "用于观察平台卡片切换后的色彩差异，以及不同粉丝规模文本的对齐表现。",
        "tags": ["热点跟进", "直播切片", "示例资料"],
        "profile_url": "https://example.com/creator/douyin-epsilon",
        "sort_order": 20,
        "status": "active",
    },
    {
        "platform_slug": "douyin",
        "display_name": "示例创作者 Zeta",
        "slug": "creator-zeta",
        "avatar_url": None,
        "follower_text": "31.2 万粉丝",
        "positioning": "辟谣摘要向占位信息",
        "description": "用于观察短标题、短文案和多标签组合时，创作者卡与头像占位的呼吸感。",
        "tags": ["摘要化", "高频误区", "示例资料"],
        "profile_url": "https://example.com/creator/douyin-zeta",
        "sort_order": 30,
        "status": "active",
    },
]


def _strip_unsupported_mysql_chars(value: str) -> str:
    return "".join(char for char in value if ord(char) <= 0xFFFF)


def _clean_text(value, *, max_length: int | None = None) -> str | None:
    if value is None:
        return None

    text = _strip_unsupported_mysql_chars(str(value)).strip()
    if not text:
        return None
    if max_length is not None:
        return text[:max_length]
    return text


def _normalize_url(value) -> str | None:
    cleaned = _clean_text(value, max_length=500)
    if not cleaned:
        return None
    match = GENERIC_URL_RE.search(cleaned)
    return match.group(0)[:500] if match else cleaned[:500]


def _slugify(value: str | None, *, fallback_prefix: str) -> str | None:
    cleaned = _clean_text(value, max_length=120)
    if not cleaned:
        return None
    slug = SLUG_RE.sub("-", cleaned.lower()).strip("-")
    slug = slug[:64].strip("-")
    if slug:
        return slug
    return f"{fallback_prefix}-{abs(hash(cleaned)) % 1000000}"


def _normalize_status(value: str | None) -> str:
    candidate = (_clean_text(value, max_length=16) or "active").lower()
    return candidate if candidate in VALID_ENTRY_STATUSES else "active"


def _normalize_platform_type(value: str | None) -> str | None:
    candidate = (_clean_text(value, max_length=16) or "").lower()
    return candidate if candidate in VALID_PLATFORM_TYPES else None


def _normalize_tags(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return [_clean_text(item, max_length=32) for item in parsed if _clean_text(item, max_length=32)]
        except json.JSONDecodeError:
            return [_clean_text(item, max_length=32) for item in re.split(r"[，,、/\n]+", stripped) if _clean_text(item, max_length=32)]
    if isinstance(value, (list, tuple, set)):
        return [_clean_text(item, max_length=32) for item in value if _clean_text(item, max_length=32)]
    return []


def _serialize_platform(platform: QuickSourcePlatform) -> dict:
    return {
        "platform_id": platform.platform_id,
        "name": platform.name,
        "slug": platform.slug,
        "platform_type": platform.platform_type,
        "short_label": platform.short_label,
        "badge_text": platform.badge_text,
        "subtitle": platform.subtitle,
        "description": platform.description,
        "scene_hint": platform.scene_hint,
        "url": platform.url,
        "theme_token": platform.theme_token,
        "sort_order": platform.sort_order,
        "status": platform.status,
        "create_time": platform.create_time.isoformat(sep=" ") if platform.create_time else None,
        "update_time": platform.update_time.isoformat(sep=" ") if platform.update_time else None,
    }


def _serialize_creator(creator: QuickSourceCreator, *, platform: QuickSourcePlatform | None = None) -> dict:
    platform_payload = _serialize_platform(platform) if platform else None
    tags = _normalize_tags(creator.tags_json)
    return {
        "creator_id": creator.creator_id,
        "platform_id": creator.platform_id,
        "platform_slug": platform.slug if platform else None,
        "platform_name": platform.name if platform else None,
        "display_name": creator.display_name,
        "slug": creator.slug,
        "avatar_url": creator.avatar_url,
        "follower_text": creator.follower_text,
        "positioning": creator.positioning,
        "description": creator.description,
        "tags": tags,
        "profile_url": creator.profile_url,
        "sort_order": creator.sort_order,
        "status": creator.status,
        "create_time": creator.create_time.isoformat(sep=" ") if creator.create_time else None,
        "update_time": creator.update_time.isoformat(sep=" ") if creator.update_time else None,
        "platform": platform_payload,
    }


def ensure_default_quick_sources(db: Session) -> None:
    try:
        platform_by_slug = {
            item.slug: item
            for item in db.query(QuickSourcePlatform).all()
            if item.slug
        }
        for record in DEFAULT_PLATFORM_SEED:
            platform = platform_by_slug.get(record["slug"])
            if platform is None:
                platform = QuickSourcePlatform(
                    name=record["name"],
                    slug=record["slug"],
                    platform_type=record["platform_type"],
                    short_label=record.get("short_label"),
                    badge_text=record.get("badge_text"),
                    subtitle=record.get("subtitle"),
                    description=record.get("description"),
                    scene_hint=record.get("scene_hint"),
                    url=record.get("url"),
                    theme_token=record.get("theme_token"),
                    sort_order=int(record.get("sort_order") or 0),
                    status=_normalize_status(record.get("status")),
                )
                db.add(platform)
            else:
                platform.name = record["name"]
                platform.platform_type = record["platform_type"]
                platform.short_label = record.get("short_label")
                platform.badge_text = record.get("badge_text")
                platform.subtitle = record.get("subtitle")
                platform.description = record.get("description")
                platform.scene_hint = record.get("scene_hint")
                platform.url = record.get("url")
                platform.theme_token = record.get("theme_token")
                platform.sort_order = int(record.get("sort_order") or 0)
                platform.status = _normalize_status(record.get("status"))
            db.flush()
            platform_by_slug[platform.slug] = platform

        existing_creators_by_slug = {
            item.slug: item
            for item in db.query(QuickSourceCreator).all()
            if item.slug
        }
        for record in DEFAULT_CREATOR_SEED:
            platform = platform_by_slug.get(record["platform_slug"])
            if platform is None:
                continue
            creator = existing_creators_by_slug.get(record["slug"])
            if creator is None:
                creator = QuickSourceCreator(
                    platform_id=platform.platform_id,
                    display_name=record["display_name"],
                    slug=record["slug"],
                    avatar_url=record.get("avatar_url"),
                    follower_text=record.get("follower_text"),
                    positioning=record.get("positioning"),
                    description=record.get("description"),
                    tags_json=json.dumps(record.get("tags") or [], ensure_ascii=False),
                    profile_url=record.get("profile_url"),
                    sort_order=int(record.get("sort_order") or 0),
                    status=_normalize_status(record.get("status")),
                )
                db.add(creator)
            else:
                creator.platform_id = platform.platform_id
                creator.display_name = record["display_name"]
                creator.avatar_url = record.get("avatar_url")
                creator.follower_text = record.get("follower_text")
                creator.positioning = record.get("positioning")
                creator.description = record.get("description")
                creator.tags_json = json.dumps(record.get("tags") or [], ensure_ascii=False)
                creator.profile_url = record.get("profile_url")
                creator.sort_order = int(record.get("sort_order") or 0)
                creator.status = _normalize_status(record.get("status"))

        db.commit()
        logger.business("速看辟谣默认来源数据初始化完成")
    except Exception as exc:
        db.rollback()
        logger.error(f"速看辟谣默认来源数据初始化失败: {exc}", exc_info=True)
        raise


def get_quick_source_overview(db: Session) -> dict:
    platform_total = db.query(QuickSourcePlatform).count()
    creator_total = db.query(QuickSourceCreator).count()
    official_total = (
        db.query(QuickSourcePlatform)
        .filter(
            QuickSourcePlatform.platform_type == "official",
            QuickSourcePlatform.status == "active",
        )
        .count()
    )
    creator_platform_total = (
        db.query(QuickSourcePlatform)
        .filter(
            QuickSourcePlatform.platform_type == "creator",
            QuickSourcePlatform.status == "active",
        )
        .count()
    )
    active_creator_total = (
        db.query(QuickSourceCreator)
        .filter(QuickSourceCreator.status == "active")
        .count()
    )

    return {
        "platform_total": platform_total,
        "creator_total": creator_total,
        "official_total": official_total,
        "creator_platform_total": creator_platform_total,
        "active_creator_total": active_creator_total,
    }


def list_public_quick_sources(db: Session) -> dict:
    platforms = (
        db.query(QuickSourcePlatform)
        .filter(QuickSourcePlatform.status == "active")
        .order_by(QuickSourcePlatform.sort_order.asc(), QuickSourcePlatform.platform_id.asc())
        .all()
    )

    official_sources = [platform for platform in platforms if platform.platform_type == "official"]
    creator_platforms = [platform for platform in platforms if platform.platform_type == "creator"]

    creator_platform_map = {platform.platform_id: platform for platform in creator_platforms}
    creators = (
        db.query(QuickSourceCreator)
        .filter(QuickSourceCreator.status == "active")
        .order_by(QuickSourceCreator.sort_order.asc(), QuickSourceCreator.creator_id.asc())
        .all()
    )

    grouped_creators: dict[str, list[dict]] = {platform.slug: [] for platform in creator_platforms}
    for creator in creators:
        platform = creator_platform_map.get(creator.platform_id)
        if platform is None:
            continue
        grouped_creators.setdefault(platform.slug, []).append(_serialize_creator(creator, platform=platform))

    return {
        "official_sources": [_serialize_platform(item) for item in official_sources],
        "creator_platforms": [_serialize_platform(item) for item in creator_platforms],
        "creator_groups": grouped_creators,
        "overview": get_quick_source_overview(db),
    }


def list_admin_platforms(
    db: Session,
    *,
    search: str | None = None,
    platform_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    query = db.query(QuickSourcePlatform)

    if search:
        keyword = f"%{search.strip()}%"
        query = query.filter(
            or_(
                QuickSourcePlatform.name.like(keyword),
                QuickSourcePlatform.slug.like(keyword),
                QuickSourcePlatform.description.like(keyword),
                QuickSourcePlatform.subtitle.like(keyword),
            )
        )
    if platform_type and platform_type != "all":
        query = query.filter(QuickSourcePlatform.platform_type == platform_type)
    if status and status != "all":
        query = query.filter(QuickSourcePlatform.status == status)

    safe_page = max(1, int(page))
    safe_page_size = max(1, min(int(page_size), 100))
    ordered_query = query.order_by(QuickSourcePlatform.sort_order.asc(), QuickSourcePlatform.platform_id.asc())
    total = ordered_query.order_by(None).count()
    items = (
        ordered_query
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )

    return {
        "items": [_serialize_platform(item) for item in items],
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


def list_admin_creators(
    db: Session,
    *,
    search: str | None = None,
    platform_id: int | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    platform_map = {
        platform.platform_id: platform
        for platform in db.query(QuickSourcePlatform)
        .filter(QuickSourcePlatform.platform_type == "creator")
        .all()
    }

    query = db.query(QuickSourceCreator)

    if search:
        keyword = f"%{search.strip()}%"
        query = query.filter(
            or_(
                QuickSourceCreator.display_name.like(keyword),
                QuickSourceCreator.slug.like(keyword),
                QuickSourceCreator.description.like(keyword),
                QuickSourceCreator.positioning.like(keyword),
            )
        )
    if platform_id:
        query = query.filter(QuickSourceCreator.platform_id == platform_id)
    if status and status != "all":
        query = query.filter(QuickSourceCreator.status == status)

    safe_page = max(1, int(page))
    safe_page_size = max(1, min(int(page_size), 100))
    ordered_query = query.order_by(QuickSourceCreator.sort_order.asc(), QuickSourceCreator.creator_id.asc())
    total = ordered_query.order_by(None).count()
    items = (
        ordered_query
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )

    return {
        "items": [_serialize_creator(item, platform=platform_map.get(item.platform_id)) for item in items],
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "platform_options": [
            {
                "platform_id": platform.platform_id,
                "name": platform.name,
                "slug": platform.slug,
            }
            for platform in sorted(platform_map.values(), key=lambda item: (item.sort_order, item.platform_id))
        ],
    }


def _validate_platform_payload(
    db: Session,
    *,
    payload: dict,
    platform_id: int | None = None,
) -> tuple[dict, str | None]:
    normalized = dict(payload)
    normalized["name"] = _clean_text(normalized.get("name"), max_length=120)
    normalized["slug"] = _slugify(normalized.get("slug") or normalized.get("name"), fallback_prefix="platform")
    normalized["platform_type"] = _normalize_platform_type(normalized.get("platform_type"))
    normalized["short_label"] = _clean_text(normalized.get("short_label"), max_length=32)
    normalized["badge_text"] = _clean_text(normalized.get("badge_text"), max_length=32)
    normalized["subtitle"] = _clean_text(normalized.get("subtitle"), max_length=120)
    normalized["description"] = _clean_text(normalized.get("description"))
    normalized["scene_hint"] = _clean_text(normalized.get("scene_hint"), max_length=160)
    normalized["url"] = _normalize_url(normalized.get("url"))
    normalized["theme_token"] = _clean_text(normalized.get("theme_token"), max_length=32)
    normalized["sort_order"] = int(normalized.get("sort_order") or 0)
    normalized["status"] = _normalize_status(normalized.get("status"))

    if not normalized["name"]:
        return normalized, "平台名称不能为空"
    if not normalized["slug"]:
        return normalized, "平台标识不能为空"
    if not normalized["platform_type"]:
        return normalized, "平台类型仅支持 official 或 creator"

    query = db.query(QuickSourcePlatform).filter(QuickSourcePlatform.slug == normalized["slug"])
    if platform_id is not None:
        query = query.filter(QuickSourcePlatform.platform_id != platform_id)
    if query.first():
        return normalized, "该平台标识已存在"

    return normalized, None


def create_platform_by_admin(db: Session, *, payload: dict):
    normalized, error = _validate_platform_payload(db, payload=payload)
    if error:
        return None, error

    platform = QuickSourcePlatform(**normalized)
    try:
        db.add(platform)
        db.commit()
        db.refresh(platform)
        return _serialize_platform(platform), None
    except Exception as exc:
        db.rollback()
        logger.error(f"创建速看平台失败: {exc}", exc_info=True)
        return None, "创建速看平台失败，请稍后重试"


def update_platform_by_admin(db: Session, *, platform_id: int, payload: dict):
    platform = db.query(QuickSourcePlatform).filter(QuickSourcePlatform.platform_id == platform_id).first()
    if platform is None:
        return None, "平台不存在"

    merged_payload = {
        "name": platform.name,
        "slug": platform.slug,
        "platform_type": platform.platform_type,
        "short_label": platform.short_label,
        "badge_text": platform.badge_text,
        "subtitle": platform.subtitle,
        "description": platform.description,
        "scene_hint": platform.scene_hint,
        "url": platform.url,
        "theme_token": platform.theme_token,
        "sort_order": platform.sort_order,
        "status": platform.status,
        **payload,
    }
    normalized, error = _validate_platform_payload(db, payload=merged_payload, platform_id=platform_id)
    if error:
        return None, error

    for field, value in normalized.items():
        setattr(platform, field, value)

    try:
        db.commit()
        db.refresh(platform)
        return _serialize_platform(platform), None
    except Exception as exc:
        db.rollback()
        logger.error(f"更新速看平台失败: {exc}", exc_info=True)
        return None, "更新速看平台失败，请稍后重试"


def delete_platforms_by_admin(db: Session, *, platform_ids: list[int]):
    target_ids = sorted({int(platform_id) for platform_id in platform_ids if platform_id is not None})
    if not target_ids:
        return 0, "请选择需要删除的平台"

    targets = db.query(QuickSourcePlatform).filter(QuickSourcePlatform.platform_id.in_(target_ids)).all()
    found_ids = {item.platform_id for item in targets}
    missing_ids = [str(platform_id) for platform_id in target_ids if platform_id not in found_ids]
    if missing_ids:
        return 0, f"以下平台不存在：{', '.join(missing_ids)}"

    try:
        deleted_count = len(targets)
        for item in targets:
            db.delete(item)
        db.commit()
        return deleted_count, None
    except Exception as exc:
        db.rollback()
        logger.error(f"删除速看平台失败: {exc}", exc_info=True)
        return 0, "删除速看平台失败，请稍后重试"


def _validate_creator_payload(
    db: Session,
    *,
    payload: dict,
    creator_id: int | None = None,
) -> tuple[dict, str | None]:
    normalized = dict(payload)
    normalized["display_name"] = _clean_text(normalized.get("display_name"), max_length=120)
    normalized["slug"] = _slugify(normalized.get("slug") or normalized.get("display_name"), fallback_prefix="creator")
    normalized["avatar_url"] = _normalize_url(normalized.get("avatar_url"))
    normalized["follower_text"] = _clean_text(normalized.get("follower_text"), max_length=64)
    normalized["positioning"] = _clean_text(normalized.get("positioning"), max_length=160)
    normalized["description"] = _clean_text(normalized.get("description"))
    normalized["profile_url"] = _normalize_url(normalized.get("profile_url"))
    normalized["sort_order"] = int(normalized.get("sort_order") or 0)
    normalized["status"] = _normalize_status(normalized.get("status"))
    normalized["tags_json"] = json.dumps(_normalize_tags(normalized.get("tags") or normalized.get("tags_json")), ensure_ascii=False)

    try:
        normalized["platform_id"] = int(normalized.get("platform_id"))
    except (TypeError, ValueError):
        return normalized, "创作者必须绑定一个平台"

    if not normalized["display_name"]:
        return normalized, "创作者名称不能为空"
    if not normalized["slug"]:
        return normalized, "创作者标识不能为空"

    platform = db.query(QuickSourcePlatform).filter(
        QuickSourcePlatform.platform_id == normalized["platform_id"],
        QuickSourcePlatform.platform_type == "creator",
    ).first()
    if platform is None:
        return normalized, "请选择有效的创作者平台"

    query = db.query(QuickSourceCreator).filter(QuickSourceCreator.slug == normalized["slug"])
    if creator_id is not None:
        query = query.filter(QuickSourceCreator.creator_id != creator_id)
    if query.first():
        return normalized, "该创作者标识已存在"

    return normalized, None


def create_creator_by_admin(db: Session, *, payload: dict):
    normalized, error = _validate_creator_payload(db, payload=payload)
    if error:
        return None, error

    creator = QuickSourceCreator(**normalized)
    try:
        db.add(creator)
        db.commit()
        db.refresh(creator)
        platform = db.query(QuickSourcePlatform).filter(QuickSourcePlatform.platform_id == creator.platform_id).first()
        return _serialize_creator(creator, platform=platform), None
    except Exception as exc:
        db.rollback()
        logger.error(f"创建速看创作者失败: {exc}", exc_info=True)
        return None, "创建速看创作者失败，请稍后重试"


def update_creator_by_admin(db: Session, *, creator_id: int, payload: dict):
    creator = db.query(QuickSourceCreator).filter(QuickSourceCreator.creator_id == creator_id).first()
    if creator is None:
        return None, "创作者不存在"

    merged_payload = {
        "platform_id": creator.platform_id,
        "display_name": creator.display_name,
        "slug": creator.slug,
        "avatar_url": creator.avatar_url,
        "follower_text": creator.follower_text,
        "positioning": creator.positioning,
        "description": creator.description,
        "tags_json": creator.tags_json,
        "profile_url": creator.profile_url,
        "sort_order": creator.sort_order,
        "status": creator.status,
        **payload,
    }
    normalized, error = _validate_creator_payload(db, payload=merged_payload, creator_id=creator_id)
    if error:
        return None, error

    for field, value in normalized.items():
        setattr(creator, field, value)

    try:
        db.commit()
        db.refresh(creator)
        platform = db.query(QuickSourcePlatform).filter(QuickSourcePlatform.platform_id == creator.platform_id).first()
        return _serialize_creator(creator, platform=platform), None
    except Exception as exc:
        db.rollback()
        logger.error(f"更新速看创作者失败: {exc}", exc_info=True)
        return None, "更新速看创作者失败，请稍后重试"


def delete_creators_by_admin(db: Session, *, creator_ids: list[int]):
    target_ids = sorted({int(creator_id) for creator_id in creator_ids if creator_id is not None})
    if not target_ids:
        return 0, "请选择需要删除的创作者"

    targets = db.query(QuickSourceCreator).filter(QuickSourceCreator.creator_id.in_(target_ids)).all()
    found_ids = {item.creator_id for item in targets}
    missing_ids = [str(creator_id) for creator_id in target_ids if creator_id not in found_ids]
    if missing_ids:
        return 0, f"以下创作者不存在：{', '.join(missing_ids)}"

    try:
        deleted_count = len(targets)
        for item in targets:
            db.delete(item)
        db.commit()
        return deleted_count, None
    except Exception as exc:
        db.rollback()
        logger.error(f"删除速看创作者失败: {exc}", exc_info=True)
        return 0, "删除速看创作者失败，请稍后重试"
