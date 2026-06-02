import os
import json
from datetime import date, datetime

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

HEADERS = ['Номер закупки', 'Название', 'Заказчик', 'Цена', 'Подача заявок до', 'Публикация', 'Статус', 'Закон', 'Ссылка']
DEADLINE_COL = 4   # 0-based: 'Подача заявок до'
STATUS_COL = 6     # 0-based: 'Статус'


def _get_client():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_sheets():
    client = _get_client()
    spreadsheet_id = os.environ.get("SPREADSHEET_ID", "")
    spreadsheet = client.open_by_key(spreadsheet_id)

    # Лист "Закупки"
    try:
        main_sheet = spreadsheet.worksheet("Закупки")
    except gspread.WorksheetNotFound:
        main_sheet = spreadsheet.add_worksheet("Закупки", rows=1000, cols=len(HEADERS))
        main_sheet.append_row(HEADERS)

    # Лист "Архив"
    try:
        archive_sheet = spreadsheet.worksheet("Архив")
    except gspread.WorksheetNotFound:
        archive_sheet = spreadsheet.add_worksheet("Архив", rows=1000, cols=len(HEADERS))
        archive_sheet.append_row(HEADERS)

    return main_sheet, archive_sheet


def load_known_ids() -> set:
    """Загружает номера закупок из листа Закупки."""
    try:
        main_sheet, _ = _get_sheets()
        rows = main_sheet.get_all_values()
        ids = set()
        for row in rows[1:]:  # пропускаем заголовок
            if row and row[0]:
                ids.add(row[0].strip())
        return ids
    except Exception as e:
        print(f"Ошибка загрузки known_ids: {e}")
        return set()


def save_to_sheets(results: list):
    """Добавляет новые закупки в лист Закупки."""
    if not results:
        return
    try:
        main_sheet, _ = _get_sheets()
        rows = []
        for r in results:
            rows.append([
                r.get('purchase_number', ''),
                r.get('name', ''),
                r.get('customer', ''),
                r.get('price', ''),
                r.get('deadline_application', ''),
                r.get('published', ''),
                r.get('status', ''),
                r.get('law', ''),
                r.get('url', ''),
            ])
        main_sheet.append_rows(rows)
        print(f"Добавлено {len(rows)} строк в Google Sheets")
    except Exception as e:
        print(f"Ошибка сохранения в Sheets: {e}")


def archive_expired():
    """Перемещает просроченные или неактивные закупки в архив."""
    try:
        main_sheet, archive_sheet = _get_sheets()
        rows = main_sheet.get_all_values()
        if len(rows) <= 1:
            print("Просроченных закупок нет")
            return

        today = date.today()
        to_archive = []
        to_keep = [rows[0]]  # заголовок

        for row in rows[1:]:
            deadline_str = row[DEADLINE_COL].strip() if len(row) > DEADLINE_COL else ''
            status_str = row[STATUS_COL].strip().lower() if len(row) > STATUS_COL else ''

            expired = False

            # По дате
            if deadline_str:
                try:
                    deadline = datetime.strptime(deadline_str, '%d.%m.%Y').date()
                    if deadline < today:
                        expired = True
                except ValueError:
                    pass

            # По статусу — всё кроме "подача заявок" уходит в архив
            if status_str and status_str != 'подача заявок':
                expired = True

            if expired:
                to_archive.append(row)
            else:
                to_keep.append(row)

        if to_archive:
            archive_sheet.append_rows(to_archive)
            main_sheet.clear()
            main_sheet.append_rows(to_keep)
            print(f"Архивировано просроченных закупок: {len(to_archive)}")
            print(f"В листе Закупки осталось: {len(to_keep) - 1} строк")
        else:
            print("Просроченных закупок нет")

    except Exception as e:
        print(f"Ошибка архивирования: {e}")
