// Filtering and sorting on the index. The cards and table are already in the
// page (written by site/build.py); this only hides and reorders them. Data
// comes from data.js. Filter state is kept in the URL fragment so a filtered
// view can be linked to, and the back button returns to it.
"use strict";

const DATA = window.SITE_DATA;
const COLOURS = ["green", "yellow", "orange", "red", "grey", "inherited"];

const FACETS = [
  ["status", "Entry", e => [!e.structured ? "notes only" : e.deprecated ? "deprecated" :
    e.framework ? "framework" : "structured"]],
  ...DATA.petals.map(p => ["petal:" + p.key, p.name, e => [petalColour(e, p.key)]]),
  ["kind", "Kind", e => [f(e, "kind")]],
  ["quote_modes", "Quote modes", e => fl(e, "quote_modes")],
  ["trade_structure", "Trade", e => [f(e, "trade_structure")]],
  ["rate", "Rate", e => [f(e, "rate")]],
  ["trade_holder", "Option holder", e => [f(e, "trade_holder")]],
  ["terms_fixed_by", "Terms fixed by", e => [f(e, "terms_fixed_by")]],
  ["price_set_by", "Price set by", e => [f(e, "price_set_by")]],
  ["price_discipline", "Price discipline", e => [f(e, "price_discipline")]],
  ["surplus_to", "Surplus to", e => [f(e, "surplus_to")]],
  ["extraction", "Bad-price exposure", e => fl(e, "extraction")],
  ["early_close", "Early close", e => [f(e, "early_close")]],
  ["class", "Class", e => [e.class || "unknown"]],
  ["cross_chain", "Cross-chain", e => [f(e, "cross_chain")]],
  ["chains", "Chains", e => fl(e, "chains")],
  ["custody", "Custody", e => [f(e, "custody")]],
  ["execution", "Exit execution", e => [f(e, "execution")]],
  ["refund_trigger", "Refund trigger", e => [f(e, "refund_trigger")]],
  ["standing_approval", "Standing approval", e => [f(e, "standing_approval")]],
  ["admin_authority", "Admin authority", e => [f(e, "admin_authority")]],
  ["upgradeable", "Upgradeable", e => [f(e, "upgradeable")]],
  ["actor_set", "Actor sets", e => fl(e, "actor_set")],
  ["jurisdiction", "Actor jurisdictions", e => fl(e, "jurisdiction")],
  ["freeze_assets", "Freezable assets", e => fl(e, "freeze_assets")],
  ["verification", "Exit verification", e => [e.verification || "unknown"]],
  ["api_key", "API key", e => [f(e, "api_key")]],
  ["integrator_identity", "Integrator identity", e => [f(e, "integrator_identity")]],
  ["gasless_start", "Gasless start", e => fl(e, "gasless_start")],
  ["testnet", "Testnet", e => [f(e, "testnet")]],
  ["finisher", "Finisher", e => [f(e, "finisher")]],
  ["source_public", "Source public", e => [f(e, "source_public")]],
  ["incidents", "Incidents", e => [f(e, "incidents")]],
];

const f = (e, k) => (e.structured && e.facets[k]) || "unknown";
const fl = (e, k) => (e.structured ? e.facets[k] : ["unknown"]);
function petalColour(e, p) {
  if (!e.structured) return "not rated";
  return e.petals[p] || "not rated";
}

const esc = s => String(s ?? "").replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function counts(e) {
  const c = { red: 0, orange: 0, grey: 0, yellow: 0, green: 0, inherited: 0 };
  for (const v of Object.values(e.petals)) c[v]++;
  return c;
}
// Mean of scored petals; inherited ones (route or asset risk) are excluded.
const total = e => {
  const v = Object.values(e.scores || {}).filter(x => x !== "inherited");
  return v.length ? v.reduce((a, x) => a + (x ?? 0), 0) / v.length : 0;
};
const rated = e => e.structured && Object.keys(e.petals).length > 0;

const GROUPS = ["Protocols", "Aggregators", "Frameworks", "Deprecated", "Not yet rated"];
// Mirrors group() in site/render.py.
const group = e => !rated(e) ? 4 : e.deprecated ? 3 : e.framework ? 2 :
  e.kind === "aggregator" ? 1 : 0;

const SORTS = {
  // Completeness first: missing facts must not lift an entry above a fully
  // researched one. Matches default_order in site/render.py.
  // Grouped: protocols, aggregators, frameworks, deprecated, not yet rated.
  // Matches default_order in site/render.py.
  complete: ["Most complete, then highest score", (a, b) => {
    const x = counts(a), y = counts(b);
    return group(a) - group(b) || x.grey - y.grey || total(b) - total(a) ||
      a.name.localeCompare(b.name);
  }],
  red: ["Fewest red, then fewest unknown", (a, b) => {
    const x = counts(a), y = counts(b);
    return rated(b) - rated(a) || x.red - y.red || x.orange - y.orange ||
      x.grey - y.grey || x.yellow - y.yellow || a.name.localeCompare(b.name);
  }],
  name: ["Name", (a, b) => a.name.localeCompare(b.name)],
  updated: ["Recently updated", (a, b) => String(b.updated).localeCompare(String(a.updated))],
};

// ------------------------------------------------------------- state

function readState() {
  const p = new URLSearchParams(location.hash.slice(1));
  const sel = {};
  for (const [k, v] of p) if (k.startsWith("f.")) (sel[k.slice(2)] ||= new Set()).add(v);
  const sort = SORTS[p.get("sort")] ? p.get("sort") : "complete";
  return { q: p.get("q") || "", sel, sort,
           view: p.get("view") || "grid" };
}

function writeState(st) {
  const p = new URLSearchParams();
  if (st.q) p.set("q", st.q);
  if (st.sort !== "complete") p.set("sort", st.sort);
  if (st.view !== "grid") p.set("view", st.view);
  for (const [k, vs] of Object.entries(st.sel)) for (const v of vs) p.append("f." + k, v);
  const s = p.toString();
  history.replaceState(null, "", s ? "#" + s : location.pathname + location.search);
}

function matches(e, st, skip) {
  if (st.q) {
    const hay = (e.name + " " + e.slug + " " + (e.scope || "")).toLowerCase();
    if (!hay.includes(st.q.toLowerCase())) return false;
  }
  for (const [key, , get] of FACETS) {
    if (key === skip) continue;
    const want = st.sel[key];
    if (want && want.size && !get(e).some(v => want.has(String(v)))) return false;
  }
  return true;
}

// ------------------------------------------------------------- drawing

const st = readState();
const cards = new Map([...document.querySelectorAll("#cards .card")].map(n => [n.dataset.slug, n]));
const rows = new Map([...document.querySelectorAll("#rows tr")].map(n => [n.dataset.slug, n]));

function update() {
  writeState(st);
  const sorted = [...DATA.entries].sort(SORTS[st.sort][1]);
  let shown = 0;
  document.querySelectorAll(".group-head").forEach(n => n.remove());
  const grouped = st.sort === "complete";
  const seen = new Set();
  for (const e of sorted) {
    const ok = matches(e, st);
    shown += ok;
    if (grouped && ok && !seen.has(group(e))) {
      seen.add(group(e));
      const h = document.createElement("h2");
      h.className = "group-head"; h.textContent = GROUPS[group(e)];
      document.getElementById("cards").appendChild(h);
      const tr = document.createElement("tr");
      tr.className = "group-head";
      tr.innerHTML = `<td colspan="99">${GROUPS[group(e)]}</td>`;
      document.getElementById("rows").appendChild(tr);
    }
    for (const [m, parent] of [[cards, "cards"], [rows, "rows"]]) {
      const n = m.get(e.slug);
      if (!n) continue;
      n.hidden = !ok;
      document.getElementById(parent).appendChild(n);  // reorders
    }
  }
  document.getElementById("cards").hidden = st.view !== "grid";
  document.getElementById("table").hidden = st.view !== "table";
  drawToolbar(shown);
  drawFilters();
}

function drawToolbar(shown) {
  const el = document.getElementById("toolbar");
  el.innerHTML = `<span>${shown} of ${DATA.entries.length}</span>
    <label>Sort <select id="sort">${Object.entries(SORTS).map(([k, [n]]) =>
      `<option value="${k}"${k === st.sort ? " selected" : ""}>${n}</option>`).join("")}</select></label>
    <label>View <select id="view"><option value="grid">Rosettes</option>
      <option value="table"${st.view === "table" ? " selected" : ""}>Table</option></select></label>
    <button id="clear">Clear filters</button>`;
  el.querySelector("#sort").onchange = ev => { st.sort = ev.target.value; update(); };
  el.querySelector("#view").onchange = ev => { st.view = ev.target.value; update(); };
  el.querySelector("#clear").onclick = () => { st.sel = {}; st.q = ""; update(); };
}

const order = v => { const i = COLOURS.indexOf(v); return i < 0 ? 9 : i; };
let drawnOnce = false;

function drawFilters() {
  const el = document.getElementById("filters");
  const open = new Set([...el.querySelectorAll("details[open]")].map(d => d.dataset.key));
  let h = `<input type="search" id="q" placeholder="Search" value="${esc(st.q)}">`;
  for (const [key, label, get] of FACETS) {
    // Counts reflect every other active filter: what ticking the box would give.
    const all = new Map();
    for (const e of DATA.entries) for (const v of get(e)) all.set(String(v), 0);
    for (const e of DATA.entries.filter(e => matches(e, st, key)))
      for (const v of get(e)) all.set(String(v), all.get(String(v)) + 1);
    const vals = [...all.entries()].sort((a, b) => key.startsWith("petal:")
      ? order(a[0]) - order(b[0]) : b[1] - a[1] || a[0].localeCompare(b[0]));
    const sel = st.sel[key] || new Set();
    const isOpen = open.has(key) || sel.size || (!drawnOnce && key.startsWith("petal:"));
    h += `<details data-key="${key}"${isOpen ? " open" : ""}><summary>${esc(label)}${sel.size ? ` (${sel.size})` : ""}</summary>`;
    for (const [v, n] of vals) {
      const dot = COLOURS.includes(v) ? `<i class="dot c-${v}"></i>` : "";
      h += `<label class="${n ? "" : "zero"}"><input type="checkbox" data-key="${key}" value="${esc(v)}"${sel.has(v) ? " checked" : ""}>${dot}${esc(v)}<span class="count">${n}</span></label>`;
    }
    h += "</details>";
  }
  drawnOnce = true;
  el.innerHTML = h;
  const q = el.querySelector("#q");
  q.oninput = () => {
    st.q = q.value; update();
    const n = document.getElementById("q");
    n.focus(); n.setSelectionRange(st.q.length, st.q.length);
  };
  el.querySelectorAll("input[type=checkbox]").forEach(cb => cb.onchange = () => {
    const s = (st.sel[cb.dataset.key] ||= new Set());
    cb.checked ? s.add(cb.value) : s.delete(cb.value);
    if (!s.size) delete st.sel[cb.dataset.key];
    update();
  });
}

update();
