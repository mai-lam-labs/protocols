# Anoma

**Verification tier:** `spec-only` (blog posts and high-level docs only; EVM Protocol Adapter source not yet read)
**Last updated:** 2026-09-16
**Class:** A (tentative — resource model may involve commitment semantics not yet verified)
**Primitive (one line):** Users express intents via the Anoma Resource Machine (ARM); solvers discover counterparties and execute settlements on-chain through a Protocol Adapter deployed to EVM chains; resource-model-based (neither UTXO nor account model).
**Product scope of this entry:** Anoma Protocol Adapter on Ethereum and EVM chains; AnomaPay as current live application

## Category 1 — Actor-gated edges

**Actors on exit path:** unknown — resource model semantics not yet verified. If intents are purely gossip-based and settlement is atomic (as described in early specs), no actors are required for exit. If the resource model involves on-chain resource commitments, actors may be required.

**Cancellation mechanisms:** unknown — requires source verification of the Protocol Adapter contract at 0x46E622226F93Ed52C584F3f66135CD06AF01c86c.

**Expiry:** unknown.

**Actors involved in filling (not exit):**
- Actor: Solvers
  - Role: discover counterparties and execute settlements matching user intents
  - Set size: unknown
  - Source: [1]

**Uptime / SLA:** unknown.

**Historical incidents:** no incidents identified — protocol is recent (2025 EVM deployment).

**Compellability profile:** unknown.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** unknown — requires reading Protocol Adapter source to determine proxy pattern, admin functions.

**Immediate-effect admin functions:** unknown.

**Grandfathering:** unknown.

## Category 3 — Data-oracle-gated edges

**Oracles in exit path:** unknown.

**Rate limits / circuit breakers / caps:** unknown.

## Category 4 — Judgment-oracle-gated edges

**Risk-scoring service integrations:** unknown. AnomaPay emphasizes "programmable privacy" and "confidential swaps" which may interact with compliance requirements.

**Stablecoin freeze exposure:** unknown — depends on custody model of Protocol Adapter.

**Compliance oracle dependencies:** unknown.

## Composite

**Stuck-leg failure modes:** cannot enumerate without understanding resource model custody semantics.

**Cross-protocol correlation:** unknown.

## Route flags for decision engine

- `class`: A (tentative)
- `custody_model`: unknown (resource model — verify)
- `requires_actor_liveness`: unknown
- `has_immediate_admin_pause`: unknown
- `upgrade_timelock_seconds`: unknown
- `source_public`: yes (GitHub EVM Protocol Adapter repo referenced in blog)

## Sources

1. https://anoma.net/blog/anoma-is-now-live-on-ethereum-mainnet — Ethereum mainnet deployment, PA address 0x46E622226F93Ed52C584F3f66135CD06AF01c86c — retrieved 2026-09-16
2. https://anoma.net/ — project overview, ARM description — retrieved 2026-09-16
3. https://specs.anoma.net/ — Anoma specs (URL structure changed, needs re-navigation) — attempted 2026-09-16
- https://github.com/anoma/anoma — listed in the original protocol index; not yet retrieved

## Notes / follow-ups

- High priority: clone EVM Protocol Adapter repo from GitHub and read the source to determine custody model, admin surface, and whether Class A is correct
- The resource model is fundamentally different from standard EVM order-signing — may need a custom framework extension to properly classify
- AnomaPay is the current live product (private payments, confidential swaps) — general intent settlement may not yet be live
- Original classification as "intents gossiped, resource-model settlement" predates the EVM Protocol Adapter deployment — verify whether the gossip-based intent model applies to the EVM deployment or only to a future Anoma-native chain
- DFlow was originally described as "Cosmos SDK OFA auctions" but may have pivoted — verify
