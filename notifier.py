import os
import asyncio
import aiohttp

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MESSAGE_LENGTH = 4000


async def send_telegram_notification(results: list[dict]):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("⚠️ TELEGRAM_TOKEN или TELEGRAM_CHAT_ID не заданы")
        return

    url = TELEGRAM_API.format(token=token)

    # Шапка сообщения
    header = f"🔔 *Новые закупки по турбинам* — найдено {len(results)} шт.\n\n"

    messages = []
    current = header

    for i, r in enumerate(results, 1):
        price = r.get("price", "—")
        entry = (
            f"*{i}. {r.get('name', 'Без названия')[:80]}*\n"
            f"📋 № `{r.get('purchase_number', '—')}`\n"
            f"🏢 {r.get('customer', '—')[:60]}\n"
            f"💰 {price}\n"
            f"📅 Подача заявок: {r.get('deadline_application', '—')}\n"
            f"⏱ Исполнение: {r.get('deadline_execution', '—')}\n"
            f"⚖️ {r.get('law', '—')} | {r.get('status', '—')}\n"
            f"🔗 [Открыть]({r.get('url', '')})\n\n"
        )

        if len(current) + len(entry) > MAX_MESSAGE_LENGTH:
            messages.append(current)
            current = entry
        else:
            current += entry

    if current:
        messages.append(current)

    async with aiohttp.ClientSession() as session:
        for msg in messages:
            payload = {
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"⚠️ Ошибка Telegram API: {resp.status} — {text}")
                else:
                    print(f"✅ Сообщение отправлено ({len(msg)} символов)")
            await asyncio.sleep(0.5)
