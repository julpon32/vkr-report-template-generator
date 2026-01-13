import json
import os
import time
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "..", "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

PROFILES_PATH = os.path.join(STORAGE_DIR, "profiles.json")
HISTORY_PATH = os.path.join(STORAGE_DIR, "history.json")
TEMPLATES_PATH = os.path.join(STORAGE_DIR, "templates.json")

def _read_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def list_profiles() -> List[Dict[str, Any]]:
    data = _read_json(PROFILES_PATH, [])
    # ожидаем список объектов: {id, name, rules, created_at}
    return data


def save_profile(name: str, rules: Dict[str, Any]) -> Dict[str, Any]:
    profiles = _read_json(PROFILES_PATH, [])
    profile_id = f"p_{int(time.time() * 1000)}"
    item = {
        "id": profile_id,
        "name": name,
        "rules": rules,
        "created_at": int(time.time()),
    }
    profiles.insert(0, item)
    _write_json(PROFILES_PATH, profiles[:50])  # ограничим до 50 профилей
    return item


def get_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    profiles = _read_json(PROFILES_PATH, [])
    for p in profiles:
        if p.get("id") == profile_id:
            return p
    return None


def delete_profile(profile_id: str) -> bool:
    profiles = _read_json(PROFILES_PATH, [])
    new_profiles = [p for p in profiles if p.get("id") != profile_id]
    if len(new_profiles) == len(profiles):
        return False
    _write_json(PROFILES_PATH, new_profiles)
    return True


def add_history(filename: str, rules: Dict[str, Any]) -> None:
    history = _read_json(HISTORY_PATH, [])
    item = {
        "id": f"h_{int(time.time() * 1000)}",
        "filename": filename,
        "created_at": int(time.time()),
        "rules": rules,
    }
    history.insert(0, item)
    _write_json(HISTORY_PATH, history[:30])  # последние 30


def list_history() -> List[Dict[str, Any]]:
    return _read_json(HISTORY_PATH, [])

def add_template(template_id: str, rules: Dict[str, Any]) -> None:
    data = _read_json(TEMPLATES_PATH, [])
    item = {
        "id": f"t_{int(time.time() * 1000)}",
        "template_id": template_id,
        "created_at": int(time.time()),
        "rules": rules,
    }
    data.insert(0, item)
    _write_json(TEMPLATES_PATH, data[:30])  # последние 30

def list_templates() -> List[Dict[str, Any]]:
    return _read_json(TEMPLATES_PATH, [])
