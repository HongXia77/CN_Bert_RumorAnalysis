# src/service/user_service.py
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.models._init_database import User
from modules.tools.logger import logger
from src.utils.security import get_password_hash

def login(db: Session, account: str, password: str):
    """
    登录业务逻辑
    :param account: 前端传来的账号（可能是 用户名、邮箱 或 手机号）
    """
    logger.request(f"收到登录请求=>用户：{account}")

    # 1. 根据 手机号 或 用户名 或 邮箱 查询用户
    db_user = db.query(User).filter(
        or_(
            User.username == account,
            User.email == account,
            User.phone == account
        )
    ).first()

    # 2. 校验用户是否存在
    if not db_user:
        logger.request(f"用户：{account} 登录失败！用户不存在或账号未注册")
        return False, "用户不存在或账号未注册"

    # 3. 校验密码
    # (注意：实际开发中强烈建议不要明文存密码，应使用 passlib 和 bcrypt 进行哈希比对)
    if db_user.password != password:
        logger.request(f"用户：{account} 登录失败！该账号密码错误")
        return False, "密码错误"

    # 4. 校验账号状态 (拦截被禁用或未激活的账号)
    if db_user.status == "禁用":
        logger.request(f"用户：{account} 登录失败！该账号已被禁用")
        return False, "该账号已被禁用，请联系管理员"
    elif db_user.status == "未激活":
        logger.request(f"用户：{account} 登录失败！该账号未激活")
        return False, "该账号未激活"

    logger.request(f"用户：{account} 登录成功！")
    # 5. 校验通过，返回成功标志和用户对象
    return True, db_user


def create_user(db: Session, user_data: dict):
    # 检查唯一性
    logger.request(f"{user_data['phone']} 意图创建用户")

    if db.query(User).filter(User.username == user_data['username']).first():
        logger.request(f"{user_data['phone']} 创建用户失败！因为用户名已存在")
        return None, "用户名已存在"
    if db.query(User).filter(User.email == user_data['email']).first():
        logger.request(f"{user_data['phone']} 创建用户失败！因为邮箱已被注册")
        return None, "邮箱已被注册"

    # 密码哈希处理
    hashed_password = get_password_hash(user_data['password'])
    user_data['password'] = hashed_password

    # 创建模型实例
    new_user = User(**user_data)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user, None
