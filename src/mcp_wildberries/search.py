# src/search.py
"""Простой поиск по методам Wildberries."""

from typing import List, Optional
from src.mcp_wildberries.catalog import Catalog
from src.mcp_wildberries.extractor import WBMethod


class Searcher:
    """Поиск методов по тексту"""

    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def search(
            self,
            query: str,
            limit: int = 10,
            api: Optional[str] = None
    ) -> List[WBMethod]:
        """Ищет методы по тексту"""
        query_lower = query.lower()
        results = []

        for method in self.catalog.methods:
            score = 0

            # Поиск в operation_id (самый сильный сигнал)
            if query_lower in method.operation_id.lower():
                score += 10

            # Поиск в summary
            if query_lower in method.summary.lower():
                score += 5

            # Поиск в description
            if query_lower in method.description.lower():
                score += 3

            # Поиск в path
            if query_lower in method.path.lower():
                score += 2

            # Поиск в section/tag
            if query_lower in method.section.lower():
                score += 1

            if score > 0:
                # Фильтр по API
                if api and method.api != api:
                    continue
                results.append((score, method))

        # Сортируем по релевантности
        results.sort(key=lambda x: x[0], reverse=True)

        return [m for _, m in results[:limit]]