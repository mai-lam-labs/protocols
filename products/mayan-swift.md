---
slug: mayan-swift
name: Mayan Swift
scope: Mayan Swift v2 on EVM chains, SwiftSource 0x40fFE85A28DC9993541449464d7529a922142960 and SwiftDest 0xD78D199f8C402e7B5Cc2abE278dF0412400a3BAe (same addresses on every EVM chain), with auctions on Solana and settlement over Wormhole; the Mayan API and Forwarder in front
kind: bridge
class: C
cross_chain: true
chains: [Solana, Ethereum, BSC, Polygon, Avalanche, Arbitrum, Optimism, Base, Linea, Unichain, HyperEVM, Monad, Sui]   # docs; EVM guardian read on seven
source_public: partial                   # EVM contracts verified on Blockscout; the swift-contracts repo isn't public
inherits: [wormhole-ntt]                 # Wormhole Guardians verify refund and unlock messages
updated: 2026-10-04

verification:
  service: spec-only
  exit: source-verified                  # SwiftSource.refundOrder, rescue, setRefundVerifier and SwiftDest.cancelOrder read from verified source
  actors: partial                        # Guardian set from docs
  admin: source-verified                 # guardian, paused, rescueVault and refundVerifier read on seven chains
  data: partial
  judgment: spec-only
  incidents: partial

exit:
  custody: escrow                        # SwiftSource holds the order's input (often converted to USDC or ETH first)
  execution: automatic                   # after the deadline anyone cancels on the destination (paid a cancel fee); the Wormhole VAA of that cancel is then submitted to refundOrder by anyone
  overrides:
    - who: Mayan, through the SwiftSource guardian EOA 0xb4cdc16e6afcca48b6fade7302b6590c664dca5a plus a rescue message emitted by Mayan's Solana Swift program
      needs: the guardian key and Mayan's Solana program; both Mayan's
      parties: organisation              # two things Mayan controls, not one key alone
      how: rescue(vm) sets any order's status and sends any amount of any token in SwiftSource to rescueVault (0x71b6e467..., a 1-of-1 Safe on Ethereum)
      reach: one
      bounded: false
      cost: none on-chain
    - who: Wormhole Guardians
      needs: 7 of 19 decline to sign the cancel message (quorum 13); 13 of 19 to sign a forged unlock
      parties: quorum
      independent: unknown
      how: withhold the VAA a refund needs, or sign an unlock that pays the driver for an unfilled order
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: timeout_proof          # cancel on the destination after deadline64, proven back to the source by a Wormhole VAA (or a fast-refund VAA through refundVerifier)
  exit_bound_seconds: unknown            # deadline64 plus Guardian signing; fees for the refund are quoted up front
  exit_bound_chosen_by: order creator    # deadline64 in the order; the API sets it
  standing_approval: immutable_target    # approve the Mayan Forwarder or SwiftSource; neither is a proxy

actors:
  - role: Canceler; calls cancelOrder on the destination after the deadline
    entity: anyone
    jurisdiction: pseudonymous
    set: permissionless                  # no caller check; the canceler is paid cancelFee
    independence: independent
  - role: Wormhole Guardians; sign the cancel VAA
    entity: 19 institutional validators
    jurisdiction: unknown
    set: m_of_n
    independence: unknown                # by docs
  - role: Refund submitter; calls refundOrder on the source with the VAA
    entity: anyone
    jurisdiction: pseudonymous
    set: permissionless                  # paid refundFee
    independence: independent

admin:
  upgradeable: false
  authority: eoa                         # guardian 0xb4cdc16e...ca5a on Ethereum, Base, Arbitrum, BSC, Polygon, Avalanche, Optimism
  timelock_seconds: none
  immediate_functions:
    - function: SwiftSource.rescue
      caller: guardian, with a rescue VAA from Mayan's Solana program
      effect: any token and amount in SwiftSource to rescueVault, and any order's status
    - function: SwiftSource.setRefundVerifier
      caller: guardian, with a VAA from Mayan's Solana program
      effect: replaces the fast-refund verifier; a fake verifier can only trigger refunds to the trader
  grandfathered: none
  outside_exit_path:
    - what: setPause
      effect: blocks new orders only; refundOrder and unlocks don't check paused
    - what: setEmitters
      effect: sets a chain's emitter once; existing emitters can't be changed (EmitterAddressExists)
    - what: setFeeManager, changeGuardian / claimGuardian
      effect: fees and the guardian handover

data_gates:
  - kind: deadline
    where: SwiftDest.cancelOrder (block.timestamp <= deadline reverts)
    trigger: before deadline64
    blocks_exit: true
    reset: bounded

judgment:
  screening:
    - kind: Chainalysis and Hermod (zeroShadow) screening; flagged addresses may not be processed
      status: active
  freeze_assets: [USDC]                  # Swift converts inputs to the primary locked asset, typically USDC or ETH
  freeze_pooled: true                    # every open order's input sits in SwiftSource

service:
  integrator_access:
    api_key: false                       # price-api.mayan.finance/v3/quote answered with no key once sdkVersion was set (2026-10-07)
    identity: unknown
    revocable: unknown
    rate_limited: unknown
  operators:
    - role: Mayan API (quotes, deadline, fees) and the Solana auction
      entity: Mayan Finance
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: Drivers; fill on the destination
      entity: unknown
      single_operator: unknown
      source_public: false
      deployment_config_public: false
  screening:
    - kind: Chainalysis, Hermod by zeroShadow
      where: transaction processing
      in_source: false
      enabled_in_production: true
  bypass: unknown                        # whether drivers fill orders created without the API isn't established; refunds need no API

integration:
  calls: ["quote via the Mayan SDK or sia.mayan.finance", "approve the Forwarder and send the built transaction (createOrderWithToken via the Forwarder)", "track with the Explorer API"]
  signatures: ["optional permit; createOrderWithSig for gasless orders"]
  offchain_required:
    - role: Mayan quote API
      api_key: unknown
      rate_limited: unknown
  finisher: anyone                       # drivers settle; anyone can cancel and refund for a fee
  gasless_start: [eip2612, prior_approval]  # createOrderWithSig: anyone submits; it applies an EIP-2612 permit when the allowance is short
  monitoring: "Explorer API clientStatus (COMPLETED / REFUNDED)"
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
  price_set_by: auction                  # drivers bid in an auction on Solana
  discipline: unknown                    # ENGLISH mode: drivers bid output upward on Mayan's Solana auction (docs: 'the best offer wins'); the auction program isn't open source and its bidder set wasn't established. Of 60 recent transactions touching auction program 8QJmxZcEzwuYmCPy6XqgN2sHcYCcFq6AEfBMJZZuLo5a (2026-10-08), 45 were paid by one fee payer and 15 by eight others; bids couldn't be decoded
  surplus_to: user                       # the auction winner's promised amount above the floor goes to the user
  extraction: []
  sides: [exact_in]                      # the input is locked at the source; minAmountOut floors the output
  rate: floating_above_bound             # the user receives fulfillAmount, at least the auction's promisedAmount, at least the signed minAmountOut
  quote_validity: api_chosen             # quotes set deadline64 60 minutes out (live 2026-10-07)
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: anyone
    paid: atomic
    fee: signed
    note: "createOrderWithSig: the trader signs hashTypedData(orderHash, amountIn, submissionFee); the caller is credited submissionFee in Mayan's FeeManager in the same call (feeManager.depositFee(msg.sender, ...)), withdrawn later by the caller"
  - action: cancel
    performer: anyone
    paid: deferred
    note: "SwiftDest.cancelOrder after the deadline, by anyone, who pays the Wormhole message fee and destination gas; the cancelFee is credited to the named canceler only later, on the source chain, when refundOrder runs"
  - action: refund
    performer: anyone
    paid: atomic
    fee: signed
    note: refundOrder with the cancel VAA; the submitter earns refundFee from the order

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: Forwarder call
    form: calldata
    bounds: bounded
    verifiable_locally: true
    api_optional: false
    note: "built by the public swap-sdk"

incidents: []                            # none found (2026-09-16)

open_questions:
  - "Who may bid in the Swift auction (open, or an allowlist of drivers), how long it runs, and whether its program source is public"
  - "Whether an auction winner who doesn't fill is penalised (no bond or penalty was found in the EVM contracts or docs); until deadline - penaltyPeriod only the winner can fill, so an unpenalised winner holds a free option for that window"
  - "swiftAuctionMode 3 is 'Guaranteed Price' (docs): exact-out for same-asset USDC, USDT and ETH transfers; who fills it and how its price is set wasn't read"
  - "Who controls Mayan's FeeManager, where createOrderWithSig credits the submitter's fee, and whether a credit can be withheld"
  - "Trade: holder, discipline (CRITERIA.md, Trade)"
  - "Paid execution, start step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - Who can make Mayan's Solana Swift program emit a rescue or refund-verifier message (its admin or upgrade authority)
  - Who holds the guardian EOA 0xb4cdc16e...ca5a and the rescueVault Safe signer
  - What each chain's refundVerifier contract accepts as a fast refund
  - Whether the docs' claim that "no single party can freeze or move assets" still stands, given rescue()
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

# Mayan Swift

**Primitive (one line):** Intent-based cross-chain swap; user locks input tokens in Swift source contract; drivers (solvers) compete in on-chain auction on Solana; winning driver fronts output tokens to user on destination chain; Wormhole Guardian VAA (13/19) proves fulfillment and releases locked tokens to driver.
**Product scope of this entry:** Mayan Swift v2 (cross-chain swap protocol)

## Gasless start: createOrderWithSig (2026-10-07)

`SwiftSource.createOrderWithSig` (verified source of `0x40fF…2960`) lets anyone
create an order the trader has signed.

- **The allowance:** if it's short, the call executes the trader's EIP-2612
  permit (`execPermit`).
- **What it pulls:** `amountIn`, plus `submissionFee` to Mayan's `FeeManager`,
  which credits it to `msg.sender`.
- **What the trader signs:** `hashTypedData(orderHash, amountIn,
  submissionFee)`, so the submitter can't change the order or the fee.

The refund submitter is credited `refundFee` in the same call. The canceller
is credited `cancelFee` only later, on the source chain, when `refundOrder`
runs, so the cancel step is paid but deferred. The order's `gasDrop` can also
deliver native gas to the recipient on the destination chain. One caveat: the
submitter's fee is a credit in Mayan's FeeManager, withdrawn later, not a
transfer.

## Category 1 — Actor-gated edges

**Actors on exit path (refund after timeout):**
- No specific actor required. Orders have a `deadline64` timestamp. If no driver fills before deadline, order becomes refundable. Docs describe refund as permissionless — "occurs automatically when no driver fills it before its deadline passes." A relayer submits the refund tx but the mechanism is permissionless.
- Source: [1]

**Guardian role:** Wormhole Guardians (13/19) are needed for driver **reimbursement** (proving fulfillment), NOT for user refund. If Guardians go offline: user gets refund after deadline (if unfilled); driver funds are stuck until Guardians return. User is protected. Source: [1]

**Admin surface:** docs state: "The contracts are permissionless and non-custodial. No single party can freeze or move assets held in them." No pause documented. Source: [1]

## Category 2 — Modification-gated edges

**Upgrade authority:** not documented as upgradeable.
**Pause mechanism:** none documented.
**Admin functions:** none documented — contracts described as permissionless.

## Category 3 — Data-oracle-gated edges

**Oracles:** Wormhole Guardians for settlement attestation (driver reimbursement). NOT for user refund.

## Category 4 — Judgment-oracle-gated edges

**Stablecoin freeze:** source contract holds locked tokens. Issuer freeze on contract address would affect escrowed funds.

## Historical incidents

No exploits of Mayan Finance (Swift/MCTP) found. Note: "Maya Protocol" (THORChain fork, August 2026 $1.7M exploit) is a DIFFERENT unrelated project despite similar name.

## Source and on-chain state (2026-10-04)

Source is the verified code on Blockscout for `SwiftSource` (`src/swift/SwiftSource.sol`, solc 0.8.28) and `SwiftDest`. Neither is a proxy.

**Corrections to the sections above:**
- **Refunds depend on Wormhole.** `refundOrder` needs a Wormhole VAA from the destination chain's Swift emitter, produced by `SwiftDest.cancelOrder`. Or, on the fast path, it needs a VAA accepted by `refundVerifier` from `refundEmitter`. Category 1 says the user refund doesn't need Guardians; that is wrong. If Guardians stop signing, unfilled orders can't be refunded either.
- **The guardian can move funds.** The docs say "no single party can freeze or move assets held in them". That isn't accurate for the EVM source contract. `rescue(vm)`, callable only by `guardian` and only with a VAA from Mayan's Solana program (`emitters[1]`), can set any order's status and send any amount of any token to `rescueVault`.

**What holds:**
- `cancelOrder` on the destination is open to anyone after the deadline, and the canceler earns `cancelFee`.
- `refundOrder` is open to anyone, and the submitter earns `refundFee`.
- `setPause` blocks only new orders.
- `setEmitters` can't overwrite an existing emitter.

**On-chain, on Ethereum, Base, Arbitrum, BSC, Polygon, Avalanche and Optimism:**
- `guardian` is `0xb4cdc16e6afcca48b6fade7302b6590c664dca5a` on both contracts. It has no code, so it is an EOA.
- `paused` is false.
- `rescueVault` is `0x71b6e467f549b367487a28ef07520147a90a5f3c`: a 1-of-1 Safe on Ethereum, and no code on the other chains.
- `refundVerifier` is set, at a different contract on each chain.

## Sources

1. https://docs.mayan.finance/ — Mayan Finance docs (Swift architecture, refund, permissionless contracts)
2. https://github.com/mayan-finance/swift-contracts — not public (absent from the org's repo list, 2026-10-04)
3. Verified source from `eth.blockscout.com/api/v2/smart-contracts/` for `0x40fFE85A…2960` (SwiftSource), `0xD78D199f…3BAe` (SwiftDest) and `0x337685fd…C3E2` (MayanForwarder2), retrieved 2026-10-04
4. https://docs.mayan.finance/ — architecture/swift, how-mayan-works/refunds, resources/chains-contracts, resources/compliance, retrieved 2026-10-04
5. `guardian()`, `paused()`, `rescueVault()`, `refundVerifier()` on seven chains through publicnode, 2026-10-04

## Notes / follow-ups

- Verify whether refund returns original input token or converted primary asset (USDC/ETH)
