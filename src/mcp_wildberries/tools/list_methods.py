"""Инструмент: список всех методов"""

import json
from typing import List
from mcp import types

from ..models import WBMethod


def list_methods_tool() -> types.Tool:
    """Возвращает описание инструмента"""
    return types.Tool(
        name="wb_list_methods",
        description="Show all Wildberries API methods (read, write, destructive)",
        inputSchema={
            "type": "object",
            "properties": {
                "safety": {
                    "type": "string",
                    "enum": ["read", "write", "destructive"],
                    "description": "Filter by safety level"
                },
                "api": {
                    "type": "string",
                    "description": "Filter by API (content, marketplace, etc.)"
                },
                "include_deprecated": {
                    "type": "boolean",
                    "description": "Include deprecated methods",
                    "default": False
                }
            }
        }
    )


async def handle_list_methods(
        methods: List[WBMethod],
        safety: str | None = None,
        api: str | None = None,
        include_deprecated: bool = False
) -> List[types.TextContent]:
    """Обрабатывает вызов инструмента"""

    filtered = methods
    if safety:
        filtered = [m for m in filtered if m.safety == safety]
    if api:
        filtered = [m for m in filtered if m.api == api]
    if not include_deprecated:
        filtered = [m for m in filtered if not m.deprecated]

    output = [{
        "operation_id": m.operation_id,
        "method": m.method,
        "path": m.path,
        "summary": m.summary,
        "api": m.api,
        "safety": m.safety,
        "deprecated": m.deprecated,
    } for m in filtered]

    return [types.TextContent(
        type="text",
        text=json.dumps(output, ensure_ascii=False, indent=2)
    )]