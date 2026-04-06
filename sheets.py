import os
import json
import urllib.request
import urllib.parse

APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_URL")


def load_known_ids() -> set:
    """Пока храним известные ID только в памяти — таблица проверяется через Apps Script."""
    return set()


def save_to_sheets(results: list[dict]):
    if not results or not APPS_SCRIPT_URL:
        print("⚠️ Нет данных или не задан APPS_SCRIPT_URL")
        return

    data = json.dumps(results).encode("utf-8")
    req = urllib.request.Request(
        APPS_SCRIPT_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = resp.read().decode()
        print(f"✅ Apps Script ответил: {result}")
