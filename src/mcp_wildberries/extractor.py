"""Парсер YAML спецификаций Wildberries"""

import yaml
from pathlib import Path
from typing import List
import logging

from .models import WBMethod

logger = logging.getLogger(__name__)


class WBParser:
    """Парсер YAML файлов Wildberries"""

    def __init__(self, yaml_path: Path):
        self.yaml_path = yaml_path
        self.methods: List[WBMethod] = []
        self._parse()

    def _parse(self):
        """Парсит YAML в методы"""
        if not self.yaml_path.exists():
            raise FileNotFoundError(f"YAML not found: {self.yaml_path}")

        with open(self.yaml_path, "r", encoding="utf-8") as f:
            spec = yaml.safe_load(f)

        paths = spec.get("paths", {})

        for path, path_item in paths.items():
            for http_method, operation in path_item.items():
                if http_method not in ["get", "post", "put", "delete", "patch"]:
                    continue

                # Извлекаем данные
                tags = operation.get("tags", [])
                tag = tags[0] if tags else "other"
                api = self._detect_api(tag, path)
                safety = self._classify_safety(http_method, path, operation.get("operationId", ""))

                # Параметры
                parameters = []
                for p in operation.get("parameters", []):
                    if p.get("name") not in ["Authorization", "Api-Key", "Client-Id"]:
                        parameters.append({
                            "name": p.get("name", ""),
                            "in": p.get("in", ""),
                            "required": p.get("required", False),
                            "description": p.get("description", ""),
                            "schema": p.get("schema", {}),
                        })

                # Request body
                request_schema = None
                if "requestBody" in operation:
                    content = operation["requestBody"].get("content", {})
                    if "application/json" in content:
                        request_schema = content["application/json"].get("schema")

                # Response schemas
                response_schemas = {}
                responses = operation.get("responses", {})
                for code, resp in responses.items():
                    content = resp.get("content", {})
                    if "application/json" in content:
                        schema = content["application/json"].get("schema")
                        if schema:
                            response_schemas[code] = schema

                method = WBMethod(
                    operation_id=operation.get("operationId", ""),
                    api=api,
                    method=http_method.upper(),
                    path=path,
                    section=tag,
                    tag=tag,
                    summary=operation.get("summary", ""),
                    description=operation.get("description", ""),
                    parameters=parameters,
                    request_schema=request_schema,
                    response_schemas=response_schemas,
                    deprecated=operation.get("deprecated", False),
                    safety=safety,
                )
                self.methods.append(method)

        logger.info(f"Parsed {len(self.methods)} methods from {self.yaml_path}")

    def _detect_api(self, tag: str, path: str) -> str:
        """Определяет API по тегу"""
        tag_lower = tag.lower()
        if "content" in tag_lower or "product" in tag_lower:
            return "content"
        elif "marketplace" in tag_lower or "order" in tag_lower:
            return "marketplace"
        elif "feedback" in tag_lower:
            return "feedbacks"
        elif "statistic" in tag_lower:
            return "statistics"
        elif "supply" in tag_lower:
            return "supplies"
        elif "advert" in tag_lower:
            return "advert"
        elif "discount" in tag_lower:
            return "discounts"
        return "other"

    def _classify_safety(self, method: str, path: str, operation_id: str) -> str:
        """Классифицирует метод: read/write/destructive"""
        read_words = {"get", "list", "info", "search", "find", "view", "show", "details"}
        destructive_words = {"delete", "remove", "cancel", "reject"}

        # Проверяем path
        last = path.split("/")[-1].lower()
        if any(w in last for w in destructive_words):
            return "destructive"
        if any(w in last for w in read_words):
            return "read"

        # Проверяем operation_id
        op_lower = operation_id.lower()
        if any(w in op_lower for w in destructive_words):
            return "destructive"
        if any(w in op_lower for w in read_words):
            return "read"

        # HTTP метод
        if method.upper() == "GET":
            return "read"
        if method.upper() == "DELETE":
            return "destructive"

        return "write"

    def get_methods(self) -> List[WBMethod]:
        return self.methods


def parse_yaml(yaml_path: Path) -> List[WBMethod]:
    """Утилита для парсинга YAML"""
    parser = WBParser(yaml_path)
    return parser.get_methods()