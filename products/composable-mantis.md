# Composable MANTIS / CVM

**Verification tier:** `spec-only` (docs.composablefoundation.com unreachable; analysis based on prior knowledge)
**Last updated:** 2026-09-16
**Class:** B (inherits from IBC)
**Primitive (one line):** Cross-chain intent settlement built on IBC and CVM (Composable Virtual Machine); inherits IBC packet timeout for refund; solvers route intent execution across IBC-connected chains.
**Product scope of this entry:** Composable MANTIS intent settlement layer

## Inherits IBC timeout mechanism

This protocol builds on IBC. The refund mechanism is IBC's packet timeout — every IBC packet carries `timeout_height` and `timeout_timestamp`, and any party can submit a timeout proof after expiry to unwind the packet. See `ibc-eureka.md` for the base IBC analysis.

## Current status

docs.composablefoundation.com DNS does not resolve as of 2026-09-16. Project status is unclear — may have rebranded, pivoted, or been deprecated. The Composable Finance ecosystem has undergone multiple rebrandings.

## Key unknowns

- Whether MANTIS/CVM adds any additional escrow or custody layer on top of base IBC
- Whether the CVM execution model introduces additional actor dependencies beyond IBC relayers
- Whether any admin/governance controls exist on the MANTIS layer
- Current deployment status and active chains

## Route flags for decision engine

- `class`: B (IBC-inherited)
- `custody_model`: inherits IBC
- `requires_actor_liveness`: IBC relayers (permissionless)
- `docs_accessible`: no (DNS failure 2026-09-16)

## Sources

1. https://docs.composablefoundation.com/ — DNS did not resolve 2026-09-16
2. https://github.com/ComposableFi/composable — source repo (verify current state)

## Notes / follow-ups

- Verify project status — may be deprecated or rebranded
- If active, clone source and verify whether CVM adds custody layers beyond IBC
- Consider removing from scope if project is no longer active
