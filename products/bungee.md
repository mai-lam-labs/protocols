---
slug: bungee
name: Bungee (Socket)
scope: Bungee / Socket aggregation through SocketGateway 0x3a23F943181408EAC424116Af7b7790c94Cb97a5, the shared approval target, and the route contracts it calls; each route's risk is the bridge or DEX it uses
kind: aggregator
class: unknown                           # inherits the chosen route's class
cross_chain: true
chains: unknown                          # read on Ethereum, Arbitrum, Base
source_public: true                      # SocketDotTech; gateway not compared with source here
inherits: []
updated: 2026-10-04

verification:
  service: spec-only
  exit: spec-only
  actors: spec-only
  admin: source-verified                 # owner and route count read on three chains; addRoute, addController, setApprovalForRouters, rescueFunds are onlyOwner in the verified source
  data: spec-only
  judgment: spec-only
  incidents: partial

exit:
  custody: user_wallet                   # the gateway passes funds to the route in the same transaction
  execution: unknown                     # the route's
  overrides:
    - who: SocketGateway owner, EOA 0xb0bbff6311b7f245761a7846d3ce7b1b100c1836, the same on Ethereum, Arbitrum, Base
      needs: one key; no timelock
      parties: key
      how: add a route that pulls from any wallet with a standing approval to the gateway (the January 2024 exploit came through a newly added route)
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: unknown
  exit_bound_seconds: unknown
  exit_bound_chosen_by: none
  standing_approval: upgradeable_target  # not a proxy, but routes are added by the owner, which has the same effect on approvals

actors: unknown

admin:
  upgradeable: true                      # behaviour extends by addRoute; the gateway itself isn't a proxy
  authority: eoa
  timelock_seconds: none
  immediate_functions:
    - function: addRoute, addController
      caller: owner EOA
      effect: new code that the gateway will call with users' approvals
    - function: setApprovalForRouters
      caller: owner EOA
      effect: the gateway approves routes to spend tokens it holds
    - function: rescueFunds / rescueEther
      caller: owner EOA
      effect: moves any tokens held by the gateway
  grandfathered: none
  outside_exit_path: []

data_gates: unknown

judgment:
  screening: unknown
  freeze_assets: []
  freeze_pooled: false

service:
  integrator_access:
    api_key: true                        # api.socket.tech /v2/quote returned 401 without a key (2026-10-07)
    identity: unknown
    revocable: unknown
    rate_limited: unknown
  operators:
    - role: Bungee / Socket API (route building)
      entity: Socket
      single_operator: true
      source_public: false
      deployment_config_public: false
  screening: unknown
  bypass: true

integration:
  calls: ["quote and build through the Bungee API", "approve SocketGateway and send the built transaction", "track by transaction hash"]
  signatures: ["ERC-20 approval to SocketGateway"]
  offchain_required:
    - role: Bungee API
      api_key: unknown
      rate_limited: unknown
  finisher: unknown
  gasless_start: none
  monitoring: "Bungee status API"
  sdk: unknown
  testnet: unknown
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: inherited
  holder: unknown
  strike: unknown
  expiry: unknown
  early_close: unknown
  premium: none
  terms_fixed_by: calldata
  price_set_by: quote
  discipline: unknown
  surplus_to: unknown
  extraction: [public_bound]             # the user sends the built transaction with its slippage bound
  sides: unknown
  rate: unknown
  quote_validity: unknown
  partial_fill: unknown
  partial_remainder: unknown

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: approve SocketGateway and send the built transaction
  - action: exit
    performer: none
    paid: none
    inherited: true
    note: the route's

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: Socket route
    form: calldata
    bounds: arbitrary
    verifiable_locally: false
    api_optional: false
    target_admin: key
    note: "calldata to SocketGateway routes, which one EOA can add"

incidents:
  - date: "2024-01-16"
    duration: unknown
    user_funds_lost: true
    exits_blocked: true
    cause: "$3.3M from 231 wallets with approvals, through a newly added route that didn't validate swapExtraData; contracts paused, about $2.3M recovered"

open_questions:
  - "Trade: holder, strike, expiry, early_close, discipline, surplus_to (CRITERIA.md, Trade)"
  - "Quote: sides, rate, quote_validity, partial_fill, partial_remainder (CRITERIA.md, Trade); these decide which quote modes (exact, atleast, upto) the venue can serve, and who decides a partial fill"
  - Who holds the owner EOA, and whether Socket has moved route administration elsewhere (e.g. a Bungee v2 contract) that this entry misses
  - Whether the owner can pause the gateway
---

# Bungee (Socket)

**Primitive (one line):** Bridge and DEX aggregator; SocketGateway contract routes calls to modular immutable "route" contracts that interact with integrated bridges/DEXs; security model inherited from whichever underlying bridge is selected per route; can chain multi-hop routes (bridge + swap) automatically.
**Product scope of this entry:** Bungee / Socket bridge aggregator

## Custody model

Socket's SocketGateway is a **pass-through** — it routes to underlying bridge/DEX contracts and does not hold pooled liquidity. However, users grant token approvals to the gateway contract, creating an approval-based attack surface. The gateway is a shared approval target across all routes.

## Admin surface

Owner can add new routes and disable existing ones but cannot modify deployed route logic ("once a module is deployed it can only be disabled by the owner, everything is immutable").

## Historical incidents

- **2024-01-16: $3.3M exploit.** A recently added route did not properly validate the `swapExtraData` parameter, enabling an attacker to inject a `transferFrom` call to drain approved assets from 231 wallets (average loss $14K). Targeted wallets with infinite approvals to Socket contracts. Socket paused all contracts, recovered ~$2.3M (1,032 ETH). Source: [1]
- **Implication:** the approval-target pattern means a single malicious or buggy route can drain ALL users who have approved the gateway — not just users of that specific route.

## On-chain state (2026-10-04)

**SocketGateway `0x3a23…97a5`:**
- **Code:** the same 24,305 bytes on Ethereum, Arbitrum and Base. It isn't a proxy.
- **Owner:** `0xb0bbff6311b7f245761a7846d3ce7b1b100c1836`, an EOA, on all three chains.
- **Routes:** `routesCount()` is 447 on Ethereum, 432 on Arbitrum and 428 on Base.

Deployed route logic is immutable, but adding routes is owner-only and immediate. In the verified source on Blockscout, `addRoute`, `addController`, `setApprovalForRouters`, `rescueFunds` and `rescueEther` are all `onlyOwner`, with no delay. One key can therefore add a route that spends every standing approval to the gateway. That is the same path as the January 2024 exploit, which used a buggy route rather than a malicious one.

## Sources

1. Various sources on Socket/Bungee January 2024 exploit ($3.3M, swapExtraData validation)
2. https://docs.socket.tech/ — Socket documentation
- https://github.com/SocketDotTech — listed in the original protocol index; not yet retrieved
