from __future__ import annotations

import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from sqlalchemy import func, or_
from sqlalchemy.orm import Query, Session

from modules.tools.logger import logger
from src.models._init_database import Rumor, User, UserUploadRumor


MAP_META_URL = "https://geojson.cn/api/china/_meta.json"
MAP_GEO_URL_TEMPLATE = "https://geojson.cn/api/china/{region_path}.json"
MAP_CACHE_DIR = Path(__file__).resolve().parents[1] / "static" / "map_cache"
MAP_CACHE_DIR.mkdir(parents=True, exist_ok=True)

REGION_PATH_PATTERN = re.compile(r"^\d{6}(?:/\d{6})?$")

PROVINCE_SHORT_NAME_MAP = {
    "北京市": "北京",
    "天津市": "天津",
    "上海市": "上海",
    "重庆市": "重庆",
    "河北省": "河北",
    "山西省": "山西",
    "辽宁省": "辽宁",
    "吉林省": "吉林",
    "黑龙江省": "黑龙江",
    "江苏省": "江苏",
    "浙江省": "浙江",
    "安徽省": "安徽",
    "福建省": "福建",
    "江西省": "江西",
    "山东省": "山东",
    "河南省": "河南",
    "湖北省": "湖北",
    "湖南省": "湖南",
    "广东省": "广东",
    "海南省": "海南",
    "四川省": "四川",
    "贵州省": "贵州",
    "云南省": "云南",
    "陕西省": "陕西",
    "甘肃省": "甘肃",
    "青海省": "青海",
    "台湾省": "台湾",
    "内蒙古自治区": "内蒙古",
    "广西壮族自治区": "广西",
    "西藏自治区": "西藏",
    "宁夏回族自治区": "宁夏",
    "新疆维吾尔自治区": "新疆",
    "香港特别行政区": "香港",
    "澳门特别行政区": "澳门",
}
PROVINCE_FULL_NAME_MAP = {short_name: full_name for full_name, short_name in PROVINCE_SHORT_NAME_MAP.items()}
DISTRICT_LEVEL_PROVINCES = {"北京市", "天津市", "上海市", "重庆市"}
REGION_SUFFIXES = (
    "特别行政区",
    "自治州",
    "自治县",
    "自治区",
    "新区",
    "地区",
    "盟",
    "市",
    "区",
    "县",
)


def _cache_file_for_region(region_path: str) -> Path:
    if region_path == "_meta":
        return MAP_CACHE_DIR / "_meta.json"
    return MAP_CACHE_DIR.joinpath(*region_path.split("/")).with_suffix(".json")


def _read_json_file(file_path: Path):
    return json.loads(file_path.read_text(encoding="utf-8"))


def _write_json_file(file_path: Path, payload: dict) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _fetch_remote_json(url: str) -> dict:
    with urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


@lru_cache(maxsize=1)
def get_map_meta() -> list[dict]:
    cache_file = _cache_file_for_region("_meta")

    try:
        payload = _fetch_remote_json(MAP_META_URL)
        _write_json_file(cache_file, payload)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.error(f"获取地图元数据失败: {exc}")
        if cache_file.exists():
            payload = _read_json_file(cache_file)
        else:
            raise RuntimeError("地图元数据获取失败") from exc

    files = payload.get("files") or []
    if not files:
        return []
    return files[0].get("children", [])


def get_map_geojson(region_path: str) -> dict:
    safe_region_path = region_path.strip().strip("/")
    if not REGION_PATH_PATTERN.fullmatch(safe_region_path):
        raise ValueError("非法地图区域编码")

    cache_file = _cache_file_for_region(safe_region_path)
    if cache_file.exists():
        return _read_json_file(cache_file)

    map_url = MAP_GEO_URL_TEMPLATE.format(region_path=safe_region_path)
    try:
        payload = _fetch_remote_json(map_url)
        _write_json_file(cache_file, payload)
        return payload
    except HTTPError as exc:
        logger.error(f"获取地图 GeoJSON 失败: {safe_region_path}, status={exc.code}")
        raise RuntimeError("地图数据暂不可用") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.error(f"获取地图 GeoJSON 失败: {safe_region_path}, error={exc}")
        raise RuntimeError("地图数据暂不可用") from exc


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _normalize_province_name(value: str | None) -> str | None:
    if not value:
        return None

    province = value.strip()
    if not province:
        return None

    return PROVINCE_FULL_NAME_MAP.get(province, province)


def _strip_region_suffix(value: str | None) -> str | None:
    if not value:
        return None

    region_name = value.strip()
    if not region_name:
        return None

    for suffix in REGION_SUFFIXES:
        if region_name.endswith(suffix) and len(region_name) > len(suffix):
            return region_name[: -len(suffix)]

    return region_name


def _province_variants(value: str | None) -> list[str]:
    province = _normalize_province_name(value)
    if not province:
        return []

    variants = {province}
    short_name = PROVINCE_SHORT_NAME_MAP.get(province)
    if short_name:
        variants.add(short_name)
    return list(variants)


def _normalize_city_name(province: str | None, city: str | None) -> str | None:
    normalized_province = _normalize_province_name(province)
    if not city:
        return None

    city_name = city.strip()
    if not city_name:
        return None

    if normalized_province in DISTRICT_LEVEL_PROVINCES and city_name in _province_variants(normalized_province):
        return None

    return city_name


def _city_variants(province: str | None, city: str | None) -> list[str]:
    normalized_city = _normalize_city_name(province, city)
    if not normalized_city:
        return []

    variants = {normalized_city}
    stripped_city = _strip_region_suffix(normalized_city)
    if stripped_city and stripped_city != normalized_city:
        variants.add(stripped_city)
    return list(variants)


def _city_group_key(province: str | None, city: str | None) -> str | None:
    normalized_city = _normalize_city_name(province, city)
    if not normalized_city:
        return None

    normalized_province = _normalize_province_name(province)
    if normalized_province in DISTRICT_LEVEL_PROVINCES:
        return _strip_region_suffix(normalized_city) or normalized_city

    return normalized_city


def _iter_normalized_provinces(values: Iterable[str | None]) -> set[str]:
    normalized = set()
    for value in values:
        province = _normalize_province_name(value)
        if province:
            normalized.add(province)
    return normalized


def _build_region_scope(province: str | None, city: str | None) -> dict:
    province = _normalize_province_name(province)
    if province and city:
        return {
            "level": "city",
            "province": province,
            "city": city,
            "display_name": f"{province} · {city}",
        }
    if province:
        return {
            "level": "province",
            "province": province,
            "city": None,
            "display_name": province,
        }
    return {
        "level": "national",
        "province": None,
        "city": None,
        "display_name": "全国地区画像",
    }


def _apply_region_filters(query: Query, *, province: str | None = None, city: str | None = None) -> Query:
    if province:
        query = query.filter(User.province.in_(_province_variants(province)))
    if city:
        query = query.filter(User.city.in_(_city_variants(province, city) or [city]))
    return query


def _base_upload_query(db: Session, *, province: str | None = None, city: str | None = None) -> Query:
    query = (
        db.query(UserUploadRumor)
        .join(User, User.user_id == UserUploadRumor.user_id)
    )
    return _apply_region_filters(query, province=province, city=city)


def _count_rumor_entities(db: Session, *, province: str | None = None, city: str | None = None) -> int:
    upload_query = _base_upload_query(db, province=province, city=city)
    merged_count = (
        upload_query.with_entities(func.count(func.distinct(UserUploadRumor.merged_rumor_id))).scalar() or 0
    )
    pending_count = upload_query.filter(UserUploadRumor.merged_rumor_id.is_(None)).count()
    return int(merged_count) + int(pending_count)


def _get_region_stat_block(db: Session, *, province: str | None = None, city: str | None = None) -> dict:
    user_query = db.query(User)
    user_query = _apply_region_filters(user_query, province=province, city=city)
    upload_query = _base_upload_query(db, province=province, city=city)

    user_count = user_query.count()
    upload_count = upload_query.count()
    rumor_count = _count_rumor_entities(db, province=province, city=city)
    high_risk_count = upload_query.filter(UserUploadRumor.rumor_probability >= 0.75).count()
    medium_risk_count = upload_query.filter(
        UserUploadRumor.rumor_probability >= 0.45,
        UserUploadRumor.rumor_probability < 0.75,
    ).count()
    low_risk_count = upload_query.filter(
        or_(
            UserUploadRumor.rumor_probability < 0.45,
            UserUploadRumor.rumor_probability.is_(None),
        )
    ).count()
    latest_upload_time = upload_query.with_entities(func.max(UserUploadRumor.upload_time)).scalar()

    return {
        "user_count": int(user_count or 0),
        "upload_count": int(upload_count or 0),
        "rumor_count": int(rumor_count or 0),
        "high_risk_count": int(high_risk_count or 0),
        "medium_risk_count": int(medium_risk_count or 0),
        "low_risk_count": int(low_risk_count or 0),
        "latest_upload_time": _serialize_datetime(latest_upload_time),
    }


def _list_top_rumors(
    db: Session,
    *,
    province: str | None = None,
    city: str | None = None,
    limit: int = 6,
) -> list[dict]:
    upload_query = (
        _base_upload_query(db, province=province, city=city)
        .outerjoin(Rumor, Rumor.rumor_id == UserUploadRumor.merged_rumor_id)
        .with_entities(
            func.coalesce(Rumor.content, UserUploadRumor.upload_content).label("content"),
            func.count(UserUploadRumor.upload_id).label("upload_count"),
            func.max(UserUploadRumor.upload_time).label("latest_upload_time"),
        )
        .group_by(func.coalesce(Rumor.content, UserUploadRumor.upload_content))
        .order_by(
            func.count(UserUploadRumor.upload_id).desc(),
            func.max(UserUploadRumor.upload_time).desc(),
        )
        .limit(limit)
        .all()
    )

    results = []
    for row in upload_query:
        content = row.content or ""
        results.append(
            {
                "content": content,
                "preview": content[:72] + ("..." if len(content) > 72 else ""),
                "upload_count": int(row.upload_count or 0),
                "latest_upload_time": _serialize_datetime(row.latest_upload_time),
            }
        )
    return results


def _list_province_stats(db: Session) -> list[dict]:
    rows = (
        db.query(
            User.province.label("name"),
            User.city.label("city"),
            func.count(func.distinct(User.user_id)).label("user_count"),
            func.count(UserUploadRumor.upload_id).label("upload_count"),
            func.max(UserUploadRumor.upload_time).label("latest_upload_time"),
        )
        .outerjoin(UserUploadRumor, User.user_id == UserUploadRumor.user_id)
        .filter(User.province.isnot(None), User.province != "")
        .group_by(User.province, User.city)
        .order_by(func.count(UserUploadRumor.upload_id).desc(), User.province.asc(), User.city.asc())
        .all()
    )

    province_stats_map: dict[str, dict] = {}
    for row in rows:
        normalized_name = _normalize_province_name(row.name)
        if not normalized_name:
            continue

        stat = province_stats_map.setdefault(
            normalized_name,
            {
                "name": normalized_name,
                "user_count": 0,
                "upload_count": 0,
                "city_keys": set(),
                "latest_upload_time": None,
            },
        )
        stat["user_count"] += int(row.user_count or 0)
        stat["upload_count"] += int(row.upload_count or 0)
        city_key = _city_group_key(normalized_name, row.city)
        if city_key:
            stat["city_keys"].add(city_key)
        if row.latest_upload_time and (
            stat["latest_upload_time"] is None or row.latest_upload_time > stat["latest_upload_time"]
        ):
            stat["latest_upload_time"] = row.latest_upload_time

    province_stats = []
    for province_name, stat in province_stats_map.items():
        province_stats.append(
            {
                "name": province_name,
                "user_count": int(stat["user_count"]),
                "upload_count": int(stat["upload_count"]),
                "city_count": len(stat["city_keys"]),
                "rumor_count": _count_rumor_entities(db, province=province_name),
                "latest_upload_time": _serialize_datetime(stat["latest_upload_time"]),
            }
        )

    province_stats.sort(key=lambda item: (-item["upload_count"], item["name"]))
    return province_stats


def _list_city_stats(db: Session, province: str) -> list[dict]:
    rows = (
        db.query(
            User.city.label("name"),
            func.count(func.distinct(User.user_id)).label("user_count"),
            func.count(UserUploadRumor.upload_id).label("upload_count"),
            func.max(UserUploadRumor.upload_time).label("latest_upload_time"),
        )
        .outerjoin(UserUploadRumor, User.user_id == UserUploadRumor.user_id)
        .filter(
            User.province.in_(_province_variants(province)),
            User.city.isnot(None),
            User.city != "",
        )
        .group_by(User.city)
        .order_by(func.count(UserUploadRumor.upload_id).desc(), User.city.asc())
        .all()
    )

    city_stats_map: dict[str, dict] = {}
    for row in rows:
        city_key = _city_group_key(province, row.name)
        if not city_key:
            continue

        stat = city_stats_map.setdefault(
            city_key,
            {
                "name": row.name,
                "user_count": 0,
                "upload_count": 0,
                "latest_upload_time": None,
            },
        )
        stat["user_count"] += int(row.user_count or 0)
        stat["upload_count"] += int(row.upload_count or 0)
        if row.latest_upload_time and (
            stat["latest_upload_time"] is None or row.latest_upload_time > stat["latest_upload_time"]
        ):
            stat["latest_upload_time"] = row.latest_upload_time
        if len((row.name or "")) > len(stat["name"] or ""):
            stat["name"] = row.name

    city_stats = []
    for city_key, stat in city_stats_map.items():
        city_stats.append(
            {
                "name": stat["name"],
                "user_count": int(stat["user_count"]),
                "upload_count": int(stat["upload_count"]),
                "rumor_count": _count_rumor_entities(db, province=province, city=city_key),
                "latest_upload_time": _serialize_datetime(stat["latest_upload_time"]),
            }
        )

    city_stats.sort(key=lambda item: (-item["upload_count"], item["name"]))
    return city_stats


def get_geo_overview(db: Session) -> dict:
    total_users = db.query(func.count(User.user_id)).scalar() or 0
    total_uploads = db.query(func.count(UserUploadRumor.upload_id)).scalar() or 0
    total_rumors = db.query(func.count(Rumor.rumor_id)).scalar() or 0
    province_rows = (
        db.query(User.province)
        .filter(User.province.isnot(None), User.province != "")
        .distinct()
        .all()
    )
    covered_provinces = len(_iter_normalized_provinces(row[0] for row in province_rows))
    city_rows = (
        db.query(User.province, User.city)
        .filter(
            User.province.isnot(None),
            User.province != "",
            User.city.isnot(None),
            User.city != "",
        )
        .distinct()
        .all()
    )
    covered_cities = len(
        {
            (_normalize_province_name(province), _city_group_key(province, city))
            for province, city in city_rows
            if _normalize_province_name(province) and _city_group_key(province, city)
        }
    )
    high_risk_uploads = (
        db.query(func.count(UserUploadRumor.upload_id))
        .filter(UserUploadRumor.rumor_probability >= 0.75)
        .scalar()
        or 0
    )

    return {
        "summary": {
            "total_users": int(total_users),
            "total_uploads": int(total_uploads),
            "total_rumors": int(total_rumors),
            "covered_provinces": int(covered_provinces),
            "covered_cities": int(covered_cities),
            "high_risk_uploads": int(high_risk_uploads),
        },
        "province_stats": _list_province_stats(db),
        "top_rumors": _list_top_rumors(db),
    }


def get_geo_detail(db: Session, *, province: str | None = None, city: str | None = None) -> dict:
    scope = _build_region_scope(province, city)
    stats = _get_region_stat_block(db, province=province, city=city)
    cities = _list_city_stats(db, province) if province and not city else []

    return {
        "scope": scope,
        "stats": stats,
        "cities": cities,
        "top_rumors": _list_top_rumors(db, province=province, city=city),
    }
