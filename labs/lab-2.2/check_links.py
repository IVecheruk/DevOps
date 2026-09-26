"""Проверяет адреса из link.txt и записывает строки «адрес -> Ok/Error»."""

import argparse
from http.client import HTTPException
import math
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent


def check_url(url, timeout=5.0):
    """Ok — конечный ответ HTTP 2xx; ошибки URL, HTTP и сети — Error."""
    try:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return "Error"
        if any(character.isspace() or ord(character) < 32 for character in url):
            return "Error"
        request = Request(url, headers={"User-Agent": "DevOps-LinkChecker/1.0"})
        # GET совместим с сайтами, не поддерживающими HEAD; тело не скачиваем.
        with urlopen(request, timeout=timeout) as response:
            return "Ok" if 200 <= response.status < 300 else "Error"
    except HTTPError as error:
        error.close()
        return "Error"
    except (URLError, OSError, ValueError, HTTPException):
        return "Error"


def create_report(input_path, output_path, timeout=5.0):
    """Пустые строки пропускаются; порядок и повторы адресов сохраняются."""
    input_path, output_path = Path(input_path), Path(output_path)
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Файлы списка адресов и отчёта должны отличаться.")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Тайм-аут должен быть конечным положительным числом.")
    # utf-8-sig принимает обычный UTF-8 и UTF-8 с BOM.
    lines = input_path.read_text(encoding="utf-8-sig").splitlines()
    urls = [line.strip() for line in lines if line.strip()]
    results = []
    with output_path.open("w", encoding="utf-8", newline="\n") as report:
        for url in urls:
            status = check_url(url, timeout)
            report.write(f"{url} -> {status}\n")
            results.append((url, status))
    return results


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=BASE_DIR / "link.txt", help="файл с адресами")
    parser.add_argument("--output", type=Path, default=BASE_DIR / "report.txt", help="файл результата")
    parser.add_argument("--timeout", type=float, default=5.0, help="тайм-аут сетевых операций в секундах")
    args = parser.parse_args(argv)

    try:
        results = create_report(args.input, args.output, args.timeout)
    except (OSError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1

    ok_count = sum(status == "Ok" for _, status in results)
    print(f"Проверено: {len(results)}; Ok: {ok_count}; Error: {len(results) - ok_count}")
    print(f"Отчёт: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
