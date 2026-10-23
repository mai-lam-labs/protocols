---
slug: squid-axelar
name: Squid / Axelar GMP
scope: A Squid Router cross-chain route over Axelar GMP (callContractWithToken); SquidRouter 0xce16F69375520ab01377ce7B88f5BA8C48F8D666 on source and destination, the legacy AxelarGateway and its governance, and the Squid API. Squid Intents (CORAL) isn't covered
kind: bridge
class: C
cross_chain: true
chains: unknown                          # Squid lists 100+ chains; read on Ethereum, Arbitrum, Base
source_public: partial                   # Axelar contracts public; SquidRouter source not reviewed
inherits: []
updated: 2026-10-04

verification:
  service: spec-only
  exit: partial                          # Axelar gateway read in source; SquidRouter's failure handling from docs
  actors: spec-only                      # validator set from docs
  admin: source-verified                 # gateway governance, timelock, mint limiter and SquidRouter owners read on-chain
  data: partial
  judgment: spec-only
  incidents: partial

exit:
  custody: in_flight_message             # tokens locked or burned at the source gateway until validators approve the destination call
  execution: automatic                   # Axelar validators approve; anyone can execute the approved call on the destination
  overrides:
    - who: SquidRouter owner on Base, Safe 0x25de76a4df4fd9fe5be6457213f339c6a542f4f7
      needs: one key (1 of 3)
      parties: key
      how: upgrade SquidRouter (no timelock) to code that keeps a chosen user's arriving tokens, or that pulls from standing approvals
      reach: one
      bounded: false
      cost: none on-chain
    - who: SquidRouter owners on Ethereum (Safe 2 of 4, 0x7178d1a7...) and Arbitrum (Safe 2 of 3, 0x87f8db64...)
      needs: 2 signers of a Squid Safe; signers not published
      parties: unknown
      how: as above
      reach: one
      bounded: false
      cost: none on-chain
    - who: Axelar validators (weighted threshold on AxelarAuthWeighted)
      needs: unknown                     # the weighted threshold for one message wasn't read on-chain
      parties: unknown
      how: withhold approval of one message, or approve a forged one
      reach: one
      bounded: false
      cost: stake at risk only if governance slashes
  refund_trigger: on_failure             # if the destination calls fail, SquidRouter sends tokens to the refund recipient on the destination chain; nothing returns to the source
  exit_bound_seconds: unknown
  exit_bound_chosen_by: none
  standing_approval: upgradeable_target  # users approve SquidRouter, an upgradeable proxy

actors:
  - role: Axelar validators; vote to approve the cross-chain message and co-sign the gateway command
    entity: about 75 PoS validators
    jurisdiction: unknown
    set: staked
    independence: unknown                # by docs; not checked
  - role: Executor; calls execute on the destination once approved
    entity: anyone                       # Axelar's relayer normally does it, paid through the gas service; anyone can
    jurisdiction: pseudonymous
    set: permissionless
    independence: independent

admin:
  upgradeable: true
  authority: multisig                    # SquidRouter owned by a Squid Safe per chain; the gateway by AxelarServiceGovernance
  timelock_seconds: none                 # SquidRouter has none; the gateway's governance has a 259200 s minimum
  immediate_functions:
    - function: SquidRouter.upgrade
      caller: Squid Safe (1 of 3 on Base, 2 of 3 on Arbitrum, 2 of 4 on Ethereum)
      effect: replaces the contract users approve and that receives bridged tokens on the destination
  grandfathered: none
  outside_exit_path:
    - what: AxelarGateway.upgrade, transferGovernance
      effect: replaces the gateway; via AxelarServiceGovernance 0x7acbae6c..., proposals from the Axelar chain's governance module with a 259200 s minimum timelock, or operator proposals once Axelar governance approves them
      caller: Axelar governance
      timelock_seconds: 259200
    - what: setTokenMintLimits
      effect: caps how much of a token the gateway mints per 6-hour epoch
      caller: mint limiter, an Axelar multisig 3 of 6 (0xcc940ae4...)

data_gates:
  - kind: mint limit
    where: AxelarGateway token mint on the destination (tokenMintLimit per 6-hour epoch)
    trigger: the epoch's mint limit for the token is reached
    blocks_exit: true
    reset: bounded                       # resets each 6-hour epoch
  - kind: gas payment
    where: Axelar relayer, before executing
    trigger: gas paid to AxelarGasService doesn't cover execution
    blocks_exit: false                   # anyone can add gas or execute manually

judgment:
  screening: unknown                     # Squid API screening not documented
  freeze_assets: [USDC]                  # native USDC locked at the source gateway for axlUSDC
  freeze_pooled: true

service:
  integrator_access:
    api_key: true                        # x-integrator-id header on every request
    identity: signup                     # issued "on a limited basis and upon review" after a partnership request
    revocable: true
    rate_limited: true                   # 1 RPS testing, 10 RPS production, custom above
  operators:
    - role: Squid API (route building)
      entity: Squid (0xSquid)
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: Axelar relayer and gas service
      entity: Axelar (Interop Labs)
      single_operator: true
      source_public: unknown
      deployment_config_public: false
  screening: unknown
  bypass: true                           # SquidRouter and the gateway are open contract calls; building routes without the API isn't documented

integration:
  calls: ["POST v2.api.squidrouter.com/v2/route with x-integrator-id", "send the returned transaction to SquidRouter", "track on Axelarscan or GET /v2/status"]
  signatures: ["none beyond the transaction; ERC-20 approval to SquidRouter"]
  offchain_required:
    - role: Squid API
      api_key: true
      rate_limited: true
  finisher: protocol                     # Axelar relayer executes; anyone can
  gasless_start: none
  monitoring: "Squid /v2/status or Axelarscan; failure leaves tokens at the refund recipient on the destination"
  sdk: "@0xsquid/sdk (TypeScript)"
  testnet: unknown
  steps: 3

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: delivery                    # delivery with swaps at each end
  holder: none
  strike: signed
  expiry: none
  early_close: none
  premium: none
  terms_fixed_by: calldata
  price_set_by: quote
  discipline: unknown
  surplus_to: unknown
  extraction: [public_bound]
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
    note: "send the built transaction to SquidRouter, prepaying Axelar gas"
  - action: deliver
    performer: anyone
    paid: deferred
    note: "the Axelar relayer executes on the destination, paid in advance at the source"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: Squid route
    form: calldata
    bounds: arbitrary
    verifiable_locally: false
    api_optional: false
    target_admin: key
    note: "multicall through SquidRouter, upgradeable by a 1-of-3 Safe on Base"

incidents:
  - date: "2026-06"
    duration: unknown
    user_funds_lost: true
    exits_blocked: unknown
    cause: "Axelar-Secret IBC bridge infinite-mint bug in ics20-for-axelar, $4.67M; not this route"
  - date: "2026-05"
    duration: unknown
    user_funds_lost: true
    exits_blocked: false
    cause: "SquidRouterModule (a third-party Safe module) exploit, $3.2M from 86 Safes; not Squid's contracts"

open_questions:
  - "Trade: discipline, surplus_to (CRITERIA.md, Trade)"
  - "Quote: sides, rate, quote_validity, partial_fill, partial_remainder (CRITERIA.md, Trade); these decide which quote modes (exact, atleast, upto) the venue can serve, and who decides a partial fill"
  - SquidRouter source and what upgrade() allows; who signs each Squid Safe
  - The AxelarAuthWeighted threshold and weights for the current epoch on each chain
  - Whether the Squid API screens users
  - Where funds go on each failure mode of the destination calls, from SquidRouter source
  - The 2026-03 CrossCurve incident (fabricated messages to a receiver) and whether it involved the gateway's validation
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: axelar-cgp
    url: https://github.com/axelarnetwork/axelar-cgp-solidity
    commit: 43ec407499434448c91da71f031e618d3ed7578a
    commit_date: 2026-08-12
---

# Squid / Axelar GMP

**Primitive (one line):** Squid is a router/aggregator built on Axelar GMP; Axelar uses ~70+ PoS validators with quadratic voting and weighted threshold signatures; Gateway contract on each chain controlled by validator-shared key; Squid Intents (CORAL) adds RFQ/solver layer with TEE execution.
**Product scope of this entry:** Squid Router + Axelar GMP infrastructure

## Category 1 — Actor-gated edges

**Actors on exit path:**
- Actor: Axelar validator set (~70+ validators)
  - Role: reach consensus on cross-chain commands, co-sign threshold signatures for Gateway execution
  - Set size: ~70+ active validators, PoS with quadratic voting (power = sqrt(stake))
  - Source: [3] `AxelarAuthWeighted.sol:30-45`, Axelar security docs

**User self-refund:** **NO.** No on-chain self-refund mechanism. When GMP transactions fail, users must manually trigger re-execution via Axelarscan UI or AxelarJS SDK. "Debug your contract and then making a new call" is the official guidance. Source: [3] Axelar transaction recovery docs

**Squid Intents (CORAL):** "automatic refunds if a transaction fails within a set timeframe" — handled by off-chain Squid system/TEE, not an on-chain self-refund.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** governance address can call `upgrade()` on AxelarGateway — full implementation replacement via delegatecall. Source: [3] `AxelarGateway.sol:391-467`

**Immediate-effect admin functions:**
- `setPauseStatus()` by pauser or governance exists in the source. **But the gateway deployed on Ethereum has no pause:** neither `setPauseStatus` nor `paused` is in the implementation at `0x99b5…4098` (selector search of the bytecode, 2026-10-04). Source: [3] `AxelarGateway.sol:461`
- Mint limiter can set per-token mint limits per 6-hour epoch. Source: [3] `AxelarGateway.sol`
- Governance can transfer governance, transfer mint limiter, bypass pause.

## Historical incidents

- **2026-06**: Axelar-Secret IBC bridge exploit — $4.67M stolen via infinite mint bug in `ics20-for-axelar` contract. Went undetected for 7 days. Source: [4]
- **2026-03**: CrossCurve $3M exploit — attacker crafted fake Axelar messages that passed validation, tricking a Receiver contract into releasing funds. Source: [5]
- **2026-05**: SquidRouterModule $3.2M exploit of 86 Gnosis Safes — third-party module, NOT Squid itself, but affects Squid users. Source: [6]
- **2024-05**: Axelar Chain Maintainer vulnerability — fixed via governance. $50K bounty paid.

## On-chain state (2026-10-04)

- **Gateway:** `AxelarGateway` `0x4F44…56A5` on Ethereum, implementation `0x99b5…4098`, which has no pause function.
  - Governance is `AxelarServiceGovernance` `0x7acb…2525`. Proposals come from the Axelar chain (`axelar10d07y265gmmuvt4z0w9aw880jnsr700j7v9daj`) with `minimumTimeLockDelay` 259,200 s (3 days).
  - Its operator, `0xc8a8…1d56`, is an EOA. It can only execute proposals that Axelar governance has approved.
  - The mint limiter is an Axelar multisig, `0xcc94…ec68`: 3 of 6, epoch 1.
- **SquidRouter `0xce16…D666`:** a proxy with no ProxyAdmin. Its owner can upgrade it directly.
  - Ethereum: owner Safe `0x7178…1d0d`, 2 of 4.
  - Arbitrum: owner Safe `0x87f8…b97c`, 2 of 3.
  - Base: owner Safe `0x25de…f4f7`, **1 of 3**.
- **What this means:** the Axelar gateway is slow to change (a 3-day timelock behind validator governance). The Squid contract that users approve and that receives tokens on the destination can be replaced at once, by one key on Base.

## Compliance / policy-related findings

- Axelar is a PoS network with governance — governance can theoretically block specific cross-chain commands or update Gateway contracts
- No documented cases of Axelar governance blocking individual user transfers for compliance reasons
- Axelar Gateway has rate limiting (per-token mint limits per 6-hour epoch) controlled by the Mint Limiter role — this could throttle large flows

## Sources

1. https://docs.squidrouter.com/ — Squid docs
2. https://docs.axelar.dev/ — Axelar docs
3. Source: `AxelarGateway.sol` (pause 512-549, upgrade 391-467), `AxelarAuthWeighted.sol` (threshold 30-45) — cloned and read 2026-09-16
4. https://forum.scrt.network/t/security-incident-axelar-secret-ibc-bridge-exploit-june-10-2026/7995
5. https://blockeden.xyz/blog/2026/03/16/crosscurve-3m-bridge-exploit-axelar-gateway-fabricated-cross-chain-messages/
6. https://www.halborn.com/blog/post/explained-the-squidroutermodule-hack-may-2026
- https://github.com/axelarnetwork/axelar-cgp-solidity — listed in the original protocol index; not yet retrieved
