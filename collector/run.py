"""收集價格、配息，計算報酬率並產生首頁。"""

from __future__ import annotations

from .build_ranking import parse_as_of, save_ranking
from .fetch_dividends import save_dividends
from .fetch_prices import load_catalog, load_quotes, save_prices
from .render_html import render


def main() -> None:
    catalog = load_catalog()
    quotes = load_quotes()
    price_meta = save_prices(catalog, quotes)
    as_of = parse_as_of(price_meta)
    dividend_meta = save_dividends(catalog, 2003, as_of.year)
    ranking = save_ranking(as_of, price_meta, dividend_meta)
    render(ranking)
    top = next(item for item in ranking["items"] if item["yield_pct"] is not None)
    print(
        f"行情日 {ranking['as_of']}｜ETF {ranking['universe']}｜"
        f"有收盤 {ranking['priced']}｜可排名 {ranking['with_yield']}｜"
        f"中位數 {ranking['median_yield_pct']:.2f}%"
    )
    print(
        f"最高 {top['code']} {top['name']} {top['yield_pct']:.2f}% "
        f"收盤 {top['close']} 平均年配息 {top['avg_annual_dividend']}"
    )


if __name__ == "__main__":
    main()
