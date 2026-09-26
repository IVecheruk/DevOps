"""Проверки на локальном HTTP-сервере без внешней сети."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "check_changes.py"


class Handler(BaseHTTPRequestHandler):
    page = b"first version"
    unavailable = False

    def do_GET(self):
        if self.path != "/page" or Handler.unavailable:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(Handler.page)))
        self.end_headers()
        self.wfile.write(Handler.page)

    def log_message(self, *args):
        pass


class CheckChangesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/page"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def run_script(self, directory):
        return subprocess.run(
            [sys.executable, "-X", "utf8", "-S", "-W", "error::ResourceWarning", "check_changes.py"],
            cwd=directory, capture_output=True, text=True, encoding="utf-8",
        )

    def test_first_repeat_change_and_error(self):
        Handler.page = b"first version"
        Handler.unavailable = False
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            shutil.copyfile(SCRIPT, folder / "check_changes.py")
            (folder / "link.txt").write_text(f"# test\n{self.url}\n\nnot-a-url\n", encoding="utf-8")

            self.assertEqual(self.run_script(directory).returncode, 0)
            self.assertEqual((folder / "report.txt").read_text(encoding="utf-8"),
                             f"{self.url} -> NEW\nnot-a-url -> ERROR\n")
            first_hashes = json.loads((folder / "hashes.json").read_text(encoding="utf-8"))
            self.assertEqual(len(first_hashes[self.url]), 64)
            self.assertNotIn("not-a-url", first_hashes)

            self.assertEqual(self.run_script(directory).returncode, 0)
            self.assertEqual((folder / "report.txt").read_text(encoding="utf-8"),
                             f"{self.url} -> OK\nnot-a-url -> ERROR\n")

            Handler.page = b"second version"
            self.assertEqual(self.run_script(directory).returncode, 0)
            self.assertEqual((folder / "report.txt").read_text(encoding="utf-8"),
                             f"{self.url} -> CHANGED\nnot-a-url -> ERROR\n")
            changed_hashes = json.loads((folder / "hashes.json").read_text(encoding="utf-8"))
            self.assertNotEqual(first_hashes[self.url], changed_hashes[self.url])

            Handler.unavailable = True
            self.assertEqual(self.run_script(directory).returncode, 0)
            self.assertEqual((folder / "report.txt").read_text(encoding="utf-8"),
                             f"{self.url} -> ERROR\nnot-a-url -> ERROR\n")
            self.assertEqual(json.loads((folder / "hashes.json").read_text(encoding="utf-8")), changed_hashes)

    def test_missing_input_does_not_create_report_or_hashes(self):
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            shutil.copyfile(SCRIPT, folder / "check_changes.py")
            result = self.run_script(directory)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((folder / "report.txt").exists())
            self.assertFalse((folder / "hashes.json").exists())


if __name__ == "__main__":
    unittest.main()
