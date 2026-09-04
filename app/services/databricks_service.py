"""
Databricks / Delta Lake SQL service.

Runs warehouse queries when DATABRICKS_HOST, DATABRICKS_TOKEN, and
DATABRICKS_HTTP_PATH are configured. Otherwise returns a clear
"not configured" result so the Data Agent can fall back to local files.
"""

import logging
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class DatabricksService:
    """Thin wrapper around the Databricks SQL connector."""

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(
            settings.DATABRICKS_HOST
            and settings.DATABRICKS_TOKEN
            and settings.DATABRICKS_HTTP_PATH
        )

    def execute_query(
        self,
        sql: str,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        max_rows: int = 200,
    ) -> dict[str, Any]:
        """
        Execute SQL against a Databricks SQL warehouse.

        Returns rows/columns on success, or an error dict if Databricks
        is not configured or the query fails.
        """
        settings = get_settings()

        if not self.is_configured():
            return {
                "success": False,
                "configured": False,
                "error": (
                    "Databricks is not configured. Set DATABRICKS_HOST, "
                    "DATABRICKS_TOKEN, and DATABRICKS_HTTP_PATH in .env"
                ),
                "rows": [],
                "columns": [],
            }

        try:
            from databricks import sql as dbsql
        except ImportError:
            return {
                "success": False,
                "configured": True,
                "error": "databricks-sql-connector is not installed. Run: pip install databricks-sql-connector",
                "rows": [],
                "columns": [],
            }

        host = settings.DATABRICKS_HOST.replace("https://", "").replace("http://", "").rstrip("/")
        catalog = catalog or settings.DATABRICKS_CATALOG or None
        schema = schema or settings.DATABRICKS_SCHEMA or None

        try:
            with dbsql.connect(
                server_hostname=host,
                http_path=settings.DATABRICKS_HTTP_PATH,
                access_token=settings.DATABRICKS_TOKEN,
            ) as connection:
                with connection.cursor() as cursor:
                    if catalog:
                        cursor.execute(f"USE CATALOG `{catalog}`")
                    if schema:
                        cursor.execute(f"USE SCHEMA `{schema}`")
                    cursor.execute(sql)
                    columns = [col[0] for col in (cursor.description or [])]
                    raw_rows = cursor.fetchmany(max_rows)
                    rows = [self._serialize_row(columns, row) for row in raw_rows]

            logger.info("[Databricks] Query returned %s rows", len(rows))
            return {
                "success": True,
                "configured": True,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "truncated": len(rows) >= max_rows,
            }
        except Exception as e:
            logger.error("[Databricks] Query failed: %s", e)
            return {
                "success": False,
                "configured": True,
                "error": str(e),
                "rows": [],
                "columns": [],
            }

    @staticmethod
    def _serialize_row(columns: list[str], row: tuple) -> dict[str, Any]:
        values = []
        for value in row:
            if hasattr(value, "isoformat"):
                values.append(value.isoformat())
            elif isinstance(value, (bytes, bytearray)):
                values.append(value.decode("utf-8", errors="replace"))
            else:
                values.append(value)
        return dict(zip(columns, values))


databricks_service = DatabricksService()
