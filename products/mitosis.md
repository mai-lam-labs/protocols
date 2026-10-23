# Mitosis

**Verification tier:** `spec-only`
**Last updated:** 2026-09-16
**Class:** C
**Primitive (one line):** Cosmos-SDK L1 blockchain functioning as cross-chain liquidity protocol; users deposit into Mitosis Vaults on supported chains, Hyperlane relays deposit info, Mitosis Chain mints 1:1 derivative tokens (miAssets); users burn miAssets to withdraw original assets + yield. Uses dPoS ISM for Hyperlane security.
**Product scope of this entry:** Mitosis cross-chain liquidity protocol

## Category 1 — Actor-gated edges

**Actors on exit path (withdrawal):**
- Mitosis Chain validators (CometBFT consensus)
- Hyperlane validators (dPoS ISM)
- Hyperlane relayers

**User self-refund:** no in-flight refund mechanism. Users can redeem miAssets for underlying assets (standard deposit/withdrawal), but cannot self-refund a failed cross-chain deposit.

## Category 2 — Modification-gated edges

**Governance:** community governance for vault creation (forum discussion → miAsset holder vote).
**ISM configurable:** Mitosis team controls ISM configuration; plan to leverage Ethereum restaking and mesh security in future.

## Historical incidents

No known exploits.

## Route flags for decision engine

- `class`: C
- `custody_model`: vault_deposit (miAsset derivative model)
- `requires_actor_liveness`: [mitosis_validators, hyperlane_validators_dpos_ism, relayers]
- `user_can_self_refund`: no (burn-to-redeem model only, no in-flight refund)

## Sources

1. https://docs.mitosis.org/ — Mitosis documentation
2. https://github.com/mitosis-org — source repos
3. https://medium.com/mitosisorg/mitosis-hyperlane-scalable-cross-chain-liquidity-5ac22543d66c — Hyperlane integration details
