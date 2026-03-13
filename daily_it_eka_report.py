from __future__ import annotations

import argparse
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus

import pandas as pd
import requests
from bs4 import BeautifulSoup


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}


@dataclass
class SearchResult:
    product_name: str
    query: str
    found: bool
    pharmacies_count: int | None
    price_from: float | None
    page_url: str
    status: str
    parsed_at: str


class ITekaAvailabilityChecker:
    def __init__(
        self,
        city: str = "astana",
        delay_range: tuple[float, float] = (0.8, 1.8),
        timeout_seconds: int = 30,
    ) -> None:
        self.base_url = "https://i-teka.kz"
        self.city = city
        self.delay_range = delay_range
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.timeout_seconds = timeout_seconds

    def _delay(self) -> None:
        time.sleep(random.uniform(*self.delay_range))

    def _fetch(self, url: str, retries: int = 3) -> str | None:
        for attempt in range(1, retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout_seconds)
                response.raise_for_status()
                return response.text
            except requests.RequestException:
                if attempt == retries:
                    return None
                time.sleep(attempt * 1.5)
        return None

    @staticmethod
    def _extract_price(text: str) -> float | None:
        m = re.search(r"(?:от\s*)?(\d+[\d\s]*[\.,]?\d*)\s*(?:₸|тг)", text, flags=re.IGNORECASE)
        if not m:
            return None
        raw = m.group(1).replace(" ", "").replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            return None

    @staticmethod
    def _extract_pharmacy_count(text: str) -> int | None:
        patterns = [
            r"Найден[ао]?\s+(\d+)\s+апт",
            r"(\d+)\s+аптек",
            r"в\s+(\d+)\s+апте",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                return int(m.group(1))
        return None

    @staticmethod
    def _normalize_query(product_name: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"\(.*?\)", "", product_name)).strip()

    def check_one(self, product_name: str) -> SearchResult:
        parsed_at = datetime.now().isoformat(timespec="seconds")
        query = self._normalize_query(product_name)
        url = f"{self.base_url}/{self.city}/search?text={quote_plus(query)}"
        html = self._fetch(url)

        if html is None:
            return SearchResult(
                product_name=product_name,
                query=query,
                found=False,
                pharmacies_count=None,
                price_from=None,
                page_url=url,
                status="request_failed",
                parsed_at=parsed_at,
            )

        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True)

        not_found_markers = ["ничего не найдено", "не найдено", "no results"]
        if any(marker in text.lower() for marker in not_found_markers):
            return SearchResult(
                product_name=product_name,
                query=query,
                found=False,
                pharmacies_count=0,
                price_from=None,
                page_url=url,
                status="not_found",
                parsed_at=parsed_at,
            )

        pharmacies_count = self._extract_pharmacy_count(text)
        price_from = self._extract_price(text)

        found = pharmacies_count is not None or price_from is not None
        status = "ok" if found else "needs_manual_check"

        return SearchResult(
            product_name=product_name,
            query=query,
            found=found,
            pharmacies_count=pharmacies_count,
            price_from=price_from,
            page_url=url,
            status=status,
            parsed_at=parsed_at,
        )

    def check_many(self, products: Iterable[str]) -> list[SearchResult]:
        results: list[SearchResult] = []
        for name in products:
            results.append(self.check_one(name))
            self._delay()
        return results


def read_products(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def save_excel(results: list[SearchResult], output_path: Path) -> None:
    df = pd.DataFrame([r.__dict__ for r in results])
    df = df.rename(
        columns={
            "product_name": "Препарат",
            "query": "Поисковый_запрос",
            "found": "Найден",
            "pharmacies_count": "Кол-во_аптек",
            "price_from": "Цена_от",
            "page_url": "Ссылка_поиска",
            "status": "Статус",
            "parsed_at": "Дата_проверки",
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)


def resolve_output_path(output: str | None) -> Path:
    if output:
        return Path(output)
    date_suffix = datetime.now().strftime("%Y-%m-%d")
    return Path("reports") / f"i_teka_astana_{date_suffix}.xlsx"


def main() -> None:
    parser = argparse.ArgumentParser(description="Ежедневная проверка доступности препаратов на i-teka.kz")
    parser.add_argument("--city", default="astana", help="Город на i-teka (например: astana)")
    parser.add_argument(
        "--input",
        default="medicine_list.txt",
        help="TXT файл со списком препаратов, по 1 позиции на строку",
    )
    parser.add_argument("--output", default=None, help="Путь к excel отчёту")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = resolve_output_path(args.output)

    products = read_products(input_path)
    checker = ITekaAvailabilityChecker(city=args.city)
    results = checker.check_many(products)
    save_excel(results, output_path)

    print(f"Готово: {output_path} ({len(results)} позиций)")


if __name__ == "__main__":
    main()