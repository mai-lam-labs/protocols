"""Scores for each petal, computed from an entry's facts (CRITERIA.md, Scores).

Every fact gets a score from 0 to 1 from the anchor table below, or the score
an entry sets by hand (`score`, with a `score_reason`). A petal's score is its
worst fact's score; `None` means not known and draws grey. Colour is a band of
the score; the rosette draws the score itself as petal length.

Change the methodology here and every entry re-scores on the next build.
"""
import re

# ------------------------------------------------------------------ anchors
# Who, or what, stands between the user and the outcome.
NO_ONE = 1.0           # nothing but the user
ANYONE = 0.8           # someone has to act, but anyone will do; or a known delay
QUORUM_INDEPENDENT = 0.6
QUORUM_UNVERIFIED = 0.4  # several parties, independence not shown
ORGANISATION = 0.2     # one organisation, even through its own multisig
ONE_KEY = 0.0          # one key, or unbounded in normal operation

BANDS = [(0.9, "green"), (0.7, "yellow"), (0.3, "orange"), (0.0, "red")]

# A fact (or a whole petal) that belongs to something the product doesn't
# control: the route an aggregator picks, or the issuer of an asset it holds.
# Shown, never scored, and not counted as missing.
INHERITED = "inherited"


def colour(score):
    if score == INHERITED:
        return INHERITED
    if score is None:
        return "grey"
    for floor, name in BANDS:
        if score >= floor - 1e-9:
            return name
    return "red"


def worst(scores):
    """Lowest known score; None (grey) beats any score that isn't red, as an
    unknown keeps a petal from showing a colour it hasn't earned."""
    scores = [s for s in scores if s != INHERITED]
    if not scores:
        return NO_ONE
    known = [s for s in scores if s is not None]
    lowest = min(known) if known else None
    if any(s is None for s in scores):
        # A known red stands; anything better is held back to grey.
        if lowest is not None and colour(lowest) == "red":
            return lowest
        return None
    return lowest


# ------------------------------------------------------------------ helpers
def is_unknown(v):
    return v is None or (isinstance(v, str) and v.strip().lower() == "unknown")


def as_list(v):
    """A list facet; None when the facet itself is unknown."""
    if isinstance(v, list):
        return v
    if v in ("none", [], None) or v is False:
        return []
    return None


def bound_max(b):
    if isinstance(b, (int, float)) and not isinstance(b, bool):
        return b
    if isinstance(b, list) and len(b) == 2 and all(
            isinstance(x, (int, float)) for x in b):
        return b[1]
    if isinstance(b, str) and b.strip() == "unbounded":
        return float("inf")
    return None


def by_hand(item):
    """An explicit score on a fact, with its reason, or None."""
    if isinstance(item, dict) and isinstance(item.get("score"), (int, float)):
        reason = item.get("score_reason") or "no reason given"
        return float(item["score"]), f"scored by hand: {reason}"
    return None


ONE_KEY_TEXT = re.compile(
    r"\bone key\b|\beoa\b|\b1[- ]of[- ]\d+\b|\bsingle key\b|\bone pauser\b|"
    r"\bany one of\b.*\b(eoa|key)s?\b", re.I)
ONE_ORG_TEXT = re.compile(
    r"\bone (party|organi[sz]ation|holder|operator|entity|company)\b|"
    r"\bsingle\b|\bone organi", re.I)
QUORUM_TEXT = re.compile(
    r"\b([2-9]|\d{2,})\s*(of|/)\s*\d+\b|more than 1/3|\bthreshold\b|\bquorum\b|"
    r"\bmajority\b", re.I)


def parties_score(parties, independent, text=""):
    """Score who it takes, from `parties` / `independent`, else from text.

    Returns (score, note). A quorum earns credit for being many; independence
    that isn't shown loses part of it.
    """
    if parties == "key":
        return ONE_KEY, ""
    if parties == "one":
        # Older entries use `one` for both a single key and a single
        # organisation; the text says which.
        if ONE_KEY_TEXT.search(text):
            return ONE_KEY, "one key"
        return ORGANISATION, "one party"
    if parties == "organisation":
        return ORGANISATION, ""
    if parties in ("quorum", "threshold"):
        if independent is True:
            return QUORUM_INDEPENDENT, ""
        if independent is False:
            return ORGANISATION, "quorum within one organisation"
        return QUORUM_UNVERIFIED, "quorum, independence not shown"
    if parties == "unknown":
        return None, ""
    # Nothing explicit: read the text, and say so.
    if ONE_KEY_TEXT.search(text):
        return ONE_KEY, "read from the text as one key"
    if ONE_ORG_TEXT.search(text):
        return ORGANISATION, "read from the text as one party"
    if QUORUM_TEXT.search(text) and not is_unknown(text):
        return QUORUM_UNVERIFIED, "read from the text as a quorum, independence not shown"
    return None, ""


def fact(score, text, note=""):
    return (score, f"{text} ({note})" if note else text)


AUTHORITY = {"none": NO_ONE, "eoa": ONE_KEY, "multisig": QUORUM_UNVERIFIED,
             "dao": QUORUM_INDEPENDENT, "validators": QUORUM_UNVERIFIED}


# ------------------------------------------------------------------ petals
def rate_exit(h):
    e = h.get("exit") or {}
    facts = []
    ex = e.get("execution")
    facts.append(({"self": NO_ONE, "permissionless": ANYONE,
                   "automatic": ANYONE, "discretionary": ORGANISATION}
                  .get(ex), f"execution: {ex}"))
    b = e.get("exit_bound_seconds")
    m = bound_max(b)
    facts.append((None if m is None else ONE_KEY if m == float("inf")
                   else NO_ONE, f"exit bound: {b}"))
    sa = e.get("standing_approval")
    facts.append(({"none": NO_ONE, "immutable_target": NO_ONE,
                   "upgradeable_target": ANYONE}.get(sa),
                  f"standing approval: {sa}"))
    ovr = as_list(e.get("overrides"))
    if ovr is None:
        facts.append((None, "overrides: unknown"))
    elif not ovr:
        facts.append((NO_ONE, "no known overrides"))
    for o in ovr or []:
        if o.get("reach") == "all":
            continue          # halts that stop everyone are rated under Admin or Data gates
        who, needs = o.get("who", "?"), o.get("needs", "?")
        hand = by_hand(o)
        if hand:
            facts.append(fact(hand[0], f"override by {who} (needs {needs})", hand[1]))
            continue
        s, note = parties_score(o.get("parties"), o.get("independent"), str(needs))
        facts.append(fact(s, f"override by {who} (needs {needs})", note))
    return worst(s for s, _ in facts), facts


def rate_actors(h):
    actors = as_list(h.get("actors"))
    if actors is None:
        return None, [(None, "actors: unknown")]
    if not actors:
        return NO_ONE, [(NO_ONE, "no one else has to act")]
    facts = []
    for a in actors:
        st, ind = a.get("set"), a.get("independence")
        text = f"{a.get('role', '?')}: {st}, {ind}"
        hand = by_hand(a)
        if hand:
            facts.append(fact(hand[0], text, hand[1]))
            continue
        if st == "permissionless":
            s = ANYONE
        elif ind in ("single_org", "affiliated"):
            s = ORGANISATION
        elif st == "single":
            s = ORGANISATION
        elif st in ("staked", "m_of_n", "whitelist"):
            s = {"independent": QUORUM_INDEPENDENT}.get(ind, QUORUM_UNVERIFIED)
        else:
            s = None
        facts.append((s, text))
    return worst(s for s, _ in facts), facts


def rate_admin(h, longest_exit):
    a = h.get("admin") or {}
    facts = []
    authority = AUTHORITY.get(a.get("authority"))
    imm = as_list(a.get("immediate_functions"))
    if imm is None:
        facts.append((None, "immediate functions: unknown"))
    for f in imm or []:
        text = f"immediate: {f.get('function', '?')} by {f.get('caller', '?')}"
        hand = by_hand(f)
        if hand:
            facts.append(fact(hand[0], text, hand[1]))
            continue
        s, note = parties_score(f.get("parties"), f.get("independent"),
                                str(f.get("caller", "")))
        if s is None and authority is not None:
            s, note = authority, f"from authority: {a.get('authority')}"
        facts.append(fact(s, text, note))
    up, tl = a.get("upgradeable"), a.get("timelock_seconds")
    if up is False:
        facts.append((NO_ONE, "not upgradeable"))
    elif up is True:
        if isinstance(tl, (int, float)) and not isinstance(tl, bool):
            if longest_exit is None:
                facts.append((None, f"upgradeable, timelock {tl} s; exit bound unknown"))
            elif tl >= longest_exit:
                facts.append((ANYONE, f"upgradeable behind a {tl} s timelock"))
            else:
                facts.append((authority, f"timelock {tl} s is shorter than the "
                                         f"exit bound {longest_exit} s"))
        elif tl == "none":
            facts.append((authority, f"upgradeable with no timelock "
                                     f"(authority: {a.get('authority')})"))
        else:
            facts.append((None, f"upgradeable, timelock: {tl}"))
    else:
        facts.append((None, f"upgradeable: {up}"))
    return worst(s for s, _ in facts), facts


def rate_data(h):
    gates = as_list(h.get("data_gates"))
    if gates is None:
        return None, [(None, "data gates: unknown")]
    facts = []
    for g in gates:
        be = g.get("blocks_exit")
        if be is False:
            continue
        name = f"{g.get('kind', '?')} at {g.get('where', '?')}"
        hand = by_hand(g)
        if hand:
            facts.append(fact(hand[0], name, hand[1]))
            continue
        if be is not True:
            facts.append((None, f"{name}: blocks exit unknown"))
            continue
        r = g.get("reset")
        if r == "bounded":
            facts.append((ANYONE, f"{name}: reset bounded"))
        elif r == "unbounded":
            # Who has to act, or fail together, to hold it shut.
            s, note = parties_score(g.get("parties"), g.get("independent"))
            facts.append(fact(ONE_KEY if s is None else s,
                              f"{name}: reset unbounded", note))
        else:
            facts.append((None, f"{name}: reset {r}"))
    if not facts:
        return NO_ONE, [(NO_ONE, "no gate blocks the exit")]
    return worst(s for s, _ in facts), facts


def rate_judgment(h):
    j = h.get("judgment") or {}
    facts = []
    scr = as_list(j.get("screening"))
    if scr is None:
        facts.append((None, "screening: unknown"))
    for s in scr or []:
        what = s.get("kind") or s.get("what") or "?"
        if s.get("on_exit") is False:
            continue
        hand = by_hand(s)
        if hand:
            facts.append(fact(hand[0], f"screening: {what}", hand[1]))
            continue
        st = s.get("status")
        if st == "active":
            facts.append((ORGANISATION, f"active screening: {what}"))
        elif st == "proposed":
            facts.append((NO_ONE, f"proposed (not rated): {what}"))
        else:
            facts.append((None, f"screening status {st}: {what}"))
    # Issuer freezes of assets held in a shared contract are the asset's risk,
    # which no operator can avoid; shown so the user can weigh them, not scored.
    pooled, assets = j.get("freeze_pooled"), as_list(j.get("freeze_assets"))
    if pooled is True:
        if assets:
            facts.append((INHERITED, "asset risk: freezable assets pooled at a "
                                     "shared address: " + ", ".join(map(str, assets))))
        elif assets is None:
            facts.append((INHERITED, "asset risk: pooled; which assets are freezable "
                                     "isn't recorded"))
    if not [f for f in facts if f[0] != INHERITED]:
        facts.append((NO_ONE, "no active screening by the protocol or its operators"))
    return worst(s for s, _ in facts), facts


def action_score(a):
    """Paid execution for one action: is whoever performs it paid for it,
    atomically, from the assets in it?"""
    name = a.get("action") or "action"
    performer, paid = a.get("performer"), a.get("paid")
    text = f"{name}: performed by {performer}, paid {paid}"
    hand = by_hand(a)
    if hand:
        return fact(hand[0], text, hand[1])
    if a.get("inherited") is True:
        return (INHERITED, f"{name}: inherited from the route chosen")
    if performer == "none":
        return (NO_ONE, f"{name}: no action needed")
    if paid == "atomic":
        if performer == "anyone" and a.get("fee") == "signed":
            return (NO_ONE, f"{text}, anyone may perform it, fee pinned by the user's signature")
        return (ANYONE, f"{text}" + ("" if a.get("fee") == "signed"
                                     else ", fee not pinned by the user's signature"))
    if paid == "deferred":
        return (QUORUM_UNVERIFIED, f"{text}: compensated, but not in the same transaction")
    if paid == "none":
        if performer == "designated":
            return (ORGANISATION, f"{name}: only a designated party may perform it, "
                                  f"and nothing pays them for it")
        where = a.get("gas_on")
        if where == "other_chain":
            return (ONE_KEY, f"{name}: no one is paid; the user needs gas or fees "
                             f"on a chain where their funds aren't")
        if where == "funds_chain":
            return (ORGANISATION, f"{name}: no one is paid; the user needs native gas")
        return (None, f"{name}: no one is paid; where the user needs gas: {where}")
    return (None, f"{text}")


def rate_cash(h):
    """Paid execution: every action the flow needs, from start to exit."""
    actions = as_list(h.get("actions"))
    if actions is None:
        return None, [(None, "actions not recorded")]
    if not actions:
        return None, [(None, "no actions listed")]
    facts = [action_score(a) for a in actions]
    return worst(s for s, _ in facts), facts


def instruction_score(i, admin_authority):
    """How far the user must trust what the API hands them to sign or send."""
    form, bounds = i.get("form"), i.get("bounds")
    path = i.get("path") or "instructions"
    hand = by_hand(i)
    if hand:
        return fact(hand[0], f"{path}: {form}", hand[1])
    if i.get("api_optional") is True or form == "self_built":
        return (NO_ONE, f"{path}: can be built without the API")
    if form == "typed_data":
        if i.get("verifiable_locally") is False:
            return (QUORUM_UNVERIFIED, f"{path}: user signs hashes of terms the API doesn't show")
        return (NO_ONE, f"{path}: user signs readable typed data the contract enforces")
    if form == "calldata":
        if bounds == "arbitrary":
            admin = i.get("target_admin")
            if admin == "key" or (admin is None and admin_authority == "eoa"):
                return (ONE_KEY, f"{path}: arbitrary API calldata through a contract one key can change")
            return (ORGANISATION, f"{path}: API calldata can make arbitrary calls with the user's approval")
        if bounds in ("bounded", "exact"):
            v = i.get("verifiable_locally")
            if v is True:
                return (ANYONE, f"{path}: API calldata, bounded by the contract and checkable locally")
            if v is False:
                return (QUORUM_UNVERIFIED, f"{path}: API calldata, bounded by the contract but not checkable locally")
            return (None, f"{path}: API calldata, bounded; local checking unknown")
        return (None, f"{path}: API calldata, bounds unknown")
    return (None, f"{path}: instruction form unknown")


def rate_censorship(h, tri):
    """Can the operator decline to serve the user, or mislead them with what it
    hands them to sign."""
    svc = h.get("service")
    if not isinstance(svc, dict):
        return None, [(None, "service not recorded")]
    facts = []
    instructions = h.get("instructions")
    if isinstance(instructions, list):
        auth = (h.get("admin") or {}).get("authority")
        facts.extend(instruction_score(i, auth) for i in instructions)
    elif svc.get("operators"):
        facts.append((None, "instructions not recorded"))
    bypass = svc.get("bypass")
    operators = svc.get("operators")
    no_operator = isinstance(operators, list) and not operators
    if bypass is True:
        facts.append((NO_ONE, "orders can be filled without the operator"))
    elif no_operator and bypass is not False:
        facts.append((NO_ONE, "no off-chain operator in the path"))
    elif bypass is False:
        facts.append((ANYONE, "orders go through the operator; no bypass"))
    else:
        facts.append((None, "bypass: " + ("not recorded" if bypass is None else str(bypass))))
    escape = bypass is True or (no_operator and bypass is not False)

    def gate(score_without_escape):
        return ANYONE if escape else score_without_escape

    ia = svc.get("integrator_access")
    ia = ia if isinstance(ia, dict) else {}
    key, ident, rev = ia.get("api_key"), ia.get("identity"), ia.get("revocable")
    if key is False:
        facts.append((NO_ONE, "no API key needed"))
    elif key == "optional":
        facts.append((ANYONE, "API key optional (works without one, at lower limits)"))
    elif key is True:
        if rev is False:
            facts.append((ANYONE, "API key required, not revocable"))
        else:
            facts.append((gate(ORGANISATION), f"API key required (revocable: {tri(rev)})"))
    else:
        facts.append((None, f"API key: {tri(key)}"))
    if ident == "kyc":
        facts.append((gate(ONE_KEY), "KYC account required"))
    elif is_unknown(ident) and key is not False:
        facts.append((None, "identity required: unknown"))

    scr = as_list(svc.get("screening"))
    if scr is None and not no_operator:
        facts.append((None, "service screening: unknown"))
    for s in scr or []:
        what = s.get("kind") or s.get("what") or "?"
        hand = by_hand(s)
        if hand:
            facts.append(fact(hand[0], f"screening: {what}", hand[1]))
            continue
        on = s.get("enabled_in_production")
        if on is True:
            facts.append((gate(ORGANISATION), f"active screening: {what}"))
        elif on is not False:
            facts.append((None, f"screening, enabled unknown: {what}"))
    return worst(s for s, _ in facts), facts
