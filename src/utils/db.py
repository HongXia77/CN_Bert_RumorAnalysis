# src/utils/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ======================
# 数据库连接地址
# ======================
DATABASE_URL = "mysql+pymysql://root:7x7x@10.51.221.116:3306/Bert_RumorAnalysis?charset=utf8"

# ======================
# 创建引擎
# ======================
engine = create_engine(
    DATABASE_URL,
    echo=True,    # 打印SQL，方便调试
    future=True   # 新版SQLAlchemy支持
)

# ======================
# 创建会话工厂
# ======================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ORM 基类（所有模型继承这个）
Base = declarative_base()

# ======================
# FastAPI 数据库依赖
# ======================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()