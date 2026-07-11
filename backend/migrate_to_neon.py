"""
Migrate data from local SQLite (ethara_seats.db) to Neon PostgreSQL.
Run from the backend/ directory:
    python3 migrate_to_neon.py

Strategy:
- Insert tables in FK-safe dependency order (no need to disable FK checks)
- Use DEFERRABLE constraints approach for circular refs if any
- Batch inserts for performance
"""
import os
import sys

NEON_URL = "postgresql://neondb_owner:npg_9ldMm0UWFnks@ep-wandering-dream-aoynlys3.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
SQLITE_URL = "sqlite:///./ethara_seats.db"

sys.path.insert(0, ".")
os.environ["DATABASE_URL"] = NEON_URL

from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import Base
from app.models.employee import Employee  # noqa
from app.models.project import Project  # noqa
from app.models.seat import Seat  # noqa
from app.models.seat_allocation import SeatAllocation  # noqa
from app.models.user import User  # noqa
from app.models.chat_message import ChatMessage  # noqa

# ── engines ───────────────────────────────────────────────────────────────────
neon_engine = create_engine(NEON_URL, pool_pre_ping=True)
sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

# ── Step 1: Create schema ─────────────────────────────────────────────────────
print("Step 1: Creating schema on Neon...")
Base.metadata.create_all(bind=neon_engine)

sqlite_meta = MetaData()
sqlite_meta.reflect(bind=sqlite_engine)

neon_meta = MetaData()
neon_meta.reflect(bind=neon_engine)
print(f"  Tables: {list(neon_meta.tables.keys())}")

# ── Step 2: Migrate in FK-safe order ─────────────────────────────────────────
# Dependency order (parents before children):
#   users        (no FK)
#   projects     (no FK)
#   employees    -> projects
#   seats        (no FK or -> projects)
#   seat_allocations -> employees, seats
#   chat_messages (no FK)

TABLE_ORDER = [
    "users",
    "projects",
    "employees",
    "seats",
    "seat_allocations",
    "chat_messages",
]

BATCH = 500

print("\nStep 2: Migrating data...")

for table_name in TABLE_ORDER:
    if table_name not in sqlite_meta.tables:
        print(f"  {table_name}: not in SQLite, skipping.")
        continue

    src = sqlite_meta.tables[table_name]
    dst = neon_meta.tables[table_name]

    # Read all rows from SQLite
    with sqlite_engine.connect() as src_conn:
        rows = [dict(r) for r in src_conn.execute(src.select()).mappings().all()]

    total = len(rows)
    print(f"  {table_name}: {total} rows...", end=" ", flush=True)

    with neon_engine.begin() as dst_conn:
        # Truncate destination (CASCADE handles child tables we'll refill anyway)
        dst_conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"))

        # Insert in batches
        for i in range(0, total, BATCH):
            batch = rows[i : i + BATCH]
            if batch:
                dst_conn.execute(dst.insert(), batch)

    print("done.")

# ── Step 3: Verify ────────────────────────────────────────────────────────────
print("\nStep 3: Verifying row counts on Neon...")
with neon_engine.connect() as conn:
    for table_name in TABLE_ORDER:
        if table_name in neon_meta.tables:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            print(f"  {table_name}: {count}")

print("\nMigration complete!")
