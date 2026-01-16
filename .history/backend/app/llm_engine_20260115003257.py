import json
import requests
from typing import Any, Dict, Optional


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "qwen2.5:3b"


def _safe_json_loads(s: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(s)
    except Exception:
        return None


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    # модель иногда окружает JSON пояснениями — достанем первый { ... } блок
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return _safe_json_loads(text[start : end + 1])


def llm_extract_rules(requirements_text: str, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Возвращает словарь с правилами. Стараемся вернуть строго JSON.
    """
    schema_hint = {
        "font_name": "Times New Roman",
        "font_size_pt": 14,
        "line_spacing": 1.5,
        "paragraph_indent_cm": 1.25,
        "margin_left_mm": 30,
        "margin_right_mm": 15,
        "margin_top_mm": 20,
        "margin_bottom_mm": 20,
        "page_numbering": True,
        "page_number_font_size_pt": 12,
        "page_number_position": "bottom_center"
    }

    prompt = f"""
Ты — помощник для извлечения требований к оформлению учебной работы из текста методических рекомендаций.
Верни ТОЛЬКО валидный JSON без комментариев и без обёрток markdown.

Нужно извлечь и нормализовать значения по полям:
- font_name (строка)
- font_size_pt (целое)
- line_spacing (число, например 1.5)
- paragraph_indent_cm (число, например 1.25)
- margin_left_mm/right_mm/top_mm/bottom_mm (целые, мм)
- page_numbering (true/false)
- page_number_font_size_pt (целое)
- page_number_position (строка из: "bottom_center", "bottom_right", "bottom_left", "top_center")

Если какое-то значение не найдено — используй разумное значение по умолчанию.

Пример формата (это подсказка, не вставляй как есть):
{json.dumps(schema_hint, ensure_ascii=False)}

Текст требований:
{requirements_text}
""".strip()

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1}
    }

    r = requests.post(OLLAMA_URL, json=payload, timeout=180)
    r.raise_for_status()
    data = r.json()

    raw = data.get("response", "") or ""
    parsed = _safe_json_loads(raw) or _extract_json_from_text(raw)
    if not parsed:
        # если модель не вернула JSON, отдаём пусто — дальше обработает hybrid/fallback
        return {"_llm_error": "LLM did not return JSON", "_llm_raw": raw[:5000]}
    return parsed
