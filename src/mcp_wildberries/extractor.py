"""Парсер YAML спецификаций Wildberries с поддержкой $ref"""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from .models import WBMethod

logger = logging.getLogger(__name__)


class WBParser:
    """Парсер YAML файлов Wildberries с полной поддержкой $ref"""

    def __init__(self, yaml_path: Path):
        self.yaml_path = yaml_path
        self.spec: Dict[str, Any] = {}
        self.methods: List[WBMethod] = []
        self._parse()

    def _parse(self):
        """Парсит YAML в методы с разрешением всех ссылок"""
        # 1. Проверяем существование файла
        if not self.yaml_path.exists():
            raise FileNotFoundError(f"YAML not found: {self.yaml_path}")

        # 2. Загружаем спецификацию
        with open(self.yaml_path, "r", encoding="utf-8") as f:
            self.spec = yaml.safe_load(f)

        # 3. Получаем пути
        paths = self.spec.get("paths", {})

        # 4. Проходим по всем эндпоинтам
        for path, path_item in paths.items():
            for http_method, operation in path_item.items():
                if http_method not in ["get", "post", "put", "delete", "patch"]:
                    continue

                # Разрешаем ссылки в операции
                operation = self._resolve_refs(operation)

                # Извлекаем данные
                tags = operation.get("tags", [])
                tag = tags[0] if tags else "other"
                api = self._detect_api(tag, path)
                safety = self._classify_safety(http_method, path, operation.get("operationId", ""))

                # Параметры с разрешением ссылок
                parameters = self._parse_parameters(operation)

                # Request body с разрешением ссылок
                request_schema = self._parse_request_body(operation)

                # Response schemas с разрешением ссылок
                response_schemas = self._parse_responses(operation)

                # Создаем метод
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
                    servers=operation.get("servers", []),
                    security=operation.get("security", []),
                    x_readonly=operation.get("x-readonly-method", False),
                    x_category=operation.get("x-category", ""),
                )
                self.methods.append(method)

        logger.info(f"Parsed {len(self.methods)} methods from {self.yaml_path}")

    def _resolve_refs(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            # Если это ссылка - разрешаем
            if "$ref" in obj and len(obj) == 1:
                return self._resolve_ref(obj["$ref"])

            # Иначе рекурсивно обрабатываем все значения
            resolved = {}
            for key, value in obj.items():
                resolved[key] = self._resolve_refs(value)
            return resolved

        elif isinstance(obj, list):
            # Обрабатываем каждый элемент списка
            return [self._resolve_refs(item) for item in obj]

        else:
            # Примитивные значения (str, int, bool и т.д.)
            return obj

    def _resolve_ref(self, ref_path: str) -> Any:
        if not ref_path.startswith("#/"):
            # Внешние ссылки не обрабатываем
            return {"$ref": ref_path}

        parts = ref_path[2:].split("/")

        # Идем по пути в спецификации
        result = self.spec
        for part in parts:
            if isinstance(result, dict) and part in result:
                result = result[part]
            else:
                logger.warning(f"Could not resolve ref: {ref_path}")
                return {"$ref": ref_path}

        # Если результат содержит ссылки - разрешаем их рекурсивно
        return self._resolve_refs(result)

    def _parse_parameters(self, operation: Dict[str, Any]) -> List[Dict[str, Any]]:

        parameters = []
        for p in operation.get("parameters", []):
            # Разрешаем ссылки в параметре
            p = self._resolve_refs(p)

            # Фильтруем заголовки авторизации
            if p.get("name") in ["Authorization", "Api-Key", "Client-Id"]:
                continue

            param = {
                "name": p.get("name", ""),
                "in": p.get("in", ""),
                "required": p.get("required", False),
                "description": p.get("description", ""),
                "schema": self._resolve_refs(p.get("schema", {})),
            }

            # Добавляем дополнительные поля
            if "example" in p:
                param["example"] = p["example"]
            if "examples" in p:
                param["examples"] = self._resolve_refs(p["examples"])
            if "deprecated" in p:
                param["deprecated"] = p["deprecated"]
            if "allowEmptyValue" in p:
                param["allowEmptyValue"] = p["allowEmptyValue"]
            if "style" in p:
                param["style"] = p["style"]
            if "explode" in p:
                param["explode"] = p["explode"]
            if "allowReserved" in p:
                param["allowReserved"] = p["allowReserved"]

            parameters.append(param)

        return parameters

    def _parse_request_body(self, operation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if "requestBody" not in operation:
            return None

        request_body = self._resolve_refs(operation["requestBody"])
        content = request_body.get("content", {})

        # Ищем application/json
        if "application/json" in content:
            schema = content["application/json"].get("schema")
            if schema:
                return self._resolve_refs(schema)

        # Ищем multipart/form-data (для загрузки файлов)
        if "multipart/form-data" in content:
            schema = content["multipart/form-data"].get("schema")
            if schema:
                return self._resolve_refs(schema)

        # Ищем application/x-www-form-urlencoded
        if "application/x-www-form-urlencoded" in content:
            schema = content["application/x-www-form-urlencoded"].get("schema")
            if schema:
                return self._resolve_refs(schema)

        return None

    def _parse_responses(self, operation: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        response_schemas = {}
        responses = operation.get("responses", {})

        for code, response in responses.items():
            # Разрешаем ссылки в ответе
            response = self._resolve_refs(response)

            # Проверяем, может быть это просто ссылка на компонент
            if isinstance(response, dict) and "$ref" in response:
                continue

            content = response.get("content", {})

            # Проверяем различные media types
            for media_type in ["application/json", "application/problem+json", "plain/text"]:
                if media_type in content:
                    schema = content[media_type].get("schema")
                    if schema:
                        response_schemas[code] = self._resolve_refs(schema)
                        break

            # Если нет схемы, но есть описание
            if code not in response_schemas and "description" in response:
                response_schemas[code] = {"description": response["description"]}

        return response_schemas

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

    def get_spec(self) -> Dict[str, Any]:
        return self._resolve_refs(self.spec)

def parse_yaml(yaml_path: Path) -> List[WBMethod]:
    parser = WBParser(yaml_path)
    return parser.get_methods()