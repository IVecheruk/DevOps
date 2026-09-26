"""Проверяет выбор курса на учебном HTML без сетевых запросов."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import runpy
import unittest
from unittest.mock import Mock, patch


LAB = Path(__file__).resolve().parents[1]
SCRIPT = LAB / "currency_rate.py"
EXAMPLE = (LAB / "examples" / "cbr_page.html").read_text(encoding="utf-8")


class CurrencyRateTests(unittest.TestCase):
    def run_script(self, html):
        response = Mock(text=html)
        output = StringIO()
        with patch("requests.get", return_value=response) as get, redirect_stdout(output):
            runpy.run_path(str(SCRIPT))
        get.assert_called_once_with("https://www.cbr.ru/currency_base/daily/", timeout=10)
        response.raise_for_status.assert_called_once()
        return output.getvalue()

    def test_finds_usd_date_units_and_rate(self):
        self.assertEqual(self.run_script(EXAMPLE), "26.09.2026: 1 USD = 84,3414 RUB\n")

    def test_missing_currency_is_reported(self):
        html = EXAMPLE.replace("<td>USD</td>", "<td>EUR</td>")
        with self.assertRaisesRegex(ValueError, "нет валюты USD"):
            self.run_script(html)

    def test_missing_table_is_reported(self):
        with self.assertRaisesRegex(ValueError, "не найдены дата или таблица"):
            self.run_script("<h2>Курсы с 26.09.2026</h2>")


if __name__ == "__main__":
    unittest.main()
