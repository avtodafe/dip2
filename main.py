import asyncio
import re
import os
from dotenv import load_dotenv
load_dotenv()

from scraper import scrape_zakupki
from sheets import save_to_sheets, load_known_ids, archive_expired
from notifier import send_telegram_notification


# Минимальная цена для тендеров по ТУРБИНАМ (для генераторов без ограничения)
MIN_PRICE_TURBINE = 8_000_000

# Ключевые слова, определяющие что тендер про турбины
TURBINE_WORDS = ['турбин']

# Слова, при наличии которых тендер считается нерелевантным
EXCLUDE_WORDS = [
    # Медицина / стоматология
    'стоматол', 'зубн', 'бормашин', 'dental',
    'медицин', 'хирург', 'ортопед', 'офтальмол',
    'наконечник', 'спирометр',
    # Звуковое оборудование
    'звуков', 'акустик',
    # Транспорт / дороги / автозапчасти
    'автомобильн', 'автотранспорт', 'автодорог',
    # Бытовое / прочее
    'насос', 'вентилятор', 'пылесос',
    'швейн', 'текстил', 'одежд',
    'воздуходувк', 'моечн',
]


def parse_price(price_str: str) -> float:
    """
    Парсит цену в российском формате.
    '254 167,50 руб' -> 254167.50
    '52 118 341,82 руб' -> 52118341.82
    """
    s = re.sub(r'[^\d\s,.]', '', price_str or '').replace(' ', '').replace(',', '.')
    parts = s.split('.')
    if len(parts) > 2:
        s = '.'.join(parts[:-1]) + '.' + parts[-1]
    try:
        return float(s)
    except ValueError:
        return 0.0


def is_relevant(result: dict) -> bool:
    """
    Проверяет:
    1. Статус — только 'Подача заявок'
    2. Если тендер про турбины — цена не менее 8 млн (для генераторов без ограничения)
    3. Название не содержит нерелевантных слов
    """
    status = result.get('status', '').strip().lower()
    if status != 'подача заявок':
        return False

    name = result.get('name', '')
    name_lower = name.lower()

    # Ценовой фильтр только для турбин
    is_turbine = any(w in name_lower for w in TURBINE_WORDS)
    if is_turbine:
        price = parse_price(result.get('price', ''))
        if price < MIN_PRICE_TURBINE:
            print(f"   Turbine < 8M ({price:,.0f}): {name[:60]}")
            return False

    # Фильтр нерелевантных слов
    for word in EXCLUDE_WORDS:
        if word in name_lower:
            print(f"   Excluded [{word}]: {name[:60]}")
            return False

    return True


async def main():
    print('Запуск парсинга zakupki.gov.ru...')

    print('Проверяем архив...')
    archive_expired()

    known_ids = load_known_ids()
    print(f'Уже известных закупок: {len(known_ids)}')

    results = await scrape_zakupki(keywords=[
        'турбины', 'турбин', 'турбина',
        'генератор', 'генераторы', 'генераторов',
    ])
    print(f'Найдено закупок по запросу: {len(results)}')

    relevant = [r for r in results if is_relevant(r)]
    print(f'Прошли фильтры: {len(relevant)} из {len(results)}')

    new_results = [r for r in relevant if r['purchase_number'] not in known_ids]
    print(f'Новых закупок: {len(new_results)}')

    if not new_results:
        print('Новых закупок нет. Завершаем.')
        return

    save_to_sheets(new_results)
    print(f'Сохранено в Google Sheets: {len(new_results)} записей')

    await send_telegram_notification(new_results)
    print('Уведомление отправлено в Telegram')


if __name__ == '__main__':
    asyncio.run(main())
