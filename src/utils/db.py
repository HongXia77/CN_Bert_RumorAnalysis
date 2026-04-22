import configparser
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import create_engine, func, inspect, or_, text
from sqlalchemy.orm import declarative_base, sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"
RUNTIME_DB_CONFIG_PATH = PROJECT_ROOT / "database.runtime.ini"
DEFAULT_DATABASE_TARGET = "remote"
DEFAULT_LOCAL_SQLITE_PATH = PROJECT_ROOT / "local.sqlite3"
DEFAULT_LOCAL_DATABASE_URL = f"sqlite:///{DEFAULT_LOCAL_SQLITE_PATH.as_posix()}"
DEFAULT_DATABASE_URL = DEFAULT_LOCAL_DATABASE_URL


def _resolve_sqlite_path(raw_path: str | os.PathLike[str] | None = None) -> Path:
    if raw_path:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
    else:
        candidate = DEFAULT_LOCAL_SQLITE_PATH
    return candidate.resolve()


def _path_for_runtime_config(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _build_sqlite_url(sqlite_path: Path) -> str:
    return f"sqlite:///{sqlite_path.as_posix()}"


def _load_remote_database_url() -> str:
    remote_database_url = os.getenv("REMOTE_DATABASE_URL", "").strip()
    if remote_database_url:
        return remote_database_url

    if ALEMBIC_INI_PATH.exists():
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(ALEMBIC_INI_PATH, encoding="utf-8")
        alembic_database_url = parser.get("alembic", "sqlalchemy.url", fallback="").strip()
        if alembic_database_url:
            return alembic_database_url

    return ""


def read_database_runtime_config() -> dict[str, str | Path]:
    parser = configparser.ConfigParser(interpolation=None)
    if RUNTIME_DB_CONFIG_PATH.exists():
        parser.read(RUNTIME_DB_CONFIG_PATH, encoding="utf-8")

    configured_target = parser.get("database", "target", fallback=DEFAULT_DATABASE_TARGET).strip().lower()
    if configured_target not in {"local", "remote"}:
        configured_target = DEFAULT_DATABASE_TARGET

    local_sqlite_path = _resolve_sqlite_path(
        parser.get(
            "database",
            "local_sqlite_path",
            fallback=DEFAULT_LOCAL_SQLITE_PATH.name,
        ).strip()
    )
    local_database_url = os.getenv("LOCAL_DATABASE_URL", "").strip() or _build_sqlite_url(local_sqlite_path)

    env_target = os.getenv("DATABASE_TARGET", "").strip().lower()
    if env_target in {"local", "remote"}:
        configured_target = env_target

    return {
        "configured_target": configured_target,
        "local_sqlite_path": local_sqlite_path,
        "local_database_url": local_database_url,
        "remote_database_url": _load_remote_database_url(),
        "runtime_config_path": RUNTIME_DB_CONFIG_PATH,
    }


def write_database_runtime_config(
    *,
    target: str | None = None,
    local_sqlite_path: str | os.PathLike[str] | None = None,
) -> dict[str, str | Path]:
    current_config = read_database_runtime_config()

    next_target = (target or current_config["configured_target"]).strip().lower()
    if next_target not in {"local", "remote"}:
        raise ValueError("数据库目标只能是 'local' 或 'remote'")

    next_local_sqlite_path = _resolve_sqlite_path(local_sqlite_path or current_config["local_sqlite_path"])

    parser = configparser.ConfigParser(interpolation=None)
    parser["database"] = {
        "target": next_target,
        "local_sqlite_path": _path_for_runtime_config(next_local_sqlite_path),
    }

    with RUNTIME_DB_CONFIG_PATH.open("w", encoding="utf-8") as config_file:
        parser.write(config_file)

    return read_database_runtime_config()


def get_database_runtime_info() -> dict[str, str | Path]:
    runtime_config = read_database_runtime_config()
    explicit_database_url = os.getenv("DATABASE_URL", "").strip()

    if explicit_database_url:
        effective_target = "explicit"
        effective_database_url = explicit_database_url
    elif runtime_config["configured_target"] == "local":
        effective_target = "local"
        effective_database_url = runtime_config["local_database_url"]
    elif runtime_config["remote_database_url"]:
        effective_target = "remote"
        effective_database_url = runtime_config["remote_database_url"]
    else:
        effective_target = "local"
        effective_database_url = runtime_config["local_database_url"]

    return {
        **runtime_config,
        "effective_target": effective_target,
        "effective_database_url": effective_database_url,
        "explicit_database_url": explicit_database_url,
    }


def mask_database_url(database_url: str) -> str:
    if not database_url:
        return database_url

    if database_url.startswith("sqlite:///"):
        return database_url

    parts = urlsplit(database_url)
    if not parts.scheme:
        return database_url

    netloc = parts.netloc
    if "@" in netloc:
        credentials, host = netloc.rsplit("@", 1)
        if ":" in credentials:
            username, _ = credentials.split(":", 1)
            netloc = f"{username}:***@{host}"
        else:
            netloc = f"{credentials}@{host}"

    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _load_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return database_url

    runtime_info = get_database_runtime_info()
    if runtime_info["effective_target"] == "local":
        return runtime_info["local_database_url"]

    if runtime_info["remote_database_url"]:
        return runtime_info["remote_database_url"]

    return runtime_info["local_database_url"]


def create_engine_for_url(database_url: str):
    engine_kwargs = {
        "echo": SQL_ECHO,
        "future": True,
        "pool_pre_ping": not database_url.startswith("sqlite"),
    }

    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    elif database_url.startswith("mysql"):
        timeout_seconds = int(os.getenv("MYSQL_CONNECT_TIMEOUT", "5"))
        engine_kwargs["connect_args"] = {
            "connect_timeout": timeout_seconds,
            "read_timeout": timeout_seconds,
            "write_timeout": timeout_seconds,
        }

    return create_engine(database_url, **engine_kwargs)


def create_session_factory(bind_engine):
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=bind_engine,
    )


SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"
DATABASE_RUNTIME_INFO = get_database_runtime_info()
DATABASE_TARGET = DATABASE_RUNTIME_INFO["effective_target"]
DATABASE_URL = _load_database_url()
LOCAL_SQLITE_PATH = DATABASE_RUNTIME_INFO["local_sqlite_path"]
REMOTE_DATABASE_URL = DATABASE_RUNTIME_INFO["remote_database_url"]

engine = create_engine_for_url(DATABASE_URL)
SessionLocal = create_session_factory(engine)


Base = declarative_base()


def _column_statements(dialect_name: str) -> dict[str, dict[str, str]]:
    if dialect_name == "mysql":
        return {
            "rumors": {
                "title": (
                    "ALTER TABLE rumors "
                    "ADD COLUMN title VARCHAR(300) NULL COMMENT '主谣言标题'"
                ),
                "claim_text": (
                    "ALTER TABLE rumors "
                    "ADD COLUMN claim_text TEXT NULL COMMENT '抽取的谣言断言文本'"
                ),
                "truth_text": (
                    "ALTER TABLE rumors "
                    "ADD COLUMN truth_text TEXT NULL COMMENT '辟谣结论/事实摘要'"
                ),
                "raw_content": (
                    "ALTER TABLE rumors "
                    "ADD COLUMN raw_content TEXT NULL COMMENT '原始文章正文'"
                ),
                "source_name": (
                    "ALTER TABLE rumors "
                    "ADD COLUMN source_name VARCHAR(255) NULL COMMENT '来源平台或出处'"
                ),
                "article_id": (
                    "ALTER TABLE rumors "
                    "ADD COLUMN article_id VARCHAR(64) NULL COMMENT '原始文章唯一标识'"
                ),
                "article_url": (
                    "ALTER TABLE rumors "
                    "ADD COLUMN article_url VARCHAR(500) NULL COMMENT '原始文章链接'"
                ),
                "publish_time": (
                    "ALTER TABLE rumors "
                    "ADD COLUMN publish_time DATETIME NULL COMMENT '原始文章发布时间'"
                ),
                "normalized_content": (
                    "ALTER TABLE rumors "
                    "ADD COLUMN normalized_content TEXT NULL COMMENT '标准化后的文本'"
                ),
                "merge_key_hash": (
                    "ALTER TABLE rumors "
                    "ADD COLUMN merge_key_hash VARCHAR(64) NULL COMMENT '归并键哈希'"
                ),
                "fact_signature": (
                    "ALTER TABLE rumors "
                    "ADD COLUMN fact_signature VARCHAR(255) NULL COMMENT '数字/时间等硬事实签名'"
                ),
                "upload_count": (
                    "ALTER TABLE rumors "
                    "ADD COLUMN upload_count INT NOT NULL DEFAULT 0 COMMENT '关联上传次数'"
                ),
                "latest_upload_time": (
                    "ALTER TABLE rumors "
                    "ADD COLUMN latest_upload_time DATETIME NULL COMMENT '最近一次上传时间'"
                ),
            },
            "user_upload_rumors": {
                "normalized_content": (
                    "ALTER TABLE user_upload_rumors "
                    "ADD COLUMN normalized_content TEXT NULL COMMENT '标准化后的上传文本'"
                ),
                "merge_key_hash": (
                    "ALTER TABLE user_upload_rumors "
                    "ADD COLUMN merge_key_hash VARCHAR(64) NULL COMMENT '归并键哈希'"
                ),
                "fact_signature": (
                    "ALTER TABLE user_upload_rumors "
                    "ADD COLUMN fact_signature VARCHAR(255) NULL COMMENT '硬事实签名'"
                ),
                "candidate_rumor_id": (
                    "ALTER TABLE user_upload_rumors "
                    "ADD COLUMN candidate_rumor_id INT NULL COMMENT '建议归并的候选主谣言ID'"
                ),
                "predicted_label": (
                    "ALTER TABLE user_upload_rumors "
                    "ADD COLUMN predicted_label INT NULL COMMENT '本次识别预测标签'"
                ),
                "rumor_probability": (
                    "ALTER TABLE user_upload_rumors "
                    "ADD COLUMN rumor_probability FLOAT NULL COMMENT '本次识别谣言概率'"
                ),
                "base_model_probability": (
                    "ALTER TABLE user_upload_rumors "
                    "ADD COLUMN base_model_probability FLOAT NULL COMMENT '基础模型谣言概率'"
                ),
                "event_match_probability": (
                    "ALTER TABLE user_upload_rumors "
                    "ADD COLUMN event_match_probability FLOAT NULL COMMENT '主谣言匹配概率'"
                ),
                "result_risk_level": (
                    "ALTER TABLE user_upload_rumors "
                    "ADD COLUMN result_risk_level VARCHAR(16) NULL COMMENT '风险等级'"
                ),
                "result_verdict": (
                    "ALTER TABLE user_upload_rumors "
                    "ADD COLUMN result_verdict VARCHAR(120) NULL COMMENT '结果结论文案'"
                ),
                "related_rumors_json": (
                    "ALTER TABLE user_upload_rumors "
                    "ADD COLUMN related_rumors_json TEXT NULL COMMENT '候选主谣言快照JSON'"
                ),
                "merge_strategy": (
                    "ALTER TABLE user_upload_rumors "
                    "ADD COLUMN merge_strategy VARCHAR(32) NULL COMMENT '归并策略'"
                ),
                "merge_confidence": (
                    "ALTER TABLE user_upload_rumors "
                    "ADD COLUMN merge_confidence FLOAT NULL COMMENT '归并置信度'"
                ),
                "merge_reason": (
                    "ALTER TABLE user_upload_rumors "
                    "ADD COLUMN merge_reason VARCHAR(255) NULL COMMENT '归并说明'"
                ),
            },
        }

    return {
        "rumors": {
            "title": "ALTER TABLE rumors ADD COLUMN title VARCHAR(300)",
            "claim_text": "ALTER TABLE rumors ADD COLUMN claim_text TEXT",
            "truth_text": "ALTER TABLE rumors ADD COLUMN truth_text TEXT",
            "raw_content": "ALTER TABLE rumors ADD COLUMN raw_content TEXT",
            "source_name": "ALTER TABLE rumors ADD COLUMN source_name VARCHAR(255)",
            "article_id": "ALTER TABLE rumors ADD COLUMN article_id VARCHAR(64)",
            "article_url": "ALTER TABLE rumors ADD COLUMN article_url VARCHAR(500)",
            "publish_time": "ALTER TABLE rumors ADD COLUMN publish_time DATETIME",
            "normalized_content": "ALTER TABLE rumors ADD COLUMN normalized_content TEXT",
            "merge_key_hash": "ALTER TABLE rumors ADD COLUMN merge_key_hash VARCHAR(64)",
            "fact_signature": "ALTER TABLE rumors ADD COLUMN fact_signature VARCHAR(255)",
            "upload_count": "ALTER TABLE rumors ADD COLUMN upload_count INTEGER NOT NULL DEFAULT 0",
            "latest_upload_time": "ALTER TABLE rumors ADD COLUMN latest_upload_time DATETIME",
        },
        "user_upload_rumors": {
            "normalized_content": "ALTER TABLE user_upload_rumors ADD COLUMN normalized_content TEXT",
            "merge_key_hash": "ALTER TABLE user_upload_rumors ADD COLUMN merge_key_hash VARCHAR(64)",
            "fact_signature": "ALTER TABLE user_upload_rumors ADD COLUMN fact_signature VARCHAR(255)",
            "candidate_rumor_id": "ALTER TABLE user_upload_rumors ADD COLUMN candidate_rumor_id INTEGER",
            "predicted_label": "ALTER TABLE user_upload_rumors ADD COLUMN predicted_label INTEGER",
            "rumor_probability": "ALTER TABLE user_upload_rumors ADD COLUMN rumor_probability FLOAT",
            "base_model_probability": "ALTER TABLE user_upload_rumors ADD COLUMN base_model_probability FLOAT",
            "event_match_probability": "ALTER TABLE user_upload_rumors ADD COLUMN event_match_probability FLOAT",
            "result_risk_level": "ALTER TABLE user_upload_rumors ADD COLUMN result_risk_level VARCHAR(16)",
            "result_verdict": "ALTER TABLE user_upload_rumors ADD COLUMN result_verdict VARCHAR(120)",
            "related_rumors_json": "ALTER TABLE user_upload_rumors ADD COLUMN related_rumors_json TEXT",
            "merge_strategy": "ALTER TABLE user_upload_rumors ADD COLUMN merge_strategy VARCHAR(32)",
            "merge_confidence": "ALTER TABLE user_upload_rumors ADD COLUMN merge_confidence FLOAT",
            "merge_reason": "ALTER TABLE user_upload_rumors ADD COLUMN merge_reason VARCHAR(255)",
        },
    }


def _index_statements(dialect_name: str) -> dict[str, dict[str, str]]:
    rumors_indexes = {
        "idx_rumors_title": "CREATE INDEX idx_rumors_title ON rumors (title)",
        "idx_rumors_merge_key_hash": "CREATE INDEX idx_rumors_merge_key_hash ON rumors (merge_key_hash)",
        "idx_rumors_fact_signature": "CREATE INDEX idx_rumors_fact_signature ON rumors (fact_signature)",
        "idx_rumors_source_name": "CREATE INDEX idx_rumors_source_name ON rumors (source_name)",
        "idx_rumors_article_id": "CREATE INDEX idx_rumors_article_id ON rumors (article_id)",
        "idx_rumors_publish_time": "CREATE INDEX idx_rumors_publish_time ON rumors (publish_time)",
    }
    if dialect_name == "mysql":
        rumors_indexes["idx_rumors_article_url"] = (
            "CREATE INDEX idx_rumors_article_url ON rumors (article_url(255))"
        )
    else:
        rumors_indexes["idx_rumors_article_url"] = (
            "CREATE INDEX idx_rumors_article_url ON rumors (article_url)"
        )

    return {
        "rumors": rumors_indexes,
        "user_upload_rumors": {
            "idx_user_upload_rumors_merge_key_hash": (
                "CREATE INDEX idx_user_upload_rumors_merge_key_hash ON user_upload_rumors (merge_key_hash)"
            ),
            "idx_user_upload_rumors_candidate_rumor_id": (
                "CREATE INDEX idx_user_upload_rumors_candidate_rumor_id "
                "ON user_upload_rumors (candidate_rumor_id)"
            ),
        },
    }


def _ensure_runtime_schema(bind_engine) -> None:
    dialect_name = bind_engine.dialect.name
    column_statements = _column_statements(dialect_name)
    index_statements = _index_statements(dialect_name)

    with bind_engine.begin() as connection:
        inspector = inspect(connection)

        for table_name, statements in column_statements.items():
            if not inspector.has_table(table_name):
                continue

            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, ddl in statements.items():
                if column_name not in existing_columns:
                    connection.execute(text(ddl))

            refreshed_inspector = inspect(connection)
            existing_indexes = {index["name"] for index in refreshed_inspector.get_indexes(table_name)}
            for index_name, ddl in index_statements.get(table_name, {}).items():
                if index_name not in existing_indexes:
                    connection.execute(text(ddl))


def _backfill_merge_metadata(session_factory) -> None:
    from src.models._init_database import Rumor, UserUploadRumor
    from src.utils.rumor_merge import build_rumor_merge_features

    session = session_factory()
    try:
        uploads_needing_backfill = (
            session.query(UserUploadRumor)
            .filter(
                or_(
                    UserUploadRumor.normalized_content.is_(None),
                    UserUploadRumor.merge_key_hash.is_(None),
                    UserUploadRumor.fact_signature.is_(None),
                    UserUploadRumor.merge_strategy.is_(None),
                )
            )
            .all()
        )

        for upload_record in uploads_needing_backfill:
            features = build_rumor_merge_features(upload_record.upload_content or "")
            upload_record.normalized_content = features.normalized_text
            upload_record.merge_key_hash = features.merge_key_hash
            upload_record.fact_signature = features.fact_signature
            if upload_record.merge_strategy is None:
                if upload_record.merged_rumor_id is not None:
                    upload_record.merge_strategy = "legacy_link"
                    upload_record.merge_confidence = upload_record.merge_confidence or 1.0
                    upload_record.merge_reason = upload_record.merge_reason or "历史数据回填到已合并记录"
                else:
                    upload_record.merge_strategy = "legacy_pending"
                    upload_record.merge_reason = upload_record.merge_reason or "历史数据回填到待合并记录"

        upload_stats_rows = (
            session.query(
                UserUploadRumor.merged_rumor_id,
                func.count(UserUploadRumor.upload_id),
                func.max(UserUploadRumor.upload_time),
            )
            .filter(UserUploadRumor.merged_rumor_id.is_not(None))
            .group_by(UserUploadRumor.merged_rumor_id)
            .all()
        )
        upload_stats = {
            rumor_id: {"count": count, "latest_upload_time": latest_upload_time}
            for rumor_id, count, latest_upload_time in upload_stats_rows
        }

        rumors_needing_backfill = (
            session.query(Rumor)
            .filter(
                or_(
                    Rumor.normalized_content.is_(None),
                    Rumor.merge_key_hash.is_(None),
                    Rumor.fact_signature.is_(None),
                )
            )
            .all()
        )

        rumors_to_visit = {rumor.rumor_id: rumor for rumor in rumors_needing_backfill}
        if upload_stats:
            linked_rumors = (
                session.query(Rumor)
                .filter(Rumor.rumor_id.in_(upload_stats.keys()))
                .all()
            )
            for rumor in linked_rumors:
                rumors_to_visit[rumor.rumor_id] = rumor

        for rumor in rumors_to_visit.values():
            features = build_rumor_merge_features(rumor.content or "")
            rumor.normalized_content = features.normalized_text
            rumor.merge_key_hash = features.merge_key_hash
            rumor.fact_signature = features.fact_signature

            derived_stats = upload_stats.get(rumor.rumor_id)
            if derived_stats is not None:
                rumor.upload_count = int(derived_stats["count"] or 0)
                rumor.latest_upload_time = derived_stats["latest_upload_time"]
            elif rumor.source_type == "user" and not rumor.upload_count:
                rumor.upload_count = 1

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _initialize_database(bind_engine, session_factory) -> None:
    from src.models._init_database import Base as ModelBase

    ModelBase.metadata.create_all(bind=bind_engine)
    _ensure_runtime_schema(bind_engine)
    _backfill_merge_metadata(session_factory)


def initialize_database():
    _initialize_database(engine, SessionLocal)


def initialize_database_for_url(database_url: str) -> None:
    bind_engine = create_engine_for_url(database_url)
    session_factory = create_session_factory(bind_engine)
    try:
        _initialize_database(bind_engine, session_factory)
    finally:
        bind_engine.dispose()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
