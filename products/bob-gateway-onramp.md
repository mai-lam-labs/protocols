---
slug: bob-gateway-onramp
name: BOB Gateway (BTC to X)
scope: BOB Gateway swaps from native BTC to tokens on EVM chains; the user sends BTC to a deposit address in the solver's wallet, and the solver releases USDT through GatewayOnrampV8 (onward swaps and bridges via Velora, Bungee or LayerZero OFT). X to BTC is in bob-gateway-offramp
kind: swap
class: D
cross_chain: true
chains: [Bitcoin, Ethereum, Base, Arbitrum, BSC, Avalanche, Unichain, Robinhood, HyperEVM]   # destinations from /v4/get-routes (336 routes), 2026-10-06
source_public: partial                   # GatewayOnrampV8 verified on Blockscout; solver and API not public
inherits: []
updated: 2026-10-06

verification:
  service: partial                       # API probed live; docs
  exit: partial                          # custody and refunds are off-chain in the solver's wallet; GatewayOnrampV8 read from verified source
  actors: partial
  admin: source-verified                 # GatewayOnrampV8 owners read on Ethereum
  data: spec-only
  judgment: partial                      # screening refusal observed at order creation
  incidents: not-reviewed

exit:
  custody: pooled                        # the user's BTC goes to "a unique Bitcoin deposit address belonging to the solver's wallet"; how that wallet is keyed isn't published
  execution: discretionary               # release and refund are both sent by the solver; nothing on-chain lets the user recover BTC
  overrides:
    - who: the Gateway solver (BOB), which controls the deposit wallet and is the only caller of GatewayOnrampV8 (owner EOA 0x1bf42bbf...4859 or 0xa9329196...60db)
      needs: one party
      parties: key
      how: neither release nor refund one deposit; the docs say refunds whose address or order owner is flagged by screening are "held for manual handling"
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: on_failure             # retries for up to an hour, then the solver commits a Bitcoin refund on-chain and pays it from its wallet
  exit_bound_seconds: unbounded          # no contract bounds it; the docs describe about an hour of retries plus a Bitcoin confirmation in normal operation
  exit_bound_chosen_by: none
  standing_approval: none                # the user sends BTC; nothing is approved on EVM

actors:
  - role: Solver; holds the deposited BTC and sends the release or the refund
    entity: BOB
    jurisdiction: unknown
    set: single
    independence: single_org

admin:
  upgradeable: false                     # GatewayOnrampV8 is not a proxy
  authority: eoa                         # every GatewayOnrampV8 function is onlyOwner; owners are EOAs 0x1bf42bbf... (3 deployments) and 0xa9329196... (3)
  timelock_seconds: none
  immediate_functions:
    - function: solver infrastructure circuit breaker (off-chain)
      caller: BOB
      effect: shuts the solver down, which stops releases and refunds alike
  grandfathered: none
  outside_exit_path:
    - what: GatewayOnrampV8 releaseFundsAndCallStrategy, refundOrder, commitBitcoinRefund, payFees, rescueTokens, setProtocolFeeDetails
      effect: bookkeeping and payout from the solver's own USDT; the contract never holds user BTC
      caller: owner EOA

data_gates:
  - kind: rate limits and circuit breaker
    where: solver infrastructure
    trigger: volume limits per account or globally, or anomaly detection
    blocks_exit: true                    # the same solver sends refunds
    reset: unknown

judgment:
  screening:
    - kind: TRM Labs screening (3 hops) of BTC sender UTXOs and refund addresses; flagged refunds held for manual handling
      status: active
    - kind: geo-IP blocking (33 countries including US and UK)
      status: active
  freeze_assets: []
  freeze_pooled: false                   # BTC isn't freezable; the solver's own USDT is the payout source

service:
  integrator_access:
    api_key: optional                    # "Do I need an API key? No — the API is self-serve"; keyless works at lower rate limits; get-routes, get-quote and create-order answered without one (2026-10-06)
    identity: none                       # a key, if wanted, is requested by email
    revocable: unknown
    rate_limited: true
  operators:
    - role: Gateway API (quotes signed by the API, order creation, register-tx broadcast, screening)
      entity: BOB (bob-collective)
      single_operator: true
      source_public: false               # the SDK client is public; the API server isn't
      deployment_config_public: false
    - role: Solver; holds BTC in its own wallet and USDT in its own EOA, releases, pays out and refunds
      entity: BOB                        # the docs describe one solver; its EOA 0x1bf42bbf... also owns the contracts
      single_operator: true
      source_public: false
      deployment_config_public: false
  screening:
    - kind: TRM Labs address screening, up to 3 hops, on BTC senders, USDT recipients, Bitcoin payout addresses and affiliates
      where: order creation and before release or payout
      in_source: false
      enabled_in_production: true        # create-order refused a well-known Bitcoin address with NON_COMPLIANT_ADDRESSES (2026-10-06)
    - kind: geo-IP blocking of 33 countries including the United States and the United Kingdom, plus Crimea, Donetsk and Luhansk
      where: Gateway API and app
      in_source: false
      enabled_in_production: true
    - kind: volume-based rate limits per account and globally; circuit breaker that shuts the solver down on anomalies
      where: solver infrastructure
      in_source: false
      enabled_in_production: true
  bypass: false                          # only the Gateway solver fills; there is no other filler and no user path on-chain

integration:
  calls: ["GET /v4/get-quote with refundAddress (BTC)", "POST /v4/create-order: returns a deposit address (and a PSBT if sender is given)", "sign the BTC transaction and PATCH /v4/register-tx with the raw hex; Gateway screens and broadcasts it", "GET /v4/get-order/{id}"]
  signatures: ["one Bitcoin transaction (PSBT)"]
  offchain_required:
    - role: Gateway API and solver
      api_key: optional
      rate_limited: true
  finisher: protocol
  gasless_start: [fee_from_asset]        # the user spends only BTC; destination gas is withheld from the fill
  monitoring: "GET /v4/get-order/{id} status, or the Gateway Explorer order page"
  sdk: "@gobob/bob-sdk (TypeScript); Gateway CLI"
  testnet: unknown                       # a staging API exists (gateway-api-staging.gobob.xyz)
  steps: 3

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: operator
  strike: off_chain
  expiry: none
  early_close: none
  premium: none
  terms_fixed_by: api                    # the quote behind the deposit address
  price_set_by: quote
  discipline: single_holder
  surplus_to: operator
  extraction: [operator_quote]
  sides: [exact_in]                      # get-quote fixes the BTC input (live 2026-10-07)
  rate: floating_above_bound             # the quote carries 100 bps slippage; nothing on-chain enforces the output
  quote_validity: 60                     # get-quote returns a quote signed by the API, valid for one minute
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: anyone
    paid: atomic
    fee: signed
    note: the user's Bitcoin transaction to the deposit address; the miner's fee comes out of the BTC itself
  - action: refund
    performer: designated
    paid: deferred
    note: the solver sends the Bitcoin refund from its own wallet; nothing pays it in that transaction

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: BTC deposit
    form: calldata
    bounds: arbitrary
    verifiable_locally: false
    api_optional: false
    target_admin: organisation
    note: "the API names a deposit address in the solver's wallet; nothing lets the user check where it leads"

incidents: []                            # not reviewed

open_questions:
  - How the solver's Bitcoin wallet is keyed (single key, multisig, MPC) and who holds it
  - Who controls owner EOAs 0x1bf42bbf...4859 and 0xa93291964...60db, and why there are six live-looking V8 deployments
  - What "manual handling" of a screened refund means in practice, and how long it takes
  - Incident history
sources:
  - repo: bob
    url: https://github.com/bob-collective/bob
    commit: 82fb406a1b8c62a88f1db121b2889655a5b8a59b
    commit_date: 2026-10-01
    note: "SDK (gateway API client), gateway-docs and the Bitcoin relay; the V7/V8 Gateway contracts aren't in it and were read as verified source on Blockscout"
---

# BOB Gateway (BTC to X)

**Primitive (one line):** The user sends BTC to a deposit address in the Gateway solver's own wallet. After confirmations and screening, the solver pays USDT from its own EOA through `GatewayOnrampV8.releaseFundsAndCallStrategy`, optionally swapped or bridged onwards, or refunds BTC from its wallet.

## How it works (docs, 2026-10-06)

The Deep Dive says it directly: "This direction is not SPV-verified: the user's BTC lands in the solver's own wallet, and the solver then releases USDT. What protects the user is the signed quote and the automatic refund path — not an on-chain proof." The light client secures only the other direction.

- **Quote and order.** `get-quote` returns a quote signed by the API and valid for one minute. `create-order` returns an `orderId` and "a unique Bitcoin deposit address belonging to the solver's wallet". A live order on 2026-10-06 returned the Taproot address `bc1p87u7…kjxh`.
- **Payment.** The user signs one Bitcoin transaction. The integrator submits the raw hex to `/v4/register-tx`, and Gateway screens it and broadcasts it.
- **Release.** After confirmations, the solver calls `releaseFundsAndCallStrategy` on `GatewayOnrampV8`, which pulls USDT from the solver's EOA with `safeTransferFrom`.
- **Refund.** If release can't land, the solver retries for up to an hour. It then calls `commitBitcoinRefund`, which only records the state, and pays the refund in BTC from its wallet, less the miner fee.
- **Held refunds.** These are "held for manual handling rather than paid out": deposits too small to refund, refunds below dust, and refund addresses or order owners flagged by screening.

## Marketing versus mechanism

The overview says "No custody at any point", "neither your app nor BOB ever holds user funds" and "Users retain custody throughout". For this direction that isn't so. The deposit address belongs to the solver's wallet, the solver is BOB's, and the only way back is the solver choosing to refund. The Deep Dive and Refunds pages describe it accurately; the overview doesn't.

## Contracts (Ethereum, verified source on Blockscout)

- **`GatewayOnrampV8`:** six deployments found by name, all for USDT. `0x0d3e…AEEC`, `0xb1D7…E707` and `0xD2D0…cF73` are owned by `0x1bf42bbf47411d47a6e3368e3b938c09968e4859`, an EOA with nonce 3,779. `0x6201…99C5`, `0xAf7a…5382` and `0x1087…1861` are owned by `0xa93291964dabfda25b5797c0aeb989bbb67960db`, also an EOA.
- **Every state-changing function is `onlyOwner`.** That covers release, `refundOrder` (which pays USDT straight from the caller to the order owner), `commitBitcoinRefund` (a state flag), `payFees`, `rescueTokens` and `setProtocolFeeDetails`. The contract never holds the user's BTC, so its code limits bookkeeping only.

## Screening and access

- **Screening.** TRM Labs screens up to 3 hops on every inbound and outbound flow. On 2026-10-06, `create-order` refused a well-known Bitcoin address with `NON_COMPLIANT_ADDRESSES` and accepted a fresh random one.
- **Geo-IP blocking.** 33 countries are refused, including the United States and the United Kingdom, plus Crimea, Donetsk and Luhansk (FAQ).
- **API key.** Optional: routes, quotes and orders all worked without one.

## Sources

1. https://docs.gobob.xyz/gateway/overview, /gateway/technical, /gateway/refunds, /gateway/faq, /gateway/onboarding, /gateway/fees — retrieved 2026-10-06
2. https://github.com/bob-collective/bob — SDK client (`sdk/src/gateway/client.ts`, generated V4 API), gateway-docs source
3. Verified `GatewayOnrampV8` source, from `eth.blockscout.com/api/v2/smart-contracts/0x0d3ead99…`, and a Blockscout name search for the other deployments, 2026-10-06
4. `owner()` and `token()` on all six V8 deployments, through publicnode, 2026-10-06
5. Live API: `gateway-api-mainnet.gobob.xyz/v4/get-routes`, `/v4/get-quote`, `/v4/create-order` (BTC → USDT on Ethereum; no BTC sent), 2026-10-06
