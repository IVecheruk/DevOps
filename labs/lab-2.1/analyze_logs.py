"""Анализ access.log; по умолчанию работает локально, без внешних зависимостей."""

import argparse
from collections import Counter
from ipaddress import ip_address
import os
from pathlib import Path
import re
import sys


DEMO_LOG = Path(__file__).resolve().parent / "examples" / "access.log"
# Начало записи common/combined: IP, ident, user, время, запрос, статус, размер.
# Экранированные символы внутри запроса не завершают поле преждевременно.
LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[[^\]]+\]\s+'
    r'"(?:[^"\\]|\\.)*"\s+(?P<status>[1-5][0-9]{2})\s+(?:[0-9]+|-)'
    r'(?:\s|$)'
)


def analyze_log(path, status=404):
    """Возвращает счётчик IP, количество строк и число пропущенных записей."""
    counts = Counter()
    total = skipped = 0
    with Path(path).open(encoding="utf-8", errors="replace") as log:
        for line in log:
            total += 1
            match = LOG_PATTERN.match(line)
            if not match:
                skipped += 1
                continue
            try:
                ip = str(ip_address(match["ip"]))
            except ValueError:
                skipped += 1
                continue
            if int(match["status"]) == status:
                counts[ip] += 1
    return counts, total, skipped


def find_suspicious(counts, threshold):
    """Порог строгий: при threshold=50 предупреждение появляется с 51 запроса."""
    return [(ip, count) for ip, count in counts.most_common() if count > threshold]


def send_telegram(token, chat_id, message):
    """Отправляет одно сообщение. Ошибки не раскрывают URL с токеном."""
    try:
        import requests
    except ImportError:
        raise RuntimeError(
            "Для Telegram установите зависимости: python -m pip install -r requirements.txt"
        ) from None

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
            allow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        raise RuntimeError(
            "Ошибка Telegram: проверьте сеть, токен и CHAT_ID."
        ) from None
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise RuntimeError("Telegram не подтвердил отправку сообщения.")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=DEMO_LOG, help="путь к access.log")
    parser.add_argument("--status", type=int, default=404, help="HTTP-статус (по умолчанию 404)")
    parser.add_argument("--threshold", type=int, default=50, help="строгий порог (по умолчанию 50)")
    parser.add_argument("--telegram", action="store_true", help="отправить предупреждения в Telegram")
    return parser


def main(argv=None):
    # UTF-8 для одинакового вывода в терминале и при перенаправлении в файл.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(argv)
    if not 100 <= args.status <= 599:
        parser.error("--status должен быть от 100 до 599")
    if args.threshold < 0:
        parser.error("--threshold должен быть неотрицательным")

    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat_id = os.environ.get("CHAT_ID", "").strip()
    if args.telegram and (not token or not chat_id):
        parser.error("для --telegram задайте переменные окружения TELEGRAM_TOKEN и CHAT_ID")

    try:
        counts, total, skipped = analyze_log(args.log, args.status)
    except OSError as error:
        print(f"Ошибка чтения лога: {error}", file=sys.stderr)
        return 1

    suspicious = find_suspicious(counts, args.threshold)
    print(f"Всего строк: {total}")
    print(f"Распознано: {total - skipped}; пропущено: {skipped}")
    print(f"Запросов со статусом {args.status}: {sum(counts.values())}")
    print(f"Уникальных IP со статусом {args.status}: {len(counts)}")
    print(f"Порог: больше {args.threshold}")
    print(f"Подозрительных IP: {len(suspicious)}")
    for ip, count in suspicious:
        message = (
            f"Обнаружена подозрительная активность! IP {ip} "
            f"получил {count} ответов HTTP {args.status}."
        )
        print(message)
        if args.telegram:
            try:
                send_telegram(token, chat_id, message)
            except RuntimeError as error:
                print(str(error), file=sys.stderr)
                return 1
            print("Сообщение отправлено в Telegram.")
    if not args.telegram:
        print("Локальный режим: отправка в Telegram отключена.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

