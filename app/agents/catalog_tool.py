import json
from app.db.database import async_session
from app.services.catalog_service import catalog_service
from app.services.sql_service import sql_service

async def get_catalog_context() -> str:
    """Returns a string describing all tables in the Data Catalog."""
    async with async_session() as db:
        entries = await catalog_service.list_entries(db)
        context = "Internal Data Catalog Schema:\n"
        context += "You have access to a DuckDB SQL engine. You can query the following datasets:\n"
        context += "- CSV/JSON/Excel: Use `SELECT * FROM 'data/real_datasets/FILENAME.ext'`\n"
        context += "- Chinook SQLite DB: Use `SELECT * FROM chinook.TABLENAME` (it is already attached).\n\n"
        
        for e in entries:
            context += f"Table: {e['table_name']}\n"
            context += f"Description: {e['description']}\n"
            if e.get("schema_json"):
                context += f"Columns: {e['schema_json']}\n"
            context += "\n"
        return context

import duckdb

import asyncio

def _run_duckdb_query(sql: str) -> str:
    # Open in-memory duckdb
    con = duckdb.connect(':memory:')
    
    # Attach SQLite databases
    con.execute("INSTALL sqlite;")
    con.execute("LOAD sqlite;")
    con.execute("ATTACH 'data/real_datasets/chinook.sqlite' AS chinook (TYPE SQLITE);")
    
    # Run query
    result = con.execute(sql).fetchdf()
    
    # Convert to JSON
    return result.head(50).to_json(orient='records')

async def execute_catalog_query(sql: str) -> str:
    """Executes a SQL query against the real datasets using DuckDB and returns JSON results."""
    try:
        return await asyncio.to_thread(_run_duckdb_query, sql)
    except Exception as e:
        return f"Error executing SQL: {e}"
