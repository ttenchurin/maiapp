#!/usr/bin/env python3
import json
import sys
import time
import requests
import os

NVD_SEARCH_URL = "https://nvd.nist.gov/extensions/nudp/services/json/nvd/cve/search/results?resultType=records&keyword={}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 YaBrowser/26.3.0.0 Safari/537.36",
    "Referer": "https://nvd.nist.gov/vuln/search",
    "Accept": "application/json, text/plain, */*"
}
DELAY = 1          # секунды между запросами
TIMEOUT = 20
RETRIES = 2

IGNORE_FILE = ".nvd-ignore"

def get_dependencies():
    with open("package.json") as f:
        data = json.load(f)
    deps = []
    deps.extend(data.get("dependencies", {}).keys())
    deps.extend(data.get("devDependencies", {}).keys())
    return deps

def load_ignore_list():
    """Загружает список игнорируемых пакетов из файла .nvd-ignore (по одному на строку)."""
    if not os.path.exists(IGNORE_FILE):
        return set()
    with open(IGNORE_FILE) as f:
        lines = f.read().splitlines()
    # Убираем пустые строки и комментарии (начинающиеся с #)
    ignored = set()
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            ignored.add(line)
    return ignored

def fetch_package_vulns(package_name):
    url = NVD_SEARCH_URL.format(package_name)
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if "response" in data and len(data["response"]) > 0:
                grid = data["response"][0].get("grid")
                if grid and "vulnerabilities" in grid:
                    return grid["vulnerabilities"]
            return []
        except Exception as e:
            if attempt == RETRIES - 1:
                print(f"  Ошибка при запросе для {package_name}: {e}", file=sys.stderr)
                return []
            time.sleep(2)

def extract_vuln_info(vuln):
    cve = vuln.get("cve", {})
    cve_id = cve.get("id", "N/A")
    desc_list = cve.get("descriptions", [])
    desc = desc_list[0].get("value", "") if desc_list else ""
    refs = cve.get("references", [])
    ref_url = refs[0].get("url", "") if refs else ""
    return cve_id, desc, ref_url

def main():
    deps = get_dependencies()
    ignored_packages = load_ignore_list()
    print(f"Проверяем {len(deps)} зависимостей по NVD...")
    if ignored_packages:
        print(f"Игнорируемые пакеты: {', '.join(ignored_packages)}")

    found_non_ignored = {}
    found_ignored = {}

    for dep in deps:
        print(f"  {dep}...", end=" ", flush=True)
        vulns = fetch_package_vulns(dep)
        if not vulns:
            print("не найдено")
            continue

        # Если пакет в игнор-листе – запоминаем отдельно
        if dep in ignored_packages:
            print("найдены уязвимости (игнорируем)")
            found_ignored[dep] = [extract_vuln_info(v) for v in vulns]
        else:
            print("найдены уязвимости!")
            found_non_ignored[dep] = [extract_vuln_info(v) for v in vulns]

        time.sleep(DELAY)

    # Вывод игнорируемых уязвимостей (только информативно)
    if found_ignored:
        print("\n⚠️ Игнорируемые уязвимости (приняты риски):\n")
        for pkg, vuln_list in found_ignored.items():
            print(f"📦 {pkg} (игнорируется):")
            for cve_id, desc, url in vuln_list:
                desc_short = desc[:200] + "..." if len(desc) > 200 else desc
                print(f"   • {cve_id}: {desc_short}")
                if url:
                    print(f"     Подробнее: {url}")
            print()

    # Если есть неигнорируемые уязвимости – ошибка
    if found_non_ignored:
        print("\n❌ Найдены уязвимости, которые не игнорируются:\n")
        for pkg, vuln_list in found_non_ignored.items():
            print(f"📦 {pkg}:")
            for cve_id, desc, url in vuln_list:
                desc_short = desc[:200] + "..." if len(desc) > 200 else desc
                print(f"   • {cve_id}: {desc_short}")
                if url:
                    print(f"     Подробнее: {url}")
            print()
        sys.exit(1)
    else:
        if found_ignored:
            print("\n✅ Все найденные уязвимости приняты как риски (игнорируются).")
        else:
            print("\n✅ Уязвимых зависимостей не обнаружено.")
        sys.exit(0)

if __name__ == "__main__":
    main()
