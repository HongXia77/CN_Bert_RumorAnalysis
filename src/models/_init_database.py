# src/models/_init_database.py
# SQLAlchemy 2.0 标准语法
import sys
import os

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import (
    Integer, String, Text, DateTime, Date, Float,
    Enum, ForeignKey, Index, desc, func, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime

from src.utils.db import engine

# SQLAlchemy 2.0 核心：新版 Base
class Base(DeclarativeBase):
    pass

# 1. 用户表
class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="用户名（昵称）")
    password: Mapped[str] = mapped_column(String(100), nullable=False, comment="密码")
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="邮箱")
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, comment="手机号")
    avatar: Mapped[str] = mapped_column(String(255), comment="头像URL或文件路径")
    role: Mapped[str] = mapped_column(Enum("admin", "user"), default="user", comment="用户身份")
    gender: Mapped[str] = mapped_column(Enum("男", "女", "未知"), default="未知", comment="性别")
    province: Mapped[str] = mapped_column(String(30), comment="所在省份")
    city: Mapped[str] = mapped_column(String(30), comment="所在城市")
    birthday: Mapped[datetime] = mapped_column(Date, comment="出生日期")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), comment="账号生成时间")
    update_time: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now(), comment="账号信息更新时间")
    status: Mapped[str] = mapped_column(Enum("正常", "禁用", "未激活"), default="未激活", comment="账号状态")

    __table_args__ = (
        Index("idx_username", "username"),
        Index("idx_email", "email"),
        Index("idx_phone", "phone"),
        Index("idx_role", "role"),
        Index("idx_status", "status"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "用户表"
        }
    )

# 2. 谣言表
class Rumor(Base):
    __tablename__ = "rumors"

    rumor_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="谣言ID")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="谣言/常识/新闻文本内容")
    label: Mapped[int] = mapped_column(Integer, nullable=False, comment="标签 0=非谣言 1=谣言")

    # 根据来源自动设置状态
    status: Mapped[str] = mapped_column(
        Enum("pass", "not_pass"),
        nullable=False,
        comment="审核状态：系统录入默认通过，用户上传默认未通过"
    )

    source_type: Mapped[str] = mapped_column(
        Enum("system", "user"),
        nullable=False,
        comment="来源类型"
    )

    # 系统录入无用户，允许 NULL
    upload_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        comment="上传用户ID（系统录入为空）"
    )

    refute_link: Mapped[str] = mapped_column(String(300), nullable=True, comment="辟谣出处链接")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now,
                                                  comment="更新时间")

    # 插入时自动根据来源设置状态
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 系统录入 → 自动通过
        if self.source_type == "系统自动录入":
            self.status = "pass"
        # 用户上传 → 待审核
        elif self.source_type == "用户上传":
            self.status = "not_pass"

    __table_args__ = (
        Index("idx_label", "label"),
        Index("idx_status", "status"),
        Index("idx_source_type", "source_type"),
        Index("idx_upload_user", "upload_user_id"),
        Index("idx_create_time", create_time.desc()),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "谣言/真实新闻/常识主表"
        }
    )

# 3. 谣言相似度关联表
class RumorSimilarity(Base):
    __tablename__ = "rumor_similarities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="ID")
    rumor_id_1: Mapped[int] = mapped_column(Integer, ForeignKey("rumors.rumor_id", ondelete="CASCADE"), nullable=False,
                                            comment="谣言1")
    rumor_id_2: Mapped[int] = mapped_column(Integer, ForeignKey("rumors.rumor_id", ondelete="CASCADE"), nullable=False,
                                            comment="谣言2")
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False, comment="相似度 0~1")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    __table_args__ = (
        Index("idx_rumor_pair", "rumor_id_1", "rumor_id_2"),  # 加速查询
        Index("idx_similarity", similarity_score.desc()),

        # 关键：防止谣言对重复
        UniqueConstraint("rumor_id_1", "rumor_id_2", name="uix_rumor_pair"),

        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "相似谣言关联表（训练用）"
        }
    )

# 创建表结构
if __name__ == "__main__":
    print("开始创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建成功！")