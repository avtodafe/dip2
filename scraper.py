import asyncio
import random
from playwright.async_api import async_playwright

BASE_URL = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"


async def human_delay(min_ms=800, max_ms=2500):
    """Случайная пауза, как у человека."""
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def human_type(page, selector, text):
    """Вводим текст посимвольно с рандомными паузами."""
    await page.click(selector)
    await human_delay(300, 700)
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.18))


async def scrape_zakupki(keywords: list[str]) -> list[dict]:
    results = []
    seen_numbers = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            locale="ru-RU",
        )

        # Скрываем признаки автоматизации
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        """)

        page = await context.new_page()

        for keyword in keywords:
            print(f"🔍 Ищем: «{keyword}»")
            try:
                await page.goto("https://zakupki.gov.ru/epz/order/extendedsearch/results.html", wait_until="domcontentloaded")
                await human_delay(1500, 3000)

                # Вводим ключевое слово в поле поиска
                search_input = page.locator('input[name="searchString"]').first
                await search_input.wait_for(state="visible", timeout=15000)
                await search_input.click()
                await human_delay(400, 800)
                await search_input.fill("")
                await human_type(page, 'input[name="searchString"]', keyword)
                await human_delay(500, 1000)

                # Нажимаем Enter или кнопку поиска
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("domcontentloaded")
                await human_delay(2000, 4000)

                # Парсим страницы результатов (до 5 страниц)
                for page_num in range(1, 6):
                    print(f"  📄 Страница {page_num}...")
                    items = await parse_page(page)
                    for item in items:
                        if item["purchase_number"] not in seen_numbers:
                            seen_numbers.add(item["purchase_number"])
                            results.append(item)

                    # Переходим на следующую страницу
                    next_btn = page.locator('a.paginator-button-next')
                    if await next_btn.count() == 0:
                        break
                    await next_btn.click()
                    await page.wait_for_load_state("domcontentloaded")
                    await human_delay(1500, 3500)

            except Exception as e:
                print(f"  ⚠️ Ошибка при поиске «{keyword}»: {e}")
                continue

        await browser.close()

    return results


async def parse_page(page) -> list[dict]:
    """Парсим карточки закупок на текущей странице."""
    items = []

    cards = page.locator('div.search-registry-entry-block')
    count = await cards.count()

    for i in range(count):
        try:
            card = cards.nth(i)
            item = {}

            # Номер закупки
            num_el = card.locator('div.registry-entry__header-mid__number a')
            if await num_el.count() > 0:
                text = await num_el.inner_text()
                href = await num_el.get_attribute("href")
                item["purchase_number"] = text.strip().replace("№ ", "")
                item["url"] = f"https://zakupki.gov.ru{href}" if href else ""
            else:
                continue

            # Наименование
            name_el = card.locator('div.registry-entry__body-value').first
            item["name"] = (await name_el.inner_text()).strip() if await name_el.count() > 0 else ""

            # Заказчик
            customer_el = card.locator('div.registry-entry__body-href a')
            item["customer"] = (await customer_el.inner_text()).strip() if await customer_el.count() > 0 else ""

            # Начальная цена
            price_el = card.locator('div.price-block__value')
            item["price"] = (await price_el.inner_text()).strip() if await price_el.count() > 0 else ""

            # Сроки
            dates = card.locator('div.data-block__value')
            date_texts = []
            for j in range(await dates.count()):
                date_texts.append((await dates.nth(j).inner_text()).strip())

            item["deadline_application"] = date_texts[0] if len(date_texts) > 0 else ""
            item["deadline_execution"] = date_texts[1] if len(date_texts) > 1 else ""

            # Статус
            status_el = card.locator('div.registry-entry__header-mid__title')
            item["status"] = (await status_el.inner_text()).strip() if await status_el.count() > 0 else ""

            # Закон (44-ФЗ / 223-ФЗ)
            law_el = card.locator('div.registry-entry__header-top__title')
            item["law"] = (await law_el.inner_text()).strip() if await law_el.count() > 0 else ""

            items.append(item)

        except Exception as e:
            print(f"    ⚠️ Ошибка парсинга карточки {i}: {e}")
            continue

    return items
