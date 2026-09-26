"""Проверки на локальном HTTP-сервере, без доступа к внешним сайтам."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.error import URLError

from check_links import check_url, create_report


SCRIPT = Path(__file__).resolve().parents[1] / "check_links.py"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/redirect", "/redirect-error"):
            self.send_response(302)
            self.send_header("Location", "/ok" if self.path == "/redirect" else "/missing")
        else:
            self.send_response({"/ok": 200, "/empty": 204, "/error": 500}.get(self.path, 404))
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


class CheckLinksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_http_responses_and_redirects(self):
        for path, expected in (
            ("/ok", "Ok"), ("/empty", "Ok"), ("/redirect", "Ok"),
            ("/missing", "Error"), ("/error", "Error"), ("/redirect-error", "Error"),
        ):
            with self.subTest(path=path):
                self.assertEqual(check_url(self.base_url + path), expected)

    def test_invalid_addresses(self):
        for url in ("not-a-url", "file:///etc/passwd", "ftp://example.com", "https://", "http://[broken", "http://a b/"):
            with self.subTest(url=url):
                self.assertEqual(check_url(url), "Error")

    def test_network_failures(self):
        for error in (URLError("DNS failure"), TimeoutError(), ConnectionResetError()):
            with self.subTest(error=type(error).__name__):
                with patch("check_links.urlopen", side_effect=error):
                    self.assertEqual(check_url("https://example.com"), "Error")

    def test_report_format_order_duplicates_and_overwrite(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "link.txt"
            report = Path(directory) / "report.txt"
            source.write_text(f"  {self.base_url}/ok  \n\n{self.base_url}/missing\n{self.base_url}/ok\nnot-a-url\n", encoding="utf-8-sig")
            report.write_text("old content", encoding="utf-8")
            results = create_report(source, report)
            self.assertEqual([status for _, status in results], ["Ok", "Error", "Ok", "Error"])
            self.assertEqual(report.read_text(encoding="utf-8"), (
                f"{self.base_url}/ok -> Ok\n{self.base_url}/missing -> Error\n"
                f"{self.base_url}/ok -> Ok\nnot-a-url -> Error\n"
            ))

    def test_empty_input(self):
        with TemporaryDirectory() as directory:
            source, report = Path(directory) / "link.txt", Path(directory) / "report.txt"
            source.write_text("\n  \n", encoding="utf-8")
            self.assertEqual(create_report(source, report), [])
            self.assertEqual(report.read_bytes(), b"")

    def test_same_file_is_not_overwritten(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "link.txt"
            source.write_text("https://example.com\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                create_report(source, source)
            self.assertEqual(source.read_text(encoding="utf-8"), "https://example.com\n")

    def test_missing_input_preserves_existing_report(self):
        with TemporaryDirectory() as directory:
            report = Path(directory) / "report.txt"
            report.write_text("previous report", encoding="utf-8")
            with self.assertRaises(OSError):
                create_report(Path(directory) / "missing.txt", report)
            self.assertEqual(report.read_text(encoding="utf-8"), "previous report")

    def test_default_paths_from_another_directory(self):
        with TemporaryDirectory() as directory:
            lab = Path(directory) / "lab"
            lab.mkdir()
            shutil.copyfile(SCRIPT, lab / "check_links.py")
            (lab / "link.txt").write_text(f"{self.base_url}/ok\n{self.base_url}/missing\n", encoding="utf-8")
            result = subprocess.run([sys.executable, "-S", str(lab / "check_links.py")], cwd=directory, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((lab / "report.txt").read_text(encoding="utf-8"), f"{self.base_url}/ok -> Ok\n{self.base_url}/missing -> Error\n")

    def test_invalid_timeout(self):
        for value in (0, -1, float("inf"), float("nan")):
            with self.subTest(timeout=value):
                with self.assertRaises(ValueError):
                    create_report("unused-input", "unused-output", value)


if __name__ == "__main__":
    unittest.main()
