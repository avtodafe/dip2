import asyncio
import os
from scraper import scrape_zakupki
from sheets import save_to_sheets, load_known_ids
from notifier import send_telegram_notification


async def main():
    print("🔍 Запуск парсинга zakupki.gov.ru...")

    # Загружаем уже известные ID закупок из таблицы
    known_ids = load_known_ids()
    print(f"📋 Уже известных закупок: {len(known_ids)}")

    # Парсим сайт
    results = await scrape_zakupki(keywords=["турбины", "турбин", "турбина"])
    print(f"🔎 Найдено закупок по запросу: {len(results)}")

    # Фильтруем только новые
    new_results = [r for r in results if r["purchase_number"] not in known_ids]
    print(f"🆕 Новых закупок: {len(new_results)}")

    if not new_results:
        print("✅ Новых закупок нет. Завершаем.")
        return

    # Сохраняем в Google Sheets
    save_to_sheets(new_results)
    print(f"💾 Сохранено в Google Sheets: {len(new_results)} записей")

    # Отправляем уведомление в Telegram
    await send_telegram_notification(new_results)
    print("📨 Уведомление отправлено в Telegram")


if __name__ == "__main__":
    asyncio.run(main())
