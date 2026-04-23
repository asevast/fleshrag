"""
Парсер кода на основе tree-sitter для AST-чанкинга.
Поддерживает: Python, JavaScript, TypeScript.
"""

import os
from typing import List, Dict, Any, Optional

try:
    from tree_sitter import Language, Parser
    import tree_sitter_python
    import tree_sitter_javascript
    import tree_sitter_typescript
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


# Расширения файлов и соответствующие языки
LANG_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}

# Node types для извлечения функций/классов
NODE_TYPES = {
    "python": {
        "function": "function_definition",
        "class": "class_definition",
        "method": "function_definition",  # внутри класса
    },
    "javascript": {
        "function": "function_declaration",
        "class": "class_declaration",
        "arrow_function": "arrow_function",
        "method": "method_definition",
    },
    "typescript": {
        "function": "function_declaration",
        "class": "class_declaration",
        "arrow_function": "arrow_function",
        "method": "method_definition",
    },
}


def _get_language(name: str):
    """Получить grammar для языка."""
    if not TREE_SITTER_AVAILABLE:
        return None
    
    if name == "python":
        return Language(tree_sitter_python.language())
    elif name == "javascript":
        return Language(tree_sitter_javascript.language())
    elif name == "typescript":
        return Language(tree_sitter_typescript.language_typescript())
    return None


def _get_parser(language: Language):
    """Создать парсер для языка."""
    if not TREE_SITTER_AVAILABLE:
        return None
    parser = Parser()
    parser.set_language(language)
    return parser


def _extract_node_text(node: Any, source: bytes) -> str:
    """Извлечь текст из узла AST."""
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")


def _walk_tree(node: Any, source: bytes, language: str, results: List[Dict[str, Any]], path: str = ""):
    """Рекурсивный обход AST для извлечения функций и классов."""
    node_types = NODE_TYPES.get(language, {})
    
    node_type = node.type
    
    # Проверяем, является ли узел функцией или классом
    if node_type == node_types.get("function"):
        name_node = node.child_by_field_name("name")
        if name_node:
            name = _extract_node_text(name_node, source)
            code = _extract_node_text(node, source)
            results.append({
                "type": "function",
                "name": name,
                "code": code,
                "path": path,
            })
    
    elif node_type == node_types.get("class"):
        name_node = node.child_by_field_name("name")
        if name_node:
            class_name = _extract_node_text(name_node, source)
            # Извлекаем методы класса
            methods = []
            for child in node.children:
                if child.type == node_types.get("method") or child.type == node_types.get("function"):
                    method_name_node = child.child_by_field_name("name")
                    if method_name_node:
                        method_name = _extract_node_text(method_name_node, source)
                        method_code = _extract_node_text(child, source)
                        methods.append({"name": method_name, "code": method_code})
            
            # Весь класс как один чанк
            class_code = _extract_node_text(node, source)
            results.append({
                "type": "class",
                "name": class_name,
                "code": class_code,
                "path": path,
                "methods": methods,
            })
            
            # Также добавляем методы отдельно
            for method in methods:
                results.append({
                    "type": "method",
                    "name": f"{class_name}.{method['name']}",
                    "code": method["code"],
                    "path": path,
                })
    
    elif node_type == NODE_TYPES.get("javascript", {}).get("arrow_function") or \
         node_type == NODE_TYPES.get("typescript", {}).get("arrow_function"):
        # Arrow функции
        code = _extract_node_text(node, source)
        results.append({
            "type": "function",
            "name": f"arrow_{node.start_byte}",
            "code": code,
            "path": path,
        })
    
    # Рекурсивный обход детей
    for child in node.children:
        _walk_tree(child, source, language, results, path)


def parse_code(path: str, max_chunks: int = 50) -> List[Dict[str, Any]]:
    """
    Парсинг файла с кодом с использованием AST.
    Возвращает список чанков: функции, классы, методы.
    
    Если tree-sitter недоступен, fallback на простой текстовый парсинг.
    """
    ext = os.path.splitext(path)[1].lower()
    language_name = LANG_EXTENSIONS.get(ext)
    
    if not language_name or not TREE_SITTER_AVAILABLE:
        # Fallback: просто читаем файл
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return [{"type": "file", "name": os.path.basename(path), "code": content, "path": path}]
        except Exception:
            return []
    
    try:
        with open(path, "rb") as f:
            source = f.read()
        
        language = _get_language(language_name)
        if not language:
            return []
        
        parser = _get_parser(language)
        if not parser:
            return []
        
        tree = parser.parse(source)
        results: List[Dict[str, Any]] = []
        
        _walk_tree(tree.root_node, source, language_name, results, path)
        
        # Если ничего не нашли, возвращаем весь файл
        if not results:
            content = source.decode("utf-8", errors="ignore")
            results.append({"type": "file", "name": os.path.basename(path), "code": content, "path": path})
        
        # Ограничиваем количество чанков
        return results[:max_chunks]
        
    except Exception as e:
        # Fallback на текстовый режим
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return [{"type": "file", "name": os.path.basename(path), "code": content, "path": path}]
        except Exception:
            return []


def parse_code_simple(path: str) -> str:
    """Простое чтение файла кода (fallback)."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""