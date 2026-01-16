import re
from typing import Tuple, Dict, Any, Optional
from docx import Document
from pypdf import PdfReader
from .schemas import ExtractedRules
from .rule_engine import apply_rules, normalize_text, split_fragments
from .ml_engine_simple import predict_labels

def _read_docx_text(file_path: str) -> str:
    doc = Document(file_path)
    parts = []
    for p in doc.paragraphs:
        if p.text:
            parts.append(p.text)
    return "\n".join(parts)

def _read_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    parts = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        if txt.strip():
            parts.append(txt)
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
    if lower.endswith(".pdf"):
        return _read_pdf_text(file_path)
    raise ValueError("Поддерживаются только .docx, .txt и .pdf")


def _find_first_int(pattern: str, text: str) -> Tuple[Optional[int], Optional[str]]:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return None, None
    return int(m.group(1)), m.group(0)


def _find_first_float(pattern: str, text: str) -> Tuple[Optional[float], Optional[str]]:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not m:
        return None, None
    val = float(m.group(1).replace(",", "."))
    return val, m.group(0)

def extract_rules(text: str) -> ExtractedRules:
    ml_preview = []
    ml_note = "ML не выполнялся."
    filtered_text = text

    try:
        from .rule_engine import normalize_text, split_fragments
        from .ml_engine_simple import predict_labels

        t = normalize_text(text)
        fragments = split_fragments(t)
        ml_tags = predict_labels(fragments)

        ml_preview = ml_tags[:30]
        ml_note = "ML: Naive Bayes классификация фрагментов; используется для фильтрации нерелевантных частей."

        keywords = [
            "шрифт", "кегл", "размер", "times", "arial", "calibri",
            "межстроч", "интервал", "отступ", "абзац",
            "поле", "поля", "мм", "сантим", "см",
            "нумерац", "номер страницы", "внизу", "по центру", "колонтитул"
        ]

        def looks_like_requirement(frag: str) -> bool:
            lf = frag.lower()
            return any(k in lf for k in keywords)

        def is_heading_context(frag: str) -> bool:
            lf = frag.lower()
            return "заголов" in lf or "глава" in lf

        def is_page_number_context(frag: str) -> bool:
            lf = frag.lower()
            return "номер страницы" in lf or "нумерац" in lf or "колонтитул" in lf

        font_frags = []
        spacing_frags = []
        indent_frags = []
        margins_frags = []
        paging_frags = []

        for it in ml_tags:
            label = it.get("label")
            score = float(it.get("score", 0))
            frag = it.get("fragment", "")
            if not frag:
                continue
            if label == "other":
                continue
            if score < 0.30:
                continue
            if not looks_like_requirement(frag):
                continue

            # раскладываем по группам
            if label == "font":
                if not is_heading_context(frag) and not is_page_number_context(frag):
                    font_frags.append(frag)
            elif label == "spacing":
                if not is_heading_context(frag):
                    spacing_frags.append(frag)
            elif label == "indent":
                if not is_heading_context(frag):
                    indent_frags.append(frag)
            elif label == "margins":
                margins_frags.append(frag)
            elif label == "paging":
                paging_frags.append(frag)

        # собираем итоговый порядок: сначала основной текст, потом поля, потом нумерация
        kept = font_frags + spacing_frags + indent_frags + margins_frags + paging_frags

        if kept:
            filtered_text = "\n".join(kept)
        else:
            filtered_text = text

    except Exception as e:
        ml_note = f"ML отключён/ошибка: {e}"

    model = apply_rules(filtered_text, fragments_override=kept if kept else None)

    evidence = dict(model.evidence or {})
    evidence["_ml_preview"] = ml_preview
    evidence["_ml_note"] = ml_note
    evidence["_ml_filtered_fragments_count"] = len(filtered_text.splitlines())

    rules = ExtractedRules(
        font_name=model.document.font_name,
        font_size_pt=model.document.font_size_pt,
        line_spacing=model.document.line_spacing,
        margin_left_mm=model.margins.left_mm,
        margin_right_mm=model.margins.right_mm,
        margin_top_mm=model.margins.top_mm,
        margin_bottom_mm=model.margins.bottom_mm,
        page_numbering=model.page_numbering.enabled,
        page_number_font_size_pt=model.page_numbering.font_size_pt,
        page_number_position=model.page_numbering.position,
        raw_matches=evidence,
        source_summary="Извлечение через внутреннюю модель требований + ML-классификация фрагментов (Naive Bayes)",
        requirements_model=model.model_dump(),
    )
    return rules

# python -m uvicorn app.main:app --reload --port 8000
# cd ~/Desktop/vkr-template-app 