# Union (zk-IBC)

**Verification tier:** `spec-only`
**Last updated:** 2026-09-16
**Class:** B (inherits from IBC)
**Primitive (one line):** Zero-knowledge infrastructure layer extending IBC to non-Cosmos chains (Ethereum, etc.) using ZK proofs of consensus instead of light client state updates; inherits IBC packet timeout for refund.
**Product scope of this entry:** Union zk-IBC bridge

## Inherits IBC timeout mechanism

Union extends IBC to non-Cosmos chains by replacing the traditional IBC light client with ZK-proven consensus proofs. The core IBC packet timeout mechanism (`timeout_height`, `timeout_timestamp`) is preserved — any party can submit a timeout proof after expiry. See `ibc-eureka.md` for base IBC analysis.

## Key differences from base IBC

- **ZK proofs replace light client updates:** instead of submitting block headers and Merkle proofs, Union submits succinct ZK proofs of the counterparty chain's consensus. This changes the trust model from "trust the light client implementation" to "trust the ZK circuit."
- **No trusted third parties:** Union emphasizes operating "without relying on trusted third parties, oracles, multi-signatures, or MPC systems." Source: [1]
- **BLS signature verification:** uses advanced ZK cryptography for BLS signature verification.

## Key unknowns

- Whether the ZK proof generation introduces any liveness dependency (can proofs be generated permissionlessly?)
- Whether the Union contracts on Ethereum have any admin/pause/upgrade surface
- Specific deployed contract addresses
- Whether timeout proof submission is fully permissionless on the non-Cosmos side

## Route flags for decision engine

- `class`: B (IBC-inherited)
- `custody_model`: ibc_escrow
- `requires_actor_liveness`: relayers + ZK proof generators (verify permissionlessness)
- `trust_model`: zk_proven (no trusted third parties, oracles, or MPC)

## Sources

1. https://docs.union.build/ — Union documentation, "hyper-efficient zero-knowledge infrastructure layer" — retrieved 2026-09-16
2. https://github.com/unionlabs/union — source repo

## Notes / follow-ups

- Clone source repo and verify Ethereum-side contract admin surface
- Verify whether ZK proof generation is permissionless or requires specific operator
- Verify timeout mechanism works identically to base IBC on the non-Cosmos side
- IBC Eureka (Solidity IBC on Ethereum) may overlap with Union's Ethereum deployment — clarify relationship
