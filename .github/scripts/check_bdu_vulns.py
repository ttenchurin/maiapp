#!/usr/bin/env python3
import json
import sys
import time
import requests
from bs4 import BeautifulSoup

BDU_SEARCH_URL = "https://bdu.fstec.ru/vul?ajax=vuls&search={}"
HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "ru,en;q=0.9",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Referer": "https://bdu.fstec.ru/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 YaBrowser/26.3.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "YaBrowser";v="26.3", "Yowser";v="2.5", "YaBrowserCorp";v="144"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"'
}
DELAY = 1          # секунды между запросами к разным пакетам
TIMEOUT = 30       # секунды ожидания ответа
RETRIES = 3        # количество повторных попыток для каждого пакета

def get_dependencies():
    with open("package.json") as f:
        data = json.load(f)
    deps = []
    deps.extend(data.get("dependencies", {}).keys())
    deps.extend(data.get("devDependencies", {}).keys())
    return deps

def fetch_with_retries(url):
    """Выполняет GET с повторными попытками и заголовками."""
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt == RETRIES - 1:
                raise
            print(f"  Попытка {attempt+1} не удалась: {e}. Повтор через 2 секунды...", file=sys.stderr)
            time.sleep(2)

def check_package(package_name):
    try:
        url = BDU_SEARCH_URL.format(package_name)
        resp = fetch_with_retries(url)
    except Exception as e:
        print(f"  Ошибка при запросе для {package_name}: {e}", file=sys.stderr)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", class_="table-vuls")
    if not table:
        return []

    vulnerabilities = []
    for row in table.find_all("tr"):
        id_link = row.find("a", class_="confirm-vul")
        if not id_link:
            continue
        vul_id = id_link.get_text(strip=True)
        vul_url = "https://bdu.fstec.ru" + id_link.get("href", "")
        desc_div = row.find("div", class_="name")
        if desc_div:
            h5 = desc_div.find("h5")
            desc = h5.get("data-content", h5.get_text(strip=True))
        else:
            desc = ""
        vulnerabilities.append((vul_id, desc, vul_url))
    return vulnerabilities

def main():
    deps = get_dependencies()
    print(f"Проверяем {len(deps)} зависимостей...")
    found = {}

    for dep in deps:
        print(f"  {dep}...", end=" ", flush=True)
        vulns = check_package(dep)
        if vulns:
            print("найдены уязвимости!")
            found[dep] = vulns
        else:
            print("не найдено")
        time.sleep(DELAY)

    if not found:
        print("\n✅ Уязвимых зависимостей не обнаружено.")
        sys.exit(0)

    print("\n❌ Найдены уязвимые зависимости:\n")
    for pkg, vulns in found.items():
        print(f"📦 {pkg}:")
        for vul_id, desc, url in vulns:
            print(f"   • {vul_id}: {desc}")
            print(f"     Подробнее: {url}")
        print()

    sys.exit(1)

if __name__ == "__main__":
    main()
