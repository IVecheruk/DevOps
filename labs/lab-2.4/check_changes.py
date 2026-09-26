"""Сравнивает содержимое сайтов с предыдущим обходом."""

import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


links = Path("link.txt").read_text(encoding="utf-8").splitlines()
hashes_file = Path("hashes.json")
old_hashes = json.loads(hashes_file.read_text(encoding="utf-8")) if hashes_file.exists() else {}
new_hashes = old_hashes.copy()

with open("report.txt", "w", encoding="utf-8") as report:
    for line in links:
        url = line.strip()
        if not url or url.startswith("#"):
            continue

        try:
            with urlopen(url, timeout=10) as response:
                page_hash = hashlib.sha256(response.read()).hexdigest()

            if url not in old_hashes:
                status = "NEW"
            elif old_hashes[url] == page_hash:
                status = "OK"
            else:
                status = "CHANGED"
            new_hashes[url] = page_hash
        except HTTPError as error:
            error.close()
            status = "ERROR"
        except (URLError, OSError, ValueError):
            status = "ERROR"

        report.write(f"{url} -> {status}\n")

hashes_file.write_text(json.dumps(new_hashes, indent=2) + "\n", encoding="utf-8")
print("Готово: результат в report.txt")
