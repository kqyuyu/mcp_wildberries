"""Инструмент: вызов метода API"""

import json
import logging
from mcp import types

from ..transport.wb_client import WBClient
from ..config import Config
from ..catalog import Catalog
from typing import List

logger = logging.getLogger(__name__)


def call_method_tool() -> types.Tool:
    """Возвращает описание инструмента"""
    return types.Tool(
        name="wb_call_method",
        description="Call a Wildberries API method (read, write, or destructive)",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Endpoint path"},
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "default": "GET"
                },
                "params": {
                    "type": "object",
                    "description": "Query parameters",
                    "default": {}
                },
                "data": {
                    "type": "object",
                    "description": "Request body (for POST/PUT/PATCH)",
                    "default": {}
                },
                "operation_id": {
                    "type": "string",
                    "description": "Optional: check safety before calling"
                }
            },
            "required": ["path"],
        }
    )


async def handle_call_method(
        client: WBClient,
        config: Config,
        catalog: Catalog,
        path: str,
        method: str = "GET",
        params: dict = None,
        data: dict = None,
        operation_id: str = None
) -> List[types.TextContent]:
    """Обрабатывает вызов инструмента"""

    if not client:
        return [types.TextContent(
            type="text",
            text="ERROR: WILDBERRIES_API_TOKEN not configured in .env"
        )]

    # Проверка безопасности (если указан operation_id)
    if operation_id:
        method_info = catalog.get_by_operation_id(operation_id)
        if method_info:
            if method_info.safety == "destructive":
                return [types.TextContent(
                    type="text",
                    text=f"⚠️  WARNING: Method '{operation_id}' is DESTRUCTIVE. "
                         f"Set operation_id to empty to bypass this check."
                )]
            logger.info(f"Calling {method_info.safety} method: {operation_id}")

    # Определяем домен
    domain = config.get_domain(path)
    url = f"https://{domain}{path}"

    logger.info(f"Calling: {method} {url}")

    try:
        result = await client.call(
            method=method,
            url=url,
            params=params or {},
            json_data=data or {}
        )

        return [types.TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]

    except TimeoutError as e:
        return [types.TextContent(
            type="text",
            text=f"ERROR: {str(e)}"
        )]
    except Exception as e:
        logger.error(f"Error calling API: {e}")
        return [types.TextContent(
            type="text",
            text=f"ERROR: {str(e)}"
        )]