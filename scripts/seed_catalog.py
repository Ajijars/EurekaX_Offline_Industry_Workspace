"""
Seed the Data Catalog with sample data sources and catalog entries
representing a mock enterprise "GlobalTech Retail".

Run: python scripts/seed_catalog.py
"""

import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import async_session, init_db
from app.services.catalog_service import catalog_service


async def seed():
    await init_db()

    async with async_session() as db:

        # ─── Check if already seeded ───
        existing = await catalog_service.list_sources(db)
        if len(existing) >= 3:
            print(f"[SKIP] Catalog already has {len(existing)} sources. Delete data/eurekax.db to re-seed.")
            return

        print("Seeding Data Catalog for GlobalTech Retail...")

        # ══════════════════════════════════════════
        # SOURCE 1: Local CSV Files
        # ══════════════════════════════════════════
        csv_source = await catalog_service.create_source(
            db,
            name="GlobalTech CSV Files",
            source_type="csv",
            connection_config={"base_path": "data/samples/"},
            description="Local CSV datasets — employee records, sales transactions",
            created_by="system",
        )
        print(f"  ✓ Source: {csv_source['name']} ({csv_source['id']})")

        # Entry: employees.csv
        await catalog_service.add_entry(
            db,
            data_source_id=csv_source["id"],
            table_name="employees",
            schema_json=[
                {"name": "employee_id", "type": "VARCHAR", "nullable": False},
                {"name": "first_name", "type": "VARCHAR", "nullable": False},
                {"name": "last_name", "type": "VARCHAR", "nullable": False},
                {"name": "department", "type": "VARCHAR", "nullable": False},
                {"name": "salary", "type": "INTEGER", "nullable": False},
                {"name": "hire_date", "type": "DATE", "nullable": False},
            ],
            description="HR employee master data — names, departments, salaries, hire dates. Contains PII.",
            tags="HR,PII,employees,sensitive",
            updated_by="system",
        )
        print("    ✓ Catalog Entry: employees")

        # Entry: sales_transactions.csv
        await catalog_service.add_entry(
            db,
            data_source_id=csv_source["id"],
            table_name="sales_transactions",
            schema_json=[
                {"name": "transaction_id", "type": "VARCHAR", "nullable": False},
                {"name": "date", "type": "TIMESTAMP", "nullable": False},
                {"name": "store_id", "type": "VARCHAR", "nullable": False},
                {"name": "amount", "type": "DECIMAL(10,2)", "nullable": False},
                {"name": "customer_segment", "type": "VARCHAR", "nullable": True},
            ],
            description="Point-of-sale retail transactions across all stores and online channel.",
            tags="Retail,Sales,Revenue,Transactions",
            updated_by="system",
        )
        print("    ✓ Catalog Entry: sales_transactions")

        # ══════════════════════════════════════════
        # SOURCE 2: Excel Financial Reports
        # ══════════════════════════════════════════
        excel_source = await catalog_service.create_source(
            db,
            name="GlobalTech Financial Reports",
            source_type="excel",
            connection_config={"base_path": "data/samples/"},
            description="Quarterly financial reports — revenue, expenses, balance sheet data",
            created_by="system",
        )
        print(f"  ✓ Source: {excel_source['name']} ({excel_source['id']})")

        # Entry: q3_financials
        await catalog_service.add_entry(
            db,
            data_source_id=excel_source["id"],
            table_name="q3_financials",
            schema_json=[
                {"name": "Category", "type": "VARCHAR", "nullable": False},
                {"name": "July_2023", "type": "INTEGER", "nullable": False},
                {"name": "August_2023", "type": "INTEGER", "nullable": False},
                {"name": "September_2023", "type": "INTEGER", "nullable": False},
                {"name": "Q3_Total", "type": "INTEGER", "nullable": False},
            ],
            description="Q3 2023 financial summary — Software, Hardware, Consulting, Server, Marketing, Payroll.",
            tags="Finance,Quarterly,Confidential,Revenue",
            updated_by="system",
        )
        print("    ✓ Catalog Entry: q3_financials")

        # ══════════════════════════════════════════
        # SOURCE 3: SQL Warehouse (mock)
        # ══════════════════════════════════════════
        sql_source = await catalog_service.create_source(
            db,
            name="GlobalTech SQL Warehouse",
            source_type="sql",
            connection_config={
                "host": "db.globaltech-internal.com",
                "port": 5432,
                "database": "globaltech_prod",
                "driver": "postgresql",
            },
            description="Primary PostgreSQL data warehouse — inventory, orders, products",
            created_by="system",
        )
        print(f"  ✓ Source: {sql_source['name']} ({sql_source['id']})")

        # Entry: inventory_master
        await catalog_service.add_entry(
            db,
            data_source_id=sql_source["id"],
            table_name="inventory_master",
            schema_json=[
                {"name": "sku", "type": "VARCHAR(50)", "nullable": False},
                {"name": "product_name", "type": "VARCHAR(255)", "nullable": False},
                {"name": "category", "type": "VARCHAR(100)", "nullable": True},
                {"name": "unit_price", "type": "DECIMAL(10,2)", "nullable": False},
                {"name": "quantity_in_stock", "type": "INTEGER", "nullable": False},
                {"name": "warehouse_location", "type": "VARCHAR(50)", "nullable": True},
                {"name": "last_restocked", "type": "TIMESTAMP", "nullable": True},
            ],
            description="Product inventory across all warehouse locations. Updated nightly via ETL pipeline.",
            tags="Inventory,Products,Warehouse,ETL",
            updated_by="system",
        )
        print("    ✓ Catalog Entry: inventory_master")

        # Entry: orders
        await catalog_service.add_entry(
            db,
            data_source_id=sql_source["id"],
            table_name="orders",
            schema_json=[
                {"name": "order_id", "type": "BIGINT", "nullable": False},
                {"name": "customer_id", "type": "INTEGER", "nullable": False},
                {"name": "order_date", "type": "TIMESTAMP", "nullable": False},
                {"name": "total_amount", "type": "DECIMAL(12,2)", "nullable": False},
                {"name": "status", "type": "VARCHAR(20)", "nullable": False},
                {"name": "shipping_address", "type": "TEXT", "nullable": True},
                {"name": "payment_method", "type": "VARCHAR(30)", "nullable": True},
            ],
            description="All customer orders — includes billing, shipping, and payment details. Contains PII.",
            tags="Orders,Retail,PII,Customers",
            updated_by="system",
        )
        print("    ✓ Catalog Entry: orders")

        # ══════════════════════════════════════════
        # SOURCE 4: MongoDB (mock)
        # ══════════════════════════════════════════
        mongo_source = await catalog_service.create_source(
            db,
            name="GlobalTech MongoDB Cluster",
            source_type="mongodb",
            connection_config={
                "uri": "mongodb+srv://readonly:****@cluster0.globaltech.mongodb.net",
                "database": "globaltech_analytics",
            },
            description="NoSQL analytics cluster — customer profiles, clickstream, reviews",
            created_by="system",
        )
        print(f"  ✓ Source: {mongo_source['name']} ({mongo_source['id']})")

        # Entry: customer_profiles
        await catalog_service.add_entry(
            db,
            data_source_id=mongo_source["id"],
            table_name="customer_profiles",
            schema_json=[
                {"name": "_id", "type": "ObjectId", "nullable": False},
                {"name": "email", "type": "String", "nullable": False},
                {"name": "name", "type": "String", "nullable": False},
                {"name": "segment", "type": "String", "nullable": True},
                {"name": "lifetime_value", "type": "Number", "nullable": True},
                {"name": "preferences", "type": "Object", "nullable": True},
                {"name": "last_login", "type": "Date", "nullable": True},
            ],
            description="Customer profile documents with behavioral data and preferences. PII-heavy.",
            tags="Customers,PII,MongoDB,Analytics",
            updated_by="system",
        )
        print("    ✓ Catalog Entry: customer_profiles")

        # Entry: product_reviews
        await catalog_service.add_entry(
            db,
            data_source_id=mongo_source["id"],
            table_name="product_reviews",
            schema_json=[
                {"name": "_id", "type": "ObjectId", "nullable": False},
                {"name": "product_sku", "type": "String", "nullable": False},
                {"name": "rating", "type": "Number", "nullable": False},
                {"name": "review_text", "type": "String", "nullable": True},
                {"name": "reviewer_name", "type": "String", "nullable": True},
                {"name": "created_at", "type": "Date", "nullable": False},
            ],
            description="User-generated product reviews and star ratings.",
            tags="Reviews,Products,UGC,Analytics",
            updated_by="system",
        )
        print("    ✓ Catalog Entry: product_reviews")

        # ══════════════════════════════════════════
        # SOURCE 5: Image Store
        # ══════════════════════════════════════════
        img_source = await catalog_service.create_source(
            db,
            name="GlobalTech Product Images",
            source_type="image",
            connection_config={"base_path": "data/samples/images/"},
            description="Product catalog images — JPG format, organized by SKU",
            created_by="system",
        )
        print(f"  ✓ Source: {img_source['name']} ({img_source['id']})")

        await catalog_service.add_entry(
            db,
            data_source_id=img_source["id"],
            table_name="product_images",
            schema_json=[
                {"name": "filename", "type": "VARCHAR", "nullable": False},
                {"name": "format", "type": "VARCHAR(10)", "nullable": False},
                {"name": "dimensions", "type": "VARCHAR(20)", "nullable": False},
            ],
            description="Product photography assets — 200x200 JPG thumbnails for catalog display.",
            tags="Images,Products,Assets,Media",
            updated_by="system",
        )
        print("    ✓ Catalog Entry: product_images")

        # ══════════════════════════════════════════
        # SOURCE 6: Market Data (CSV)
        # ══════════════════════════════════════════
        market_source = await catalog_service.create_source(
            db,
            name="GlobalTech Market Data Feed",
            source_type="csv",
            connection_config={"base_path": "data/samples/"},
            description="External market data — stock prices, competitor benchmarks, industry KPIs",
            created_by="system",
        )
        print(f"  ✓ Source: {market_source['name']} ({market_source['id']})")

        await catalog_service.add_entry(
            db,
            data_source_id=market_source["id"],
            table_name="stock_prices",
            schema_json=[
                {"name": "date", "type": "DATE", "nullable": False},
                {"name": "ticker", "type": "VARCHAR(10)", "nullable": False},
                {"name": "open", "type": "DECIMAL(10,2)", "nullable": False},
                {"name": "high", "type": "DECIMAL(10,2)", "nullable": False},
                {"name": "low", "type": "DECIMAL(10,2)", "nullable": False},
                {"name": "close", "type": "DECIMAL(10,2)", "nullable": False},
                {"name": "volume", "type": "BIGINT", "nullable": False},
            ],
            description="Daily OHLCV stock data for GLTK and competitor tickers (sourced from Kaggle).",
            tags="Market,Stocks,Finance,External,Kaggle",
            updated_by="system",
        )
        print("    ✓ Catalog Entry: stock_prices")

        # ── Add lineage to show data flow ──
        entries = await catalog_service.list_entries(db)
        entry_map = {e["table_name"]: e["id"] for e in entries}

        # sales_transactions feeds into q3_financials
        if "sales_transactions" in entry_map and "q3_financials" in entry_map:
            await catalog_service.update_lineage(db, entry_map["q3_financials"], {
                "upstream": [
                    {"table": "sales_transactions", "source": "GlobalTech CSV Files", "type": "aggregation"},
                    {"table": "inventory_master", "source": "GlobalTech SQL Warehouse", "type": "join"},
                ],
                "downstream": [
                    {"table": "stock_prices", "source": "GlobalTech Market Data Feed", "type": "correlation"},
                ],
            })
            print("    ✓ Lineage: sales_transactions → q3_financials → stock_prices")

        # employees feeds into orders via join
        if "employees" in entry_map and "orders" in entry_map:
            await catalog_service.update_lineage(db, entry_map["orders"], {
                "upstream": [
                    {"table": "customer_profiles", "source": "GlobalTech MongoDB Cluster", "type": "lookup"},
                    {"table": "inventory_master", "source": "GlobalTech SQL Warehouse", "type": "join"},
                ],
                "downstream": [
                    {"table": "sales_transactions", "source": "GlobalTech CSV Files", "type": "export"},
                ],
            })
            print("    ✓ Lineage: customer_profiles + inventory → orders → sales_transactions")

        print("\n✅ Catalog seeding complete!")
        print(f"   Sources: {len(await catalog_service.list_sources(db))}")
        print(f"   Entries: {len(await catalog_service.list_entries(db))}")


if __name__ == "__main__":
    asyncio.run(seed())
