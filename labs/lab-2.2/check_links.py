from urllib.request import urlopen
from urllib.error import HTTPError, URLError

# Открываем список сайтов и файл для результатов.
with open("link.txt", encoding="utf-8") as links:
    with open("report.txt", "w", encoding="utf-8") as report:
        for line in links:
            url = line.strip()
            if not url:
                continue

            # Пробуем открыть сайт.
            try:
                with urlopen(url, timeout=5) as response:
                    if 200 <= response.status < 300:
                        status = "Ok"
                    else:
                        status = "Error"
            except HTTPError as error:
                error.close()
                status = "Error"
            except (URLError, OSError, ValueError):
                status = "Error"

            # Записываем результат проверки.
            report.write(f"{url} -> {status}\n")
