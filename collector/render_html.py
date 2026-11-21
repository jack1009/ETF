"""把排名寫成 GitHub Pages 用的靜態 HTML。"""

from __future__ import annotations

from .util import ROOT


def _esc(value) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _price(value) -> str:
    if value is None:
        return "—"
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    if "." not in text:
        return text + ".00"
    if len(text.split(".", 1)[1]) == 1:
        return text + "0"
    return text


def _cash(value) -> str:
    if value is None:
        return "—"
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _pct(value) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}%"


def _change(value) -> str:
    if value is None:
        return '<span class="flat">—</span>'
    if value > 0:
        return f'<span class="up">+{_price(value)}</span>'
    if value < 0:
        return f'<span class="down">{_price(value)}</span>'
    return '<span class="flat">0.00</span>'


def _year_cell(item: dict, year: int) -> str:
    if year not in item["years_used"]:
        return '<td class="muted">—</td>'
    cash = item["annual"].get(str(year))
    mark = '<span class="star">*</span>' if year in item["partial_years"] else ""
    return f"<td>{_cash(cash)}{mark}</td>"


def _attr(value) -> str:
    if value is None:
        return ""
    return _esc(value)


def render(ranking: dict) -> None:
    window = ranking["window"]
    max_yield = max((item["yield_pct"] or 0) for item in ranking["items"]) or 1
    categories = ["全部"] + sorted({item["category"] for item in ranking["items"]})
    frequencies = ["全部", "月配", "雙月配", "季配", "半年配", "年配", "不定期", "無配息"]
    rows = []
    for item in ranking["items"]:
        width = 0 if not item["yield_pct"] else min(100, round(item["yield_pct"] / max_yield * 100))
        full = "1" if len(item["years_used"]) == len(window) and not item["partial_years"] else "0"
        year_data = " ".join(
            f'data-y{year}="{_attr(item["annual"].get(str(year)) if year in item["years_used"] else None)}"'
            for year in window
        )
        yield_cell = "—"
        if item["yield_pct"] is not None:
            yield_cell = (
                f'{_pct(item["yield_pct"])}'
                f'<span class="bar" aria-hidden="true"><i style="width:{width}%"></i></span>'
            )
        ytd = "—" if item["ytd_dividend"] is None else _cash(item["ytd_dividend"])
        rows.append(
            "<tr "
            f'data-code="{_attr(item["code"])}" '
            f'data-name="{_attr(item["name"])}" '
            f'data-fullname="{_attr(item["full_name"])}" '
            f'data-category="{_attr(item["category"])}" '
            f'data-frequency="{_attr(item["frequency"])}" '
            f'data-close="{_attr(item["close"])}" '
            f'data-change="{_attr(item["change"])}" '
            f'data-open="{_attr(item["open"])}" '
            f'data-high="{_attr(item["high"])}" '
            f'data-low="{_attr(item["low"])}" '
            f'data-yield="{_attr(item["yield_pct"])}" '
            f'data-avg="{_attr(item["avg_annual_dividend"])}" '
            f'data-ytd="{_attr(item["ytd_dividend"])}" '
            f'data-rank="{_attr(item["rank"])}" '
            f'{year_data} '
            f'data-full="{full}">'
            f'<td class="rank">{item["rank"] or "—"}</td>'
            f'<td class="left code">{_esc(item["code"])}</td>'
            f'<td class="left name-cell" title="{_attr(item["full_name"])}"><span class="name">{_esc(item["name"])}</span>'
            f'<span class="sub">{_esc(item["full_name"])}</span></td>'
            f'<td class="yield">{yield_cell}</td>'
            f'<td class="left">{_esc(item["frequency"])}</td>'
            f'<td>{_price(item["close"])}</td>'
            f'<td>{_change(item["change"])}</td>'
            f'<td>{_cash(item["avg_annual_dividend"])}</td>'
            + "".join(_year_cell(item, year) for year in window)
            + f"<td>{ytd}</td>"
            f'<td>{_price(item["open"])}</td>'
            f'<td>{_price(item["high"])}</td>'
            f'<td>{_price(item["low"])}</td>'
            f'<td class="left"><span class="tag">{_esc(item["category"])}</span></td>'
            "</tr>"
        )

    year_headers = "".join(
        f'<th data-key="y{year}" data-type="num" aria-sort="none">{year}</th>' for year in window
    )
    # Year cells are not data-attributes; sorting those columns falls back to null.
    # Put year totals on the row so the header sort works.
    category_options = "".join(f'<option>{_esc(name)}</option>' for name in categories)
    frequency_options = "".join(f'<option>{_esc(name)}</option>' for name in frequencies)
    median = "—" if ranking["median_yield_pct"] is None else f'{ranking["median_yield_pct"]:.2f}%'
    window_label = f"{window[0]}–{window[-1]}"
    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>台灣上市 ETF 配息報酬率</title>
  <meta name="description" content="依當日收盤價與近三個完整年度的年配息，計算台灣上市 ETF 的配息報酬率。">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Noto+Sans+TC:wght@400;500;700&family=Noto+Serif+TC:wght@600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <main class="wrap">
    <header class="mast">
      <div class="seal">臺</div>
      <div>
        <p class="kicker">TWSE ETF Yield</p>
        <h1>台灣上市 ETF 配息報酬率</h1>
        <p class="lede">月配與季配已依除息日加總成年配息。報酬率是近三個完整年度的平均年配息，除以當日收盤價，不含價差。上市未滿或剛好 {ranking["min_listed_years"]} 年的 ETF 不列入。{ranking["dividend_years"][0]} 到 {ranking["dividend_years"][-1]} 必須每年都有配息。</p>
      </div>
      <p class="asof">行情日<strong>{_esc(ranking["as_of"])}</strong>完整年度 {window_label}</p>
    </header>
    <section class="stats" aria-label="摘要">
      <div class="stat"><span>符合條件</span><b>{ranking["universe"]}</b></div>
      <div class="stat"><span>有當日收盤</span><b>{ranking["priced"]}</b></div>
      <div class="stat"><span>近三年有配息</span><b>{ranking["with_dividend"]}</b></div>
      <div class="stat"><span>有配息者中位數</span><b>{median}</b></div>
    </section>
    <div class="toolbar">
      <input id="q" class="search" type="search" placeholder="搜尋代號或名稱，例如 0056" aria-label="搜尋">
      <select id="category" aria-label="類別">{category_options}</select>
      <select id="frequency" aria-label="配息節奏">{frequency_options}</select>
      <label class="check"><input id="hide-partial" type="checkbox">只看三年都滿年</label>
      <span class="muted">顯示 <b id="visible-count">{len(ranking["items"])}</b> 檔</span>
    </div>
    <div class="board">
      <table id="board">
        <thead>
          <tr>
            <th data-key="rank" data-type="num" aria-sort="none">排名</th>
            <th class="left" data-key="code" data-type="text" aria-sort="none">代號</th>
            <th class="left" data-key="name" data-type="text" aria-sort="none">名稱</th>
            <th data-key="yield" data-type="num" aria-sort="descending">報酬率</th>
            <th class="left" data-key="frequency" data-type="text" aria-sort="none">節奏</th>
            <th data-key="close" data-type="num" aria-sort="none">收盤</th>
            <th data-key="change" data-type="num" aria-sort="none">漲跌</th>
            <th data-key="avg" data-type="num" aria-sort="none">平均年配息</th>
            {year_headers}
            <th data-key="ytd" data-type="num" aria-sort="none">{ranking["items"][0]["ytd_year"] if ranking["items"] else ""}至今</th>
            <th data-key="open" data-type="num" aria-sort="none">開</th>
            <th data-key="high" data-type="num" aria-sort="none">高</th>
            <th data-key="low" data-type="num" aria-sort="none">低</th>
            <th class="left" data-key="category" data-type="text" aria-sort="none">類別</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows)}
        </tbody>
      </table>
      <p id="empty" class="empty" hidden>沒有符合條件的 ETF。</p>
    </div>
    <footer class="foot">
      <p>標有 <span class="star">*</span> 的年度是上市未滿一年，仍列入平均。沒有列入的年度以破折號表示，不當作零配息。</p>
      <p>{_esc(ranking["note"])} 配息可能包含收益平準金，過去配息不代表未來。</p>
      <p>價格來源 <a href="{_esc(ranking["sources"]["prices"])}">證交所當日行情</a>，
      配息來源 <a href="{_esc(ranking["sources"]["dividends"])}">ETF 收益分配</a>。
      個股檔案在 <code>data/prices/</code> 與 <code>data/dividends/</code>。更新於 {_esc(ranking["generated_at"])}。</p>
    </footer>
  </main>
  <script src="assets/app.js"></script>
</body>
</html>
"""
    # Attach per-year values for sorting. Done as a second pass to keep the row template readable.
    (ROOT / "index.html").write_text(html, encoding="utf-8")

