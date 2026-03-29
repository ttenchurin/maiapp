#!/usr/bin/env python3
import json
import sys
import time
import requests

NVD_SEARCH_URL = "https://nvd.nist.gov/extensions/nudp/services/json/nvd/cve/search/results?resultType=records&keyword={}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 YaBrowser/26.3.0.0 Safari/537.36",
    "Referer": "https://nvd.nist.gov/vuln/search",
    "Accept": "application/json, text/plain, */*"
}
DELAY = 1          # секунды между запросами
TIMEOUT = 20
RETRIES = 2

def get_dependencies():
    with open("package.json") as f:
        data = json.load(f)
    deps = []
    deps.extend(data.get("dependencies", {}).keys())
    deps.extend(data.get("devDependencies", {}).keys())
    return deps

def fetch_package_vulns(package_name):
    url = NVD_SEARCH_URL.format(package_name)
    for attempt in range(RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            # Проверяем наличие ответа
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
    # Описание
    desc_list = cve.get("descriptions", [])
    desc = desc_list[0].get("value", "") if desc_list else ""
    # Ссылка
    refs = cve.get("references", [])
    ref_url = refs[0].get("url", "") if refs else ""
    return cve_id, desc, ref_url

def main():
    deps = get_dependencies()
    print(f"Проверяем {len(deps)} зависимостей по NVD...")
    found = {}

    for dep in deps:
        print(f"  {dep}...", end=" ", flush=True)
        vulns = fetch_package_vulns(dep)
        if vulns:
            print("найдены уязвимости!")
            found[dep] = [extract_vuln_info(v) for v in vulns]
        else:
            print("не найдено")
        time.sleep(DELAY)

    if not found:
        print("\n✅ Уязвимых зависимостей не обнаружено.")
        sys.exit(0)

    print("\n❌ Найдены уязвимые зависимости:\n")
    for pkg, vuln_list in found.items():
        print(f"📦 {pkg}:")
        for cve_id, desc, url in vuln_list:
            # Обрезаем описание, если слишком длинное
            desc_short = desc[:200] + "..." if len(desc) > 200 else desc
            print(f"   • {cve_id}: {desc_short}")
            if url:
                print(f"     Подробнее: {url}")
        print()

    sys.exit(1)

if __name__ == "__main__":
    main()
