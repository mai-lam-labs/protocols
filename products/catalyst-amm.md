# Catalyst AMM

**Verification tier:** `spec-only`
**Last updated:** 2026-09-16
**Class:** C
**Primitive (one line):** Cross-chain AMM; vault-based liquidity with swaps routed over IBC, Wormhole, or Polymer messaging layers; settlement depends on the chosen messaging layer's attestation/timeout mechanism.
**Product scope of this entry:** Catalyst cross-chain AMM

## Category 1 — Actor-gated edges

**Actors on exit path:** depends on messaging layer used:
- IBC: permissionless relayers (see ibc-eureka.md)
- Wormhole: 19 Guardian validators, 13/19 threshold
- Polymer: verify

**User self-refund:** depends on messaging layer — IBC has permissionless timeout proofs; Wormhole and Polymer require attestation.

## Route flags for decision engine

- `class`: C
- `custody_model`: vault_pool (AMM liquidity)
- `requires_actor_liveness`: depends on messaging layer
- `messaging_layer_options`: [ibc, wormhole, polymer]

## Sources

1. https://docs.catalyst.exchange/ — Catalyst documentation (verify URL)
2. https://github.com/catalystsystem/catalyst-amm — source repo (verify)

## Notes / follow-ups

- Clone source and verify vault mechanics, admin surface
- The messaging layer choice makes this protocol's risk profile variable per route
- May be more of a liquidity venue than an intent protocol (similar to Arrakis HOT finding)
