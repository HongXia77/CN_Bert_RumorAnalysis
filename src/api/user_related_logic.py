# src/api/user.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.utils.db import get_db
from src.utils import security, file_handler
from src.service import user_service
from datetime import datetime
from modules.tools.logger import logger

router = APIRouter()


# 接收前端传来的 JSON 数据结构
class UserLogin(BaseModel):
    username: str  # 对应前端的 loginForm.username (实为 用户名/邮箱/手机号)
    password: str  # 对应前端的 loginForm.password


@router.post("/login")
def login_user(user_in: UserLogin, db: Session = Depends(get_db)):
    # 1. 调用 Service 层进行登录校验
    success, result = user_service.login(
        db=db,
        account=user_in.username,
        password=user_in.password
    )

    # 2. 如果失败（success为False），抛出 400 错误和对应原因
    if not success:
        raise HTTPException(status_code=400, detail=result)

    # 3. 如果成功，解析出用户对象
    user = result

    # 4. 返回前端所需的数据（包含用户级别 role）
    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role,  # 返回用户级别：'admin' 或 'user'
            "avatar": user.avatar,  # 可以顺便把头像返回给前端渲染
            "status": user.status
        }
    }

# 独立头像上传接口
@router.post("/upload-avatar")
async def upload_avatar(file: UploadFile = File(...)):
    url, error = await file_handler.save_avatar(file)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"code": 200, "url": url}

# 注册接口
@router.post("/register")
def register(
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    gender: str = Form(...),
    province: str = Form(...),
    city: str = Form(...),
    birthday_ts: int = Form(...), # 接收前端的时间戳
    avatar: str = Form(None),
    db: Session = Depends(get_db)
):
    # 转换时间戳
    birthday_dt = datetime.fromtimestamp(birthday_ts / 1000)

    user_dict = {
        "username": username, "password": password, "email": email,
        "phone": phone, "gender": gender, "province": province,
        "city": city, "birthday": birthday_dt, "avatar": avatar,
        "status": "正常" # 注册后直接设为正常
    }

    user, error = user_service.create_user(db, user_dict)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # 注册成功直接发放令牌
    token = security.create_access_token({"sub": user.username})
    return {
        "code": 200,
        "message": "注册成功",
        "access_token": token,
        "data": {"user_id": user.user_id}
    }