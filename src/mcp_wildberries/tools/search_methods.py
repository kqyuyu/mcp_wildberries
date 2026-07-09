"""Инструмент: поиск методов"""

import json
from typing import List, Optional
from mcp import types

from ..models import WBMethod
from ..search import Searcher


def search_methods_tool() -> types.Tool:
    """Возвращает описание инструмента"""
    return types.Tool(
        name="wb_search_methods",
        description="Search Wildberries API methods by query",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results", "default": 10},
                "api": {"type": "string", "description": "Filter by API"},
                "safety": {
                    "type": "string",
                    "enum": ["read", "write", "destructive"],
                    "description": "Filter by safety level"
                },
                "include_deprecated": {
                    "type": "boolean",
                    "description": "Include deprecated methods",
                    "default": False
                }
            },
            "required": ["query"],
        }
    )


async def handle_search_methods(
        searcher: Searcher,
        query: str,
        limit: int = 10,
        api: Optional[str] = None,
        safety: Optional[str] = None,
        include_deprecated: bool = False
) -> List[types.TextContent]:
    """Обрабатывает вызов инструмента"""

    results = searcher.search(query, limit, api, safety, include_deprecated)

    output = [{
        "operation_id": m.operation_id,
        "method": m.method,
        "path": m.path,
        "summary": m.summary,
        "api": m.api,
        "safety": m.safety,
        "deprecated": m.deprecated,
        "score": i + 1,  # условный рейтинг
    } for i, m in enumerate(results)]

    return [types.TextContent(
        type="text",
        text=json.dumps(output, ensure_ascii=False, indent=2)
    )]