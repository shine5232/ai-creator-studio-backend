"""Migrate data from SQLite to MySQL.

Usage:
1. Start MySQL service
2. Create empty database: CREATE DATABASE ai_creator_studio;
3. Run this script: python migrate_to_mysql.py
"""
import asyncio
import sys

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

# Import all models to ensure they're registered with SQLAlchemy
from app.models import (
    ai_gateway, analytics, asset, character, knowledge,
    project, publish, script, user
)
from app.models.base import Base


def copy_data(source_engine, target_engine):
    """Copy all data from source to target database."""
    source_session = sessionmaker(bind=source_engine)()
    target_session = sessionmaker(bind=target_engine)()

    try:
        # Get all table names
        tables = Base.metadata.tables.keys()

        for table_name in sorted(tables):
            table = Base.metadata.tables[table_name]

            # Check if table has data
            result = source_session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            print(f"  {table_name}: {count} records")

            if count == 0:
                continue

            # Copy data
            source_session.execute(text(f"SELECT * FROM {table_name}"))
            rows = source_session.fetchall()

            # Get column names
            columns = [col.name for col in table.columns]

            # Insert into target
            for row in rows:
                row_dict = dict(zip(columns, row))
                target_session.execute(table.insert().values(**row_dict))

            target_session.commit()
            print(f"    → Copied {len(rows)} records")

        print("\n✓ Migration completed successfully!")

    except Exception as e:
        target_session.rollback()
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)
    finally:
        source_session.close()
        target_session.close()


async def migrate():
    """Perform migration from SQLite to MySQL."""
    print("=== SQLite to MySQL Migration ===\n")

    # Source: SQLite
    sqlite_url = "sqlite:///./data/openclaw.db"
    print(f"Source: {sqlite_url}")
    source_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

    # Target: MySQL (update with your credentials)
    mysql_url = "mysql+pymysql://root:password@localhost:3306/ai_creator_studio"
    print(f"Target: {mysql_url}")
    target_engine = create_engine(mysql_url)

    # Create all tables in MySQL
    print("\nCreating tables in MySQL...")
    Base.metadata.create_all(target_engine)
    print("✓ Tables created\n")

    # Copy data
    print("Copying data:")
    copy_data(source_engine, target_engine)

    # Close engines
    source_engine.dispose()
    target_engine.dispose()

    print("\nNext steps:")
    print("1. Update .env file: DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/ai_creator_studio")
    print("2. Restart the application")
    print("3. Verify the migration")


if __name__ == "__main__":
    print("\n⚠️  Make sure MySQL is running and the database exists!")
    print("   CREATE DATABASE ai_creator_studio CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n")

    confirm = input("Continue with migration? (yes/no): ")
    if confirm.lower() == "yes":
        asyncio.run(migrate())
    else:
        print("Migration cancelled.")
