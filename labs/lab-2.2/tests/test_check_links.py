"""Проверки готового скрипта на локальном HTTP-сервере."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import unittest


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

    def run_script(self, directory):
        return subprocess.run(
            [sys.executable, "-S", "-W", "error::ResourceWarning", str(SCRIPT)],
            cwd=directory, capture_output=True, text=True, encoding="utf-8",
        )

    def check_report(self, input_text, expected):
        with TemporaryDirectory() as directory:
            (Path(directory) / "link.txt").write_text(input_text, encoding="utf-8")
            report = Path(directory) / "report.txt"
            report.write_text("old report", encoding="utf-8")
            result = self.run_script(directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            self.assertEqual(report.read_text(encoding="utf-8"), expected)

    def test_http_responses_and_redirects(self):
        cases = [("/ok", "Ok"), ("/empty", "Ok"), ("/redirect", "Ok"),
                 ("/missing", "Error"), ("/error", "Error"), ("/redirect-error", "Error")]
        urls = "".join(f"{self.base_url}{path}\n" for path, _ in cases)
        expected = "".join(f"{self.base_url}{path} -> {status}\n" for path, status in cases)
        self.check_report(urls, expected)

    def test_spaces_blank_lines_duplicates_and_overwrite(self):
        url = self.base_url + "/ok"
        self.check_report(f"  {url}  \n\n{url}\n", f"{url} -> Ok\n{url} -> Ok\n")

    def test_empty_input(self):
        self.check_report("\n  \n", "")

    def test_invalid_url_does_not_stop_remaining_checks(self):
        url = self.base_url + "/ok"
        self.check_report(f"not-a-url\n{url}\n", f"not-a-url -> Error\n{url} -> Ok\n")

    def test_missing_input_preserves_existing_report(self):
        with TemporaryDirectory() as directory:
            report = Path(directory) / "report.txt"
            report.write_text("previous report", encoding="utf-8")
            result = self.run_script(directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("FileNotFoundError", result.stderr)
            self.assertEqual(report.read_text(encoding="utf-8"), "previous report")


if __name__ == "__main__":
    unittest.main()
