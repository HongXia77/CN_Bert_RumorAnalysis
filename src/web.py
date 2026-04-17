import uvicorn
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from src.models import User
from src.utils.db import get_db
from pydantic import BaseModel
import hashlib

# 导入日志工具
from modules.tools.logger import logger

app = FastAPI()

# 系统启动日志
logger.system("FastAPI应用初始化")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    phone: str = None

class UserLogin(BaseModel):
    username: str
    password: str

# 密码加密
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# 注册接口
@app.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # 请求日志
    logger.request(f"收到注册请求: {user.username}")
    
    try:
        # 数据库操作日志
        logger.database(f"检查用户名是否存在: {user.username}")
        # 检查用户名是否已存在
        existing_user = db.query(User).filter(User.username == user.username).first()
        if existing_user:
            logger.error(f"注册失败: 用户名已存在 - {user.username}")
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        # 数据库操作日志
        logger.database(f"检查邮箱是否存在: {user.email}")
        # 检查邮箱是否已存在
        existing_email = db.query(User).filter(User.email == user.email).first()
        if existing_email:
            logger.error(f"注册失败: 邮箱已存在 - {user.email}")
            raise HTTPException(status_code=400, detail="邮箱已存在")
        
        # 业务逻辑日志
        logger.business(f"创建新用户: {user.username}")
        # 创建新用户
        hashed_password = hash_password(user.password)
        new_user = User(
            username=user.username,
            password=hashed_password,
            email=user.email,
            phone=user.phone,
            age=0,  # 设置默认值
            gender="未知",  # 设置默认值
            province="",  # 设置默认值
            city=""  # 设置默认值
        )
        
        # 数据库操作日志
        logger.database(f"保存用户到数据库: {user.username}")
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # 业务逻辑日志
        logger.business(f"注册成功: {user.username}, 用户ID: {new_user.user_id}")
        return {"message": "注册成功", "user_id": new_user.user_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="注册失败，请稍后再试")

# 登录接口
@app.post("/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    # 请求日志
    logger.request(f"收到登录请求: {user.username}")
    
    try:
        # 数据库操作日志
        logger.database(f"查找用户: {user.username}")
        # 查找用户
        existing_user = db.query(User).filter(User.username == user.username).first()
        if not existing_user:
            logger.error(f"登录失败: 用户不存在 - {user.username}")
            raise HTTPException(status_code=400, detail="用户名或密码错误")
        
        # 验证密码
        if hash_password(user.password) != existing_user.password:
            logger.error(f"登录失败: 密码错误 - {user.username}")
            raise HTTPException(status_code=400, detail="用户名或密码错误")
        
        # 业务逻辑日志
        logger.business(f"登录成功: {user.username}, 用户ID: {existing_user.user_id}")
        return {"message": "登录成功", "user_id": existing_user.user_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="登录失败，请稍后再试")

@app.get("/home")
async def home():
    # 请求日志
    logger.request("收到home请求")
    # 业务逻辑日志
    logger.business("处理home请求")
    return {"Hello": "World"}

@app.get("/select/{id}")
async def select_data(id:int):
    # 请求日志
    logger.request(f"收到select请求，ID: {id}")
    # 业务逻辑日志
    logger.business(f"处理select请求，ID: {id}")
    return f"你查询到了{id}"


if __name__ == "__main__":
    # 系统启动日志
    logger.system("启动FastAPI服务器")
    logger.system("服务器配置: host=127.0.0.1, port=8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)