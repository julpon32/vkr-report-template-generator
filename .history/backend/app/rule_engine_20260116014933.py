import re
from typing import Any, Dict, List, Optional, Tuple
from .model import RequirementsModel


def normalize_text(text: str) -> str:
    t = text.replace("\u00a0", " ")  # non-breaking space
    t = t.replace("ё", "е").replace("Ё", "Е")
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def split_fragments(text: str) -> List[str]:
    lines = []
    for part in text.split("\n"):
        p = part.strip()
        if not p:
            continue
        if re.search(r"\.{8,}", p):
            continue
        lines.append(p)

    frags: List[str] = []
    for ln in lines:
        chunks = re.split(r"[.;:]\s+| — | – | - ", ln)
        for c in chunks:
            c = c.strip()
            if not c:
                continue
            if len(c) > 400:
                continue
            frags.append(c)

    # удаляем дубли
    seen = set()
    out = []
    for f in frags:
        key = f.lower()
        if key not in seen:
            seen.add(key)
            out.append(f)

    return out


def _extract_first_number(fragment: str) -> Optional[float]:
    m = re.search(r"(\d+(?:[.,]\d+)?)", fragment)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def _extract_mm(fragment: str) -> Optional[int]:
    # числа в мм: берем первое число и округляем
    val = _extract_first_number(fragment)
    if val is None:
        return None
    return int(round(val))


def _contains_all(fragment: str, keywords: List[str]) -> bool:
    f = fragment.lower()
    return all(k.lower() in f for k in keywords)

def _clip(text: str, limit: int = 300) -> str:
    t = " ".join(str(text).split())
    if len(t) <= limit:
        return t
    return t[:limit].rstrip() + "…"


def _is_heading_context(frag: str) -> bool:
    lf = frag.lower()
    return ("заголов" in lf) or ("глава" in lf)

def _is_page_number_context(frag: str) -> bool:
    lf = frag.lower()
    return ("номер страницы" in lf) or ("нумерац" in lf) or ("колонтитул" in lf)

def _pick_best_with_score(fragments: List[str], predicate, scorer) -> Tuple[Optional[str], Optional[int]]:
    best = None
    best_score = None
    for frag in fragments:
        if not predicate(frag):
            continue
        s = int(scorer(frag))
        if best is None or s > best_score:
            best = frag
            best_score = s
    return best, best_score


def _score_font_fragment(frag: str) -> int:
    lf = frag.lower()
    score = 0

    if "основн" in lf or "основного текста" in lf:
        score += 5

    if "сноск" in lf or "примечан" in lf:
        score -= 5
    if "таблиц" in lf or "рисунк" in lf or "подпис" in lf:
        score -= 3
    if "заголов" in lf or "глава" in lf:
        score -= 3
    if "номер страницы" in lf or "нумерац" in lf:
        score -= 5

    if "times new roman" in lf or "arial" in lf or "calibri" in lf:
        score += 2

    return score

def _pick_best(fragments: List[str], predicate, scorer) -> Optional[str]:
    best = None
    best_score = None
    for frag in fragments:
        if not predicate(frag):
            continue
        s = scorer(frag)
        if best is None or s > best_score:
            best = frag
            best_score = s
    return best

def _score_textbody_fragment(frag: str) -> int:
    lf = frag.lower()
    score = 0
    if "основн" in lf or "основного текста" in lf:
        score += 5
    if "сноск" in lf or "примечан" in lf:
        score -= 5
    if "таблиц" in lf or "рисунк" in lf or "подпис" in lf:
        score -= 3
    if "заголов" in lf or "глава" in lf:
        score -= 3
    if "по левому" in lf:
        score -= 2  # часто про подписи/перечни
    return score

def apply_rules(text: str, fragments_override: Optional[List[str]] = None) -> RequirementsModel:
    model = RequirementsModel()
    evidence: Dict[str, Any] = {}

    t = normalize_text(text)
    fragments = fragments_override if fragments_override is not None else split_fragments(t)

    # -------- ШРИФТ ДОКУМЕНТА (основной текст) --------
    def _is_doc_font_candidate(frag: str) -> bool:
        lf = frag.lower()
        if "шрифт" not in lf:
            return False
        if not ("times new roman" in lf or "arial" in lf or "calibri" in lf):
            return False
        if _is_heading_context(frag) or _is_page_number_context(frag):
            return False
        return True

    def _score_doc_font_fragment(frag: str) -> int:
        lf = frag.lower()
        score = 0
        if "основн" in lf or "основного текста" in lf:
            score += 10
        if "текст" in lf:
            score += 3

        if "таблиц" in lf or "рисунк" in lf or "подпис" in lf:
            score -= 3
        if "сноск" in lf or "примечан" in lf:
            score -= 5

        if "times new roman" in lf or "arial" in lf or "calibri" in lf:
            score += 2
        return score

    best_doc_font, best_doc_font_score = _pick_best_with_score(
        fragments, _is_doc_font_candidate, _score_doc_font_fragment
    )

    if best_doc_font and (best_doc_font_score is not None) and best_doc_font_score >= 2:
        lf = best_doc_font.lower()
        if "times new roman" in lf:
            model.document.font_name = "Times New Roman"
        elif "arial" in lf:
            model.document.font_name = "Arial"
        elif "calibri" in lf:
            model.document.font_name = "Calibri"
        evidence["font_name"] = best_doc_font

    # -------- РАЗМЕР ШРИФТА ОСНОВНОГО ТЕКСТА --------
    def _is_doc_fontsize_candidate(frag: str) -> bool:
        lf = frag.lower()
        # нужно упоминание шрифта/кегля и число
        if ("шрифт" not in lf) and ("кегл" not in lf) and ("кегль" not in lf):
            return False
        n = _extract_first_number(frag)
        if n is None:
            return False
        # НЕ берём "шрифт заголовка" и "номер страницы" как размер основного текста
        if _is_heading_context(frag) or _is_page_number_context(frag):
            return False
        return True

    def _score_doc_fontsize_fragment(frag: str) -> int:
        lf = frag.lower()
        score = 0
        if "основн" in lf or "основного текста" in lf:
            score += 10
        if "текст" in lf:
            score += 3

        # штрафуем частые ложные контексты
        if "таблиц" in lf or "рисунк" in lf or "подпис" in lf:
            score -= 3
        if "снос" in lf or "примечан" in lf:
            score -= 5

        # бонус, если рядом есть название шрифта
        if "times new roman" in lf or "arial" in lf or "calibri" in lf:
            score += 1
        return score

    best_doc_fontsize, best_doc_fontsize_score = _pick_best_with_score(
        fragments, _is_doc_fontsize_candidate, _score_doc_fontsize_fragment
    )

    if best_doc_fontsize and (best_doc_fontsize_score is not None) and best_doc_fontsize_score >= 1:
        n = _extract_first_number(best_doc_fontsize)
        if n and 6 <= n <= 30:
            model.document.font_size_pt = int(n)
            evidence["font_size_pt"] = best_doc_fontsize

    # -------- ШРИФТ НУМЕРАЦИИ СТРАНИЦ --------
    def _is_page_font_candidate(frag: str) -> bool:
        lf = frag.lower()
        if not _is_page_number_context(frag):
            return False
        return ("times new roman" in lf or "arial" in lf or "calibri" in lf)

    best_page_font, best_page_font_score = _pick_best_with_score(
        fragments, _is_page_font_candidate, _score_font_fragment
    )

    if best_page_font and (best_page_font_score is not None) and best_page_font_score >= -2:
        lf = best_page_font.lower()
        if "times new roman" in lf:
            model.page_numbering.font_name = "Times New Roman"
        elif "arial" in lf:
            model.page_numbering.font_name = "Arial"
        elif "calibri" in lf:
            model.page_numbering.font_name = "Calibri"
        evidence["page_number_font_name"] = best_page_font


    for frag in fragments:
        if _contains_all(frag, ["кегл"] ) or _contains_all(frag, ["размер", "шрифт"]) or _contains_all(frag, ["шрифт", "14"]):
            n = _extract_first_number(frag)
            if n and 6 <= n <= 30:
                model.document.font_size_pt = int(n)
                evidence["font_size_pt"] = frag
                break

    def _is_spacing_candidate(frag: str) -> bool:
        lf = frag.lower()
        return ("межстроч" in lf or "интервал" in lf)

    best_spacing = _pick_best(fragments, _is_spacing_candidate, _score_textbody_fragment)
    if best_spacing:
        n = _extract_first_number(best_spacing)
        if n and 1.0 <= n <= 3.0:
            model.document.line_spacing = float(n)
            evidence["line_spacing"] = best_spacing

    def _is_indent_candidate(frag: str) -> bool:
        lf = frag.lower()
        return ("абзац" in lf and ("отступ" in lf or "красн" in lf)) or ("отступ" in lf and ("первой строки" in lf))

    best_indent = _pick_best(fragments, _is_indent_candidate, _score_textbody_fragment)
    if best_indent:
        n = _extract_first_number(best_indent)
        if n and 0.5 <= n <= 3.0:
            model.document.paragraph_indent_cm = float(n)
            evidence["paragraph_indent_cm"] = best_indent

    for frag in fragments:
        lf = frag.lower()
        if "лев" in lf and "пол" in lf and ("мм" in lf or "миллимет" in lf):
            v = _extract_mm(frag)
            if v:
                model.margins.left_mm = v
                evidence["margin_left_mm"] = frag

        if "прав" in lf and "пол" in lf and ("мм" in lf or "миллимет" in lf):
            v = _extract_mm(frag)
            if v:
                model.margins.right_mm = v
                evidence["margin_right_mm"] = frag

        if "верх" in lf and "пол" in lf and ("мм" in lf or "миллимет" in lf):
            v = _extract_mm(frag)
            if v:
                model.margins.top_mm = v
                evidence["margin_top_mm"] = frag

        if "ниж" in lf and "пол" in lf and ("мм" in lf or "миллимет" in lf):
            v = _extract_mm(frag)
            if v:
                model.margins.bottom_mm = v
                evidence["margin_bottom_mm"] = frag

    for frag in fragments:
        lf = frag.lower()
        if "нумерац" in lf and "страниц" in lf:
            model.page_numbering.enabled = True
            evidence["page_numbering"] = frag

        if "внизу" in lf and "цент" in lf and "номер" in lf:
            model.page_numbering.position = "bottom_center"
            evidence["page_number_position"] = frag

        if "номер" in lf and "страниц" in lf and "шрифт" in lf:

            n = _extract_first_number(frag)
            if n and 6 <= n <= 30:
                model.page_numbering.font_size_pt = int(n)
                evidence["page_number_font_size_pt"] = frag

    model.page_numbering.first_page_numbered = False

    evidence_clipped = {}
    for k, v in evidence.items():
        evidence_clipped[k] = _clip(v, 300)

    model.evidence = evidence_clipped
    return model

def filter_fragments_by_ml(fragments: List[str], ml_tags: List[Dict[str, Any]], label: str, min_score: float = 0.45) -> List[str]:
    out = []
    for item in ml_tags:
        if item.get("label") == label and float(item.get("score", 0)) >= min_score:
            out.append(item.get("fragment", ""))
    return [x for x in out if x]
