# _delete_all.py
from src.utils.db import engine
from sqlalchemy import inspect

# 一键清空所有表
def delete_all_tables():
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    with engine.connect() as conn:
        # 关闭外键约束（防止删不掉）
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 0")

        for table in tables:
            conn.exec_driver_sql(f"DROP TABLE {table}")
            print(f"🗑️ 已删除：{table}")

        # 恢复外键约束
        conn.exec_driver_sql("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()

    print("\n✅ 所有表已全部删除！")


delete_all_tables()