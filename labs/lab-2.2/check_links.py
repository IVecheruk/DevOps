from urllib.error import HTTPError, URLError
from urllib.request import urlopen

with open("link.txt", encoding="utf-8") as links, open("report.txt", "w", encoding="utf-8") as report:
    for line in links:
        url = line.strip()
        if not url:
            continue

        try:
            with urlopen(url, timeout=5) as response:
                status = "Ok" if 200 <= response.status < 300 else "Error"
        except HTTPError as error:
            error.close()
            status = "Error"
        except (URLError, OSError, ValueError):
            status = "Error"

        report.write(f"{url} -> {status}\n")
