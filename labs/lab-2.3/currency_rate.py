"""Показывает официальный курс доллара США к рублю с сайта Банка России."""

import re

import requests
from bs4 import BeautifulSoup


URL = "https://www.cbr.ru/currency_base/daily/"
CURRENCY = "USD"

response = requests.get(URL, timeout=10)
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

heading = soup.find("h2")
table = soup.find("table", class_="data")
if heading is None or table is None:
    raise ValueError("На странице не найдены дата или таблица курсов")

date = re.search(r"\d{2}\.\d{2}\.\d{4}", heading.get_text())
if date is None:
    raise ValueError("На странице не найдена дата курса")

for row in table.find_all("tr"):
    cells = row.find_all("td")
    if len(cells) >= 5 and cells[1].get_text(strip=True) == CURRENCY:
        units = cells[2].get_text(strip=True)
        rate = cells[4].get_text(strip=True)
        print(f"{date.group()}: {units} {CURRENCY} = {rate} RUB")
        break
else:
    raise ValueError(f"В таблице нет валюты {CURRENCY}")
