"""
Seed the Data Catalog with empty data sources pointing to the local data folders
and database connections.

Run: python scripts/seed_catalog.py
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import async_session, init_db
from app.services.catalog_service import catalog_service


async def seed():
    await init_db()

    async with async_session() as db:
        print("Seeding Data Catalog with base sources...")

        # Clear existing sources first (optional, but good for reset)
        existing = await catalog_service.list_sources(db)
        for src in existing:
            await catalog_service.delete_source(db, src["id"])

        # 1. CSV Source
        csv_source = await catalog_service.create_source(
            db,
            name="CSV Data Folder",
            source_type="csv",
            connection_config={"base_path": "data/csv/"},
            description="Local folder for CSV datasets",
            created_by="system",
        )
        print(f"  - Source: {csv_source['name']}")

        # 2. JSON Source
        json_source = await catalog_service.create_source(
            db,
            name="JSON Data Folder",
            source_type="json",
            connection_config={"base_path": "data/json/"},
            description="Local folder for JSON datasets",
            created_by="system",
        )
        print(f"  - Source: {json_source['name']}")

        # 3. Excel Source
        excel_source = await catalog_service.create_source(
            db,
            name="Excel Data Folder",
            source_type="excel",
            connection_config={"base_path": "data/excel/"},
            description="Local folder for Excel datasets",
            created_by="system",
        )
        print(f"  - Source: {excel_source['name']}")

        # 4. SQL Database
        sql_source = await catalog_service.create_source(
            db,
            name="Local SQL Database",
            source_type="sql",
            connection_config={
                "driver": "sqlite",
                "database": "data/sql/database.sqlite",
            },
            description="Local SQL database (update connection in UI as needed)",
            created_by="system",
        )
        print(f"  - Source: {sql_source['name']}")

        # 5. MongoDB Database
        mongo_source = await catalog_service.create_source(
            db,
            name="MongoDB Cluster",
            source_type="mongodb",
            connection_config={
                "uri": "mongodb://localhost:27017",
                "database": "default_db",
            },
            description="MongoDB connection (update connection in UI as needed)",
            created_by="system",
        )
        print(f"  - Source: {mongo_source['name']}")

        print("\n[SUCCESS] Catalog seeding complete!")
        print(f"   Sources: {len(await catalog_service.list_sources(db))}")
        print("   Place your files in data/csv, data/json, data/excel to start working.")


if __name__ == "__main__":
    asyncio.run(seed())
