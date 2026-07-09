"""Инструмент: описание метода"""

import json
from mcp import types
from ..catalog import Catalog
from typing import List


def describe_method_tool() -> types.Tool:
    """Возвращает описание инструмента"""
    return types.Tool(
        name="wb_describe_method",
        description="Get full description of a Wildberries API method by operation_id",
        inputSchema={
            "type": "object",
            "properties": {
                "operation_id": {"type": "string", "description": "Method ID"},
            },
            "required": ["operation_id"],
        }
    )


async def handle_describe_method(
        catalog: Catalog,
        operation_id: str
) -> List[types.TextContent]:
    """Обрабатывает вызов инструмента"""

    method = catalog.get_by_operation_id(operation_id)
    if not method:
        return [types.TextContent(
            type="text",
            text=f"ERROR: Method '{operation_id}' not found"
        )]

    return [types.TextContent(
        type="text",
        text=json.dumps(method.to_dict(), ensure_ascii=False, indent=2)
    )]