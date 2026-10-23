# Router Protocol (CCIF)

**Verification tier:** `spec-only`
**Last updated:** 2026-09-16
**Class:** C
**Primitive (one line):** Cross-chain intent framework; user deposits on source chain; Router chain validators attest cross-chain messages; solvers fill on destination chain; settlement through Router chain validator consensus.
**Product scope of this entry:** Router Protocol CCIF (Cross-Chain Intent Framework)

## Category 1 — Actor-gated edges

**Actors on exit path:**
- Actor: Router chain validator set
  - Role: attest cross-chain messages for both fill settlement and refund/cancel flows
  - Set size: PoS validator set on Router chain
  - Source: [1]

**User self-refund:** unknown — requires source verification of the CCIF contracts.

## Route flags for decision engine

- `class`: C
- `custody_model`: unknown (verify)
- `requires_actor_liveness`: [router_chain_validators]
- `user_can_self_refund`: unknown

## Historical incidents

- Date: 2025-07-02, Cause: Router Protocol asset bridge module exploit — $1.1M+ in unauthorized token transfers. Per Router Protocol incident report. Source: [3]

## Sources

1. https://docs.routerprotocol.com/ — Router Protocol documentation
2. https://github.com/router-protocol — source repos
3. https://routerprotocol.medium.com/incident-report-router-protocol-asset-bridge-exploit-and-response-833f5bb95a31 — July 2025 exploit incident report

## Notes / follow-ups

- Clone source and verify the CCIF escrow/refund mechanism
- Verify Router chain validator set size and composition
- Determine whether user has any self-service refund capability
