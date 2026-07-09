#!/usr/bin/env python3
"""MCP server for Wildberries API (all methods, all YAML files)"""

import json
import asyncio
import logging
import sys
from pathlib import Path

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from .config import Config
from .catalog import load_catalog
from .search import Searcher
from .transport.wb_client import WBClient
from .tools import (
    list_methods_tool, handle_list_methods,
    search_methods_tool, handle_search_methods,
    describe_method_tool, handle_describe_method,
    call_method_tool, handle_call_method,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Загружаем конфигурацию
config = Config.from_env()
logger.info(f"Config: sandbox={config.sandbox_mode}, yaml={config.yaml_file}")

# Загружаем ВСЕ YAML файлы из папки data/
data_dir = Path(__file__).parent.parent.parent / "data"
yaml_files = list(data_dir.glob("*.yaml")) + list(data_dir.glob("*.yml"))

if not yaml_files:
    logger.warning(f"No YAML files found in {data_dir}, using config file")
    yaml_files = [config.yaml_file]

logger.info(f"Loading {len(yaml_files)} YAML files: {[f.name for f in yaml_files]}")

catalog = load_catalog(yaml_files)
searcher = Searcher(catalog)
logger.info(f"Loaded {catalog.total} methods from {len(yaml_files)} files")

# Создаем клиент
client = None
if config.api_token:
    client = WBClient(config.api_token, config.timeout)
    logger.info("WBClient initialized")
else:
    logger.warning("No API token found - call_method will not work")

# MCP сервер
server = Server("wildberries-mcp")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        list_methods_tool(),
        search_methods_tool(),
        describe_method_tool(),
        call_method_tool(),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "wb_list_methods":
            return await handle_list_methods(
                catalog.methods,
                arguments.get("safety"),
                arguments.get("api"),
                arguments.get("include_deprecated", False)
            )

        elif name == "wb_search_methods":
            return await handle_search_methods(
                searcher,
                arguments["query"],
                arguments.get("limit", 10),
                arguments.get("api"),
                arguments.get("safety"),
                arguments.get("include_deprecated", False)
            )

        elif name == "wb_describe_method":
            return await handle_describe_method(
                catalog,
                arguments["operation_id"]
            )

        elif name == "wb_call_method":
            return await handle_call_method(
                client,
                config,
                catalog,
                arguments["path"],
                arguments.get("method", "GET"),
                arguments.get("params", {}),
                arguments.get("data", {}),
                arguments.get("operation_id")
            )

        else:
            return [types.TextContent(
                type="text",
                text=f"ERROR: Unknown tool: {name}"
            )]

    except KeyError as e:
        return [types.TextContent(
            type="text",
            text=f"ERROR: Missing required argument: {str(e)}"
        )]
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=f"ERROR: {str(e)}"
        )]


async def main():
    logger.info("Starting Wildberries MCP server...")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="wildberries-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)