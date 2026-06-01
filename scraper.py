import urllib.request
import urllib.parse
import re
import time
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}

BASE_URL = "https://zakupki.gov.ru"
SEARCH_URL = f"{BASE_URL}/epz/order/extendedsearch/results.html"


def _get_html(keyword: str, page: int = 1) -> str:
    params = urllib.parse.urlencode({
        "searchString": keyword,
        "morphology": "on",
        "fz44": "on",
        "fz223": "on",
        "recordsPerPage": "_50",
        "pageNumber": str(page),
        "sortDirection": "false",
        "sortBy": "UPDATE_DATE",
    })
    req = urllib.request.Request(f"{SEARCH_URL}?{params}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _clean(text: str) -> str:
    import html as html_mod
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_mod.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_entries(html: str) -> list:
    results = []

    # Поддерживаем оба формата URL:
    # 44-FZ: https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber=...
    # 223-FZ: https://zakupki.gov.ru/223/purchase/public/purchase/info/common-info.html?regNumber=...
    pattern = r'"(https://zakupki\.gov\.ru(?:/epz/order/notice/[^"?]+|/\d+/purchase/public/purchase/info)/common-info\.html\?regNumber=([0-9A-Z\-]+))"'
    matches = list(re.finditer(pattern, html))

    for i, m in enumerate(matches):
        full_url = m.group(1)
        reg_number = m.group(2)

        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        block = html[start:end]

        # Название
        name_m = re.search(
            r'Объект закупки</div>\s*<div[^>]*>\s*(.*?)\s*</div>',
            block, re.DOTALL
        )
        name = _clean(name_m.group(1)) if name_m else ""

        # Заказчик
        customer_m = re.search(
            r'Заказчик</div>\s*<div[^>]*>\s*(?:<a[^>]*>)?\s*(.*?)\s*(?:</a>)?\s*</div>',
            block, re.DOTALL
        )
        customer = _clean(customer_m.group(1)) if customer_m else ""

        # Цена
        price_m = re.search(
            r'price-block__value[^>]*>\s*([\d\s,.]+\s*(?:&#8381;|руб\.?|₽)?)',
            block, re.DOTALL
        )
        price = _clean(price_m.group(1)) if price_m else ""

        # Дата окончания подачи заявок
        deadline_m = re.search(
            r'Окончание подачи заявок</div>\s*<div[^>]*>\s*(\d{2}\.\d{2}\.\d{4})',
            block, re.DOTALL
        )
        deadline_app = deadline_m.group(1) if deadline_m else ""

        # Дата публикации
        published_m = re.search(
            r'Размещено</div>\s*<div[^>]*>\s*(\d{2}\.\d{2}\.\d{4})',
            block, re.DOTALL
        )
        published = published_m.group(1) if published_m else ""

        # Статус
        status_m = re.search(r'registry-entry__header-mid__title[^>]*>\s*(.*?)\s*</div>', block, re.DOTALL)
        status = _clean(status_m.group(1)) if status_m else ""

        # Закон
        law_m = re.search(r'(44-ФЗ|223-ФЗ|615-ПП)', block)
        law = law_m.group(1) if law_m else ""

        results.append({
            "purchase_number": reg_number,
            "name": name[:300],
            "customer": customer[:200],
            "price": price,
            "deadline_application": deadline_app,
            "published": published,
            "status": status,
            "law": law,
            "url": full_url,
        })

    return results


async def scrape_zakupki(keywords: list) -> list:
    all_results = []
    seen = set()

    for keyword in keywords:
        print(f"Searching: {keyword}")
        try:
            html = _get_html(keyword, page=1)
            entries = _parse_entries(html)
            print(f"   Found: {len(entries)}")
            for entry in entries:
                num = entry.get("purchase_number", "")
                if num and num not in seen:
                    seen.add(num)
                    all_results.append(entry)
        except Exception as e:
            print(f"Error for {keyword}: {e}")
        time.sleep(random.uniform(2, 4))

    return all_results
