# src/catalog.py
"""Индекс всех методов Wildberries API."""

from typing import Optional, List, Dict, Any
from src.mcp_wildberries.extractor import WBMethod, WBParser
from pathlib import Path


class Catalog:
    """Поисковый индекс методов"""

    def __init__(self, methods: List[WBMethod]):
        self.methods = methods
        self.by_operation_id: Dict[str, WBMethod] = {
            m.operation_id: m for m in methods if m.operation_id
        }
        self.by_path: Dict[tuple, WBMethod] = {
            (m.method, m.path): m for m in methods
        }
        self._sections: Dict[str, List[WBMethod]] = {}
        for m in methods:
            self._sections.setdefault(m.section, []).append(m)

    def get_by_operation_id(self, operation_id: str) -> Optional[WBMethod]:
        return self.by_operation_id.get(operation_id)

    def get_by_path(self, method: str, path: str) -> Optional[WBMethod]:
        return self.by_path.get((method.upper(), path))

    def list_sections(self) -> List[Dict[str, Any]]:
        """Возвращает список секций"""
        return [
            {"section": section, "count": len(methods)}
            for section, methods in self._sections.items()
        ]

    def get_section(self, section: str) -> List[WBMethod]:
        """Возвращает методы из секции"""
        return self._sections.get(section, [])

    @property
    def total(self) -> int:
        return len(self.methods)


def load_catalog(yaml_files: List[Path]) -> Catalog:
    """Загружает каталог из YAML файлов"""
    all_methods = []
    for yaml_file in yaml_files:
        parser = WBParser(yaml_file)
        all_methods.extend(parser.get_methods())

    return Catalog(all_methods)