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
    model = apply_rules(text)

    t = normalize_text(text)
    fragments = split_fragments(t)

    ml_tags = predict_labels(fragments)

    ml_preview = ml_tags[:30]

    evidence = dict(model.evidence or {})
    evidence["_ml_preview"] = ml_preview
    evidence["_ml_note"] = "ML: Naive Bayes классификация фрагментов требований (учебная модель)."

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
# быстрый индекс: fragment -> (label, score)
ml_index = {}
for it in ml_tags:
    frag = it.get("fragment", "")
    ml_index[frag] = (it.get("label"), float(it.get("score", 0)))

def _ok(frag: str, expected_label: str) -> bool:
    if not frag:
        return False
    label, score = ml_index.get(frag, (None, 0.0))
    if label is None:
        return True
    if score < 0.45:
        return True
    return label == expected_label

# фильтрация evidence
expected = {
    "font_name": "font",
    "font_size_pt": "font",
    "line_spacing": "spacing",
    "paragraph_indent_cm": "indent",
    "margin_left_mm": "margins",
    "margin_right_mm": "margins",
    "margin_top_mm": "margins",
    "margin_bottom_mm": "margins",
    "page_numbering": "paging",
    "page_number_position": "paging",
    "page_number_font_size_pt": "paging",
}

cleaned = {}
for k, v in (model.evidence or {}).items():
    if k in expected:
        if _ok(v, expected[k]):
            cleaned[k] = v
        else:
            cleaned[k] = f"{v} (отфильтровано ML как нерелевантное)"
    else:
        cleaned[k] = v

evidence = cleaned
evidence["_ml_preview"] = ml_preview
evidence["_ml_note"] = "ML: Naive Bayes классификация фрагментов требований; используется для фильтрации нерелевантных доказательств."
