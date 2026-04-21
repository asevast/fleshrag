"""
Fallback-парсер на основе MarkItDown от Microsoft.
Конвертирует различные форматы файлов → Markdown.
"""

import os
from markitdown import MarkItDown

_md = None


def _get_markitdown() -> MarkItDown:
    """Ленивая инициализация MarkItDown."""
    global _md
    if _md is None:
        _md = MarkItDown()
    return _md


def parse_markitdown(path: str) -> str:
    """
    Конвертация файла в Markdown через MarkItDown.
    Используется как fallback для неподдерживаемых форматов.
    """
    try:
        md = _get_markitdown()
        result = md.convert(path)
        return result.text_content or ""
    except Exception as e:
        # Fallback: читаем как текст
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""


def parse_markitdown_with_metadata(path: str) -> dict:
    """
    Конвертация файла в Markdown с метаданными.
    Возвращает dict с text и metadata.
    """
    try:
        md = _get_markitdown()
        result = md.convert(path)
        return {
            "text": result.text_content or "",
            "metadata": {
                "title": getattr(result, "title", None),
                "author": getattr(result, "author", None),
                "source": path,
            }
        }
    except Exception as e:
        return {
            "text": "",
            "metadata": {"error": str(e), "source": path}
        }
