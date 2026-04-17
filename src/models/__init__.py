# src/models/models.py
# SQLAlchemy 2.0 标准语法重构版
from sqlalchemy import (
    Integer, String, Text, DateTime, Date,
    Enum, ForeignKey, Index, desc, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime

# ------------------------------
# SQLAlchemy 2.0 核心：新版 Base
# ------------------------------
class Base(DeclarativeBase):
    pass

# ------------------------------
# 1. 用户表
# ------------------------------
class User(Base):
    __tablename__ = "users"

    # 使用 Mapped[类型] 和 mapped_column
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="用户名")
    password: Mapped[str] = mapped_column(String(100), nullable=False, comment="密码（加密存储）")
    email: Mapped[str] = mapped_column(String(100), unique=True, comment="邮箱")
    phone: Mapped[str] = mapped_column(String(20), comment="手机号")
    age: Mapped[int] = mapped_column(Integer, comment="年龄")
    gender: Mapped[str] = mapped_column(Enum("男", "女", "未知"), default="未知", comment="性别")
    province: Mapped[str] = mapped_column(String(30), comment="省份")
    city: Mapped[str] = mapped_column(String(30), comment="城市")
    # 使用 lambda 或 func.now() 避免时间固化
    create_time: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), comment="注册时间")
    update_time: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now(), comment="更新时间")
    status: Mapped[str] = mapped_column(Enum("正常", "禁用"), default="正常", comment="账号状态")

    __table_args__ = (
        Index("idx_province", "province"),
        Index("idx_age", "age"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "用户表"
        }
    )

# ------------------------------
# 2. 权威辟谣主谣言表
# ------------------------------
class Rumor(Base):
    __tablename__ = "rumors"

    rumor_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="谣言ID")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="谣言标题/核心内容")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="谣言完整描述")
    refute_content: Mapped[str] = mapped_column(Text, nullable=False, comment="官方辟谣内容")
    official_source: Mapped[str] = mapped_column(String(100), nullable=False, comment="官方来源")
    official_link: Mapped[str] = mapped_column(String(300), comment="官方辟谣链接")
    publish_time: Mapped[datetime] = mapped_column(DateTime, comment="官方发布时间")
    heat_score: Mapped[int] = mapped_column(Integer, default=0, comment="热度分数")
    upload_count: Mapped[int] = mapped_column(Integer, default=0, comment="被用户上传次数")
    view_count: Mapped[int] = mapped_column(Integer, default=0, comment="总浏览量")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now())

    __table_args__ = (
        # 修复：直接使用 desc(列对象)，类型检查器现在能正确识别
        Index("idx_heat_score", desc(heat_score)),
        Index("idx_upload_count", desc(upload_count)),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "权威辟谣主谣言表"
        }
    )

# ------------------------------
# 3. 用户上传谣言记录表
# ------------------------------
class UserUploadRumor(Base):
    __tablename__ = "user_upload_rumors"

    upload_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="上传ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    upload_content: Mapped[str] = mapped_column(Text, nullable=False, comment="用户上传的原始文本")
    merged_rumor_id: Mapped[int] = mapped_column(Integer, ForeignKey("rumors.rumor_id", ondelete="SET NULL"))
    upload_time: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), comment="上传时间")
    status: Mapped[str] = mapped_column(Enum("待合并", "已合并", "无效"), default="待合并", comment="处理状态")

    __table_args__ = (
        Index("idx_merged", "merged_rumor_id"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "用户上传谣言记录表"
        }
    )

# ------------------------------
# 4. 用户浏览记录表
# ------------------------------
class UserBrowseRecord(Base):
    __tablename__ = "user_browse_records"

    record_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    rumor_id: Mapped[int] = mapped_column(Integer, ForeignKey("rumors.rumor_id", ondelete="CASCADE"), nullable=False)
    browse_time: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), comment="浏览时间")

    __table_args__ = (
        # 修复：移除非法的 descending=True，改用 desc()
        Index("idx_user_time", "user_id", desc(browse_time)),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "用户浏览记录"
        }
    )

# ------------------------------
# 5. 谣言每日统计表
# ------------------------------
class RumorInteraction(Base):
    __tablename__ = "rumor_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="统计ID")
    rumor_id: Mapped[int] = mapped_column(Integer, ForeignKey("rumors.rumor_id", ondelete="CASCADE"), nullable=False)
    stat_date: Mapped[datetime] = mapped_column(Date, nullable=False, comment="统计日期")
    daily_upload: Mapped[int] = mapped_column(Integer, default=0, comment="当日上传量")
    daily_view: Mapped[int] = mapped_column(Integer, default=0, comment="当日浏览量")

    __table_args__ = (
        Index("idx_date", "stat_date"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "谣言每日统计数据（绘图用）"
        }
    )

# ------------------------------
# 6. 地区谣言统计表
# ------------------------------
class AreaRumorStat(Base):
    __tablename__ = "area_rumor_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="统计ID")
    province: Mapped[str] = mapped_column(String(30), nullable=False, comment="省份")
    city: Mapped[str] = mapped_column(String(30), comment="城市")
    rumor_count: Mapped[int] = mapped_column(Integer, default=0, comment="该地区谣言总量")
    stat_date: Mapped[datetime] = mapped_column(Date, nullable=False, comment="统计日期")

    __table_args__ = (
        Index("idx_province", province, desc(rumor_count)),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "地区谣言分布统计"
        }
    )

# ------------------------------
# 7. 年龄段谣言统计表
# ------------------------------
class AgeRumorStat(Base):
    __tablename__ = "age_rumor_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="统计ID")
    age_group: Mapped[str] = mapped_column(String(20), nullable=False, comment="年龄段：0-18/19-25/26-35/36-45/46+")
    rumor_related_count: Mapped[int] = mapped_column(Integer, default=0, comment="相关谣言数量")
    stat_date: Mapped[datetime] = mapped_column(Date, nullable=False, comment="统计日期")

    __table_args__ = (
        # 修复：移除 illegal descending=True，改用 desc()
        Index("idx_age_group", age_group, desc(rumor_related_count)),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "年龄段谣言统计"
        }
    )

# ------------------------------
# 8. 排行榜配置表
# ------------------------------
class RankingConfig(Base):
    __tablename__ = "ranking_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="配置ID")
    rank_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="排行榜名称")
    rank_type: Mapped[str] = mapped_column(Enum("heat", "confirmed"), nullable=False, comment="热度排行/已证实谣言")
    refresh_time: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), comment="更新时间")

    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "comment": "排行榜配置"
    }

#9,配置谣言存储表
