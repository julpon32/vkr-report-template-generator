from pydantic import BaseModel
from typing import Optional, Dict, Any


class ExtractedRules(BaseModel):
    # базовые правила оформления
    font_name: str = "Times New Roman"
    font_size_pt: int = 14
    line_spacing: float = 1.5

    # поля в мм
    margin_left_mm: int = 30
    margin_right_mm: int = 15
    margin_top_mm: int = 20
    margin_bottom_mm: int = 20

    # нумерация страниц
    page_numbering: bool = True
    page_number_font_size_pt: int = 12
    page_number_position: str = "bottom_center"

    # диагностическая информация
    raw_matches: Dict[str, Any] = {}
    source_summary: Optional[str] = None

    # ВНУТРЕННЯЯ МОДЕЛЬ (для ВКР и для расширений)
    requirements_model: Dict[str, Any] = {}
