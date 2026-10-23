"""HTML for the static site: one page per product and per doc, and an index.

Every page is complete without JavaScript. On the index, app.js adds filtering
and sorting over the cards that are already there.
"""
import math
import re
import subprocess
from html import escape as esc

# Petal length is the score; a zero still draws a stub so the petal shows.
MIN_LENGTH = 0.12
RINGS = (0.3, 0.7, 1.0)                  # band edges: red|orange, orange|yellow, full
SOLIDITY = {"source-verified": 0.95, "partial": 0.6, "spec-only": 0.3}

LEGEND = """<ul class="legend">
<li><i class="dot c-green"></i> needs no one but you</li>
<li><i class="dot c-yellow"></i> needs someone, but anyone will do; or a known delay</li>
<li><i class="dot c-orange"></i> needs a quorum of parties to cooperate</li>
<li><i class="dot c-red"></i> one organisation or one key can refuse, or unbounded</li>
<li><i class="dot c-grey"></i> not known (dashed)</li>
<li><i class="dot c-inherited"></i> inherited: the route's or the asset's, not scored (dotted)</li>
</ul>
<p class="legend">Petal length is the score (0 to 1). Fill: solid = source-verified, faint = spec-only.</p>"""


INTRO = """<div class="intro">
<h1>No gatekeepers. No custodians.</h1>
<p>Every protocol here is measured against that ideal: anyone can use it, and you
remain sovereign over your funds throughout. Where a protocol falls short, we
record exactly where: a committee, an upgradeable contract, an API that can say
no. Each petal is one place a protocol can depart from the ideal, and green
means it doesn't.</p>
<dl class="petal-key">
<dt>Exit path</dt><dd>Who can get my funds back, and by when?</dd>
<dt>Actors</dt><dd>Who else has to act, and can they be stopped?</dd>
<dt>Admin</dt><dd>Can the rules change while my funds are in flight?</dd>
<dt>Data gates</dt><dd>Can an automatic condition hold my exit shut?</dd>
<dt>Judgment</dt><dd>Can someone refuse me for their own reasons?</dd>
<dt>Censorship resistance</dt><dd>Can they decline to serve me at all?</dd>
<dt>Paid execution</dt><dd>Can every step run without me holding gas, because whoever performs it is paid from the assets in it?</dd>
</dl>
""" + LEGEND + """
<p class="note">How each colour is computed: <a href="docs/CRITERIA.html">CRITERIA.md</a>.
How an entry is researched: <a href="docs/METHOD.html">METHOD.md</a>.</p>
</div>"""


def rosette(e, petals, size, labels):
    """Petal length is the score; unknown is full length, dashed, unfilled."""
    r = size / 2
    R = r * 0.52 if labels else r * 0.92
    n = len(petals)
    angle = [math.radians(-90 + i * 360 / n) for i in range(n)]
    out = [f'<svg class="rosette" width="{size}" height="{size}" '
           f'viewBox="{-r} {-r} {size} {size}" role="img" '
           f'aria-label="{esc(e["name"])} rosette">']
    for lvl in RINGS:
        pts = " ".join(f"{math.cos(a) * R * lvl:.1f},{math.sin(a) * R * lvl:.1f}"
                       for a in angle)
        out.append(f'<polygon class="ring" points="{pts}"/>')
    for i, p in enumerate(petals):
        pt = e["petals"].get(p["key"]) if e["structured"] else None
        colour = pt["colour"] if pt else "grey"
        score = pt.get("score") if pt else None
        numeric = isinstance(score, (int, float))
        length = max(MIN_LENGTH, score) if numeric else 1.0
        L, w = R * length, R * 0.26
        op = 0 if colour in ("grey", "inherited") else SOLIDITY.get(pt["verification"], 0.15)
        d = (f"M0,0 C{w:.1f},{-L * .35:.1f} {w * .8:.1f},{-L * .85:.1f} 0,{-L:.1f} "
             f"C{-w * .8:.1f},{-L * .85:.1f} {-w:.1f},{-L * .35:.1f} 0,0 Z")
        title = f'{p["name"]}: {colour}' + (
            f" {score:.1f}" if numeric else "") + (
            f' ({pt["verification"]})' if pt else "" if e["structured"]
            else " (not rated)")
        out.append(f'<path class="petal-{colour}" d="{d}" '
                   f'transform="rotate({i * 360 / n:g})" fill-opacity="{op}" '
                   f'stroke-width="1.2"><title>{esc(title)}</title></path>')
        if labels:
            x, y = math.cos(angle[i]) * (R + 12), math.sin(angle[i]) * (R + 12)
            anchor = "middle" if abs(x) < 5 else "start" if x > 0 else "end"
            out.append(f'<text x="{x:.1f}" y="{y + 4:.1f}" '
                       f'text-anchor="{anchor}">{esc(p["short"])}</text>')
    out.append("</svg>")
    return "".join(out)


def page(title, body, prefix, docs, scripts=""):
    nav = f'<a href="{prefix}quotes.html">quotes</a>' + "".join(
        f'<a href="{prefix}docs/{d[:-3]}.html">'
        f'{esc(d[:-3].replace("_", " ").lower())}</a>' for d in docs)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{prefix}style.css">
</head>
<body>
<header class="top">
<a href="{prefix}index.html" class="brand">Protocols: permissionless and trustless, checked</a>
<nav>{nav}</nav>
</header>
<main>
{body}
</main>
{scripts}
</body>
</html>
"""


LINK = re.compile(r'href="([^":#]*?)([\w.-]+)\.md(#[^"]*)?"')


def markdown(text, slugs, docs):
    """GFM to HTML with pandoc; links between repo .md files become pages.

    Every rendered page sits one directory down, so targets start with ../
    """
    html = subprocess.run(["pandoc", "-f", "gfm", "-t", "html"], input=text,
                          capture_output=True, text=True, check=True).stdout

    def fix(m):
        stem, frag = m.group(2), m.group(3) or ""
        if stem in slugs:
            return f'href="../products/{stem}.html{frag}"'
        if f"{stem}.md" in docs:
            return f'href="../docs/{stem}.html{frag}"'
        return m.group(0)
    return LINK.sub(fix, html)


def product_page(e, petals, body_html, slugs, docs):
    side = []
    if e["structured"] and e["petals"]:
        side.append(rosette(e, petals, 320, True) + LEGEND)
        side.append('<div class="petal-facts">')
        for p in petals:
            pt = e["petals"][p["key"]]
            side.append(f'<h3><i class="dot c-{pt["colour"]}"></i> '
                        f'{esc(p["name"])} <span class="score">{fmt(pt["score"])}</span> '
                        f'<span class="ver">{esc(pt["verification"])}</span></h3><ul>')
            side.extend(f'<li><i class="dot c-{f["colour"]}"></i>'
                        f'<span class="score">{fmt(f["score"])}</span>'
                        f'<span>{esc(f["text"])}</span></li>' for f in pt["facts"])
            side.append("</ul>")
        side.append('<p class="note">Colours are computed from the entry\'s facts '
                    'by the rules in <a href="../docs/CRITERIA.html">CRITERIA.md'
                    '</a>. To dispute a score, dispute the fact or the rule.'
                    '</p></div>')
    elif e["structured"]:
        side.append('<p class="note">No petals could be rated for this entry; '
                    'their risk is the route they choose.</p>')
    else:
        side.append(rosette(e, petals, 320, True) +
                    '<p class="note">This entry has no structured header yet, so '
                    'nothing is rated. The notes are in the earlier format.</p>')
    if e["structured"]:
        inh = ", ".join(
            f'<a href="{s}.html">{esc(s)}</a>' if s in slugs else esc(str(s))
            for s in e["inherits"])
        fc = e["facets"]
        rows = [("Kind", esc(str(e["kind"]))), ("Class", esc(str(e["class"] or ""))),
                ("Updated", esc(str(e["updated"] or ""))), ("Inherits", inh),
                ("Chains", esc(", ".join(fc["chains"]))),
                ("Custody", esc(fc["custody"])), ("Execution", esc(fc["execution"])),
                ("Refund trigger", esc(fc["refund_trigger"])),
                ("Incidents", str(len(e["incidents"]))),
                ("Open questions", str(len(e["open_questions"])))]
        side.append('<div class="facts"><h3>Facts</h3><dl>' + "".join(
            f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows if v) + "</dl></div>")
        side.append(trade_panel(e.get("trade") or {}))
    side.append(sources(e.get("sources") or []))
    side.append(f'<p class="note"><a href="{e["slug"]}.md">Raw entry with YAML '
                f'header</a></p>')
    body = (f'<p class="crumb"><a href="../index.html">All products</a></p>'
            f'<div class="detail"><aside>{"".join(side)}</aside>'
            f'<article class="md">{body_html}</article></div>')
    return page(e["name"], body, "../", docs)


TRADE_ROWS = [("structure", "Structure"), ("holder", "Option holder"),
              ("strike", "Strike"), ("expiry", "Expiry"),
              ("early_close", "Early close"), ("premium", "Premium"),
              ("terms_fixed_by", "Terms fixed by"), ("price_set_by", "Price set by"),
              ("discipline", "Price discipline"), ("surplus_to", "Surplus to"),
              ("extraction", "Bad-price exposure"), ("sides", "Fixable side"),
              ("rate", "Rate"), ("quote_validity", "Quote validity"),
              ("partial_fill", "Partial fill"), ("partial_remainder", "Partial remainder")]


def trade_panel(t):
    """The trade the user enters, described, not rated (CRITERIA.md, Trade)."""
    if not t:
        return ('<div class="facts"><h3>Trade</h3><p class="note">Not recorded '
                'yet.</p></div>')
    def val(v):
        if isinstance(v, list):
            return ", ".join(map(str, v)) or "none recorded"
        return "unknown" if v is None else str(v)
    rows = "".join(f"<dt>{label}</dt><dd>{esc(val(t.get(k)))}</dd>"
                   for k, label in TRADE_ROWS if k in t)
    return (f'<div class="facts"><h3>Trade</h3><dl>{rows}</dl><p class="note">'
            f'Described, not rated: see <a href="../docs/CRITERIA.html#trade">'
            f'CRITERIA.md, Trade</a>.</p></div>')


def tree_url(url, commit):
    """Link to the repository as it was at the commit read."""
    url = url.rstrip("/")
    if "gitlab.com" in url:
        return f"{url}/-/tree/{commit}"
    if "github.com" in url:
        return f"{url}/tree/{commit}"
    return url


def sources(items):
    if not items:
        return ('<div class="sources"><h3>Sources read</h3><p class="note">No '
                'repositories recorded.</p></div>')
    li = []
    for s in items:
        commit = str(s.get("commit", ""))
        is_hash = len(commit) >= 7 and all(c in "0123456789abcdefABCDEF" for c in commit)
        # A git commit links to the tree at that commit; anything else (a
        # package version, a verified-source date, a docs snapshot) is shown
        # as written.
        at = (f'<a href="{esc(tree_url(s["url"], commit))}"><code>{esc(commit[:10])}</code></a>'
              if is_hash else f'<code>{esc(commit)}</code>')
        li.append(
            f'<li><a href="{esc(s["url"])}">{esc(s.get("repo") or s["url"])}</a>'
            f' at {at} ({esc(str(s.get("commit_date", "")))})'
            + (f'<div class="note">{esc(s["note"])}</div>' if s.get("note") else "")
            + "</li>")
    return f'<div class="sources"><h3>Sources read</h3><ul>{"".join(li)}</ul></div>'


def doc_page(name, body_html, docs):
    return page(name[:-3], f'<article class="md doc">{body_html}</article>',
                "../", docs)


def fmt(score):
    if score == "inherited":
        return "inh."
    return "?" if score is None else f"{score:.1f}"


def colour_counts(e):
    c = dict.fromkeys(("red", "orange", "grey", "yellow", "green", "inherited"), 0)
    for p in (e.get("petals") or {}).values():
        c[p["colour"]] += 1
    return c


def total_score(e):
    """Mean of the petals the product is scored on (inherited ones excluded),
    so an aggregator rated on two petals compares fairly with a six-petal
    entry. Unknown petals count as zero here; completeness sorts first."""
    scored = [p for p in (e.get("petals") or {}).values() if p.get("score") != "inherited"]
    if not scored:
        return 0.0
    return sum(p["score"] or 0 for p in scored) / len(scored)


GROUPS = ["Protocols", "Aggregators", "Frameworks", "Deprecated", "Not yet rated"]


def group(e):
    """Which list an entry ranks in. Aggregators are compared only with each
    other: their own petals rate the layer they control, and the rest belong
    to whatever route they pick. Frameworks describe a standard rather than a
    deployment, and deprecated products shouldn't be chosen."""
    if not (e["structured"] and e["petals"]):
        return 4
    if e.get("deprecated"):
        return 3
    if e.get("framework"):
        return 2
    if e.get("kind") == "aggregator":
        return 1
    return 0


def default_order(e):
    """Group first (see group()); then fewest unknown (grey) petals; then
    highest mean score over the petals the entry is rated on; then name.

    Completeness comes before score, so an entry can't rank higher by having
    facts missing. Inherited petals (an aggregator's route) are neither
    missing nor scored, so they count for neither. Within the same
    completeness, the mean decides, so a verified quorum ranks above one
    organisation and that above one key.
    """
    c = colour_counts(e)
    return (group(e), c["grey"], -round(total_score(e), 3), e["name"].lower())


def card(e, petals):
    bits = [("framework" if e.get("framework") else e["kind"]) if e["structured"]
            else "notes only", e.get("deprecated") and "deprecated",
            e.get("class") and f'Class {e["class"]}', e.get("updated")]
    meta = " · ".join(str(b) for b in bits if b)
    if e["structured"] and not e["petals"]:  # (no petals: shouldn't happen now)
        rose = ('<div class="note norose">aggregator: see the routes it '
                'uses</div>')
    else:
        rose = rosette(e, petals, 150, False)
    cls = "card" + ("" if e["structured"] else " legacy")
    return (f'<a class="{cls}" data-slug="{e["slug"]}" '
            f'href="products/{e["slug"]}.html">{rose}'
            f'<div class="name">{esc(e["name"])}</div>'
            f'<div class="meta">{esc(meta)}</div></a>')


def table(entries, petals):
    head = "".join(f"<th>{esc(p['name'])}</th>" for p in petals)
    rows = []
    for e in entries:
        cells = []
        for p in petals:
            pt = e["petals"].get(p["key"]) if e["structured"] else None
            cells.append(f'<td><i class="dot c-{pt["colour"]}" '
                         f'title="{pt["colour"]}"></i></td>' if pt
                         else '<td class="note">–</td>')
        fc = e.get("facets") or {}
        rows.append(
            f'<tr data-slug="{e["slug"]}"><td><a href="products/{e["slug"]}.html">'
            f'{esc(e["name"])}</a></td>{"".join(cells)}'
            f'<td>{esc(fc.get("kind", "notes only"))}</td>'
            f'<td>{esc(str(e.get("class") or ""))}</td>'
            f'<td>{esc(fc.get("custody", ""))}</td>'
            f'<td>{esc(fc.get("execution", ""))}</td>'
            f'<td>{esc(str(e.get("verification") or ""))}</td>'
            f'<td>{esc(str(e.get("updated") or ""))}</td></tr>')
    return (f'<div class="tablewrap"><table class="rank"><thead><tr><th>Product</th>'
            f'{head}<th>Kind</th><th>Class</th><th>Custody</th><th>Execution</th>'
            f'<th>Verification</th><th>Updated</th></tr></thead>'
            f'<tbody id="rows">{"".join(rows)}</tbody></table></div>')


QUOTE_COLS = [("modes", "Quote modes"), ("rate", "Rate"), ("sides", "Fixable side"),
              ("quote_validity", "Quote validity"), ("partial_fill", "Partial fill decided by"),
              ("terms_fixed_by", "Terms fixed by"), ("holder", "Option holder"),
              ("surplus_to", "Surplus to"), ("gasless", "Gasless start"),
              ("cash", "Paid execution")]


def quotes_page(entries, docs):
    """One row per venue: the quotes it can serve (CRITERIA.md, Trade)."""
    def cell(v):
        if isinstance(v, list):
            return ", ".join(map(str, v)) or "none"
        return "unknown" if v is None else str(v)
    rows = []
    for e in sorted(entries, key=lambda e: e["name"].lower()):
        if not e["structured"]:
            continue
        t, fc = e.get("trade") or {}, e["facets"]
        cash = e["petals"].get("cash", {})
        vals = {"modes": fc.get("quote_modes"), "gasless": fc.get("gasless_start"),
                "cash": f'{cash.get("colour", "grey")} {fmt(cash.get("score"))}'}
        tds = "".join(
            f'<td class="{"unk" if cell(vals.get(k, t.get(k))) == "unknown" else ""}">'
            f'{esc(cell(vals.get(k, t.get(k))))}</td>' for k, _ in QUOTE_COLS)
        rows.append(f'<tr><td><a href="products/{e["slug"]}.html">{esc(e["name"])}</a>'
                    f'<div class="note">{esc(str(e.get("kind") or ""))}'
                    f'{" · deprecated" if e.get("deprecated") else ""}'
                    f'{" · framework" if e.get("framework") else ""}</div></td>{tds}</tr>')
    head = "".join(f"<th>{esc(n)}</th>" for _, n in QUOTE_COLS)
    body = f"""<article class="md doc"><h1>Quotes</h1>
<p>Which quote modes each venue can serve, generated from the entries' <code>trade</code>
facts (see <a href="docs/CRITERIA.html#trade">CRITERIA.md, Trade</a>). <b>exact</b> needs a firm
rate; <b>atleast</b> needs a fixable input with a signed floor; <b>upto</b> needs a fixable
output. Quote validity is in seconds where measured. <i>unknown</i> cells are open questions
on the entry. The same data is in <a href="data.json">data.json</a>.</p></article>
<div class="tablewrap"><table class="quotes"><thead><tr><th>Venue</th>{head}</tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>"""
    return page("Quotes", body, "", docs)


def index_page(entries, petals, docs):
    entries = sorted(entries, key=default_order)
    n = sum(e["structured"] for e in entries)
    cards, last = [], None
    for e in entries:
        g = group(e)
        if g != last:
            cards.append(f'<h2 class="group-head" data-group="{g}">{GROUPS[g]}</h2>')
            last = g
        cards.append(card(e, petals))
    body = f"""<div class="layout">
<aside class="filters" id="filters"><p class="note">{len(entries)} entries,
{n} with structured headers. Filtering needs JavaScript; without it every
entry is listed.</p></aside>
<section>
{INTRO}
<div class="toolbar" id="toolbar"></div>
<div class="grid" id="cards">{"".join(cards)}</div>
<div id="table" hidden>{table(entries, petals)}</div>
</section>
</div>"""
    scripts = '<script src="data.js"></script>\n<script src="app.js"></script>'
    return page("Protocols: permissionless and trustless, checked", body, "", docs, scripts)
