"""Pydantic модели для OpenAPI спецификации"""

from typing import List, Dict, Any, Optional, Literal, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, validator, field_validator


# === Enums ===

class SafetyType(str, Enum):
    """Тип безопасности метода"""
    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"


class ParameterLocation(str, Enum):
    """Где находится параметр"""
    QUERY = "query"
    PATH = "path"
    HEADER = "header"
    COOKIE = "cookie"


class HttpMethod(str, Enum):
    """HTTP методы"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class ApiCategory(str, Enum):
    """Категории API Wildberries"""
    CONTENT = "content"
    MARKETPLACE = "marketplace"
    FEEDBACKS = "feedbacks"
    STATISTICS = "statistics"
    SUPPLIES = "supplies"
    ADVERT = "advert"
    DISCOUNTS = "discounts"
    OTHER = "other"


# === Models ===

class ParameterSchema(BaseModel):
    """Схема параметра"""
    name: str = Field(..., description="Название параметра")
    in_location: ParameterLocation = Field(..., alias="in", description="Где находится параметр")
    required: bool = Field(default=False, description="Обязательный ли параметр")
    description: str = Field(default="", description="Описание параметра")
    schema: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema")
    example: Optional[Any] = Field(None, description="Пример значения")
    examples: Optional[Dict[str, Any]] = Field(None, description="Примеры значений")
    deprecated: bool = Field(default=False, description="Устаревший ли параметр")
    allow_empty_value: bool = Field(default=False, description="Может ли быть пустым")
    style: Optional[str] = Field(None, description="Стиль сериализации")
    explode: Optional[bool] = Field(None, description="Разворачивать ли объекты")
    allow_reserved: bool = Field(default=False, description="Разрешать зарезервированные символы")

    class Config:
        populate_by_name = True
        use_enum_values = True

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v:
            raise ValueError("Parameter name cannot be empty")
        return v


class Server(BaseModel):
    """Сервер"""
    url: Union[HttpUrl, str] = Field(..., description="URL сервера")
    description: Optional[str] = Field(None, description="Описание сервера")
    variables: Optional[Dict[str, Any]] = Field(None, description="Переменные URL")


class SecurityRequirement(BaseModel):
    """Требование безопасности"""
    name: str = Field(..., description="Название схемы безопасности")
    scopes: List[str] = Field(default_factory=list, description="Необходимые scope'ы")


class WBMethod(BaseModel):
    """Модель метода API с валидацией"""

    # Основные поля
    operation_id: str = Field(default="", description="Уникальный ID операции")
    api: ApiCategory = Field(..., description="Категория API")
    method: HttpMethod = Field(..., description="HTTP метод")
    path: str = Field(..., description="URL путь")

    # Метаданные
    section: str = Field(..., description="Секция API (первый тег)")
    tag: str = Field(..., description="Основной тег")
    summary: str = Field(default="", description="Краткое описание")
    description: str = Field(default="", description="Полное описание")

    # Компоненты
    parameters: List[ParameterSchema] = Field(default_factory=list, description="Параметры")
    request_schema: Optional[Dict[str, Any]] = Field(None, description="Схема тела запроса")
    response_schemas: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Схемы ответов")

    # Дополнительные поля
    deprecated: bool = Field(default=False, description="Устаревший ли метод")
    safety: SafetyType = Field(..., description="Тип безопасности (read/write/destructive)")
    servers: List[Server] = Field(default_factory=list, description="Серверы для метода")
    security: List[SecurityRequirement] = Field(default_factory=list, description="Требования безопасности")

    # Wildberries специфичные поля
    x_readonly: bool = Field(default=False, description="Только для чтения")
    x_category: str = Field(default="", description="Категория в x-category")
    x_token_types: List[str] = Field(default_factory=list, description="Типы токенов")

    class Config:
        populate_by_name = True
        use_enum_values = True

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v.startswith('/'):
            raise ValueError(f"Path must start with '/': {v}")
        return v

    @field_validator('response_schemas')
    @classmethod
    def validate_response_schemas(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        # Проверяем, что ключи - это коды ответов
        for key in v.keys():
            if not key.isdigit() and key not in ["default"]:
                raise ValueError(f"Invalid response code: {key}")
        return v

    def is_read(self) -> bool:
        """Является ли метод read-операцией"""
        return self.safety == SafetyType.READ

    def is_write(self) -> bool:
        """Является ли метод write-операцией"""
        return self.safety == SafetyType.WRITE

    def is_destructive(self) -> bool:
        """Является ли метод destructive-операцией"""
        return self.safety == SafetyType.DESTRUCTIVE

    def get_full_url(self, server_url: Optional[str] = None) -> str:
        """Возвращает полный URL"""
        if server_url:
            base = server_url.rstrip('/')
        elif self.servers:
            base = str(self.servers[0].url).rstrip('/')
        else:
            base = ""
        return f"{base}{self.path}"

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует в словарь"""
        return self.model_dump(by_alias=True, exclude_none=True)


class OpenAPISpec(BaseModel):
    """Корневая модель OpenAPI спецификации"""

    openapi: str = Field(..., description="Версия OpenAPI")
    info: Dict[str, Any] = Field(..., description="Информация о спецификации")
    paths: Dict[str, Dict[str, Any]] = Field(..., description="Пути и методы")
    servers: List[Server] = Field(default_factory=list, description="Серверы")
    components: Dict[str, Any] = Field(default_factory=dict, description="Компоненты")
    security: List[Dict[str, List[str]]] = Field(default_factory=list, description="Глобальные требования безопасности")
    tags: List[Dict[str, str]] = Field(default_factory=list, description="Теги")

    @field_validator('openapi')
    @classmethod
    def validate_openapi_version(cls, v: str) -> str:
        if not v.startswith(('3.0', '3.1')):
            raise ValueError(f"Unsupported OpenAPI version: {v}")
        return v