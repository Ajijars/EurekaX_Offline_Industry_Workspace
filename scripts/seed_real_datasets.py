import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import async_session
from app.services.catalog_service import catalog_service

async def seed():
    async with async_session() as db:
        print("Seeding Real Datasets...")

        # SOURCE 1: Real Datasets Folder
        existing_sources = await catalog_service.list_sources(db)
        existing_map = {s["name"]: s["id"] for s in existing_sources}
        
        if "Real World File Datasets" in existing_map:
            file_source_id = existing_map["Real World File Datasets"]
            await catalog_service.delete_source(db, file_source_id)
            print("  - Deleted existing Real World File Datasets source")
            
        file_source = await catalog_service.create_source(
            db,
            name="Real World File Datasets",
            source_type="csv",
            connection_config={"base_path": "data/real_datasets/"},
            description="California Housing, Products JSON, and Financial Excel",
            created_by="system",
        )
        file_source_id = file_source['id']
        print(f"  - Source: {file_source['name']} ({file_source_id})")

        # Entry: california_housing.csv
        await catalog_service.add_entry(
            db,
            data_source_id=file_source_id,
            table_name="california_housing",
            schema_json=[
                {"name": "longitude", "type": "FLOAT", "nullable": False},
                {"name": "latitude", "type": "FLOAT", "nullable": False},
                {"name": "housing_median_age", "type": "FLOAT", "nullable": False},
                {"name": "total_rooms", "type": "FLOAT", "nullable": False},
                {"name": "total_bedrooms", "type": "FLOAT", "nullable": True},
                {"name": "population", "type": "FLOAT", "nullable": False},
                {"name": "households", "type": "FLOAT", "nullable": False},
                {"name": "median_income", "type": "FLOAT", "nullable": False},
                {"name": "median_house_value", "type": "FLOAT", "nullable": False},
                {"name": "ocean_proximity", "type": "VARCHAR", "nullable": False},
            ],
            description="California housing prices and demographics dataset",
            tags="RealEstate,California,Demographics",
            updated_by="system",
        )
        
        # Entry: dummy_products.json
        await catalog_service.add_entry(
            db,
            data_source_id=file_source["id"],
            table_name="dummy_products",
            schema_json=[
                {"name": "id", "type": "INTEGER", "nullable": False},
                {"name": "title", "type": "VARCHAR", "nullable": False},
                {"name": "description", "type": "VARCHAR", "nullable": False},
                {"name": "price", "type": "FLOAT", "nullable": False},
                {"name": "rating", "type": "FLOAT", "nullable": False},
                {"name": "stock", "type": "INTEGER", "nullable": False},
                {"name": "brand", "type": "VARCHAR", "nullable": True},
                {"name": "category", "type": "VARCHAR", "nullable": False},
            ],
            description="Dummy JSON products listing",
            tags="Products,Retail,JSON",
            updated_by="system",
        )
        
        # Entry: products_financial.xlsx
        await catalog_service.add_entry(
            db,
            data_source_id=file_source["id"],
            table_name="products_financial",
            schema_json=[
                {"name": "id", "type": "INTEGER", "nullable": False},
                {"name": "title", "type": "VARCHAR", "nullable": False},
                {"name": "category", "type": "VARCHAR", "nullable": False},
                {"name": "price", "type": "FLOAT", "nullable": False},
                {"name": "rating", "type": "FLOAT", "nullable": False},
                {"name": "stock", "type": "INTEGER", "nullable": False},
                {"name": "brand", "type": "VARCHAR", "nullable": True},
            ],
            description="Excel export of dummy products",
            tags="Products,Excel,Financial",
            updated_by="system",
        )

        # SOURCE 2: Chinook SQLite Database
        if "Chinook Music Store Database" in existing_map:
            sql_source_id = existing_map["Chinook Music Store Database"]
            await catalog_service.delete_source(db, sql_source_id)
            print("  - Deleted existing Chinook source")

        sql_source = await catalog_service.create_source(
            db,
            name="Chinook Music Store Database",
            source_type="sql",
            connection_config={
                "driver": "sqlite",
                "database": "data/real_datasets/chinook.sqlite",
            },
            description="Chinook digital media store SQLite database",
            created_by="system",
        )
        print(f"  - Source: {sql_source['name']} ({sql_source['id']})")
        
        # Entry: tracks
        await catalog_service.add_entry(
            db,
            data_source_id=sql_source["id"],
            table_name="Track",
            schema_json=[
                {"name": "TrackId", "type": "INTEGER", "nullable": False},
                {"name": "Name", "type": "NVARCHAR(200)", "nullable": False},
                {"name": "AlbumId", "type": "INTEGER", "nullable": True},
                {"name": "MediaTypeId", "type": "INTEGER", "nullable": False},
                {"name": "GenreId", "type": "INTEGER", "nullable": True},
                {"name": "Composer", "type": "NVARCHAR(220)", "nullable": True},
                {"name": "Milliseconds", "type": "INTEGER", "nullable": False},
                {"name": "Bytes", "type": "INTEGER", "nullable": True},
                {"name": "UnitPrice", "type": "NUMERIC(10,2)", "nullable": False},
            ],
            description="Chinook Tracks table",
            tags="Music,Tracks,Chinook",
            updated_by="system",
        )

        print("\n[SUCCESS] Real Datasets seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed())
