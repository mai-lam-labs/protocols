# DFlow

**Verification tier:** `spec-only` (limited public documentation; docs.dflow.net unreachable)
**Last updated:** 2026-09-16
**Class:** A (tentative — original classification; requires verification)
**Primitive (one line):** Order flow auction platform on Solana; market makers bid for the right to fill retail order flow with guaranteed price improvement.
**Product scope of this entry:** DFlow OFA on Solana

## Category 1 — Actor-gated edges

**Actors on exit path:** unknown — documentation not accessible (docs.dflow.net DNS does not resolve as of 2026-09-16).

**Cancellation mechanisms:** unknown.

**Expiry:** unknown.

**Uptime / SLA:** unknown.

**Historical incidents:** unknown.

**Compellability profile:** unknown.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** unknown.

**Immediate-effect admin functions:** unknown.

## Category 3 — Data-oracle-gated edges

**Oracles in exit path:** unknown.

## Category 4 — Judgment-oracle-gated edges

**Risk-scoring service integrations:** unknown.

**Stablecoin freeze exposure:** unknown.

## Composite

**Stuck-leg failure modes:** cannot enumerate without documentation.

## Route flags for decision engine

- `class`: A (tentative — verify)
- `custody_model`: unknown
- `chain`: Solana (not Cosmos SDK as originally listed in the original protocol index)
- `source_public`: unknown (GitHub org https://github.com/dflow-protocol may contain source)
- `docs_accessible`: no (docs.dflow.net unreachable as of 2026-09-16)

## Sources

1. https://www.dflow.net/ — landing page, "Intelligent Trade Execution on Solana" — retrieved 2026-09-16
2. https://docs.dflow.net/ — documentation site — DNS did not resolve 2026-09-16

## Notes / follow-ups

- Original the original protocol index listed DFlow as "Cosmos SDK OFA auctions" — this appears incorrect; the live product is on Solana
- docs.dflow.net is unreachable — project may have pivoted, been deprecated, or docs relocated
- Verify GitHub at https://github.com/dflow-protocol for any public source
- Consider whether DFlow should remain in the audit scope given documentation inaccessibility — may warrant removal or deferral
- Update the original protocol index description to reflect Solana, not Cosmos SDK
