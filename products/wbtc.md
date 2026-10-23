---
slug: wbtc
name: Wrapped Bitcoin (WBTC)
scope: WBTC on Ethereum (token, Controller, Factory, Members) and its custody. Bridged copies are listed under issuance; their bridges are not analysed here
kind: token
cross_chain: false
chains: [Ethereum]
source_public: true
inherits: []
updated: 2026-09-29
depth: basics                             # partial pass; see open_questions

verification:
  exit: partial                           # Factory burn flow read in source; custodian behaviour off-chain
  actors: partial
  admin: source-verified                  # every owner read on Ethereum
  data: spec-only
  judgment: partial
  incidents: partial

backing:
  kind: custodian
  holders:
    - entity: BitGo                       # one key, via its US technology entity
      jurisdiction: [US]
    - entity: BiT Global                  # two keys: one Hong Kong, one Singapore
      jurisdiction: [HK, SG]
  keys: 3                                 # BitGo multisig; BiT Global holds the user and backup keys
  threshold: unknown
  reserve_check: unknown                  # wbtc.network proof-of-reserves dashboard returned 404
  supply: 116132.18                       # WBTC on Ethereum, read on-chain

issuance:
  - chain: Ethereum
    contract: "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"
    native: true
    mint_authority: "Factory 0xe5a5f138005e19a3e6d0fe68b039397eeef2322b, via Controller; on a custodian-confirmed merchant request"
    freeze_authority: none                # no blacklist in the token
  - chain: Arbitrum
    contract: "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f"
    native: false
    bridge: Arbitrum ERC20 gateway        # beacon proxy; beacon owner 0xcf57572261c7c2bcf21ffd220ea7d1a27d40a827
    supply: 7367.56
  - chain: Polygon
    contract: "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6"
    native: false
    bridge: Polygon PoS bridge            # proxy owner 0x355b8e02e7f5301e6fac9b7cac1d6d9c86c0343f (a contract)
    supply: 1915.86
  - chain: Solana
    contract: 3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh
    native: false
    bridge: Wormhole Portal
    supply: unknown

redemption:
  eligible: merchants                     # 48 merchant addresses in Members; ordinary holders sell
  kyc: true                               # merchants are onboarded institutions
  minimum: unknown
  fee: unknown
  bound_seconds: unbounded                # nothing on-chain obliges the custodian to act
  steps: 3                                # merchant burn request; custodian sends BTC; custodian confirms with the txid

exit:
  custody: escrow                         # off-chain, custodian-held BTC
  execution: discretionary                # the custodian decides whether to send BTC for each burn request
  overrides:
    - who: custodian (BitGo / BiT Global)
      needs: one organisation
      how: not sending BTC for a merchant's burn request; rejecting it
      reach: one
      bounded: false
      cost: reputational
  refund_trigger: none
  exit_bound_seconds: unbounded
  standing_approval: none

actors:
  - role: releases BTC for burns
    entity: BitGo and BiT Global
    jurisdiction: [US, HK, SG]
    set: m_of_n
    independence: affiliated              # joint arrangement under one custody product
  - role: merchant, the only party that may redeem
    entity: 48 onboarded merchants
    jurisdiction: unknown
    set: whitelist
    independence: independent

admin:
  upgradeable: false                      # Solidity 0.4.24, no proxy
  authority: multisig
  owners:
    - contract: WBTC token
      owner: "Controller 0xca06411bd7a7296d7dbdd0050dfc846e95febeb7"
    - contract: Controller
      owner: "0x972eed35781f09987a5c40f761f6a24623c570de"
      m: 6
      n: 10
    - contract: Members (merchant and custodian lists)
      owner: "0x4dbbbfb0e68be9d8f5a377a4654604a62e851e80"
      m: 5
      n: 9
    - contract: custodian address
      owner: "0xb0f42d187145911c2ad1755831aded125619bd27 (contract with 3 signers)"
  timelock_seconds: none
  immediate_functions:
    - function: pause
      caller: Controller owner (6 of 10)
      effect: stops all WBTC transfers and burns
    - function: setFactory / setMembers
      caller: Controller owner (6 of 10)
      effect: replaces who can mint and burn, and the merchant and custodian lists
  grandfathered: none
  outside_exit_path: []

data_gates: []                            # none found on-chain; custodian-side limits unknown

judgment:
  screening:
    - kind: merchant KYC
      status: active
  freeze_assets: none                     # WBTC has no blacklist
  freeze_pooled: false

service:
  integrator_access:
    api_key: false
    identity: kyc
    revocable: true
    rate_limited: false
    note: "minting and redeeming need merchant onboarding; Members' owner can remove a merchant"
  operators:
    - role: custodian
      entity: BitGo / BiT Global
      single_operator: true
      source_public: false
  screening:
    - kind: merchant onboarding
      where: Members whitelist
      in_source: true
      enabled_in_production: true
  bypass: false                           # a holder who isn't a merchant can only sell

integration:
  calls: [transfer, approve]
  signatures: [approval]                  # no EIP-2612 permit on Ethereum; Arbitrum copy has permit
  offchain_required: []
  finisher: user
  gasless_start: none
  monitoring: none for holding; redemption needs a merchant
  sdk: none
  testnet: unknown
  steps: 1

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: claim
  holder: user
  strike: par
  expiry: none
  early_close: none
  premium: none
  terms_fixed_by: issuer
  price_set_by: par
  discipline: none
  surplus_to: none
  extraction: []
  sides: none
  rate: none
  quote_validity: none
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: transfer
    performer: user
    paid: none
    gas_on: funds_chain
    note: an ordinary ERC-20 transfer
  - action: redeem
    performer: designated
    paid: unknown
    note: burn request to a merchant; the custodian sends BTC

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: mint / redeem
    form: unknown
    note: "merchant process"

incidents:
  - date: 2024-08-09
    duration: 60 days
    funds_lost: false
    exits_blocked: false
    cause: "custody moved from BitGo alone to BitGo and BiT Global (Justin Sun-linked); completed 2024-10-08"

open_questions:
  - "Paid execution, redeem step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - "What is the custody multisig threshold (2 of 3?), and can BitGo's key alone block a release?"
  - "Where is the current proof of reserves published? wbtc.network/dashboard/audit returned 404"
  - "What are the merchant fees, minimums and turnaround for a burn?"
  - "Who owns the Polygon proxy owner 0x355b… and the Arbitrum beacon owner 0xcf57…, and can they upgrade the copies?"
  - "Who controls the Solana copy's Wormhole wrapped mint?"
  - "Which merchants are active, and in which jurisdictions?"
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: wbtc-contracts
    url: https://github.com/WrappedBTC/bitcoin-token-smart-contracts
    commit: 41dc747a4649b524b583e93f734351a331e766d4
    commit_date: 2023-12-27
---

# WBTC

Research was cut short; this records what was read. Sources: the
`wbtc-contracts` clone (`ethereum/contracts/`), on-chain reads on Ethereum,
Arbitrum and Polygon on 2026-09-29.

## How it works

Minting and redemption are merchant-only. `Factory.sol`:

- **Mint**: a merchant calls `addMintRequest` with the BTC txid of a deposit to
  the custodian's per-merchant address; the custodian calls
  `confirmMintRequest`, which mints through the Controller.
- **Burn**: a merchant calls `burn`, which burns the WBTC and records a request
  to pay BTC to the merchant's registered address; the custodian sends the BTC
  and calls `confirmBurnRequest` with the txid.

Nothing on-chain obliges the custodian to send the BTC. There were 810 mint and
510 burn requests at read time.

`WBTC.sol` is an OpenZeppelin 0.4.24 mintable, burnable, pausable token. Only
the owner (the Controller) can burn, `finishMinting` is disabled, renouncing
ownership reverts. There's no blacklist.

## Who holds what

- Token owner: the Controller.
- Controller owner: a 6-of-10 multisig (old Gnosis `MultiSigWallet`).
- Members owner: a 5-of-9 multisig. Members holds the custodian address and
  48 merchants.
- Custodian: a contract at `0xb0f4…` with three signers.

Since 2024-10-08 the BTC has been held by BitGo with BiT Global: BiT Global
holds two keys (Hong Kong, Singapore), BitGo one (US).

## Bridged copies

Arbitrum (7,367.56) and Polygon (1,915.86) copies are minted by those chains'
canonical bridges, and the Solana copy by Wormhole Portal. A copy's exit is
this entry's plus its bridge's.

## Sources

- https://unchainedcrypto.com/wbtc-completes-shift-to-multi-jurisdiction-custody-model/ (2026-09-29)
- https://www.bitgo.com/resources/blog/bitgo-to-move-wbtc-to-multi-jurisdictional-custody-to-accelerate-global/ (2026-09-29)
- https://governance.aave.com/t/chaos-labs-wbtc-bitgo-custody-update/18607 (2026-09-29)
- https://wbtc.network/dashboard/audit (2026-09-29, 404)
