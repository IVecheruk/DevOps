"""Проверки выполняются без сети, requests и Telegram-токена."""

from collections import Counter
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from analyze_logs import DEMO_LOG, analyze_log, find_suspicious, send_telegram


ROOT = Path(__file__).resolve().parents[1]


class LogAnalysisTests(unittest.TestCase):
    def test_demo_counts(self):
        counts, total, skipped = analyze_log(DEMO_LOG)
        self.assertEqual((total, skipped), (111, 2))
        self.assertEqual(counts, {
            "203.0.113.10": 51,
            "198.51.100.20": 50,
            "2001:db8::1": 3,
        })
        self.assertEqual(find_suspicious(counts, 50), [("203.0.113.10", 51)])

    def test_strict_threshold(self):
        counts = Counter({"192.0.2.1": 49, "192.0.2.2": 50, "192.0.2.3": 51})
        self.assertEqual(find_suspicious(counts, 50), [("192.0.2.3", 51)])

    def test_another_status(self):
        counts, _, _ = analyze_log(DEMO_LOG, 500)
        self.assertEqual(counts, {"192.0.2.40": 1})

    def test_parse_real_status_and_validate_ip(self):
        lines = [
            '192.0.2.1 - - [26/Sep/2026:12:00:00 +0000] "GET /404 HTTP/1.1" 200 42 "-" "bot 404"',
            '999.0.0.1 - - [26/Sep/2026:12:00:00 +0000] "GET / HTTP/1.1" 404 42',
            '2001:0db8:0:0:0:0:0:1 - - [26/Sep/2026:12:00:00 +0000] "GET / HTTP/1.1" 404 42',
            '2001:db8::1 - - [26/Sep/2026:12:00:00 +0000] "GET / HTTP/1.1" 404 42',
            '192.0.2.2 - - [26/Sep/2026:12:00:00 +0000] "GET / HTTP/1.1" 4040 42',
            "broken line",
        ]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "access.log"
            path.write_text("\n".join(lines), encoding="utf-8")
            counts, total, skipped = analyze_log(path)
        self.assertEqual(counts, {"2001:db8::1": 2})
        self.assertEqual((total, skipped), (6, 3))

    def test_default_run_from_another_directory(self):
        with TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-S", str(ROOT / "analyze_logs.py")],
                cwd=directory, capture_output=True, text=True, encoding="utf-8",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Подозрительных IP: 1", result.stdout)
        self.assertIn("отправка в Telegram отключена", result.stdout)

    def test_missing_file_and_invalid_options(self):
        with TemporaryDirectory() as directory:
            cases = [
                (["--log", str(Path(directory) / "missing.log")], 1),
                (["--threshold", "-1"], 2),
                (["--status", "999"], 2),
            ]
            for arguments, code in cases:
                with self.subTest(arguments=arguments):
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "analyze_logs.py"), *arguments],
                        capture_output=True, text=True, encoding="utf-8",
                    )
                    self.assertEqual(result.returncode, code)
                    self.assertNotIn("Traceback", result.stderr)


class TelegramTests(unittest.TestCase):
    def setUp(self):
        self.requests = Mock()
        self.requests.RequestException = type("RequestException", (Exception,), {})

    def test_successful_request(self):
        self.requests.post.return_value.json.return_value = {"ok": True}
        with patch.dict(sys.modules, {"requests": self.requests}):
            send_telegram("test-token", "123", "test message")
        self.requests.post.assert_called_once_with(
            "https://api.telegram.org/bottest-token/sendMessage",
            json={"chat_id": "123", "text": "test message"},
            timeout=10, allow_redirects=False,
        )

    def test_api_rejection(self):
        self.requests.post.return_value.json.return_value = {"ok": False}
        with patch.dict(sys.modules, {"requests": self.requests}):
            with self.assertRaisesRegex(RuntimeError, "не подтвердил"):
                send_telegram("test-token", "123", "test")

    def test_network_error_does_not_expose_token(self):
        self.requests.post.side_effect = self.requests.RequestException("URL contains test-token")
        with patch.dict(sys.modules, {"requests": self.requests}):
            with self.assertRaises(RuntimeError) as error:
                send_telegram("test-token", "123", "test")
        self.assertNotIn("test-token", str(error.exception))

    def test_missing_optional_dependency(self):
        with patch.dict(sys.modules, {"requests": None}):
            with self.assertRaisesRegex(RuntimeError, "pip install"):
                send_telegram("test-token", "123", "test")


if __name__ == "__main__":
    unittest.main()
