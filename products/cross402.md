# Cross402

**Verification tier:** `spec-only`
**Last updated:** 2026-09-16
**Class:** C
**Primitive (one line):** Multi-chain x402 facilitator; extends the x402 payment protocol (Class A for single-chain) to cross-chain by introducing a facilitator that orchestrates settlement across chains; inherits intent-protocol revocability concerns when facilitator manages cross-chain state.
**Product scope of this entry:** Cross402 multi-chain x402 extension

## Inherits from

See [x402-payment.md](x402-payment.md) for the base x402 analysis. The single-chain payment leg is Class A. Cross402 introduces cross-chain orchestration which may elevate to Class C.

## Key difference from base x402

- Base x402: user signs authorization, facilitator settles on same chain. Class A — no deposit, no escrow.
- Cross402: facilitator orchestrates settlement across multiple chains. This introduces state that spans chains, potentially requiring the facilitator to hold or relay funds cross-chain. The facilitator becomes an actor on the exit path.

## Status

Docs emerging; exact architecture not yet public. Source: original INDEX entry notes.

## Route flags for decision engine

- `class`: C (when cross-chain state management introduces facilitator dependency)
- `inherits`: x402-payment (for single-chain payment leg)
- `requires_actor_liveness`: [facilitator] (for cross-chain orchestration)
- `docs_accessible`: limited

## Sources

1. https://x402.org/ — base x402 specification
2. x402 Foundation docs (verify for Cross402 specifics)

## Notes / follow-ups

- Architecture not yet fully public — revisit when docs are available
- The key question is whether the facilitator takes custody or just orchestrates signed authorizations
- If facilitator only relays signed authorizations (no custody), this may stay Class A
