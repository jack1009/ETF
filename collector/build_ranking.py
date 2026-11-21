"""以當日收盤價與全部年度配息的常態分配中間 50% 計算報酬率。"""

from __future__ import annotations

import json
from datetime import date, datetime
from statistics import fmean, median, pstdev

from .util import DATA, DIVIDENDS, PRICES, frequency_label, now_iso, write_json


MIN_LISTED_YEARS = 8
MIN_DIVIDEND_YEARS = 8
# 標準常態分配第 75 百分位。中間 50% 是 μ ± 這個值 × σ。
NORMAL_MIDDLE_50_Z = 0.6744897501960817


def complete_years(as_of: date) -> list[int]:
    """當年尚未結束，近三年用前三個完整日曆年。"""
    end = as_of.year - 1
    return [end - 2, end - 1, end]


def listed_cutoff(as_of: date, years: int = MIN_LISTED_YEARS) -> date:
    """上市日早於這一天，才算超過指定年數。剛好滿年的不列入。"""
    try:
        return as_of.replace(year=as_of.year - years)
    except ValueError:
        return as_of.replace(year=as_of.year - years, day=28)


def listed_long_enough(listed: date | None, as_of: date) -> bool:
    if listed is None:
        return False
    return listed < listed_cutoff(as_of)


def dividend_years_required(as_of: date) -> list[int]:
    """今年往回數滿指定年數，每一年都要有現金配息。"""
    start = as_of.year - (MIN_DIVIDEND_YEARS - 1)
    return list(range(start, as_of.year + 1))


def middle_half_average(pairs: list[tuple[int, float]]) -> dict:
    """全部年配息視為常態分配，只平均落在中間 50% 區間內的年度。"""
    cleaned = [(year, round(float(amount), 6)) for year, amount in pairs if amount is not None and float(amount) > 0]
    if not cleaned:
        return {"average": None, "low": None, "high": None, "kept_years": []}
    amounts = [amount for _, amount in cleaned]
    center = fmean(amounts)
    if len(cleaned) == 1 or pstdev(amounts) == 0:
        return {
            "average": round(center, 6),
            "low": round(center, 6),
            "high": round(center, 6),
            "kept_years": [year for year, _ in cleaned],
        }
    sigma = pstdev(amounts)
    low = center - NORMAL_MIDDLE_50_Z * sigma
    high = center + NORMAL_MIDDLE_50_Z * sigma
    kept = [(year, amount) for year, amount in cleaned if low <= amount <= high]
    average = center if not kept else fmean(amount for _, amount in kept)
    return {
        "average": round(average, 6),
        "low": round(low, 6),
        "high": round(high, 6),
        "kept_years": [year for year, _ in kept],
    }


def continuous_dividends(annual: dict, years: list[int]) -> bool:
    for year in years:
        row = annual.get(year)
        if row is None or float(row["cash_per_unit"]) <= 0:
            return False
    return True


def _load(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _listed(value: str | None) -> date | None:
    if not value:
        return None
    year, month, day = (int(part) for part in value.split("-"))
    return date(year, month, day)


def build_items(as_of: date) -> tuple[list[dict], list[int], int, int]:
    window = complete_years(as_of)
    required_dividend_years = dividend_years_required(as_of)
    items = []
    excluded_young = 0
    excluded_dividend = 0
    for path in sorted(PRICES.glob("*.json")):
        price = _load(path)
        dividend_path = DIVIDENDS / path.name
        dividend = _load(dividend_path) if dividend_path.exists() else {"annual": [], "frequency": None}
        annual = {int(row["year"]): row for row in dividend.get("annual") or []}
        listed = _listed(price.get("listed_on"))
        if not listed_long_enough(listed, as_of):
            excluded_young += 1
            continue
        if not continuous_dividends(annual, required_dividend_years):
            excluded_dividend += 1
            continue
        used = []
        partial = []
        for year in window:
            row = annual.get(year)
            total = 0.0 if row is None else float(row["cash_per_unit"])
            payments = 0 if row is None else int(row["payments"])
            if listed and listed > date(year, 12, 31):
                continue
            full_year = listed is None or listed <= date(year, 1, 1)
            if full_year:
                used.append({"year": year, "cash_per_unit": round(total, 6), "payments": payments, "partial": False})
            elif total > 0:
                used.append({"year": year, "cash_per_unit": round(total, 6), "payments": payments, "partial": True})
                partial.append(year)
        history = [
            (year, float(row["cash_per_unit"]))
            for year, row in sorted(annual.items())
            if float(row["cash_per_unit"]) > 0
        ]
        summary = middle_half_average(history)
        kept_years = summary["kept_years"]
        avg = summary["average"]
        yield_pct = None
        close = price.get("close")
        if avg is not None and close not in (None, 0):
            yield_pct = round(avg / close * 100, 4)
        typical = next((row["payments"] for row in reversed(used) if row["payments"] > 0), 0)
        ytd_year = as_of.year
        ytd_row = annual.get(ytd_year)
        items.append(
            {
                "code": price["code"],
                "name": price.get("name") or "",
                "full_name": price.get("full_name") or "",
                "category": price.get("category") or "其他",
                "fund_type": price.get("fund_type") or "",
                "listed_on": price.get("listed_on"),
                "date": price.get("date"),
                "open": price.get("open"),
                "high": price.get("high"),
                "low": price.get("low"),
                "close": close,
                "change": price.get("change"),
                "volume_shares": price.get("volume_shares"),
                "frequency": frequency_label(typical) if typical else (dividend.get("frequency") or "無配息"),
                "annual": {str(row["year"]): row["cash_per_unit"] for row in used},
                "payments": {str(row["year"]): row["payments"] for row in used},
                "partial_years": partial,
                "years_used": [row["year"] for row in used],
                "dividend_years_all": [year for year, _ in history],
                "dividend_years_kept": kept_years,
                "avg_interval_low": summary["low"],
                "avg_interval_high": summary["high"],
                "avg_annual_dividend": avg,
                "yield_pct": yield_pct,
                "ytd_year": ytd_year,
                "ytd_dividend": None if ytd_row is None else ytd_row["cash_per_unit"],
                "ytd_payments": 0 if ytd_row is None else ytd_row["payments"],
            }
        )
    items.sort(key=lambda item: (item["yield_pct"] is None, -(item["yield_pct"] or 0), item["code"]))
    rank = 0
    for item in items:
        if item["yield_pct"] is None:
            item["rank"] = None
            continue
        rank += 1
        item["rank"] = rank
    return items, window, excluded_young, excluded_dividend


def save_ranking(as_of: date, price_meta: dict, dividend_meta: dict) -> dict:
    items, window, excluded_young, excluded_dividend = build_items(as_of)
    yields = [item["yield_pct"] for item in items if item["yield_pct"] is not None]
    positive = [value for value in yields if value > 0]
    cutoff = listed_cutoff(as_of)
    required_dividend_years = dividend_years_required(as_of)
    payload = {
        "as_of": as_of.isoformat(),
        "window": window,
        "min_listed_years": MIN_LISTED_YEARS,
        "listed_before": cutoff.isoformat(),
        "excluded_listed_within_years": excluded_young,
        "min_dividend_years": MIN_DIVIDEND_YEARS,
        "dividend_years": required_dividend_years,
        "excluded_dividend_gap": excluded_dividend,
        "formula": "全部年度配息的常態分配中間 50% 平均 ÷ 當日收盤價",
        "note": (
            "月配、季配已依除息日加總為年配息。平均年配息取所有有配息的年度，"
            "以平均數與標準差建立常態分配，只平均落在中間 50% 區間內的年度。"
            f"上市未滿或剛好 {MIN_LISTED_YEARS} 年的 ETF 已排除，只保留上市日早於 {cutoff.isoformat()} 的基金。"
            f"另外，{required_dividend_years[0]} 到 {required_dividend_years[-1]} 每年都要有現金配息，中間中斷的不列入。"
            "此報酬率只反映配息對股價，不含價差。"
        ),
        "generated_at": now_iso(),
        "universe": len(items),
        "priced": sum(1 for item in items if item["close"] is not None),
        "with_yield": len(yields),
        "with_dividend": len(positive),
        "median_yield_pct": None if not positive else round(median(positive), 4),
        "sources": {
            "prices": "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
            "catalog": "https://openapi.twse.com.tw/v1/opendata/t187ap47_L",
            "dividends": "https://www.twse.com.tw/rwd/zh/ETF/etfDiv",
        },
        "price_fetched_at": price_meta["fetched_at"],
        "dividend_fetched_at": dividend_meta["fetched_at"],
        "items": items,
    }
    write_json(DATA / "ranking.json", payload)
    return payload


def parse_as_of(price_meta: dict) -> date:
    if not price_meta.get("as_of"):
        raise RuntimeError("當日行情沒有交易日期")
    return datetime.strptime(price_meta["as_of"], "%Y-%m-%d").date()
