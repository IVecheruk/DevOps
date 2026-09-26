"""Ищет IP с более чем 50 ответами 404 в учебном логе Nginx."""

import re
from collections import Counter
from ipaddress import ip_address
from pathlib import Path


LOG_FILE = Path(__file__).resolve().parent / "examples" / "access.log"
THRESHOLD = 50
errors = Counter()

for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
    # IP стоит в начале строки, статус — сразу после запроса в кавычках.
    match = re.search(r'^(\S+).*?"[^"]*"\s404\s', line)
    if not match:
        continue

    ip = match.group(1)
    try:
        ip_address(ip)
    except ValueError:
        continue
    errors[ip] += 1

print(f"HTTP 404 responses: {sum(errors.values())}")
for ip, count in errors.items():
    if count > THRESHOLD:
        print(f"Suspicious IP {ip}: {count} HTTP 404 responses")
