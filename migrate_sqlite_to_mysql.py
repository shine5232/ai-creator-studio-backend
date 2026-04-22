"""
Migrate all data from SQLite (data/openclaw.db) to MySQL (aigc database).

Uses raw SQL only: sqlite3 for reading, pymysql for writing.
Disables foreign key checks during migration to handle insertion order.
"""

import re
import sqlite3
import pymysql
from datetime import datetime


def normalize_datetime(value):
    """Convert SQLite datetime strings (ISO 8601 with timezone) to MySQL-compatible format."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    # Match ISO 8601 patterns like: 2026-04-19T12:41:38.566149+00:00 or 2026-04-19T12:41:38+00:00
    iso_pattern = r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(?:\.\d+)?(?:[+-]\d{2}:\d{2}|Z)$"
    m = re.match(iso_pattern, value)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return value

# --- Configuration ---
SQLITE_PATH = "data/openclaw.db"
MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_USER = "admin"
MYSQL_PASS = "zhsh1219"
MYSQL_DB = "aigc"

# Insertion order based on foreign key dependency graph:
# Root tables (no FK deps) -> tables that depend on them -> leaf tables
INSERTION_ORDER = [
    "alembic_version",
    "users",
    "ai_providers",
    "user_quotas",           # -> users
    "social_accounts",       # -> users
    "ai_models",             # -> ai_providers
    "api_keys",              # -> ai_providers
    "projects",              # -> users
    "kb_cases",              # -> users
    "kb_elements",
    "kb_frameworks",
    "workflow_steps",        # -> projects
    "scripts",               # -> projects
    "characters",            # -> projects
    "kb_script_templates",   # -> kb_cases, users
    "storyboards",           # -> scripts
    "character_periods",     # -> characters
    "shots",                 # -> storyboards
    "assets",                # -> shots, projects
    "generation_costs",      # -> shots, users, projects
    "publish_records",       # -> assets, social_accounts, projects
    "content_analytics",     # -> publish_records, projects
]


def main():
    # Connect to SQLite
    lite_conn = sqlite3.connect(SQLITE_PATH)
    lite_conn.row_factory = sqlite3.Row
    lite_cur = lite_conn.cursor()

    # Connect to MySQL
    my_conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASS,
        database=MYSQL_DB,
        charset="utf8mb4",
        autocommit=False,
    )
    my_cur = my_conn.cursor()

    # Disable foreign key checks
    my_cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
    my_conn.commit()

    total_tables = 0
    total_rows = 0

    for table_name in INSERTION_ORDER:
        # --- Read from SQLite ---
        lite_cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        row_count = lite_cur.fetchone()[0]

        if row_count == 0:
            print(f"[SKIP] {table_name}: 0 rows (empty)")
            total_tables += 1
            continue

        lite_cur.execute(f'SELECT * FROM "{table_name}"')
        rows = lite_cur.fetchall()
        columns = [desc[0] for desc in lite_cur.description]

        # --- Clear existing MySQL data for this table (if any) ---
        my_cur.execute(f"DELETE FROM `{table_name}`")

        # --- Build INSERT statement ---
        col_list = ", ".join(f"`{c}`" for c in columns)
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO `{table_name}` ({col_list}) VALUES ({placeholders})"

        # --- Convert rows to list of tuples, normalizing datetime strings ---
        data = []
        for row in rows:
            converted = tuple(normalize_datetime(v) for v in row)
            data.append(converted)

        # --- Batch insert into MySQL ---
        batch_size = 500
        inserted = 0
        for i in range(0, len(data), batch_size):
            batch = data[i : i + batch_size]
            my_cur.executemany(insert_sql, batch)
            inserted += len(batch)

        my_conn.commit()
        total_tables += 1
        total_rows += inserted
        print(f"[OK]   {table_name}: {inserted} rows migrated")

    # Re-enable foreign key checks
    my_cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
    my_conn.commit()

    # --- Summary ---
    print("\n" + "=" * 50)
    print(f"Migration complete: {total_tables} tables, {total_rows} total rows")

    # --- Verify row counts ---
    print("\nVerification (SQLite vs MySQL row counts):")
    mismatches = 0
    for table_name in INSERTION_ORDER:
        lite_cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        sqlite_count = lite_cur.fetchone()[0]

        my_cur.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        mysql_count = my_cur.fetchone()[0]

        status = "MATCH" if sqlite_count == mysql_count else "MISMATCH"
        if sqlite_count != mysql_count:
            mismatches += 1
        if sqlite_count > 0 or mysql_count > 0:
            print(f"  {table_name}: SQLite={sqlite_count}, MySQL={mysql_count} [{status}]")

    if mismatches == 0:
        print("\nAll row counts match!")
    else:
        print(f"\nWARNING: {mismatches} table(s) have mismatched row counts!")

    # Cleanup
    lite_cur.close()
    lite_conn.close()
    my_cur.close()
    my_conn.close()


if __name__ == "__main__":
    main()
