from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from modules.tools.logger import logger
from src.service import (
    analytics_service,
    prediction_service,
    quick_source_service,
    rumor_service,
    user_excel_service,
    user_service,
)
from src.utils import file_handler, security
from src.utils.db import get_db


router = APIRouter()
security_scheme = HTTPBearer(auto_error=False)


class UserLogin(BaseModel):
    username: str
    password: str


class PredictionRequest(BaseModel):
    text: str


class ProfileUpdate(BaseModel):
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    gender: str | None = None
    province: str | None = None
    city: str | None = None
    birthday_ts: int | None = None


class AdminUserUpdate(BaseModel):
    role: str | None = None
    status: str | None = None


class AdminBatchDeleteRequest(BaseModel):
    user_ids: list[int]


class AdminRumorPayload(BaseModel):
    title: str | None = None
    content: str | None = None
    claim_text: str | None = None
    truth_text: str | None = None
    raw_content: str | None = None
    source_name: str | None = None
    article_id: str | None = None
    article_url: str | None = None
    publish_time: str | None = None
    label: int | None = 1
    status: str | None = None
    source_type: str | None = None


class AdminBatchDeleteRumorRequest(BaseModel):
    rumor_ids: list[int]


class AdminRumorImportRequest(BaseModel):
    file_path: str | None = None


class AdminUploadReviewPayload(BaseModel):
    action: str
    rumor_id: int | None = None
    reason: str | None = None


class AdminQuickPlatformPayload(BaseModel):
    name: str | None = None
    slug: str | None = None
    platform_type: str | None = None
    short_label: str | None = None
    badge_text: str | None = None
    subtitle: str | None = None
    description: str | None = None
    scene_hint: str | None = None
    url: str | None = None
    theme_token: str | None = None
    sort_order: int | None = None
    status: str | None = None


class AdminQuickPlatformDeleteRequest(BaseModel):
    platform_ids: list[int]


class AdminQuickCreatorPayload(BaseModel):
    platform_id: int | None = None
    display_name: str | None = None
    slug: str | None = None
    avatar_url: str | None = None
    follower_text: str | None = None
    positioning: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    profile_url: str | None = None
    sort_order: int | None = None
    status: str | None = None


class AdminQuickCreatorDeleteRequest(BaseModel):
    creator_ids: list[int]


def _build_auth_response(user, message: str):
    serialized_user = user_service.serialize_user(user)
    token = security.create_access_token(
        {
            "sub": str(user.user_id),
            "username": user.username,
            "role": user.role,
        }
    )
    return {
        "code": 200,
        "message": message,
        "access_token": token,
        "data": serialized_user,
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
        )

    payload = security.decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态已失效，请重新登录",
        )

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录令牌无效，请重新登录",
        ) from exc

    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="当前用户不存在，请重新登录",
        )

    return user


def require_admin(current_user=Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    return current_user


@router.get("/bootstrap-status")
def bootstrap_status(db: Session = Depends(get_db)):
    return {"code": 200, "data": user_service.get_bootstrap_status(db)}


@router.post("/login")
def login_user(user_in: UserLogin, db: Session = Depends(get_db)):
    success, result = user_service.login(
        db=db,
        account=user_in.username,
        password=user_in.password,
    )

    if not success:
        raise HTTPException(status_code=400, detail=result)

    return _build_auth_response(result, "登录成功")


@router.post("/upload-avatar")
async def upload_avatar(file: UploadFile = File(...)):
    url, error = await file_handler.save_avatar(file)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"code": 200, "url": url}


@router.post("/register")
def register(
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    gender: str = Form(...),
    province: str = Form(...),
    city: str = Form(...),
    birthday_ts: int = Form(...),
    avatar: str = Form(None),
    db: Session = Depends(get_db),
):
    birthday_dt = datetime.fromtimestamp(birthday_ts / 1000).date()

    user_dict = {
        "username": username,
        "password": password,
        "email": email,
        "phone": phone,
        "gender": gender,
        "province": province,
        "city": city,
        "birthday": birthday_dt,
        "avatar": avatar,
        "status": "正常",
    }

    user, error = user_service.create_user(db, user_dict)
    if error:
        raise HTTPException(status_code=400, detail=error)

    return _build_auth_response(user, "注册成功")


@router.get("/me")
def get_profile(current_user=Depends(get_current_user)):
    return {
        "code": 200,
        "data": user_service.serialize_user(current_user),
    }


@router.put("/me")
def update_profile(
    payload: ProfileUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    update_data = payload.dict(exclude_none=True)

    if "birthday_ts" in update_data:
        update_data["birthday"] = datetime.fromtimestamp(update_data.pop("birthday_ts") / 1000).date()

    updated_user, error = user_service.update_user_profile(db, current_user, update_data)
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "资料更新成功",
        "data": user_service.serialize_user(updated_user),
    }


@router.post("/predict")
def predict_rumor(
    payload: PredictionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        official_candidates = rumor_service.find_related_rumors(
            db,
            text=payload.text,
            limit=12,
        )
        result = prediction_service.predict_text(
            payload.text,
            official_candidates=official_candidates,
        )
        storage_result, storage_error = user_service.save_user_prediction_record(
            db,
            user=current_user,
            raw_text=payload.text,
            prediction_result=result,
        )
        if storage_error:
            raise HTTPException(status_code=500, detail=storage_error)

        result["storage"] = storage_result
        logger.business(
            f"用户 {current_user.user_id} 完成文本识别并入库，risk={result['risk_level']}, "
            f"prob={result['rumor_probability']:.4f}, rumor_id={storage_result['rumor_id']}, "
            f"upload_id={storage_result['upload_id']}, merge_strategy={storage_result['merge_strategy']}"
        )
        return {"code": 200, "data": result}
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"模型识别失败: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="模型识别失败，请稍后重试") from exc


@router.get("/rumors/library")
def list_public_rumors(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = rumor_service.list_public_rumors(
        db,
        search=search,
        page=page,
        page_size=page_size,
    )
    return {
        "code": 200,
        "data": {
            "items": [rumor_service.serialize_rumor(rumor) for rumor in result["items"]],
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
        },
    }


@router.get("/rumors/library/{rumor_id}")
def get_public_rumor_detail(
    rumor_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rumor = rumor_service.get_public_rumor_by_id(db, rumor_id)
    if rumor is None:
        raise HTTPException(status_code=404, detail="未找到对应主谣言")

    return {
        "code": 200,
        "data": rumor_service.serialize_rumor(rumor),
    }


@router.get("/history")
def get_prediction_history(
    limit: int = Query(default=100, ge=1, le=200),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "code": 200,
        "data": user_service.list_user_prediction_history(
            db,
            user=current_user,
            limit=limit,
        ),
    }


@router.get("/quick-look/feed")
def get_quick_look_feed(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "code": 200,
        "data": quick_source_service.list_public_quick_sources(db),
    }


@router.delete("/history/{upload_id}")
def delete_prediction_history_record(
    upload_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    success, error = user_service.delete_user_prediction_record(
        db,
        user=current_user,
        upload_id=upload_id,
    )
    if not success:
        raise HTTPException(status_code=404, detail=error)

    return {
        "code": 200,
        "message": "识别记录已删除",
    }


@router.delete("/history")
def clear_prediction_history(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted_count, error = user_service.clear_user_prediction_history(db, user=current_user)
    if error:
        raise HTTPException(status_code=500, detail=error)

    return {
        "code": 200,
        "message": "识别记录已清空",
        "data": {"deleted_count": deleted_count},
    }


@router.get("/map-meta")
def get_map_meta(current_user=Depends(get_current_user)):
    try:
        return {
            "code": 200,
            "data": analytics_service.get_map_meta(),
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/map-geo/{region_path:path}")
def get_map_geojson(region_path: str, current_user=Depends(get_current_user)):
    try:
        return analytics_service.get_map_geojson(region_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/analytics/geo/overview")
def get_geo_analytics_overview(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return {
        "code": 200,
        "data": analytics_service.get_geo_overview(db),
    }


@router.get("/analytics/geo/detail")
def get_geo_analytics_detail(
    province: str | None = Query(default=None),
    city: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return {
        "code": 200,
        "data": analytics_service.get_geo_detail(db, province=province, city=city),
    }


@router.get("/admin/overview")
def admin_overview(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return {"code": 200, "data": user_service.get_admin_overview(db)}


@router.get("/admin/quick-look/overview")
def admin_quick_look_overview(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return {
        "code": 200,
        "data": quick_source_service.get_quick_source_overview(db),
    }


@router.get("/admin/users")
def admin_list_users(
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    result = user_service.list_users(
        db,
        search=search,
        role=role,
        status=status_value,
        page=page,
        page_size=page_size,
    )
    return {
        "code": 200,
        "data": {
            "items": [user_service.serialize_user(user) for user in result["items"]],
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
        },
    }


@router.patch("/admin/users/{target_user_id}")
def admin_update_user(
    target_user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    updated_user, error = user_service.update_user_by_admin(
        db,
        current_user=current_user,
        target_user_id=target_user_id,
        role=payload.role,
        status=payload.status,
    )

    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "用户信息更新成功",
        "data": user_service.serialize_user(updated_user),
    }


@router.delete("/admin/users")
def admin_batch_delete_users(
    payload: AdminBatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    deleted_count, error = user_service.delete_users_by_admin(
        db,
        current_user=current_user,
        user_ids=payload.user_ids,
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "用户删除成功",
        "data": {"deleted_count": deleted_count},
    }


@router.post("/admin/users/import")
async def admin_import_users(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    filename = (file.filename or "").lower()
    if not filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="仅支持导入 .xlsx 格式的 Excel 文件")

    file_bytes = await file.read()
    result, error = user_excel_service.import_users_from_excel(
        db,
        current_user=current_user,
        file_bytes=file_bytes,
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "用户 Excel 导入成功",
        "data": result,
    }


@router.get("/admin/users/export")
def admin_export_users(
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    export_bytes = user_excel_service.export_users_to_excel(
        db,
        search=search,
        role=role,
        status=status_value,
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    headers = {
        "Content-Disposition": f'attachment; filename="users_export_{timestamp}.xlsx"',
    }
    return StreamingResponse(
        iter([export_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/admin/users/import-template")
def admin_download_import_template(current_user=Depends(require_admin)):
    template_bytes = user_excel_service.build_user_import_template()
    headers = {
        "Content-Disposition": 'attachment; filename="users_import_template.xlsx"',
    }
    return StreamingResponse(
        iter([template_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/admin/rumors")
def admin_list_rumors(
    search: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_name: str | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    result = rumor_service.list_rumors(
        db,
        search=search,
        source_type=source_type,
        status=status_value,
        source_name=source_name,
        page=page,
        page_size=page_size,
    )
    return {
        "code": 200,
        "data": {
            "items": [rumor_service.serialize_rumor(rumor) for rumor in result["items"]],
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
        },
    }


@router.get("/admin/quick-look/platforms")
def admin_list_quick_platforms(
    search: str | None = Query(default=None),
    platform_type: str | None = Query(default=None),
    status_value: str | None = Query(default="all", alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return {
        "code": 200,
        "data": quick_source_service.list_admin_platforms(
            db,
            search=search,
            platform_type=platform_type,
            status=status_value,
            page=page,
            page_size=page_size,
        ),
    }


@router.post("/admin/quick-look/platforms")
def admin_create_quick_platform(
    payload: AdminQuickPlatformPayload,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    result, error = quick_source_service.create_platform_by_admin(
        db,
        payload=payload.dict(exclude_unset=True),
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "速看平台已创建",
        "data": result,
    }


@router.patch("/admin/quick-look/platforms/{platform_id}")
def admin_update_quick_platform(
    platform_id: int,
    payload: AdminQuickPlatformPayload,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    result, error = quick_source_service.update_platform_by_admin(
        db,
        platform_id=platform_id,
        payload=payload.dict(exclude_unset=True),
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "速看平台已更新",
        "data": result,
    }


@router.delete("/admin/quick-look/platforms")
def admin_delete_quick_platforms(
    payload: AdminQuickPlatformDeleteRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    deleted_count, error = quick_source_service.delete_platforms_by_admin(
        db,
        platform_ids=payload.platform_ids,
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "速看平台已删除",
        "data": {"deleted_count": deleted_count},
    }


@router.get("/admin/quick-look/creators")
def admin_list_quick_creators(
    search: str | None = Query(default=None),
    platform_id: int | None = Query(default=None),
    status_value: str | None = Query(default="all", alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return {
        "code": 200,
        "data": quick_source_service.list_admin_creators(
            db,
            search=search,
            platform_id=platform_id,
            status=status_value,
            page=page,
            page_size=page_size,
        ),
    }


@router.post("/admin/quick-look/creators")
def admin_create_quick_creator(
    payload: AdminQuickCreatorPayload,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    result, error = quick_source_service.create_creator_by_admin(
        db,
        payload=payload.dict(exclude_unset=True),
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "创作者资料已创建",
        "data": result,
    }


@router.patch("/admin/quick-look/creators/{creator_id}")
def admin_update_quick_creator(
    creator_id: int,
    payload: AdminQuickCreatorPayload,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    result, error = quick_source_service.update_creator_by_admin(
        db,
        creator_id=creator_id,
        payload=payload.dict(exclude_unset=True),
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "创作者资料已更新",
        "data": result,
    }


@router.delete("/admin/quick-look/creators")
def admin_delete_quick_creators(
    payload: AdminQuickCreatorDeleteRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    deleted_count, error = quick_source_service.delete_creators_by_admin(
        db,
        creator_ids=payload.creator_ids,
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "创作者资料已删除",
        "data": {"deleted_count": deleted_count},
    }


@router.get("/admin/upload-reviews")
def admin_list_upload_reviews(
    search: str | None = Query(default=None),
    status_value: str | None = Query(default="all", alias="status"),
    risk_level: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    result = user_service.list_admin_upload_reviews(
        db,
        search=search,
        status=status_value,
        risk_level=risk_level,
        page=page,
        page_size=page_size,
    )
    return {"code": 200, "data": result}


@router.patch("/admin/upload-reviews/{upload_id}")
def admin_review_upload_record(
    upload_id: int,
    payload: AdminUploadReviewPayload,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    result, error = user_service.review_prediction_record_by_admin(
        db,
        upload_id=upload_id,
        action=payload.action,
        rumor_id=payload.rumor_id,
        reason=payload.reason,
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "审核操作已完成",
        "data": result,
    }


@router.post("/admin/rumors")
def admin_create_rumor(
    payload: AdminRumorPayload,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    rumor, error = rumor_service.create_rumor_by_admin(
        db,
        payload=payload.dict(exclude_unset=True),
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "谣言创建成功",
        "data": rumor_service.serialize_rumor(rumor),
    }


@router.patch("/admin/rumors/{rumor_id}")
def admin_update_rumor(
    rumor_id: int,
    payload: AdminRumorPayload,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    rumor, error = rumor_service.update_rumor_by_admin(
        db,
        rumor_id=rumor_id,
        payload=payload.dict(exclude_unset=True),
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "谣言更新成功",
        "data": rumor_service.serialize_rumor(rumor),
    }


@router.delete("/admin/rumors")
def admin_batch_delete_rumors(
    payload: AdminBatchDeleteRumorRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    deleted_count, error = rumor_service.delete_rumors_by_admin(
        db,
        rumor_ids=payload.rumor_ids,
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "谣言删除成功",
        "data": {"deleted_count": deleted_count},
    }


@router.post("/admin/rumors/import-piyao")
def admin_import_piyao_rumors(
    payload: AdminRumorImportRequest | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    summary, error = rumor_service.import_rumors_from_piyao_file(
        db,
        file_path=payload.file_path if payload else None,
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "code": 200,
        "message": "平台谣言数据导入完成",
        "data": summary,
    }
