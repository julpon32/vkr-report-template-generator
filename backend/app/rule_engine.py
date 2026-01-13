import re
from typing import Any, Dict, List, Optional, Tuple
from .model import RequirementsModel


def normalize_text(text: str) -> str:
    t = text.replace("\u00a0", " ")  # non-breaking space
    t = t.replace("ё", "е").replace("Ё", "Е")
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def split_fragments(text: str) -> List[str]:
    # простая сегментация под студенческий проект: переносы строк + точки
    # (для pdf это особенно полезно)
    raw = []
    for part in text.split("\n"):
        p = part.strip()
        if p:
            raw.append(p)

    joined = " ".join(raw)
    # разделим по . ; :
    frags = re.split(r"[.;:]\s+", joined)
    frags = [f.strip() for f in frags if f.strip()]
    return frags


def _extract_first_number(fragment: str) -> Optional[float]:
    # минимальная “регэксп-часть”: числа почти всегда проще всего доставать так
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

def apply_rules(text: str) -> RequirementsModel:
    model = RequirementsModel()
    evidence: Dict[str, Any] = {}

    t = normalize_text(text)
    fragments = split_fragments(t)

    # 1) Шрифт (ищем фрагмент где есть слово "шрифт" и упоминание названия)
    for frag in fragments:
        lf = frag.lower()
        if "шрифт" in lf:
            if "times new roman" in lf:
                model.document.font_name = "Times New Roman"
                model.page_numbering.font_name = "Times New Roman"
                evidence["font_name"] = frag
                break
            if "arial" in lf:
                model.document.font_name = "Arial"
                model.page_numbering.font_name = "Arial"
                evidence["font_name"] = frag
                break
            if "calibri" in lf:
                model.document.font_name = "Calibri"
                model.page_numbering.font_name = "Calibri"
                evidence["font_name"] = frag
                break

    # 2) Кегль / размер шрифта
    for frag in fragments:
        if _contains_all(frag, ["кегл"] ) or _contains_all(frag, ["размер", "шрифт"]) or _contains_all(frag, ["шрифт", "14"]):
            n = _extract_first_number(frag)
            if n and 6 <= n <= 30:
                model.document.font_size_pt = int(n)
                evidence["font_size_pt"] = frag
                break

    # 3) Межстрочный интервал
    for frag in fragments:
        if "межстроч" in frag.lower() or "интервал" in frag.lower():
            n = _extract_first_number(frag)
            if n and 1.0 <= n <= 3.0:
                model.document.line_spacing = float(n)
                evidence["line_spacing"] = frag
                break

    # 4) Абзацный отступ (см)
    for frag in fragments:
        lf = frag.lower()
        if "абзац" in lf and ("отступ" in lf or "красн" in lf):
            n = _extract_first_number(frag)
            if n and 0.5 <= n <= 3.0:
                model.document.paragraph_indent_cm = float(n)
                evidence["paragraph_indent_cm"] = frag
                break

    # 5) Поля (мм). Ищем контекст “поле/поля” + левое/правое/верхнее/нижнее
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

    # 6) Нумерация страниц
    for frag in fragments:
        lf = frag.lower()
        if "нумерац" in lf and "страниц" in lf:
            model.page_numbering.enabled = True
            evidence["page_numbering"] = frag

        if "внизу" in lf and "цент" in lf and "номер" in lf:
            model.page_numbering.position = "bottom_center"
            evidence["page_number_position"] = frag

        if "номер" in lf and "страниц" in lf and "шрифт" in lf:
            # пример: "шрифт номера страницы — Times New Roman, размер 12"
            n = _extract_first_number(frag)
            if n and 6 <= n <= 30:
                model.page_numbering.font_size_pt = int(n)
                evidence["page_number_font_size_pt"] = frag

    model.page_numbering.first_page_numbered = False

    # обрезаем “доказательства”, чтобы не тянуть большие фрагменты из PDF
    evidence_clipped = {}
    for k, v in evidence.items():
        evidence_clipped[k] = _clip(v, 300)

    model.evidence = evidence_clipped
    return model
