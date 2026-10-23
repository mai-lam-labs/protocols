---
slug: symbiosis
name: Symbiosis
scope: Symbiosis cross-chain swaps on EVM chains (MetaRouterGateway, Portal, Synthesis, BridgeV2, Fabric) relayed by its MPC relayer network through the Symbiosis host chain; contracts read on Ethereum
kind: bridge
class: C
cross_chain: true
chains: unknown                          # 45+ per site; read on Ethereum
source_public: true                      # symbiosis-finance/core-contracts; not cloned, deployed proxies read
inherits: []
updated: 2026-10-04

verification:
  service: spec-only
  exit: spec-only                        # revert flow from docs; contracts not read in source
  actors: spec-only
  admin: source-verified                 # proxies, ProxyAdmin owner and Bridge MPC address read on Ethereum
  data: spec-only
  judgment: spec-only
  incidents: partial

exit:
  custody: in_flight_message             # locked in Portal (or burned as sTokens) until the relayers execute the next leg
  execution: automatic                   # relayers sign with the MPC key and call BridgeV2 on the next chain
  overrides:
    - who: Symbiosis relayer MPC group (BridgeV2 mpc 0xd9c9b4d9...24a8 on Ethereum)
      needs: unknown                     # MPC group size and signing threshold not read; epoch changes need 2/3 of stake
      parties: unknown
      how: decline to relay or revert one operation, or sign a forged one (the 2026-09 syBTC mint came through message validation)
      reach: one
      bounded: false
      cost: stake at risk only if slashed
    - who: ProxyAdmin owner, Safe 0x5112eba9bc2468bb5134cbfbeab9334edae7106a (3 of 5)
      needs: 3 of 5 Safe signers; not identified
      parties: unknown
      how: upgrade Portal, Synthesis or BridgeV2 (no timelock), or replace the MPC address "manually" as the emergencies page describes
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: on_failure             # a stuck operation is reverted through the app, which the relayers then execute; it isn't automatic
  exit_bound_seconds: unknown
  exit_bound_chosen_by: none
  standing_approval: immutable_target    # users approve MetaRouterGateway, which isn't a proxy; it forwards into the upgradeable Portal

actors:
  - role: Relayers; sign with the MPC key and submit each leg
    entity: registered relayer nodes (PoS staking, optionally Symbiotic)
    jurisdiction: unknown
    set: staked
    independence: unknown

admin:
  upgradeable: true                      # Portal, Synthesis, BridgeV2, Fabric are transparent proxies under ProxyAdmin 0x1da522b3...
  authority: multisig                    # ProxyAdmin and the contracts' owner: Safe 3 of 5
  timelock_seconds: none
  immediate_functions:
    - function: ProxyAdmin.upgrade on Portal, Synthesis, BridgeV2
      caller: Safe (3 of 5)
      effect: replaces the contracts holding locked tokens and minting sTokens
    - function: BridgeV2 MPC change by the owner (per the emergencies page)
      caller: Safe (3 of 5)
      effect: replaces the key whose signatures move funds
    - function: pause per route
      caller: unknown
      effect: BTC routes were halted in 2026-09 while others ran
  grandfathered: none
  outside_exit_path: []

data_gates: unknown

judgment:
  screening: unknown
  freeze_assets: [USDC, USDT]            # stablecoins are transit tokens
  freeze_pooled: true                    # Portal holds locked tokens; Octopools hold liquidity

service:
  integrator_access:
    api_key: false                       # api.symbiosis.finance /crosschain/v1/swap answered with no key (2026-10-07)
    identity: unknown
    revocable: unknown
    rate_limited: unknown
  operators:
    - role: Symbiosis API and app (quotes, revert requests)
      entity: Symbiosis
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: Advisor and Broadcaster microservices used by relayers
      entity: Symbiosis                  # the docs say these are centralised today
      single_operator: true
      source_public: unknown
      deployment_config_public: false
  screening: unknown
  bypass: unknown

integration:
  calls: ["quote through the Symbiosis API or js-sdk", "approve MetaRouterGateway and call metaRoute", "if stuck, request a revert through the app or SDK"]
  signatures: ["ERC-20 approval"]
  offchain_required:
    - role: Symbiosis API
      api_key: unknown
      rate_limited: unknown
  finisher: protocol
  gasless_start: none
  monitoring: "Symbiosis explorer / API by transaction hash"
  sdk: "symbiosis-js-sdk (TypeScript)"
  testnet: unknown
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: delivery                    # delivery with swaps along the route
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
  sides: [exact_in]                      # swapExactIn paths; the API takes tokenAmountIn (live 2026-10-07)
  rate: floating_above_bound             # tokenAmountOutMin follows the requested slippage (1% in the live quote)
  quote_validity: unknown
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: approve MetaRouterGateway and call metaRoute
  - action: revert
    performer: designated
    paid: unknown
    note: a stuck operation is reverted on request; whether the relayers are paid for it wasn't read

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: metaRoute
    form: calldata
    bounds: arbitrary
    verifiable_locally: false
    api_optional: false
    target_admin: quorum
    note: "MetaRouter executes the routing calldata the API builds"

incidents:
  - date: "2026-09-11"
    duration: unknown
    user_funds_lost: unknown
    exits_blocked: true
    cause: "syBTC minted without collateral through inaccurate message validation in the Bitcoin bridge; BTC routes halted; about 15 BTC recovered"

open_questions:
  - "Trade: discipline, surplus_to (CRITERIA.md, Trade)"
  - "Quote: quote_validity (CRITERIA.md, Trade); these decide which quote modes (exact, atleast, upto) the venue can serve, and who decides a partial fill"
  - "Paid execution, revert step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - MPC group size and signing threshold, and relayer identities
  - core-contracts source for Portal revert functions and the owner's MPC-change function
  - Who signs the 3-of-5 Safe, and whether other chains use the same one
  - Who can pause a route
---

# Symbiosis

**Primitive (one line):** Cross-chain AMM bridge using MPC relayer network with Threshold Signature Scheme (TSS); Portal contract locks tokens on source chain, Synthesis contract mints synthetic assets on destination; relayers use MPC keys to sign cross-chain messages; Octopools AMM routes liquidity.
**Product scope of this entry:** Symbiosis cross-chain DEX (45+ chains)

## Category 1 — Actor-gated edges

**Actors on exit path:**
- Actor: MPC relayer network
  - Role: signs cross-chain messages using TSS. Required for both fill settlement and refund/revert.
  - Set size: MPC threshold group — no single party can move funds
  - Source: [1]

**User self-refund:** unknown — requires source verification. Standard bridge revert mechanisms likely depend on MPC relayer attestation.

## Category 2 — Modification-gated edges

**Upgrade authority:** unknown — requires source verification.
**Pause mechanism:** confirmed exists — BTC routes were halted during September 2026 exploit while other routes stayed operational. Source: [2]

## Historical incidents

- Date: 2026-09-11, Cause: Bitcoin Bridge exploit — inaccurate message validation allowed malicious minting of synthetic BTC (syBTC) without real collateral. Hacker minted >2^62 raw syBTC but could only convert a small portion to real assets. BTC routes halted; other routes unaffected. ~15 BTC recovered. Source: [2][3]
- **Implication:** the exploit was in the message validation layer (MPC-signed messages not properly validated), which is the same layer that would need to work correctly for refunds. This validates the Category 1 concern about MPC relayer dependency.

## On-chain state, Ethereum (2026-10-04)

Addresses are from `symbiosis-finance/js-sdk` `src/crosschain/config/mainnet.ts`.

- **Proxies:** `Portal` `0xb8f2…81A8`, `Synthesis` `0xD7c3…38B3`, `BridgeV2` `0x5523…227E` and `Fabric` `0xbBFb…9428` are all transparent proxies.
- **ProxyAdmin** `0x1da5…aa75` is owned by Safe `0x5112…106a`, 3 of 5. The same Safe is `owner()` of the contracts themselves. There is no timelock.
- **Gateways:** `MetaRouter` and `MetaRouterGateway` are not proxies.
- **BridgeV2 `mpc()`:** `0xd9c9…24a8`, an address with no code, as expected for a TSS key. The previous MPC was `0x148c…bfe`.
- **Docs on emergencies:** the emergencies page says that if relayers can't sign an MPC change, the fix is to "replace the MPC address with a new one manually". That fits the owner setting the MPC directly.

## Sources

1. https://symbiosis.finance/ — protocol overview, 45+ chains, MPC TSS architecture
2. https://www.kucoin.com/news/flash/symbiosis-recovers-15-btc-after-bitcoin-bridge-exploit — BTC bridge exploit recovery
3. https://en.coin-turk.com/symbiosis-halts-bitcoin-bridge-after-336000-exploit-highlights-cross-chain-risks/ — exploit details
4. https://docs.symbiosis.finance/ — bridge-contracts, synthesizing-process, relayers network architecture and emergencies pages, retrieved 2026-10-04
5. https://github.com/symbiosis-finance/js-sdk `src/crosschain/config/mainnet.ts` (raw), 2026-10-04
6. Proxy slots, `owner()`, Safe thresholds, BridgeV2 `mpc()` / `oldMPC()` on Ethereum, 2026-10-04

## Notes / follow-ups

- The September 2026 exploit is very recent — verify current remediation status
- MPC relayer set composition and threshold should be verified
