import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Body
from .storage import (
    list_profiles, save_profile, get_profile, delete_profile,
    add_history, list_history
)
from .parser import read_text_by_extension, extract_rules
from .schemas import ExtractedRules
from .generator import generate_report_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "..", "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

app = FastAPI(title="Report Template Builder (VKR MVP)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/analyze", response_model=ExtractedRules)
async def analyze(file: UploadFile = File(...)):
    filename = file.filename or "uploaded"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".docx", ".txt", ".pdf"]:
        raise HTTPException(status_code=400, detail="На MVP поддерживаются только .docx и .txt")

    file_id = str(uuid.uuid4())
    saved_path = os.path.join(STORAGE_DIR, f"{file_id}{ext}")

    content = await file.read()
    with open(saved_path, "wb") as f:
        f.write(content)

    try:
        text = read_text_by_extension(saved_path, filename)
        rules = extract_rules(text)
        add_history(filename=filename, rules=rules.model_dump())
        return rules
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {e}")


@app.post("/api/generate")
async def generate(rules: ExtractedRules):
    file_id = str(uuid.uuid4())
    out_path = os.path.join(STORAGE_DIR, f"{file_id}_report_template.docx")
    try:
        generate_report_template(rules, out_path)
        return {"template_id": file_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {e}")


@app.get("/api/download/{template_id}")
async def download(template_id: str):
    path = os.path.join(STORAGE_DIR, f"{template_id}_report_template.docx")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="report_template.docx",
    )

@app.get("/api/history")
def history():
    return {"items": list_history()}


@app.get("/api/profiles")
def profiles():
    return {"items": list_profiles()}


@app.post("/api/profiles")
def create_profile(payload: dict = Body(...)):
    name = (payload.get("name") or "").strip()
    rules = payload.get("rules") or {}
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    item = save_profile(name=name, rules=rules)
    return item


@app.get("/api/profiles/{profile_id}")
def read_profile(profile_id: str):
    item = get_profile(profile_id)
    if not item:
        raise HTTPException(status_code=404, detail="profile not found")
    return item


@app.delete("/api/profiles/{profile_id}")
def remove_profile(profile_id: str):
    ok = delete_profile(profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="profile not found")
    return {"deleted": True}
