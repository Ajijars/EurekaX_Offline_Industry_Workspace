import json
from app.db.database import async_session
from app.services.catalog_service import catalog_service
from app.services.sql_service import sql_service

MYSQL_URL = "mysql+aiomysql://root:root@localhost:3307/mysql"

async def get_catalog_context() -> str:
    """Returns a string describing all tables in the Data Catalog."""
    async with async_session() as db:
        entries = await catalog_service.list_entries(db)
        context = "Internal Data Catalog Schema:\n"
        context += "You have access to a MySQL database containing auto-ingested files (CSV, Excel).\n"
        context += "Use standard MySQL SQL syntax to query the tables below.\n\n"
        
        for e in entries:
            # Only include SQL tables for now
            if e.get("data_source_id") == "sql" or "MySQL" in e.get("description", ""):
                context += f"Table: {e['table_name']}\n"
                context += f"Description: {e['description']}\n"
                if e.get("schema_json"):
                    context += f"Columns: {e['schema_json']}\n"
                context += "\n"
        return context

async def execute_catalog_query(sql: str) -> str:
    """Executes a SQL query against MySQL using sql_service and returns JSON results."""
    try:
        async with async_session() as db:
            result = await sql_service.execute(
                db, 
                sql=sql, 
                source_name="mysql", 
                connection_string=MYSQL_URL
            )
            if not result.get("success"):
                return f"Error executing SQL: {result.get('error')}"
            
            # Convert to JSON
            return json.dumps(result.get("rows", [])[:50], default=str)
    except Exception as e:
        return f"Error executing SQL: {e}"
