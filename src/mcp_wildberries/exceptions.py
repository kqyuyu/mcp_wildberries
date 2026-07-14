"""Кастомные исключения для парсера"""

class ParserError(Exception):
    """Базовое исключение для парсера"""
    pass

class SpecLoadError(ParserError):
    """Ошибка загрузки спецификации"""
    pass

class RefResolutionError(ParserError):
    """Ошибка разрешения $ref ссылки"""
    pass

class ValidationError(ParserError):
    """Ошибка валидации данных"""
    pass

class UnsupportedFormatError(ParserError):
    """Неподдерживаемый формат"""
    pass