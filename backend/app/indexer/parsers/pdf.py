import fitz  # PyMuPDF


def parse_pdf(path: str) -> str:
    doc = fitz.open(path)
    lines = []
    for page_num, page in enumerate(doc, start=1):
        lines.append(f"\n--- Страница {page_num} ---\n")
        lines.append(page.get_text())

        # Извлечение таблиц (PyMuPDF 1.23+)
        try:
            tables = page.find_tables()
            if tables and tables.tables:
                lines.append("\n[Таблицы на странице]\n")
                for t_idx, table in enumerate(tables.tables, start=1):
                    lines.append(f"Таблица {t_idx}:")
                    for row in table.extract():
                        row_text = " | ".join(str(cell) if cell is not None else "" for cell in row)
                        lines.append(row_text)
        except Exception:
            pass

    doc.close()
    return "\n".join(lines)
