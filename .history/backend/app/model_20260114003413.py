from pydantic import BaseModel, Field
from typing import Dict, Any


class DocumentFormatting(BaseModel):
    font_name: str = "Times New Roman"
    font_size_pt: int = 14
    line_spacing: float = 1.5
    paragraph_indent_cm: float = 1.25


class PageMargins(BaseModel):
    left_mm: int = 30
    right_mm: int = 15
    top_mm: int = 20
    bottom_mm: int = 20


class PageNumbering(BaseModel):
    enabled: bool = True
    position: str = "bottom_center"
    font_name: str = "Times New Roman"
    font_size_pt: int = 12
    first_page_numbered: bool = False


class RequirementsModel(BaseModel):
    document: DocumentFormatting = Field(default_factory=DocumentFormatting)
    margins: PageMargins = Field(default_factory=PageMargins)
    page_numbering: PageNumbering = Field(default_factory=PageNumbering)

    # удобно для отладки/ВКР: что нашлось и где
    evidence: Dict[str, Any] = Field(default_factory=dict)
