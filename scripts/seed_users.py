"""
Seed employee users and their dataset permissions.

Creates:
    1. Rahul Sharma (ML/DS Engineer) — access to employees, sales_transactions, stock_prices, customer_profiles
    2. Priya Patel (Finance Analyst) — access to q3_financials, sales_transactions, stock_prices, orders

Run: python -X utf8 scripts/seed_users.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from app.db.database import async_session, init_db
from app.db.models import User, Permission
from app.auth.security import hash_password
from app.services.catalog_service import catalog_service


EMPLOYEES = [
    {
        "email": "rahul.ds@globaltech.com",
        "username": "Rahul",
        "password": "Rahul@123",
        "role": "employee",
        "permitted_tables": ["employees", "sales_transactions", "stock_prices", "customer_profiles"],
    },
    {
        "email": "priya.fin@globaltech.com",
        "username": "Priya",
        "password": "Priya@123",
        "role": "employee",
        "permitted_tables": ["q3_financials", "sales_transactions", "stock_prices", "orders"],
    },
]


async def seed():
    await init_db()

    async with async_session() as db:
        # Get admin user (granter)
        admin_result = await db.execute(select(User).where(User.role == "admin"))
        admin = admin_result.scalar_one_or_none()
        admin_id = admin.id if admin else None

        # Get all catalog entries for mapping
        all_entries = await catalog_service.list_entries(db)
        entry_map = {e["table_name"]: e["id"] for e in all_entries}
        print(f"Found {len(entry_map)} catalog entries: {list(entry_map.keys())}")

        for emp in EMPLOYEES:
            # Check if user already exists
            existing = await db.execute(
                select(User).where(
                    (User.email == emp["email"]) | (User.username == emp["username"])
                )
            )
            user = existing.scalar_one_or_none()

            if user:
                print(f"[SKIP] User '{emp['username']}' already exists (id={user.id})")
            else:
                user = User(
                    email=emp["email"],
                    username=emp["username"],
                    hashed_password=hash_password(emp["password"]),
                    role=emp["role"],
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                print(f"[+] Created user: {user.username} ({user.email}) role={user.role} id={user.id}")

            # Grant permissions
            for table_name in emp["permitted_tables"]:
                entry_id = entry_map.get(table_name)
                if not entry_id:
                    print(f"  [!] Table '{table_name}' not found in catalog, skipping")
                    continue

                # Check if permission already exists
                perm_check = await db.execute(
                    select(Permission).where(
                        Permission.user_id == user.id,
                        Permission.resource_type == "catalog_entry",
                        Permission.resource_id == str(entry_id),
                    )
                )
                if perm_check.scalar_one_or_none():
                    print(f"  [SKIP] Permission for '{table_name}' already granted")
                    continue

                perm = Permission(
                    user_id=user.id,
                    resource_type="catalog_entry",
                    resource_id=str(entry_id),
                    access_level="read",
                    granted_by=admin_id,
                )
                db.add(perm)
                await db.commit()
                print(f"  [+] Granted access to '{table_name}' (entry_id={entry_id})")

        # Summary
        user_count = await db.execute(select(func.count(User.id)))
        perm_count = await db.execute(
            select(func.count(Permission.id)).where(Permission.resource_type == "catalog_entry")
        )
        print(f"\nDone! Users: {user_count.scalar()}, Dataset Permissions: {perm_count.scalar()}")


if __name__ == "__main__":
    asyncio.run(seed())
