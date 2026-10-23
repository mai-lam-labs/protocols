#!/usr/bin/env python3
"""Build the static site from products/*.md into _site/.

Colours are computed here from the YAML header facts, following the rules in
CRITERIA.md. Every colour carries the reasons that produced it, so the page can
show which fact decided it. Entries without a header are listed with grey
petals until they are converted.

Usage: python3 site/build.py [--out _site]
Needs Python 3, PyYAML and pandoc. The output is plain HTML pages that work
from file:// with JavaScript off; JS only adds filtering on the index.
"""
import argparse
import datetime
import json
import re
import shutil
import sys
from pathlib import Path

import yaml

import render
import scoring

ROOT = Path(__file__).resolve().parent.parent
SITE_SRC = Path(__file__).resolve().parent
DOCS = ["CONSTRAINT.md", "CRITERIA.md", "DESIGN_IMPLICATIONS.md", "METHOD.md",
        "GASLESS.md"]

PETALS = ["exit", "actors", "admin", "data", "judgment", "censorship", "cash"]
PETAL_NAMES = {"exit": "Exit path", "actors": "Actors", "admin": "Admin",
               "data": "Data gates", "judgment": "Judgment",
               "censorship": "Censorship resistance",
               "cash": "Paid execution"}
# Short labels for the rosette, where the full name doesn't fit.
PETAL_SHORT = {"censorship": "Censorship"}
# Which verification level in the header backs each petal.
VERIFICATION_KEY = {"exit": "exit", "actors": "actors", "admin": "admin",
                    "data": "data", "judgment": "judgment",
                    "censorship": "service", "cash": "exit"}

CHAIN_ALIASES = {
    "eth": "Ethereum", "ethereum": "Ethereum",
    "arbitrum": "Arbitrum", "optimism": "Optimism", "op mainnet": "Optimism",
    "base": "Base", "polygon": "Polygon", "polygon pos": "Polygon",
    "bnb": "BNB Chain", "bsc": "BNB Chain", "bnb chain": "BNB Chain",
    "bnb smart chain": "BNB Chain",
    "avax": "Avalanche", "avalanche": "Avalanche",
    "btc": "Bitcoin", "doge": "Dogecoin", "ltc": "Litecoin",
    "bch": "Bitcoin Cash", "xrp": "XRP",
    "xlayer": "X Layer", "x layer": "X Layer",
    "worldchain": "World Chain", "world chain": "World Chain",
}


def is_unknown(v):
    return v is None or (isinstance(v, str) and v.strip().lower() == "unknown")


def as_list(v):
    """A list facet; returns None when the facet itself is unknown."""
    if isinstance(v, list):
        return v
    if v in ("none", [], None) or v is False:
        return []
    return None


def bound_max(b):
    """The upper end of exit_bound_seconds: a number, inf, or None if unknown."""
    if isinstance(b, (int, float)) and not isinstance(b, bool):
        return b
    if isinstance(b, list) and len(b) == 2 and all(
            isinstance(x, (int, float)) for x in b):
        return b[1]
    if isinstance(b, str) and b.strip() == "unbounded":
        return float("inf")
    return None


# ---------------------------------------------------------------- parsing

def split_header(text):
    if not text.startswith("---"):
        return None, text
    _, head, body = text.split("---", 2)
    # YAML keeps the last of two equal keys and drops the first without a
    # word; refuse that, since it silently loses recorded facts.
    seen = set()
    for line in head.splitlines():
        m = re.match(r"^([A-Za-z_]+):", line)
        if m:
            if m.group(1) in seen:
                raise ValueError(f"duplicate top-level key {m.group(1)!r}")
            seen.add(m.group(1))
    return yaml.safe_load(head), body.lstrip("\n")


LEGACY_FIELDS = {
    "verification": re.compile(r"\*\*Verification tier:\*\*\s*`([^`]+)`"),
    "updated": re.compile(r"\*\*Last updated:\*\*\s*(\S+)"),
    "class": re.compile(r"\*\*Class:\*\*\s*([A-E])\b"),
}


def legacy_entry(slug, body, h=None):
    """An entry in the earlier prose format. Its header, if any, holds only
    `sources`."""
    title = re.search(r"^#\s+(.+)$", body, re.M)
    e = {"slug": slug, "name": title.group(1).strip() if title else slug,
         "structured": False, "petals": {},
         "sources": (h or {}).get("sources") or []}
    for k, rx in LEGACY_FIELDS.items():
        m = rx.search(body)
        e[k] = m.group(1) if m else None
    return e


def resolve_same_as(headers, h, key):
    v = h.get(key)
    seen = set()
    while isinstance(v, dict) and "same_as" in v and v["same_as"] not in seen:
        seen.add(v["same_as"])
        other = headers.get(v["same_as"])
        if not other:
            break
        v = other.get(key)
    return v


def norm_chain(c):
    return CHAIN_ALIASES.get(str(c).strip().lower(), str(c).strip())


def tri(v):
    """Booleans and unknowns as facet labels."""
    if v is True:
        return "yes"
    if v is False:
        return "no"
    if is_unknown(v):
        return "unknown"
    return str(v)


def gasless(v):
    """gasless_start lists the token standards a start with no native gas
    works for; legacy true/false are still read."""
    if isinstance(v, list):
        return sorted(map(str, v)) or ["none"]
    if v is False or v == "none":
        return ["none"]
    if v is True:
        return ["yes, standards not recorded"]
    return ["unknown"]


BOUNDED_RATES = ("firm", "floating_above_bound", "decaying", "curve", "par")


def quote_modes(t):
    """Which quote modes the facts allow (CRITERIA.md, Trade)."""
    sides, rate = t.get("sides"), t.get("rate")
    if sides == "none":
        return ["none"]
    if rate == "inherited":
        return ["inherited"]
    if not isinstance(sides, list) and is_unknown(rate):
        return ["unknown"]
    sides = sides if isinstance(sides, list) else []
    modes = []
    if rate == "firm":
        modes.append("exact")
    if "exact_in" in sides and rate in BOUNDED_RATES:
        modes.append("atleast")
    if "exact_out" in sides:
        modes.append("upto")
    if not modes:
        return ["unknown"] if is_unknown(rate) or not sides else ["none"]
    if is_unknown(rate):
        modes.append("rate unknown")      # exact and atleast can't be decided yet
    if t.get("partial_fill") in ("submitter_chooses", "counterparty_chooses"):
        modes.append("partial by others")
    return modes


def structured_entry(slug, h, headers):
    h = dict(h)
    for key in ("admin", "judgment", "service"):
        h[key] = resolve_same_as(headers, h, key)
    e = h.get("exit") or {}
    m = bound_max(e.get("exit_bound_seconds"))
    longest = None if m is None else m

    aggregator = h.get("kind") == "aggregator"
    petals = {}
    if True:
        rated = {
            "exit": scoring.rate_exit(h),
            "actors": scoring.rate_actors(h),
            "admin": scoring.rate_admin(h, longest),
            "data": scoring.rate_data(h),
            "judgment": scoring.rate_judgment(h),
            "censorship": scoring.rate_censorship(h, tri),
            "cash": scoring.rate_cash(h),
        }
        if aggregator:
            # The route decides these; the aggregator is rated on its own router
            # (Admin) and its own service (Censorship resistance).
            for p in ("exit", "actors", "data", "judgment"):
                rated[p] = (scoring.INHERITED,
                            [(scoring.INHERITED, "inherited from the route chosen; "
                                                 "see the routes' own entries")])
        ver = h.get("verification") or {}
        for p in PETALS:
            score, facts = rated[p]
            petals[p] = {"score": score, "colour": scoring.colour(score),
                         "verification": tri(ver.get(VERIFICATION_KEY[p])),
                         "facts": [{"score": fs, "colour": scoring.colour(fs),
                                    "text": t} for fs, t in facts]}

    chains = h.get("chains")
    actors = as_list(h.get("actors")) or []
    svc = h.get("service") or {}
    ia = svc.get("integrator_access") or {} if isinstance(svc, dict) else {}
    integ = h.get("integration") or {}
    adm = h.get("admin") or {}
    jud = h.get("judgment") or {}
    incidents = as_list(h.get("incidents")) or []
    trade = h.get("trade") if isinstance(h.get("trade"), dict) else {}
    bad = [q for q in h.get("open_questions") or [] if not isinstance(q, str)]
    if bad:
        # An unquoted ": " turns a question into a mapping (METHOD.md).
        raise ValueError(f"open_questions must be strings; quote this: {bad[0]!r}")
    return {
        "slug": slug,
        "name": h.get("name", slug),
        "structured": True,
        "framework": h.get("framework") is True,
        "deprecated": h.get("status") == "deprecated",
        "scope": h.get("scope"),
        "kind": h.get("kind"),
        "class": h.get("class"),
        "updated": str(h.get("updated")) if h.get("updated") else None,
        "inherits": h.get("inherits") or [],
        "trade": trade,
        "petals": petals,
        "verification": (h.get("verification") or {}).get("exit"),
        "incidents": incidents,
        "open_questions": h.get("open_questions") or [],
        "sources": h.get("sources") or [],
        "facets": {
            "kind": tri(h.get("kind")),
            "class": tri(h.get("class")),
            "cross_chain": tri(h.get("cross_chain")),
            "chains": sorted({norm_chain(c) for c in chains})
            if isinstance(chains, list) else ["unknown"],
            "custody": tri(e.get("custody")),
            "execution": tri(e.get("execution")),
            "refund_trigger": tri(e.get("refund_trigger")),
            "standing_approval": tri(e.get("standing_approval")),
            "admin_authority": tri(adm.get("authority")),
            "upgradeable": tri(adm.get("upgradeable")),
            "actor_set": sorted({tri(a.get("set")) for a in actors}) or ["none"],
            "jurisdiction": sorted({tri(a.get("jurisdiction"))
                                    for a in actors}) or ["none"],
            "freeze_assets": sorted(map(str, as_list(jud.get("freeze_assets"))
                                        or [])) or ["none"],
            "api_key": tri(ia.get("api_key")),
            "integrator_identity": tri(ia.get("identity")),
            "gasless_start": gasless(integ.get("gasless_start")),
            "testnet": tri(integ.get("testnet")),
            "finisher": tri(integ.get("finisher")),
            "source_public": tri(h.get("source_public")),
            "incidents": "yes" if incidents else "none recorded",
            "trade_structure": tri(trade.get("structure")),
            "quote_modes": quote_modes(trade),
            "rate": tri(trade.get("rate")),
            "trade_holder": tri(trade.get("holder")),
            "terms_fixed_by": tri(trade.get("terms_fixed_by")),
            "price_set_by": tri(trade.get("price_set_by")),
            "price_discipline": tri(trade.get("discipline")),
            "surplus_to": tri(trade.get("surplus_to")),
            "early_close": tri(trade.get("early_close")),
            "extraction": (sorted(map(str, trade["extraction"])) or ["none recorded"])
            if isinstance(trade.get("extraction"), list) else ["unknown"],
        },
    }


def build(out):
    prods = sorted((ROOT / "products").glob("*.md"))
    raw = {}
    for p in prods:
        try:
            h, body = split_header(p.read_text())
        except Exception as exc:
            sys.exit(f"{p.name}: {exc}")
        raw[p.stem] = (h, body)
    headers = {s: h for s, (h, _) in raw.items() if h and "exit" in h}

    entries, problems = [], []
    for slug, (h, body) in raw.items():
        try:
            if h and "exit" in h:
                entries.append(structured_entry(slug, h, headers))
            else:
                entries.append(legacy_entry(slug, body, h))
        except Exception as exc:  # keep building; report at the end
            problems.append(f"{slug}: {exc}")
            entries.append(legacy_entry(slug, body, h))

    docs = [d for d in DOCS if (ROOT / d).exists()]
    petals = [{"key": p, "name": PETAL_NAMES[p],
               "short": PETAL_SHORT.get(p, PETAL_NAMES[p])} for p in PETALS]
    slugs = set(raw)

    if out.exists():
        shutil.rmtree(out)
    (out / "products").mkdir(parents=True)
    (out / "docs").mkdir()
    for name in ("app.js", "style.css"):
        shutil.copy(SITE_SRC / name, out / name)
    (out / ".nojekyll").touch()

    for e in entries:
        _, body = raw[e["slug"]]
        shutil.copy(ROOT / "products" / f"{e['slug']}.md", out / "products")
        (out / "products" / f"{e['slug']}.html").write_text(
            render.product_page(e, petals, render.markdown(body, slugs, docs),
                                slugs, docs))
    for d in docs:
        shutil.copy(ROOT / d, out / "docs" / d)
        (out / "docs" / f"{d[:-3]}.html").write_text(render.doc_page(
            d, render.markdown((ROOT / d).read_text(), slugs, docs), docs))
    (out / "index.html").write_text(render.index_page(entries, petals, docs))
    (out / "quotes.html").write_text(render.quotes_page(entries, docs))

    # Everything computed, for anyone who wants the data rather than the pages.
    (out / "data.json").write_text(json.dumps({
        "built": datetime.date.today().isoformat(), "petals": petals,
        "docs": docs, "entries": entries}, indent=1, default=str))
    # Only what the index's filters need, as a script so it loads from file://.
    slim = [{"slug": e["slug"], "name": e["name"], "scope": e.get("scope"),
             "structured": e["structured"], "class": e.get("class"),
             "framework": e.get("framework", False),
             "deprecated": e.get("deprecated", False),
             "kind": e.get("kind"),
             "verification": e.get("verification"),
             "updated": e.get("updated"), "facets": e.get("facets"),
             "petals": {k: v["colour"] for k, v in e.get("petals", {}).items()},
             "scores": {k: v["score"] for k, v in e.get("petals", {}).items()}}
            for e in entries]
    (out / "data.js").write_text("window.SITE_DATA = " + json.dumps(
        {"petals": petals, "entries": slim}, default=str) + ";\n")

    n = sum(e["structured"] for e in entries)
    print(f"{len(entries)} entries ({n} structured, {len(entries) - n} "
          f"notes only) -> {out}")
    for msg in problems:
        print("problem:", msg, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "_site"))
    sys.exit(build(Path(ap.parse_args().out)))
