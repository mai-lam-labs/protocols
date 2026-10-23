# Khalani

**Verification tier:** `spec-only` (docs site down — DNS not found)
**Last updated:** 2026-09-16
**Class:** verify (likely B or C — constraint model implies escrow)
**Primitive (one line):** Decentralized solver infrastructure for intent-driven coordination; Validity VM (VVM) provides executable specifications for collaborative intent solving with deterministic settlement assurances; Intent Compatibility Layer normalizes intents from different protocols; Universal Settlement Layer enables atomic multi-domain settlements.
**Product scope of this entry:** Khalani solver network

## Custody model

Users define constraints (e.g., "swap 1 ETH for at least 4000 USDC within 10 seconds") and if constraints aren't met, "funds never move." This implies a **constraint-checked escrow model** — funds are committed but only released if the constraint is satisfied. Detailed deposit/escrow mechanics not documented publicly.

## Status

Mainnet beta ("Arcadia") launched February 2025. Epoch Protocol integrated as solver network. $2.5M seed round (August 2024). docs.khalani.network is currently down (DNS not found).

## Route flags for decision engine

- `class`: verify (constraint model — likely B or C)
- `custody_model`: constraint_checked_escrow (implied)
- `docs_accessible`: no (DNS failure 2026-09-16)
- `stage`: early (mainnet beta)

## Sources

1. https://docs.khalani.network/ — documentation (DNS not found 2026-09-16)
2. https://github.com/khalani-network — source repos (verify)

## Notes / follow-ups

- Docs site down — cannot verify custody model, admin surface, or refund mechanism
- The constraint model ("funds never move" if constraints not met) is interesting — may be a stronger revocability property than standard escrow if enforced on-chain
- Revisit when documentation is accessible
