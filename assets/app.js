(function () {
  const table = document.querySelector("#board");
  if (!table) return;
  const tbody = table.tBodies[0];
  const search = document.querySelector("#q");
  const category = document.querySelector("#category");
  const frequency = document.querySelector("#frequency");
  const hidePartial = document.querySelector("#hide-partial");
  const visibleCount = document.querySelector("#visible-count");
  const empty = document.querySelector("#empty");
  const headers = Array.from(table.tHead.rows[0].cells);

  const rows = Array.from(tbody.rows).filter((row) => row.dataset.code);

  function numberValue(row, key) {
    const raw = row.dataset[key];
    if (raw === undefined || raw === "") return null;
    const value = Number(raw);
    return Number.isFinite(value) ? value : null;
  }

  function apply() {
    const query = search.value.trim().toLowerCase();
    const cat = category.value;
    const freq = frequency.value;
    const onlyFull = hidePartial.checked;
    let shown = 0;
    rows.forEach((row) => {
      const hay = (row.dataset.code + " " + row.dataset.name + " " + row.dataset.fullname).toLowerCase();
      const ok =
        (!query || hay.includes(query)) &&
        (cat === "全部" || row.dataset.category === cat) &&
        (freq === "全部" || row.dataset.frequency === freq) &&
        (!onlyFull || row.dataset.full === "1");
      row.hidden = !ok;
      if (ok) shown += 1;
    });
    let rank = 0;
    rows.forEach((row) => {
      if (row.hidden) return;
      rank += 1;
      const cell = row.querySelector(".rank");
      if (cell) cell.textContent = row.dataset.yield === "" ? "—" : String(rank);
    });
    visibleCount.textContent = String(shown);
    empty.hidden = shown !== 0;
  }

  function sortBy(index, direction) {
    const key = headers[index].dataset.key;
    const numeric = headers[index].dataset.type === "num";
    rows.sort((a, b) => {
      if (numeric) {
        const av = numberValue(a, key);
        const bv = numberValue(b, key);
        if (av === null && bv === null) return a.dataset.code.localeCompare(b.dataset.code);
        if (av === null) return 1;
        if (bv === null) return -1;
        const diff = direction === "asc" ? av - bv : bv - av;
        return diff || a.dataset.code.localeCompare(b.dataset.code);
      }
      const av = (a.dataset[key] || "").toString();
      const bv = (b.dataset[key] || "").toString();
      const diff = av.localeCompare(bv, "zh-Hant");
      return direction === "asc" ? diff : -diff;
    });
    rows.forEach((row) => tbody.appendChild(row));
    headers.forEach((header, i) => {
      header.setAttribute("aria-sort", i === index ? (direction === "asc" ? "ascending" : "descending") : "none");
    });
    apply();
  }

  headers.forEach((header, index) => {
    header.addEventListener("click", () => {
      const current = header.getAttribute("aria-sort");
      const next = current === "descending" ? "asc" : "desc";
      sortBy(index, next);
    });
  });

  [search, category, frequency, hidePartial].forEach((node) => {
    node.addEventListener("input", apply);
  });

  apply();
})();
