"""HTTP、民國日期與數值解析。"""

from __future__ import annotations

import html
import json
import ssl
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PRICES = DATA / "prices"
DIVIDENDS = DATA / "dividends"
TAIPEI = timezone(timedelta(hours=8))
UA = "etf-yield-pages/1.0 (research; +https://www.twse.com.tw)"


def clean_text(value) -> str:
    return html.unescape(str(value or "")).replace("\u3000", " ").strip()


def now_iso() -> str:
    return datetime.now(TAIPEI).isoformat(timespec="seconds")


def fetch_json(url: str, retries: int = 4, pause: float = 0.6):
    ctx = ssl.create_default_context()
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                raw = resp.read()
            return json.loads(raw.decode("utf-8-sig"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(pause * (attempt + 1))
    raise RuntimeError(f"無法取得 {url}: {last}")


def roc_compact_to_date(value) -> date | None:
    text = str(value or "").strip()
    if not text.isdigit():
        return None
    if len(text) == 7:
        year, month, day = int(text[:3]), int(text[3:5]), int(text[5:7])
    elif len(text) == 6:
        year, month, day = int(text[:2]), int(text[2:4]), int(text[4:6])
    else:
        return None
    try:
        return date(year + 1911, month, day)
    except ValueError:
        return None


def roc_phrase_to_date(value) -> date | None:
    text = str(value or "").strip()
    if "年" not in text or "月" not in text or "日" not in text:
        return None
    try:
        year = int(text.split("年", 1)[0])
        month = int(text.split("年", 1)[1].split("月", 1)[0])
        day = int(text.split("月", 1)[1].split("日", 1)[0])
        return date(year + 1911, month, day)
    except (ValueError, IndexError):
        return None


def parse_number(value) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("X", "").replace("＋", "").replace("+", "")
    if text in {"", "--", "—", "---", "null", "None"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def categorize(fund_type: str, name: str) -> str:
    text = f"{fund_type} {name}"
    if "槓桿" in text or "反向" in text:
        return "槓桿反向"
    if "不動產" in text or "REIT" in text.upper():
        return "不動產"
    if "債" in text:
        return "債券"
    if "期貨" in fund_type:
        return "期貨"
    if "主動" in fund_type:
        return "主動股票"
    if "平衡" in fund_type:
        return "平衡"
    if "境外" in fund_type or "連結" in fund_type:
        return "境外"
    if "國內" in fund_type:
        return "國內股票"
    if "國外" in fund_type:
        return "國外股票"
    return "其他"


def frequency_label(payments: int) -> str:
    if payments <= 0:
        return "無配息"
    if payments == 1:
        return "年配"
    if payments == 2:
        return "半年配"
    if payments == 4:
        return "季配"
    if payments == 6:
        return "雙月配"
    if payments >= 11:
        return "月配"
    return "不定期"
