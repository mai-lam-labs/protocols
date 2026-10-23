---
slug: btcb
name: Binance-Peg BTC (BTCB)
scope: BTCB on BNB Smart Chain, Binance's collateral for it, and the other Binance-Peg BTC contracts
kind: token
cross_chain: false
chains: [BNB Smart Chain, Ethereum, opBNB]
source_public: true                       # verified BEP20Token template
inherits: []
updated: 2026-09-29
depth: basics

verification:
  exit: spec-only                         # redemption is a Binance account operation
  actors: spec-only
  admin: source-verified
  data: partial                           # Binance's published withdrawal parameters
  judgment: partial
  incidents: partial

backing:
  kind: custodian
  holders:
    - entity: "Binance: Nest Clearing and Custody Limited (ADGM) under the 2026 terms"
      jurisdiction: [AE]
  reserve_check: "published collateral address 3LYJfcfHPXYJreMsASk2jkn69LWEYKzexb (68,200 BTC), and Binance's lockinfo endpoint (collateral ratio 1.0003)"

issuance:
  - chain: BNB Smart Chain
    contract: "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c"
    native: true
    mint_authority: "owner 0xf68a4b64162906eff0ff6ae34e2bb1cd42fef62d (EOA)"
    freeze_authority: none
    supply: 65300.97
  - chain: Ethereum
    contract: "0x9be89d2a4cd102d8fecc6bf9da793be995c22541"
    native: true                          # BinancePeggyToken behind an AdminUpgradeabilityProxy
    mint_authority: "owner 0xd183f2bbf8b28d9fec8367cb06fe72b88778c86b (EOA); proxy admin 0x6a0b3611214d5001fa5efae91b7222a316c12b52 (EOA)"
    freeze_authority: unknown
    supply: 2900
  - chain: opBNB
    contract: "0x7c6b91D9Be155A6Db01f749217d76fF02A7227F2"
    native: false
    bridge: opBNB standard bridge         # L1 ProxyAdmin owned by a 5-of-8 Safe
    supply: 0.56

redemption:
  eligible: Binance account holders       # deposit BTCB, withdraw BTC
  kyc: true                               # Binance requires identity verification to deposit and withdraw
  minimum: 0.0001                         # BTC withdrawal minimum
  fee: 0.00002                            # BTC withdrawal fee
  bound_seconds: unbounded
  steps: 2

exit:
  custody: escrow
  execution: discretionary
  overrides:
    - who: Binance
      needs: one organisation
      how: refusing or freezing an account's withdrawal
      reach: one
      bounded: false
      cost: reputational
  refund_trigger: none
  exit_bound_seconds: unbounded
  standing_approval: none

actors:
  - role: custodian; releases BTC
    entity: Binance
    jurisdiction: [AE]
    set: single
    independence: single_org

admin:
  upgradeable: false                      # BSC contract; the Ethereum contract is upgradeable
  authority: eoa
  timelock_seconds: none
  immediate_functions:
    - function: mint
      caller: owner EOA
      effect: mints BTCB to the owner, with no on-chain check against collateral
    - function: transferOwnership
      caller: owner EOA
      effect: hands the mint power on
  grandfathered: none
  outside_exit_path: []

data_gates:
  - kind: withdrawal limits
    where: Binance account
    trigger: per-withdrawal maximum (1,286 BTC) and Binance's own suspensions
    blocks_exit: true
    reset: unbounded

judgment:
  screening:
    - kind: account KYC and prohibited jurisdictions (US, UK, EEA and others on Binance.com)
      status: active
  freeze_assets: none                     # the BSC token has no blacklist or pause
  freeze_pooled: false

service:
  integrator_access:
    api_key: false
    identity: kyc
    revocable: true
    rate_limited: false
    note: "minting and redeeming need a Binance account"
  operators:
    - role: issuer and custodian
      entity: Binance
      single_operator: true
      source_public: false
  bypass: false

integration:
  calls: [transfer, approve]
  signatures: [approval]                  # no permit
  offchain_required: []
  finisher: user
  gasless_start: none
  monitoring: none for holding
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
    note: redemption through Binance

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: mint / redeem
    form: calldata
    bounds: arbitrary
    verifiable_locally: false
    api_optional: false
    target_admin: organisation
    note: "Binance account deposit addresses"

incidents:
  - date: 2023-01-24
    duration: unknown
    funds_lost: false
    exits_blocked: false
    cause: "Binance disclosed B-Token collateral held in a wallet with customer funds (Binance 8); whether BTCB was affected is not stated"
  - date: 2023-09-07
    duration: until 2024-01-02
    funds_lost: false
    exits_blocked: true
    cause: "precedent: Binance-Peg BUSD withdrawals stopped, then balances converted to FDUSD. Shows how a pegged token is retired"

open_questions:
  - "Paid execution, redeem step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - "Does the Ethereum BinancePeggyToken have a blacklist or pause?"
  - "Total issued across chains against total collateral: the cross-check wasn't finished"
  - "Which Binance entity legally owns the collateral?"
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: opbnb-bridge-tokens
    url: https://github.com/bnb-chain/opbnb-bridge-tokens
    commit: 21699c666d8a337b54d8e181b4fb6088f4172f9d
    commit_date: 2024-04-03
---

# BTCB

Research was cut short; this records what was read. On-chain reads on BNB
Smart Chain, Ethereum and opBNB on 2026-09-29; Binance's public coin
configuration and `tokencanal/lockinfo` endpoints; `mempool.space` for the
collateral address.

## Contract

BTCB on BSC is Binance's `BEP20Token` template (Solidity 0.5.16, not a
proxy). The owner, an EOA, can mint to itself; holders can burn their own.
There's no pause and no blacklist. Supply was 65,300.97 BTCB.

The Ethereum contract is a `BinancePeggyToken` behind an upgradeable proxy,
with an EOA owner and an EOA proxy admin. It held 2,900.

## Collateral

Binance publishes `3LYJfcfHPXYJreMsASk2jkn69LWEYKzexb` as the reserve; it held
68,200 BTC, unmoved since 2022-11-18. Binance's lockinfo endpoint reports a
collateral ratio of 1.0003 for its pegged BTC.

## Redemption

Only through a Binance account: deposit BTCB (BEP20), withdraw BTC. Binance's
configuration when read: BTC withdrawal fee 0.00002, minimum 0.0001, maximum
1,286; BTCB deposits credited after one confirmation.

## Sources

- https://www.bnbchain.org/en/blog/btcb-on-binance-smart-chain-101 (2026-09-29)
- https://www.binance.com/en/blog/all/introducing-bitcoinpegged-token-on-bnb-chain-347360878904684544 (2026-09-29)
- https://www.binance.com/en/collateral-btokens (2026-09-29)
- https://cointelegraph.com/news/binance-holds-token-collateral-and-user-funds-on-same-wallet-by-mistake (2026-09-29)
- https://www.binance.com/en/blog/ecosystem/how-we-back-binancepeg-busd-and-explaining-historical-discrepancies-7761334533351669941 (2026-09-29)
- https://www.binance.com/en/support/announcement/notice-regarding-the-removal-of-busd-and-conversion-of-busd-to-fdusd-1c98ce7bb464422dbbaeda7066ae445b (2026-09-29)
- https://www.binance.com/en/legal/licenses (2026-09-29)
- https://docs.bnbchain.org/bnb-opbnb/core-concepts/opbnb-protocol-addresses/ (2026-09-29)
- https://github.com/DefiLlama/DefiLlama-Adapters/pull/20885 (2026-09-29)
