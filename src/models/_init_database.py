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
        Index("idx_users_username", "username"),
        Index("idx_users_email", "email"),
        Index("idx_users_phone", "phone"),
        Index("idx_users_role", "role"),
        Index("idx_users_status", "status"),
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
    title: Mapped[str | None] = mapped_column(String(300), nullable=True, comment="主谣言标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="主谣言核心断言文本")
    claim_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="抽取的谣言断言文本")
    truth_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="辟谣结论/事实摘要")
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="原始文章正文")
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="来源平台或出处")
    article_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="原始文章唯一标识")
    article_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="原始文章链接")
    publish_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="原始文章发布时间")
    normalized_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="标准化后的文本")
    merge_key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="归并键哈希")
    fact_signature: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="数字/时间等硬事实签名")
    label: Mapped[int] = mapped_column(Integer, nullable=False, comment="标签 0=非谣言 1=谣言")
    upload_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="关联上传次数")

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
    latest_upload_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最近一次上传时间")
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now,
                                                  comment="更新时间")

    # 插入时自动根据来源设置状态
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 系统录入 → 自动通过
        if self.source_type == "system":
            self.status = "pass"
        # 用户上传 → 待审核
        elif self.source_type == "user":
            self.status = "not_pass"

    __table_args__ = (
        Index("idx_rumors_title", "title"),
        Index("idx_rumors_label", "label"),
        Index("idx_rumors_status", "status"),
        Index("idx_rumors_source_type", "source_type"),
        Index("idx_rumors_source_name", "source_name"),
        Index("idx_rumors_article_id", "article_id"),
        Index("idx_rumors_publish_time", publish_time.desc()),
        Index("idx_rumors_upload_user_id", "upload_user_id"),
        Index("idx_rumors_merge_key_hash", "merge_key_hash"),
        Index("idx_rumors_fact_signature", "fact_signature"),
        Index("idx_rumors_create_time", create_time.desc()),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "谣言/真实新闻/常识主表"
        }
    )

# 3. 用户上传谣言记录表
class UserUploadRumor(Base):
    __tablename__ = "user_upload_rumors"

    upload_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="上传ID")
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        comment="上传用户ID",
    )
    upload_content: Mapped[str] = mapped_column(Text, nullable=False, comment="用户上传的原始文本")
    normalized_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="标准化后的上传文本")
    merge_key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="归并键哈希")
    fact_signature: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="硬事实签名")
    merged_rumor_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("rumors.rumor_id", ondelete="SET NULL"),
        nullable=True,
        comment="关联主谣言ID",
    )
    candidate_rumor_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="建议归并的候选主谣言ID")
    upload_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="上传时间")
    predicted_label: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="本次识别预测标签")
    rumor_probability: Mapped[float | None] = mapped_column(Float, nullable=True, comment="本次识别谣言概率")
    base_model_probability: Mapped[float | None] = mapped_column(Float, nullable=True, comment="基础模型谣言概率")
    event_match_probability: Mapped[float | None] = mapped_column(Float, nullable=True, comment="主谣言匹配概率")
    result_risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="风险等级")
    result_verdict: Mapped[str | None] = mapped_column(String(120), nullable=True, comment="结果结论文案")
    related_rumors_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="候选主谣言快照JSON")
    status: Mapped[str] = mapped_column(
        Enum("待合并", "已合并", "无效"),
        default="待合并",
        comment="上传记录状态",
    )
    merge_strategy: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="归并策略")
    merge_confidence: Mapped[float | None] = mapped_column(Float, nullable=True, comment="归并置信度")
    merge_reason: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="归并说明")

    __table_args__ = (
        Index("idx_user_upload_rumors_user_id", "user_id"),
        Index("idx_user_upload_rumors_merged_rumor_id", "merged_rumor_id"),
        Index("idx_user_upload_rumors_candidate_rumor_id", "candidate_rumor_id"),
        Index("idx_user_upload_rumors_merge_key_hash", "merge_key_hash"),
        Index("idx_user_upload_rumors_upload_time", upload_time.desc()),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "用户上传谣言记录表"
        }
    )

# 4. 谣言相似度关联表
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
        Index("idx_rumor_similarities_pair", "rumor_id_1", "rumor_id_2"),  # 加速查询
        Index("idx_rumor_similarities_score", similarity_score.desc()),

        # 关键：防止谣言对重复
        UniqueConstraint("rumor_id_1", "rumor_id_2", name="uix_rumor_pair"),

        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "相似谣言关联表（训练用）"
        }
    )

# 5. 速看来源平台表
class QuickSourcePlatform(Base):
    __tablename__ = "quick_source_platforms"

    platform_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="平台ID")
    name: Mapped[str] = mapped_column(String(120), nullable=False, comment="平台名称")
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="平台唯一标识")
    platform_type: Mapped[str] = mapped_column(
        Enum("official", "creator"),
        nullable=False,
        comment="平台类型：权威机构/创作者平台",
    )
    short_label: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="短标签，如 PIYAO / NHC")
    badge_text: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="徽标标签，如 国家级 / 健康")
    subtitle: Mapped[str | None] = mapped_column(String(120), nullable=True, comment="副标题或平台说明")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="平台说明")
    scene_hint: Mapped[str | None] = mapped_column(String(160), nullable=True, comment="适用场景或推荐说明")
    url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="平台访问链接")
    theme_token: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="前端主题标识")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序值")
    status: Mapped[str] = mapped_column(
        Enum("active", "inactive"),
        default="active",
        nullable=False,
        comment="状态：启用/停用",
    )
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    __table_args__ = (
        Index("idx_quick_source_platforms_slug", "slug"),
        Index("idx_quick_source_platforms_type", "platform_type"),
        Index("idx_quick_source_platforms_status", "status"),
        Index("idx_quick_source_platforms_sort_order", "sort_order"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "速看来源平台表",
        },
    )


# 6. 速看创作者表
class QuickSourceCreator(Base):
    __tablename__ = "quick_source_creators"

    creator_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="创作者ID")
    platform_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("quick_source_platforms.platform_id", ondelete="CASCADE"),
        nullable=False,
        comment="所属创作者平台ID",
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False, comment="创作者名称")
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, comment="创作者唯一标识")
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="头像链接")
    follower_text: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="粉丝数显示文本")
    positioning: Mapped[str | None] = mapped_column(String(160), nullable=True, comment="定位说明")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="简介")
    tags_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="标签JSON")
    profile_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="主页链接")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序值")
    status: Mapped[str] = mapped_column(
        Enum("active", "inactive"),
        default="active",
        nullable=False,
        comment="状态：启用/停用",
    )
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    __table_args__ = (
        Index("idx_quick_source_creators_platform_id", "platform_id"),
        Index("idx_quick_source_creators_slug", "slug"),
        Index("idx_quick_source_creators_status", "status"),
        Index("idx_quick_source_creators_sort_order", "sort_order"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "comment": "速看创作者表",
        },
    )

# 创建表结构
if __name__ == "__main__":
    print("开始创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建成功！")
