"""Pydantic модели для Wildberries API"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class WBMethod(BaseModel):
    """Модель метода Wildberries API"""
    operation_id: str
    api: str
    method: str
    path: str
    section: str
    tag: str
    summary: str
    description: str
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    request_schema: Optional[Dict[str, Any]] = None
    response_schemas: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    deprecated: bool = False
    safety: Literal["read", "write", "destructive"] = "write"
    auth_type: str = "Bearer Token"

    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь"""
        return self.model_dump(exclude_none=True)


class WBSearchResult(BaseModel):
    """Результат поиска"""
    operation_id: str
    method: str
    path: str
    summary: str
    score: int


class WBError(BaseModel):
    """Модель ошибки"""
    error: str
    message: str
    code: Optional[int] = None
    endpoint: Optional[str] = None
    retryable: bool = False