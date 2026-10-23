---
slug: hyperlane-warp
name: Hyperlane Warp Routes
framework: true                          # a framework: each route deployer picks its ISM, owner and upgradeability
scope: The Warp Route standard (HypERC20Collateral, HypERC20, HypNative, xERC20 variants) on Hyperlane as each deployer configures it; the ISM, owner and upgradeability are per route and none is read here. Skip Go Fast's Hyperlane configuration is in skip-go-fast
kind: bridge
class: C
cross_chain: true
chains: unknown                          # per route
source_public: true
inherits: []
updated: 2026-10-04

verification:
  service: spec-only
  exit: spec-only
  actors: spec-only
  admin: spec-only
  data: spec-only
  judgment: spec-only
  incidents: partial

exit:
  custody: in_flight_message             # locked in the collateral router or burned until the destination router mints or releases
  execution: automatic                   # validators sign checkpoints; anyone can relay through Mailbox.process
  overrides:
    - who: the route's ISM signers
      needs: unknown                     # per route; a multisig ISM's threshold, or whatever ISM the owner set
      parties: unknown
      how: withhold signatures for one message, or sign a forged one
      reach: one
      bounded: false
      cost: none on-chain
    - who: the route's owner
      needs: unknown                     # per route
      parties: unknown
      how: change the ISM, hook or remote routers, or upgrade the router if it is a proxy
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: none
  exit_bound_seconds: unknown
  exit_bound_chosen_by: none
  standing_approval: unknown             # approve the collateral router; whether it's upgradeable depends on the route

actors:
  - role: ISM validators; sign the origin checkpoint
    entity: unknown                      # per route
    jurisdiction: unknown
    set: unknown
    independence: unknown
  - role: Relayer; calls Mailbox.process on the destination
    entity: anyone
    jurisdiction: pseudonymous
    set: permissionless                  # Mailbox.process has no caller check (see skip-go-fast)
    independence: independent

admin:
  upgradeable: unknown
  authority: unknown
  timelock_seconds: unknown
  immediate_functions: unknown           # setInterchainSecurityModule, setHook, enrollRemoteRouter; upgrade if proxied; xERC20 setLimits
  grandfathered: none
  outside_exit_path: []

data_gates: unknown                      # xERC20 routes have mint and burn limits set by the token owner

judgment:
  screening: unknown
  freeze_assets: unknown
  freeze_pooled: unknown

service:
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: false
  operators: []
  screening: unknown
  bypass: true

integration:
  calls: ["quoteGasPayment", "transferRemote on the origin router", "relayer delivers; track by message id"]
  signatures: ["ERC-20 approval to a collateral router"]
  offchain_required: []
  finisher: anyone
  gasless_start: none
  monitoring: "Hyperlane Explorer by message id, or Dispatch / Process events"
  sdk: "@hyperlane-xyz/sdk (TypeScript)"
  testnet: true
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: delivery
  holder: none
  strike: par
  expiry: none
  early_close: none
  premium: none
  terms_fixed_by: contract
  price_set_by: par
  discipline: none
  surplus_to: none
  extraction: []
  sides: [exact_in]
  rate: par                              # same asset across chains, less any fee
  quote_validity: none
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: "transferRemote, paying the interchain gas payment in native gas"
  - action: deliver
    performer: anyone
    paid: deferred
    note: "the relayer delivers, paid in advance by the sender's interchain gas payment"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: transferRemote
    form: self_built

incidents: []

open_questions:
  - ISM, owner and upgradeability of the specific Warp Routes that routes use
---

# Hyperlane Warp Routes

**Primitive (one line):** Modular cross-chain token bridge using Hyperlane messaging; tokens locked in collateral contract on origin, minted as synthetic on destination; security model fully configurable via Interchain Security Modules (ISMs) — deployer chooses validator set, threshold, and verification logic per route.
**Product scope of this entry:** Hyperlane Warp Routes (token bridge, not intent protocol)

## Category 1 — Actor-gated edges

**Actors on exit path:**
- Hyperlane validators (per ISM configuration) — verify cross-chain messages
- Hyperlane relayers — deliver messages to destination Mailbox
- **No timeout or refund mechanism.** Once tokens are locked and message dispatched, there is no built-in mechanism to reverse or timeout. If message delivery fails or ISM rejects it, locked tokens remain locked with no automatic release.

**User self-refund:** **NO.** No timeout, no refund, no rollback at the protocol level.

## Category 2 — Modification-gated edges

**Critical deployer trust:** deployer controls ISM selection and upgradeability. Per Hyperlane docs: "the deployer of a Warp Route could keep their security model upgradeable, and later on upgrade the security model to a simple multisig and rug." Users must verify trust assumptions per-route.

**Rate limiting:** for xERC20 routes, owner manages minting/burning limits via `setLimits()`.

## Historical incidents

No known exploits of Hyperlane protocol or Warp Routes.

## Sources

1. https://docs.hyperlane.xyz/docs/protocol/warp-routes/warp-routes-overview — Warp Routes overview, ISM configuration
2. https://github.com/hyperlane-xyz/hyperlane-monorepo — source repo

## Notes / follow-ups

- The lack of timeout/refund is a significant gap — locked tokens with no refund path if delivery fails
- Per-route ISM variability means the routing engine must evaluate ISM configuration for each specific Warp Route, not just "Hyperlane" generically
- More of a bridge than an intent protocol — included because it's used as infrastructure by intent protocols (Skip Go Fast, Mitosis, OIF)
