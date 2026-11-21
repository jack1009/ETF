"""下載台灣上市 ETF 當日開高低收，依股號各存一檔。"""

from __future__ import annotations

from .util import (
    PRICES,
    categorize,
    clean_text,
    fetch_json,
    now_iso,
    parse_number,
    roc_compact_to_date,
    write_json,
)

CATALOG_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap47_L"
QUOTE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"


def load_catalog() -> list[dict]:
    rows = fetch_json(CATALOG_URL)
    catalog = []
    for row in rows:
        code = str(row.get("基金代號") or "").strip()
        if not code:
            continue
        listed = roc_compact_to_date(row.get("上市日期"))
        name = clean_text(row.get("基金簡稱"))
        fund_type = clean_text(row.get("基金類型"))
        catalog.append(
            {
                "code": code,
                "name": name,
                "full_name": clean_text(row.get("基金中文名稱")),
                "english_name": clean_text(row.get("基金英文名稱")),
                "fund_type": fund_type,
                "category": categorize(fund_type, name),
                "listed_on": listed.isoformat() if listed else None,
                "inception_on": (
                    roc_compact_to_date(row.get("成立日期")).isoformat()
                    if roc_compact_to_date(row.get("成立日期"))
                    else None
                ),
                "index_name": clean_text(row.get("標的指數/追蹤指數名稱")),
            }
        )
    catalog.sort(key=lambda item: item["code"])
    return catalog


def load_quotes() -> dict[str, dict]:
    quotes = {}
    for row in fetch_json(QUOTE_URL):
        code = str(row.get("Code") or "").strip()
        if not code:
            continue
        trade_date = roc_compact_to_date(row.get("Date"))
        quotes[code] = {
            "date": trade_date.isoformat() if trade_date else None,
            "roc_date": str(row.get("Date") or ""),
            "name": clean_text(row.get("Name")),
            "open": parse_number(row.get("OpeningPrice")),
            "high": parse_number(row.get("HighestPrice")),
            "low": parse_number(row.get("LowestPrice")),
            "close": parse_number(row.get("ClosingPrice")),
            "change": parse_number(row.get("Change")),
            "volume_shares": parse_number(row.get("TradeVolume")),
            "turnover": parse_number(row.get("TradeValue")),
            "transactions": parse_number(row.get("Transaction")),
        }
    return quotes


def save_prices(catalog: list[dict], quotes: dict[str, dict]) -> dict:
    fetched_at = now_iso()
    kept = set()
    priced = 0
    as_of = None
    for fund in catalog:
        code = fund["code"]
        kept.add(code)
        quote = quotes.get(code)
        if quote and quote.get("date") and as_of is None:
            as_of = quote["date"]
        payload = {
            "code": code,
            "name": (quote or {}).get("name") or fund["name"],
            "full_name": fund["full_name"],
            "category": fund["category"],
            "fund_type": fund["fund_type"],
            "listed_on": fund["listed_on"],
            "market": "TWSE",
            "date": None if quote is None else quote["date"],
            "open": None if quote is None else quote["open"],
            "low": None if quote is None else quote["low"],
            "high": None if quote is None else quote["high"],
            "close": None if quote is None else quote["close"],
            "change": None if quote is None else quote["change"],
            "volume_shares": None if quote is None else quote["volume_shares"],
            "turnover": None if quote is None else quote["turnover"],
            "transactions": None if quote is None else quote["transactions"],
            "source": QUOTE_URL,
            "fetched_at": fetched_at,
        }
        if payload["close"] is not None:
            priced += 1
        write_json(PRICES / f"{code}.json", payload)
    for path in PRICES.glob("*.json"):
        if path.stem not in kept:
            path.unlink()
    return {"etf_count": len(catalog), "priced": priced, "as_of": as_of, "fetched_at": fetched_at}
