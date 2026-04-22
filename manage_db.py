import argparse
import socket
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import MetaData, delete, inspect, select, text

from src.utils import db as db_utils


SYNC_TABLES = [
    "users",
    "rumors",
    "user_upload_rumors",
    "rumor_similarities",
]


def _probe_database_host(database_url: str, timeout: float = 3.0) -> tuple[bool, str]:
    parts = urlsplit(database_url)
    if parts.scheme.startswith("sqlite"):
        return True, ""

    if not parts.hostname:
        return False, "remote database url is missing a hostname"

    port = parts.port or 3306
    try:
        with socket.create_connection((parts.hostname, port), timeout=timeout):
            return True, ""
    except OSError as exc:
        return False, str(exc)


def _print_status() -> None:
    runtime_info = db_utils.get_database_runtime_info()
    local_sqlite_path = runtime_info["local_sqlite_path"]
    remote_database_url = runtime_info["remote_database_url"]

    print(f"configured_target: {runtime_info['configured_target']}")
    print(f"effective_target: {runtime_info['effective_target']}")
    print(f"runtime_config: {runtime_info['runtime_config_path']}")
    print(f"local_sqlite_path: {local_sqlite_path}")
    print(f"local_sqlite_exists: {Path(local_sqlite_path).exists()}")
    print(f"effective_database_url: {db_utils.mask_database_url(runtime_info['effective_database_url'])}")
    print(
        "remote_database_url: "
        f"{db_utils.mask_database_url(remote_database_url) if remote_database_url else '<not configured>'}"
    )


def _init_local_database(local_database_url: str) -> None:
    db_utils.initialize_database_for_url(local_database_url)


def command_status(_args) -> int:
    _print_status()
    return 0


def command_init_local(args) -> int:
    runtime_info = db_utils.write_database_runtime_config(local_sqlite_path=args.local_path) if args.local_path else db_utils.read_database_runtime_config()
    _init_local_database(runtime_info["local_database_url"])
    print(f"local SQLite initialized: {runtime_info['local_sqlite_path']}")
    return 0


def command_use_local(args) -> int:
    runtime_info = db_utils.write_database_runtime_config(target="local", local_sqlite_path=args.local_path)
    _init_local_database(runtime_info["local_database_url"])
    print(f"active database target switched to local")
    print(f"local SQLite path: {runtime_info['local_sqlite_path']}")
    return 0


def command_use_remote(_args) -> int:
    runtime_info = db_utils.write_database_runtime_config(target="remote")
    print("active database target switched to remote")
    print(
        "remote database url: "
        f"{db_utils.mask_database_url(runtime_info['remote_database_url']) if runtime_info['remote_database_url'] else '<not configured>'}"
    )
    return 0


def command_sync_local(args) -> int:
    runtime_info = db_utils.write_database_runtime_config(local_sqlite_path=args.local_path) if args.local_path else db_utils.read_database_runtime_config()
    local_database_url = runtime_info["local_database_url"]
    remote_database_url = runtime_info["remote_database_url"]

    if not remote_database_url:
        print("remote database url is not configured")
        return 1

    host_reachable, host_error = _probe_database_host(remote_database_url)
    if not host_reachable:
        print(f"remote database host is unreachable: {host_error}")
        return 1

    _init_local_database(local_database_url)

    remote_engine = db_utils.create_engine_for_url(remote_database_url)
    local_engine = db_utils.create_engine_for_url(local_database_url)

    try:
        remote_inspector = inspect(remote_engine)
        local_inspector = inspect(local_engine)
        tables_to_sync = [
            table_name
            for table_name in SYNC_TABLES
            if remote_inspector.has_table(table_name) and local_inspector.has_table(table_name)
        ]

        if not tables_to_sync:
            print("no common tables were found between remote and local databases")
            return 1

        remote_metadata = MetaData()
        local_metadata = MetaData()
        remote_metadata.reflect(bind=remote_engine, only=tables_to_sync)
        local_metadata.reflect(bind=local_engine, only=tables_to_sync)

        summary: list[tuple[str, int]] = []
        with remote_engine.connect() as remote_conn, local_engine.begin() as local_conn:
            if local_engine.dialect.name == "sqlite":
                local_conn.execute(text("PRAGMA foreign_keys = OFF"))

            for table_name in reversed(tables_to_sync):
                local_conn.execute(delete(local_metadata.tables[table_name]))

            for table_name in tables_to_sync:
                remote_table = remote_metadata.tables[table_name]
                local_table = local_metadata.tables[table_name]
                common_columns = [column_name for column_name in local_table.columns.keys() if column_name in remote_table.columns.keys()]
                rows = remote_conn.execute(
                    select(*(remote_table.c[column_name] for column_name in common_columns))
                ).mappings().all()

                payload = [{column_name: row[column_name] for column_name in common_columns} for row in rows]
                if payload:
                    local_conn.execute(local_table.insert(), payload)
                summary.append((table_name, len(payload)))

            if local_engine.dialect.name == "sqlite":
                local_conn.execute(text("PRAGMA foreign_keys = ON"))

        db_utils.initialize_database_for_url(local_database_url)

        print(f"local SQLite synced: {runtime_info['local_sqlite_path']}")
        for table_name, row_count in summary:
            print(f"{table_name}: {row_count} rows")
        return 0
    except Exception as exc:
        print(f"sync failed: {type(exc).__name__}: {exc}")
        return 1
    finally:
        remote_engine.dispose()
        local_engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage remote/local database switching for this project.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Show the current database target and paths.")
    status_parser.set_defaults(func=command_status)

    init_local_parser = subparsers.add_parser("init-local", help="Create or repair the local SQLite schema.")
    init_local_parser.add_argument("--local-path", help="Custom SQLite file path.")
    init_local_parser.set_defaults(func=command_init_local)

    use_local_parser = subparsers.add_parser("use-local", help="Switch runtime database target to local SQLite.")
    use_local_parser.add_argument("--local-path", help="Custom SQLite file path.")
    use_local_parser.set_defaults(func=command_use_local)

    use_remote_parser = subparsers.add_parser("use-remote", help="Switch runtime database target to remote MySQL.")
    use_remote_parser.set_defaults(func=command_use_remote)

    sync_local_parser = subparsers.add_parser(
        "sync-local",
        help="Copy remote MySQL data into the local SQLite database.",
    )
    sync_local_parser.add_argument("--local-path", help="Custom SQLite file path.")
    sync_local_parser.set_defaults(func=command_sync_local)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
