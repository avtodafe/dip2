import urllib.request
import urllib.parse
import json
import time
import random


API_URL = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"
SEARCH_API = "https://zakupki.gov.ru/epz/order/extendedsearch/getTable.html"


def search_zakupki(keyword: str) -> list[dict]:
    params = urllib.parse.urlencode({
        "searchString": keyword,
        "morphology": "on",
        "search-filter": "Дата+размещения",
        "pageNumber": "1",
        "sortDirection": "false",
        "recordsPerPage": "_50",
        "showLotsInfoHidden": "false",
        "sortBy": "UPDATE_DATE",
        "fz44": "on",
        "fz223": "on",
        "af": "on",
        "ca": "on",
        "pc": "on",
        "pa": "on",
    })

    url = f"{SEARCH_API}?{params}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*",
        "Referer": "https://zakupki.gov.ru/epz/order/extendedsearch/results.html",
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8")
            return parse_response(data, keyword)
    except Exception as e:
        print(f"⚠️ Ошибка запроса для «{keyword}»: {e}")
        return []


def parse_response(html: str, keyword: str) -> list[dict]:
    """Парсим HTML-ответ от API."""
    from html.parser import HTMLParser

    results = []

    class ZakupkiParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.current = {}
            self.capture = None
            self.depth = 0

        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            classes = attrs_dict.get("class", "")

            if "registry-entry__header-mid__number" in classes:
                self.capture = "number"
            elif "registry-entry__body-value" in classes and "name" not in self.current:
                self.capture = "name"
            elif "registry-entry__body-href" in classes:
                self.capture = "customer"
            elif "price-block__value" in classes:
                self.capture = "price"

            if tag == "a" and self.capture == "number":
                href = attrs_dict.get("href", "")
                if href:
                    self.current["url"] = f"https://zakupki.gov.ru{href}"

        def handle_data(self, data):
            data = data.strip()
            if not data:
                return
            if self.capture == "number":
                self.current["purchase_number"] = data.replace("№ ", "").strip()
                self.capture = None
            elif self.capture == "name":
                self.current["name"] = data
                self.capture = None
            elif self.capture == "customer":
                self.current["customer"] = data
                self.capture = None
            elif self.capture == "price":
                self.current["price"] = data
                self.capture = None

        def handle_endtag(self, tag):
            if tag == "div" and self.current.get("purchase_number"):
                if len(self.current) >= 2:
                    results.append({**self.current})
                    self.current = {}

    parser = ZakupkiParser()
    parser.feed(html)
    return results


async def scrape_zakupki(keywords: list[str]) -> list[dict]:
    results = []
    seen = set()

    for keyword in keywords:
        print(f"🔍 Ищем: «{keyword}»")
        items = search_zakupki(keyword)
        for item in items:
            num = item.get("purchase_number", "")
            if num and num not in seen:
                seen.add(num)
                # Заполняем недостающие поля
                item.setdefault("deadline_application", "")
                item.setdefault("deadline_execution", "")
                item.setdefault("status", "")
                item.setdefault("law", "")
                results.append(item)

        time.sleep(random.uniform(1, 3))

    return results
