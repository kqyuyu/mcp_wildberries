#!/usr/bin/env python3
"""MCP server for Wildberries API (READONLY methods only)"""

import json
import asyncio
import os
from pathlib import Path

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from parser import parse_wb_swagger


# ============================================================
# 1. ЗАГРУЗКА ПЕРЕМЕННЫХ
# ============================================================

def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


load_env()

# ============================================================
# 2. ПАРСИМ НУЖНЫЙ YAML ФАЙЛ
# ============================================================

# Путь к файлу - можно менять
YAML_FILE = "02-items.yaml"  # ← ИЗМЕНИТЕ НА НУЖНЫЙ ФАЙЛ
yaml_path = Path(__file__).parent.parent / "data" / YAML_FILE

print(f"[INFO] Parsing: {yaml_path}")
METHODS = parse_wb_swagger(yaml_path)
print(f"[INFO] Loaded {len(METHODS)} READONLY methods")

# Индексы для поиска
BY_OPERATION_ID = {m.get("operation_id"): m for m in METHODS if m.get("operation_id")}
API_TOKEN = os.getenv("WILDBERRIES_API_TOKEN", "")
SANDBOX_MODE = os.getenv("WILDBERRIES_SANDBOX", "false").lower() == "true"

# ============================================================
# 3. ДОМЕНЫ
# ============================================================

if SANDBOX_MODE:
    DOMAINS = {
        "content": "content-api-sandbox.wildberries.ru",
        "marketplace": "marketplace-api-sandbox.wildberries.ru",
        "feedbacks": "feedbacks-api-sandbox.wildberries.ru",
        "supplies": "supplies-api-sandbox.wildberries.ru",
        "advert": "advert-api-sandbox.wildberries.ru",
        "statistics": "statistics-api-sandbox.wildberries.ru",
        "discounts": "discounts-prices-api-sandbox.wildberries.ru",
    }
else:
    DOMAINS = {
        "content": "content-api.wildberries.ru",
        "marketplace": "marketplace-api.wildberries.ru",
        "feedbacks": "feedbacks-api.wildberries.ru",
        "supplies": "supplies-api.wildberries.ru",
        "advert": "advert-api.wildberries.ru",
        "statistics": "statistics-api.wildberries.ru",
        "discounts": "discounts-prices-api.wildberries.ru",
    }

print(f"[INFO] Sandbox mode: {SANDBOX_MODE}")
print(f"[INFO] Domains: {DOMAINS}")

# ============================================================
# 4. MCP СЕРВЕР
# ============================================================

server = Server("wildberries-readonly")


def get_domain_for_path(path: str) -> str:
    """Определяет домен по пути"""
    if "feedbacks" in path or "rating" in path:
        return DOMAINS["feedbacks"]
    elif "content" in path or "products" in path or "cards" in path:
        return DOMAINS["content"]
    elif "marketplace" in path or "supply" in path or "orders" in path:
        return DOMAINS["marketplace"]
    elif "advert" in path or "campaign" in path:
        return DOMAINS["advert"]
    elif "statistics" in path or "report" in path:
        return DOMAINS["statistics"]
    elif "discounts" in path or "prices" in path:
        return DOMAINS["discounts"]
    else:
        return DOMAINS["content"]


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="wb_list_methods",
            description="Show all READONLY Wildberries API methods",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="wb_search_methods",
            description="Search READONLY methods by query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max results", "default": 10},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="wb_describe_method",
            description="Get full description of a READONLY method by operation_id",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation_id": {"type": "string", "description": "Method ID"},
                },
                "required": ["operation_id"],
            },
        ),
        types.Tool(
            name="wb_call_method",
            description="Call a READONLY Wildberries API method",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Endpoint path"},
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
                    "params": {"type": "object", "description": "Query parameters"},
                },
                "required": ["path"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "wb_list_methods":
        output = [{
            "operation_id": m.get("operation_id"),
            "method": m["method"],
            "path": m["path"],
            "summary": m.get("summary", ""),
        } for m in METHODS]
        return [types.TextContent(type="text", text=json.dumps(output, ensure_ascii=False, indent=2))]

    elif name == "wb_search_methods":
        query = arguments["query"].lower()
        limit = arguments.get("limit", 10)
        results = []
        for m in METHODS:
            score = 0
            if query in m.get("operation_id", "").lower(): score += 10
            if query in m.get("summary", "").lower(): score += 8
            if query in m.get("description", "").lower(): score += 5
            if query in m["path"].lower(): score += 3
            if score > 0:
                results.append((score, m))
        results.sort(key=lambda x: x[0], reverse=True)
        output = [{
            "operation_id": m.get("operation_id"),
            "method": m["method"],
            "path": m["path"],
            "summary": m.get("summary", ""),
            "score": score,
        } for score, m in results[:limit]]
        return [types.TextContent(type="text", text=json.dumps(output, ensure_ascii=False, indent=2))]

    elif name == "wb_describe_method":
        operation_id = arguments["operation_id"]
        method = BY_OPERATION_ID.get(operation_id)
        if not method:
            return [types.TextContent(type="text", text=f"ERROR: Method '{operation_id}' not found")]
        return [types.TextContent(type="text", text=json.dumps(method, ensure_ascii=False, indent=2))]

    elif name == "wb_call_method":
        if not API_TOKEN:
            return [types.TextContent(type="text", text="ERROR: Set WILDBERRIES_API_TOKEN in .env")]

        import httpx
        path = arguments["path"]
        method = arguments.get("method", "GET")
        params = arguments.get("params", {})

        domain = get_domain_for_path(path)
        url = f"https://{domain}{path}"
        headers = {"Authorization": f"Bearer {API_TOKEN}"}

        print(f"[DEBUG] Calling: {method} {url}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, headers=headers, params=params)
                result = response.json() if response.text else {"status": response.status_code}
        except Exception as e:
            result = {"error": str(e)}

        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    else:
        return [types.TextContent(type="text", text=f"ERROR: Unknown tool: {name}")]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="wildberries-readonly",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())