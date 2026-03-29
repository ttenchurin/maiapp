#!/usr/bin/env python3
import json
import sys
import time
import requests
from bs4 import BeautifulSoup

BDU_SEARCH_URL = "https://bdu.fstec.ru/vul?ajax=vuls&search={}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}
DELAY = 1  # секунды между запросами, чтобы не перегружать сайт

def get_dependencies():
    """Читает package.json и возвращает список имён пакетов."""
    with open("package.json") as f:
        data = json.load(f)
    deps = []
    deps.extend(data.get("dependencies", {}).keys())
    deps.extend(data.get("devDependencies", {}).keys())
    return deps

def check_package(package_name):
    """Выполняет поиск уязвимости для пакета и возвращает список (id, title, url)."""
    url = BDU_SEARCH_URL.format(package_name)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"Ошибка при запросе для {package_name}: {e}", file=sys.stderr)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    # Ищем таблицу с результатами
    table = soup.find("table", class_="table-vuls")
    if not table:
        return []

    vulnerabilities = []
    rows = table.find_all("tr")
    for row in rows:
        # Ищем ссылку с идентификатором
        id_link = row.find("a", class_="confirm-vul")
        if not id_link:
            continue
        vul_id = id_link.get_text(strip=True)  # например "BDU:2026-00173"
        vul_url = "https://bdu.fstec.ru" + id_link.get("href", "")
        # Описание находится в data-content атрибуте h5
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
