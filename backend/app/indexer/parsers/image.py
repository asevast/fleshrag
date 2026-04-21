import easyocr

_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        # detail=0 не применяется к Reader, используем detail=0 в readtext
        _reader = easyocr.Reader(["ru", "en"], gpu=False, verbose=False)
    return _reader


def parse_image(path: str) -> str:
    reader = _get_reader()
    result = reader.readtext(path, detail=0)
    return "\n".join(result)


def parse_images_batch(paths: list[str]) -> list[str]:
    """Батчевая OCR для нескольких изображений (один и тот же reader)."""
    reader = _get_reader()
    results = []
    for path in paths:
        result = reader.readtext(path, detail=0)
        results.append("\n".join(result))
    return results

