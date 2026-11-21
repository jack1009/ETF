"""下載上市 ETF 收益分配，月配與季配加總為年配息。"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from .util import DIVIDENDS, clean_text, fetch_json, frequency_label, now_iso, parse_number, roc_phrase_to_date, write_json

DIV_URL = "https://www.twse.com.tw/rwd/zh/ETF/etfDiv"


def _fetch_span(start: date, end: date) -> list[dict]:
    url = (
        f"{DIV_URL}?response=json"
        f"&startDate={start.strftime('%Y%m%d')}"
        f"&endDate={end.strftime('%Y%m%d')}"
    )
    payload = fetch_json(url)
    rows = payload.get("data") or []
    parsed = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 6:
            continue
        ex_date = roc_phrase_to_date(row[2])
        if ex_date is None:
            continue
        parsed.append(
            {
                "code": clean_text(row[0]),
                "name": clean_text(row[1]),
                "ex_date": ex_date.isoformat(),
                "record_date": roc_phrase_to_date(row[3]).isoformat() if roc_phrase_to_date(row[3]) else None,
                "pay_date": roc_phrase_to_date(row[4]).isoformat() if roc_phrase_to_date(row[4]) else None,
                "cash_per_unit": parse_number(row[5]),
                "announce_year": int(row[7]) + 1911 if len(row) > 7 and str(row[7]).isdigit() else None,
            }
        )
    return parsed


def collect_distributions(start_year: int, end_year: int) -> dict[str, list[dict]]:
    """證交所日期篩選會跨到鄰近年，依除息日去重後自行分年。"""
    chosen: dict[tuple[str, str], dict] = {}
    for year in range(start_year - 1, end_year + 1):
        for row in _fetch_span(date(year, 1, 1), date(year, 12, 31)):
            ex_year = int(row["ex_date"][:4])
            if ex_year < start_year or ex_year > end_year:
                continue
            key = (row["code"], row["ex_date"])
            current = chosen.get(key)
            if current is None:
                chosen[key] = row
                continue
            old_cash = current["cash_per_unit"]
            new_cash = row["cash_per_unit"]
            if old_cash is None and new_cash is not None:
                chosen[key] = row
            elif old_cash is not None and new_cash is not None and new_cash > old_cash:
                chosen[key] = row
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in chosen.values():
        grouped[row["code"]].append(row)
    for code in grouped:
        grouped[code].sort(key=lambda item: item["ex_date"], reverse=True)
    return grouped


def annualize(distributions: list[dict]) -> list[dict]:
    totals: dict[int, float] = defaultdict(float)
    counts: dict[int, int] = defaultdict(int)
    for row in distributions:
        cash = row["cash_per_unit"]
        if cash is None:
            continue
        year = int(row["ex_date"][:4])
        totals[year] += cash
        counts[year] += 1
    annual = []
    for year in sorted(totals):
        payments = counts[year]
        annual.append(
            {
                "year": year,
                "cash_per_unit": round(totals[year], 6),
                "payments": payments,
                "frequency": frequency_label(payments),
            }
        )
    return annual


def save_dividends(catalog: list[dict], start_year: int, end_year: int) -> dict:
    grouped = collect_distributions(start_year, end_year)
    fetched_at = now_iso()
    kept = set()
    with_cash = 0
    for fund in catalog:
        code = fund["code"]
        kept.add(code)
        distributions = grouped.get(code, [])
        annual = annualize(distributions)
        if any(item["cash_per_unit"] > 0 for item in annual):
            with_cash += 1
        latest = next((item for item in reversed(annual) if item["payments"] > 0), None)
        payload = {
            "code": code,
            "name": fund["name"],
            "frequency": None if latest is None else latest["frequency"],
            "distributions": distributions,
            "annual": annual,
            "source": DIV_URL,
            "fetched_at": fetched_at,
        }
        write_json(DIVIDENDS / f"{code}.json", payload)
    for path in DIVIDENDS.glob("*.json"):
        if path.stem not in kept:
            path.unlink()
    return {
        "with_cash": with_cash,
        "distribution_rows": sum(len(rows) for rows in grouped.values()),
        "fetched_at": fetched_at,
    }
