# Osmosis + IBC Hooks

**Verification tier:** `spec-only`
**Last updated:** 2026-09-16
**Class:** B (inherits from IBC)
**Primitive (one line):** IBC transfer + CosmWasm contract call on destination; uses IBC packet timeout for refund; `ibc-hooks` module enables arbitrary contract execution on packet receipt with automatic ack-based unwind on failure.
**Product scope of this entry:** Osmosis IBC Hooks module (IBC middleware)

## Inherits IBC timeout mechanism

IBC Hooks is a Cosmos SDK middleware module that wraps IBC transfers. The underlying IBC packet carries `timeout_height` and `timeout_timestamp`. On timeout, the transfer unwinds automatically via IBC's standard timeout mechanism. See `ibc-eureka.md` for base IBC analysis.

## Additional properties beyond base IBC

- **Ack-based unwind:** if the CosmWasm contract call on the destination chain fails, the IBC acknowledgement signals failure, and the source chain automatically refunds the sender. This is a stronger guarantee than base IBC — failure on the destination side also triggers refund.
- **Permissionless relaying:** IBC relayers are permissionless. Any party can relay packets and timeout proofs.
- **No admin surface on the hooks module itself** — it's Cosmos SDK middleware governed by chain governance (Osmosis governance for parameter changes).

## Route flags for decision engine

- `class`: B (IBC-inherited)
- `custody_model`: ibc_escrow (standard IBC escrow module)
- `requires_actor_liveness`: IBC relayers (permissionless)
- `has_ack_unwind`: yes (failed CosmWasm call triggers refund via ack)
- `governance`: Osmosis chain governance

## Sources

1. https://docs.osmosis.zone/osmosis-core/modules/ibc-hooks/ — IBC Hooks module docs
2. https://github.com/osmosis-labs/osmosis — source repo

## Notes / follow-ups

- Verify whether any chain governance parameters could affect in-flight packets (parameter changes, module disable)
- The ack-based unwind is a significant safety property — verify it cannot be circumvented
