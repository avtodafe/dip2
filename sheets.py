import os
import json
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "Номер закупки",
    "Наименование",
    "Заказчик",
    "Начальная цена",
    "Срок подачи заявок",
    "Срок исполнения",
    "Статус",
    "Закон",
    "Ссылка",
]


def get_sheet():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    spreadsheet_id = os.environ.get("SPREADSHEET_ID")

    if not creds_json or not spreadsheet_id:
        raise ValueError("Не заданы GOOGLE_CREDENTIALS_JSON или SPREADSHEET_ID")

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(spreadsheet_id)

    # Берём первый лист или создаём "Закупки"
    try:
        sheet = spreadsheet.worksheet("Закупки")
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title="Закупки", rows=1000, cols=20)
        sheet.append_row(HEADERS)

    return sheet


def load_known_ids() -> set:
    """Загружаем все уже записанные номера закупок."""
    try:
        sheet = get_sheet()
        all_values = sheet.get_all_values()
        if len(all_values) <= 1:
            return set()
        # Первая колонка — номер закупки (пропускаем заголовок)
        return {row[0] for row in all_values[1:] if row[0]}
    except Exception as e:
        print(f"⚠️ Не удалось загрузить известные ID: {e}")
        return set()


def save_to_sheets(results: list[dict]):
    """Записываем новые закупки в таблицу."""
    if not results:
        return

    sheet = get_sheet()

    rows = []
    for r in results:
        rows.append([
            r.get("purchase_number", ""),
            r.get("name", ""),
            r.get("customer", ""),
            r.get("price", ""),
            r.get("deadline_application", ""),
            r.get("deadline_execution", ""),
            r.get("status", ""),
            r.get("law", ""),
            r.get("url", ""),
        ])

    sheet.append_rows(rows, value_input_option="USER_ENTERED")
    print(f"✅ Добавлено {len(rows)} строк в Google Sheets")
