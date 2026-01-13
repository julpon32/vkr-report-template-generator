import re
from typing import Tuple, Dict, Any, Optional
from docx import Document

from .schemas import ExtractedRules


def _read_docx_text(file_path: str) -> str:
    doc = Document(file_path)
    parts = []
    for p in doc.paragraphs:
        if p.text:
            parts.append(p.text)
    return "\n".join(parts)


def _read_txt_text(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def read_text_by_extension(file_path: str, filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".docx"):
        return _read_docx_text(file_path)
    if lower.endswith(".txt"):
        return _read_txt_text(file_path)
    # на MVP: поддержим только docx/txt
    raise ValueError("Поддерживаются только .docx и .txt на текущем этапе MVP")


def _find_first_int(pattern: str, text: str) -> Tuple[Optional[int], Optional[str]]:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return None, None
    return int(m.group(1)), m.group(0)


def _find_first_float(pattern: str, text: str) -> Tuple[Optional[float], Optional[str]]:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return None, None
    # заменим запятую на точку
    val = float(m.group(1).replace(",", "."))
    return val, m.group(0)


def extract_rules(text: str) -> ExtractedRules:
    """
    MVP: извлекаем самое базовое:
    - шрифт (Times New Roman / Arial / Calibri встречаются чаще всего)
    - размер шрифта
    - межстрочный интервал (1.5 / 1,5 / 2)
    - поля (левое/правое/верхнее/нижнее) в мм
    - параметры нумерации страниц
    """
    rules = ExtractedRules()
    matches: Dict[str, Any] = {}

    # шрифт
    font_candidates = ["Times New Roman", "Arial", "Calibri"]
    for fc in font_candidates:
        if re.search(rf"\b{re.escape(fc)}\b", text, flags=re.IGNORECASE):
            rules.font_name = fc
            matches["font_name"] = fc
            break

    # размер шрифта: "шрифт ... 14" или "кегль 14"
    size, raw = _find_first_int(r"(?:шрифт|кегл[ья])\s*(?:\w*\s*){0,3}(\d{2})\b", text)
    if size:
        rules.font_size_pt = size
        matches["font_size_pt"] = raw

    # интервал: "межстрочный интервал 1,5" / "интервал 1.5"
    ls, raw = _find_first_float(r"(?:межстрочн\w*\s+интервал|интервал)\s*(\d[.,]\d)", text)
    if ls:
        rules.line_spacing = ls
        matches["line_spacing"] = raw

    # поля: "левое 30 мм", "правое 15 мм" и т.п.
    left, raw = _find_first_int(r"лев\w*\s+(\d{2})\s*мм", text)
    if left:
        rules.margin_left_mm = left
        matches["margin_left_mm"] = raw

    right, raw = _find_first_int(r"прав\w*\s+(\d{2})\s*мм", text)
    if right:
        rules.margin_right_mm = right
        matches["margin_right_mm"] = raw

    top, raw = _find_first_int(r"верхн\w*\s+(\d{2})\s*мм", text)
    if top:
        rules.margin_top_mm = top
        matches["margin_top_mm"] = raw

    bottom, raw = _find_first_int(r"нижн\w*\s+(\d{2})\s*мм", text)
    if bottom:
        rules.margin_bottom_mm = bottom
        matches["margin_bottom_mm"] = raw

    # нумерация страниц
    if re.search(r"нумерац\w*\s+страниц", text, flags=re.IGNORECASE):
        rules.page_numbering = True
        matches["page_numbering"] = "найдено упоминание нумерации страниц"

    pn_size, raw = _find_first_int(r"шрифт\s+номер\w*\s+страниц\w*\s+\w*\s*(\d{2})\b", text)
    if pn_size:
        rules.page_number_font_size_pt = pn_size
        matches["page_number_font_size_pt"] = raw

    # позиция номера: "внизу по центру"
    if re.search(r"внизу\s+по\s+центру", text, flags=re.IGNORECASE):
        rules.page_number_position = "bottom_center"
        matches["page_number_position"] = "внизу по центру"

    rules.raw_matches = matches
    rules.source_summary = "Извлечено регулярными выражениями (MVP)"
    return rules
