import urllib.request
import urllib.parse
import json
import time
import random


def search_by_api(keyword: str) -> list[dict]:
    """Используем официальный API zakupki.gov.ru"""
    url = "https://api.zakupki.gov.ru/api/search/searches"
    params = urllib.parse.urlencode({
        "q": keyword,
        "size": 50,
        "from": 0,
    })
    full_url = f"{url}?{params}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    req = urllib.request.Request(full_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return parse_api_response(data)
    except Exception as e:
        print(f"⚠️ Ошибка API для «{keyword}»: {e}")
        return []


def parse_api_response(data: dict) -> list[dict]:
    results = []
    items = data.get("data", data.get("items", data.get("result", [])))
    if isinstance(data, list):
        items = data
    for item in items:
        results.append({
            "purchase_number": str(item.get("regNum", item.get("number", ""))),
            "name": item.get("name", item.get("purchaseName", "")),
            "customer": item.get("customer", {}).get("name", "") if isinstance(item.get("customer"), dict) else str(item.get("customer", "")),
            "price": str(item.get("maxPrice", item.get("initialSum", ""))),
            "deadline_application": str(item.get("biddingDeadline", item.get("endDate", ""))),
            "deadline_execution": str(item.get("contractEndDate", "")),
            "status": item.get("status", ""),
            "law": item.get("federalLaw", ""),
            "url": f"https://zakupki.gov.ru/epz/order/notice/ea44/view/common-info.html?regNumber={item.get('regNum', '')}",
        })
    return results


async def scrape_zakupki(keywords: list[str]) -> list[dict]:
    results = []
    seen = set()
    for keyword in keywords:
        print(f"🔍 Ищем: «{keyword}»")
        items = search_by_api(keyword)
        print(f"  Найдено: {len(items)}")
        for item in items:
            num = item.get("purchase_number", "")
            if num and num not in seen:
                seen.add(num)
                results.append(item)
        time.sleep(random.uniform(1, 2))
    return results
