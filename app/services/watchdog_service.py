"""
Watchdog Service — Auto-ingests files from data directories.
"""

import asyncio
import json
import logging
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.services.catalog_service import catalog_service
from app.services.mongodb_service import mongodb_service
from app.db.database import async_session

logger = logging.getLogger(__name__)

MYSQL_URL = "mysql+pymysql://root:root@localhost:3307/mysql"
DATA_DIR = Path("data")


class AutoIngestHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.processing = set()

    def on_created(self, event):
        if event.is_directory:
            return
        self._handle_file(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self._handle_file(event.src_path)

    def _handle_file(self, src_path: str):
        path = Path(src_path)
        if path.name.startswith(".") or path.name.startswith("~"):
            return
        
        # Debounce to avoid multiple triggers
        if path in self.processing:
            return
        self.processing.add(path)
        
        # Dispatch to asyncio loop
        asyncio.run_coroutine_threadsafe(self._process_file_async(path), self.loop)

    async def _process_file_async(self, path: Path):
        try:
            # Wait briefly to ensure file is fully written
            await asyncio.sleep(1.0)
            logger.info(f"[Watchdog] Processing new file: {path.name}")
            
            ext = path.suffix.lower()
            table_name = path.stem.replace(" ", "_").replace("-", "_").lower()
            
            if ext in [".csv", ".xlsx"]:
                # Parse with pandas
                if ext == ".csv":
                    df = pd.read_csv(path)
                else:
                    df = pd.read_excel(path)
                
                # Push to MySQL
                engine = create_engine(MYSQL_URL)
                df.to_sql(table_name, engine, if_exists="replace", index=False)
                engine.dispose()
                
                # Register in catalog
                await self._register_catalog(table_name, "MySQL (Auto-Ingested)", "sql")
                logger.info(f"[Watchdog] Ingested {path.name} into MySQL table '{table_name}'")

            elif ext == ".json":
                # Parse JSON
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if isinstance(data, dict):
                    data = [data]
                
                # Push to MongoDB
                if mongodb_service.db is not None:
                    collection = mongodb_service.db[table_name]
                    await collection.delete_many({}) # Replace
                    if data:
                        await collection.insert_many(data)
                        await self._register_catalog(table_name, "MongoDB (Auto-Ingested)", "mongodb")
                        logger.info(f"[Watchdog] Ingested {path.name} into MongoDB collection '{table_name}'")
                else:
                    logger.error("[Watchdog] MongoDB not connected")
                    
        except Exception as e:
            logger.error(f"[Watchdog] Failed to process {path.name}: {e}")
        finally:
            if path in self.processing:
                self.processing.remove(path)

    async def _register_catalog(self, table_name: str, desc: str, source: str):
        # Find data source ID
        async with async_session() as db:
            sources = await catalog_service.get_data_sources(db)
            source_id = next((s["id"] for s in sources if s["type"] == source), None)
            
            if source_id:
                # Add entry
                await catalog_service.create_catalog_entry(
                    db,
                    data_source_id=source_id,
                    table_name=table_name,
                    description=f"{desc}. Auto-inferred schema.",
                    tags=["auto-ingested"]
                )


class WatchdogService:
    def __init__(self):
        self.observer = Observer()
        self.is_running = False

    def start(self):
        if self.is_running:
            return
        
        loop = asyncio.get_running_loop()
        handler = AutoIngestHandler(loop)
        
        for subdir in ["csv", "json", "excel"]:
            path = DATA_DIR / subdir
            path.mkdir(parents=True, exist_ok=True)
            self.observer.schedule(handler, str(path), recursive=False)
            
        self.observer.start()
        self.is_running = True
        logger.info("[Watchdog] Started monitoring data directories")

    def stop(self):
        if self.is_running:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            logger.info("[Watchdog] Stopped")

watchdog_service = WatchdogService()
