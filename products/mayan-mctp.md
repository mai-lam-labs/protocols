---
slug: mayan-mctp
name: Mayan MCTP
scope: Mayan MCTP (MayanCircle 0x875d6d37EC55c8cF220B9E5080717549d8Aa8EcA on EVM) over Circle CCTP with Wormhole messages for order data; Fast MCTP (0xC1062b7C...) is the CCTP v2 variant and wasn't read
kind: bridge
class: C
cross_chain: true
chains: [Solana, Ethereum, BSC, Polygon, Avalanche, Arbitrum, Optimism, Base, Unichain, Sui]   # docs
source_public: partial                   # verified on Blockscout; no public repo
inherits: [cctp-v2-standard, wormhole-ntt]
updated: 2026-10-04

verification:
  service: spec-only
  exit: source-verified                  # MayanCircle refund, redeemWithFee, fulfillOrder, rescueToken read from verified source
  actors: partial
  admin: source-verified                 # guardian and paused read on Ethereum, Arbitrum, Base
  data: partial
  judgment: spec-only
  incidents: partial

exit:
  custody: in_flight_message             # USDC burned through CCTP; minted on the destination only inside MayanCircle's own calls (destination caller pinned)
  execution: automatic                   # a driver fulfills; after the deadline anyone calls refund with the CCTP attestation and the Wormhole VAA
  overrides:
    - who: Circle (CCTP attesters)
      needs: one organisation; see cctp-v2-standard
      parties: organisation
      how: withhold the attestation for one burn
      reach: one
      bounded: false
      cost: none on-chain
    - who: Wormhole Guardians
      needs: 7 of 19 decline to sign the order message (quorum 13)
      parties: quorum
      independent: unknown
      how: withhold the VAA that refund and fulfillOrder both require
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: timeout_proof          # after order.deadline, refund pays the minted USDC to the user's destination address, not back on the source
  exit_bound_seconds: unknown            # CCTP finality plus Guardian signing plus the deadline
  exit_bound_chosen_by: order creator
  standing_approval: immutable_target    # MayanCircle and the Forwarder aren't proxies

actors:
  - role: Circle attestation service
    entity: Circle
    jurisdiction: United States
    set: single
    independence: single_org
  - role: Wormhole Guardians
    entity: 19 institutional validators
    jurisdiction: unknown
    set: m_of_n
    independence: unknown                # same Guardian set as wormhole-ntt; not verified
  - role: Refund submitter
    entity: anyone
    jurisdiction: pseudonymous
    set: permissionless                  # paid redeemFee
    independence: independent

admin:
  upgradeable: false
  authority: eoa                         # guardian 0x933e3922...1ea8 on Ethereum, Arbitrum, Base
  timelock_seconds: none
  immediate_functions:
    - function: rescueToken / rescueEth
      caller: guardian EOA
      effect: any balance held by MayanCircle; user USDC normally isn't held there, since it is minted and paid out in the same call
  grandfathered: none
  outside_exit_path:
    - what: setPause
      effect: blocks new bridge and order calls; refund and fulfillOrder don't check it
    - what: setFeeManager, setConsistencyLevel; setDomainCallers, setMintRecipient and setEmitter are each set once (AlreadySet)
      effect: fees and Wormhole consistency for new orders; routing entries can't be changed once set, and the mint recipient is fixed in the burn

data_gates:
  - kind: CCTP source finality
    where: Circle before attesting
    trigger: source block not final
    blocks_exit: true
    reset: bounded

judgment:
  screening:
    - kind: Chainalysis and Hermod (zeroShadow) screening by Mayan
      status: active
  freeze_assets: [USDC]
  freeze_pooled: false                   # USDC is burned in flight and minted straight to the recipient

service:
  integrator_access:
    api_key: false                       # price-api.mayan.finance/v3/quote answered with no key once sdkVersion was set (2026-10-07)
    identity: unknown
    revocable: unknown
    rate_limited: unknown
  operators:
    - role: Mayan API and Solana auction
      entity: Mayan Finance
      single_operator: true
      source_public: false
      deployment_config_public: false
  screening:
    - kind: Chainalysis, Hermod by zeroShadow
      where: transaction processing
      in_source: false
      enabled_in_production: true
  bypass: unknown

integration:
  calls: ["quote via the Mayan SDK", "approve the Forwarder and send createOrder / bridgeWithFee", "driver fulfills, or after the deadline anyone calls refund"]
  signatures: ["optional permit"]
  offchain_required:
    - role: Mayan quote API
      api_key: unknown
      rate_limited: unknown
  finisher: anyone
  gasless_start: none
  monitoring: "Mayan Explorer API clientStatus"
  sdk: "@mayanfinance/swap-sdk (TypeScript)"
  testnet: partial                       # Swift V1 (single contract, unverified) at 0x66c928b540fCd3456597C5e2B9968ef9353E0F66 on Sepolia and Base Sepolia, testnet Forwarder 0x076baB2Bf1aa0a06F47BD32245527f6D84d62Fd1, and @testnet-mayan/swap-sdk 1.2.0; last contract activity 2025-04-08, testnet price, explorer and relayer APIs return 503; nothing for Swift V2 (2026-10-07)
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: unknown
  strike: signed
  expiry: api_chosen
  early_close: none
  premium: none
  terms_fixed_by: signature
  price_set_by: auction
  discipline: unknown
  surplus_to: user                       # the auction winner's promised amount above the floor goes to the user
  extraction: []
  sides: [exact_in]                      # amountIn is locked; minAmountOut floors the output
  rate: floating_above_bound             # the user receives amountOut, at least the auction's promisedAmount, at least minAmountOut
  quote_validity: api_chosen             # quotes set deadline64 60 minutes out (live 2026-10-07)
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: approve the Forwarder and send createOrder
  - action: refund
    performer: anyone
    paid: unknown
    note: refund with the CCTP attestation and Wormhole VAA; whether the caller is paid wasn't read

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: Forwarder call
    form: calldata
    bounds: bounded
    verifiable_locally: true
    api_optional: false
    note: "built by the public swap-sdk"

incidents: []

open_questions:
  - "Trade: holder, discipline (CRITERIA.md, Trade)"
  - "Paid execution, refund step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - Fast MCTP (0xC1062b7C...) source and admin
  - Who holds the guardian EOA 0x933e3922...1ea8
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: mayan-swap-sdk
    url: https://github.com/mayan-finance/swap-sdk
    commit: c4c98031aaad9264d17630d7b4de0cb18688cf78
    commit_date: 2026-09-10
  - repo: npm-mayan-swap-sdk-15.2.2      # the published @mayanfinance/swap-sdk package (dist), read for order hashing, typed data and API hosts
    url: https://registry.npmjs.org/@mayanfinance/swap-sdk/-/swap-sdk-15.2.2.tgz
    commit: "15.2.2"
    commit_date: unknown
  - repo: npm-testnet-mayan-swap-sdk-1.2.0  # @testnet-mayan/swap-sdk, last published 2025-04-09
    url: https://registry.npmjs.org/@testnet-mayan/swap-sdk/-/swap-sdk-1.2.0.tgz
    commit: "1.2.0"
    commit_date: 2025-04-09
  - repo: mayan-wormhole-sdk-route       # Wormhole SDK route; maps testnet chains to @testnet-mayan/swap-sdk
    url: https://github.com/mayan-finance/wormhole-sdk-route
    commit: 7828f6494cb9ae62be9e9ae69dca36bafb9f1857
    commit_date: 2025-08-01
  - repo: mayan-protocol-test            # OldSwift test against the Sepolia Swift V1 contract
    url: https://github.com/mayan-finance/protocol-test
    commit: 2a2576546ec1571ab7e0ebf19991a1f47bdf334d
    commit_date: 2025-04-17
  - repo: mayan-docs
    url: https://github.com/mayan-finance/docs
    commit: f872b37df28f3c3154c2e8e7f05d513abfa6ae7d
    commit_date: 2026-10-06
---

# Mayan MCTP

**Primitive (one line):** Combines Circle CCTP burn-and-mint with Wormhole messaging; input tokens swapped to USDC and burned via CCTP on source chain; **dual attestation required** (Circle Iris + Wormhole Guardian VAA) for destination chain to mint USDC; drivers compete on Solana for best conversion rate.
**Product scope of this entry:** Mayan MCTP (CCTP + Wormhole hybrid, including Fast MCTP variant)

## Category 1 — Actor-gated edges

**Actors on exit path (refund after timeout):**
- Same permissionless deadline-based refund as Swift. If no driver fills before deadline, order becomes refundable. Source: [1]

**Dual dependency for fill completion:**
- Actor: Circle Iris attestation service — attests to USDC burn event
- Actor: Wormhole Guardians (13/19) — attests to transfer metadata
- **Both must be operational.** Failure of either blocks destination mint. Source: [1]

**If either system offline:** USDC burned on source, cannot be minted on destination. Refund mechanism may also be blocked depending on implementation (verify).

## Category 2 — Modification-gated edges

**Admin surface:** same as Swift — "contracts are permissionless and non-custodial." Source: [1]
**But inherits dependencies' admin surfaces:**
- Circle can freeze/blacklist USDC addresses
- Wormhole Guardians control attestation

## Category 4 — Judgment-oracle-gated edges

**Dual judgment-oracle dependency:** both Circle (compliance decisions) and Wormhole Guardians (attestation decisions) are judgment-oracle-gated edges. Either can independently block a transfer.

**Stablecoin freeze:** MCTP routes exclusively through USDC. Maximum exposure to Circle freeze capabilities.

## Source and on-chain state (2026-10-04)

Source is the verified `MayanCircle` on Blockscout (solc 0.8.4). It is not a proxy.

**Refund (`MayanCircle.sol:650`):**
- After `order.deadline`, anyone can call `refund` with the CCTP message and attestation and the Wormhole VAA over the order hash.
- The contract mints through CCTP and pays the USDC, less `redeemFee`, to the order's `destAddr` **on the destination chain**. The user gets USDC there, not their input back on the source chain.
- This answers the follow-up below: the refund path also needs both attestations.

**Admin:**
- `guardian` is `0x933e3922e04d47a466e60a20e486b372b64f1ea8`, an EOA, the same on Ethereum, Arbitrum and Base. It can `rescueToken` and `rescueEth` any balance with no delay.
- `setPause` blocks only new orders.
- `paused` is false.

## Sources

1. https://docs.mayan.finance/ — Mayan Finance docs (MCTP architecture, dual attestation)
2. https://github.com/mayan-finance/mctp-contracts — not public (absent from the org, 2026-10-04)
3. Verified `MayanCircle` source from `eth.blockscout.com`, and `guardian()` / `paused()` on three chains, 2026-10-04
4. https://docs.mayan.finance/architecture/mctp.md, retrieved 2026-10-04

## Notes / follow-ups

- Dual dependency is the defining risk — strictly worse than either CCTP or Swift alone for liveness
- Verify whether refund path also requires dual attestation or can work with timeout only
- "MCTP ensures that users can still transfer assets even if both Mayan Swift and the Liquidity Layer are temporarily unavailable" — this is a redundancy claim, but MCTP itself has its own dependencies
