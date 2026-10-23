---
slug: cbbtc
name: Coinbase Wrapped BTC (cbBTC)
scope: cbBTC on Ethereum, Base and Arbitrum (one address), and Solana. Coinbase custody and its account-based mint and redemption
kind: token
cross_chain: false
chains: [Ethereum, Base, Arbitrum, Solana]
source_public: true                       # Circle's FiatToken, verified at the deployed address
inherits: []
updated: 2026-09-29
depth: basics

verification:
  exit: spec-only                         # redemption is a Coinbase account operation
  actors: spec-only
  admin: partial                          # roles read on three EVM chains; Solana not read
  data: partial
  judgment: source-verified               # blacklist in source, and in use
  incidents: not-reviewed

backing:
  kind: custodian
  holders:
    - entity: Coinbase
      jurisdiction: unknown
  reserve_check: unknown

issuance:
  - chain: Ethereum
    contract: "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf"
    native: true
    mint_authority: "MintForwarder 0x000000000CBDC84a73055389D392710263Bb31e7; caller 0x598DA72e5F690776248C8250A3f7D18AE5416a26 (EOA), 3,500 cbBTC per 24 h"
    freeze_authority: "blacklister 0x5130bF38bF5342aa06CC79b8Cc198cCE832b01Af"
  - chain: Base
    contract: "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf"
    native: true
    mint_authority: "same MintForwarder; caller 0x224b3e71ae18bea534ba3a5c3bdb72e2e4a9c13f (EOA), 1,800 cbBTC per 24 h"
    freeze_authority: blacklister
  - chain: Arbitrum
    contract: "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf"
    native: true
    mint_authority: "same MintForwarder; caller 0x387E43A41D75fAa718E36f5725095cABe4DD651f (EOA), 450 cbBTC per 24 h"
    freeze_authority: blacklister
  - chain: Solana
    contract: cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij
    native: true
    mint_authority: unknown
    freeze_authority: unknown

redemption:
  eligible: Coinbase account holders      # deposit cbBTC to Coinbase, withdraw BTC
  kyc: true
  minimum: unknown
  fee: unknown
  bound_seconds: unbounded
  steps: 2                                # deposit to Coinbase; withdraw BTC

exit:
  custody: escrow
  execution: discretionary
  overrides:
    - who: Coinbase
      needs: one organisation
      how: refusing or freezing an account's withdrawal; blacklisting the holder's address
      reach: one
      bounded: false
      cost: reputational
  refund_trigger: none
  exit_bound_seconds: unbounded
  standing_approval: none

actors:
  - role: custodian; releases BTC
    entity: Coinbase
    jurisdiction: unknown
    set: single
    independence: single_org

admin:
  upgradeable: true                       # FiatTokenProxy → FiatTokenV2_1
  authority: eoa
  roles:                                  # same on Ethereum, Base, Arbitrum
    proxy_admin: "0x5e8114643966b7fd7d5cfdd8695ffc5c51ff32c0"
    implementation: "0x7458bfdc30034eb860b265e6068121d18fa5aa72"
    owner: "0x16360cb10ae1168981cda9d0773f2723c5be27db (EOA)"
    master_minter: "MintForwarder 0x000000000CBDC84a73055389D392710263Bb31e7"
    blacklister: "0x5130bF38bF5342aa06CC79b8Cc198cCE832b01Af (set 2025-09-04)"
    pauser: unknown
  timelock_seconds: none
  immediate_functions:
    - function: upgradeTo
      caller: proxy admin
      effect: replaces the token's code
    - function: pause
      caller: pauser
      effect: stops all transfers
    - function: blacklist
      caller: blacklister
      effect: freezes one address's balance; it can neither send nor receive
  grandfathered: none
  outside_exit_path: []

data_gates:
  - kind: mint rate limit
    where: MintForwarder
    trigger: per-caller allowance, refilled every 86400 s
    blocks_exit: false
    reset: bounded

judgment:
  screening:
    - kind: account KYC
      status: active
  freeze_assets: [cbBTC]                  # token-level blacklist; used, e.g. nine addresses on 2026-09-10
  freeze_pooled: false

service:
  integrator_access:
    api_key: false
    identity: kyc
    revocable: true
    rate_limited: false
    note: "minting and redeeming need a Coinbase account"
  operators:
    - role: issuer and custodian
      entity: Coinbase
      single_operator: true
      source_public: false
  bypass: false

integration:
  calls: [transfer, approve]
  signatures: [EIP-2612 permit, EIP-3009 transferWithAuthorization]
  offchain_required: []
  finisher: user
  gasless_start: [eip3009]               # EIP-3009 lets a relayer pay gas
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
    note: "an ordinary transfer; EIP-3009 lets someone else submit it, but the token pays them nothing"
  - action: redeem
    performer: designated
    paid: unknown
    note: redemption through Coinbase

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: mint / redeem
    form: calldata
    bounds: arbitrary
    verifiable_locally: false
    api_optional: false
    target_admin: organisation
    note: "Coinbase account deposit addresses"

incidents: []

open_questions:
  - "Paid execution, redeem step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - "Is the proxy admin 0x5e81… an EOA or a multisig?"
  - "Who is the pauser now?"
  - "What are Solana's mint and freeze authorities, and does the mint use token-2022 extensions?"
  - "Where and how are reserves attested (proof of reserves, auditor)?"
  - "Which jurisdictions and account types can redeem, and with what fees and minimums?"
  - "Which Coinbase entity is the issuer and custodian?"
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: stablecoin-evm
    url: https://github.com/circlefin/stablecoin-evm
    commit: fc85788bc7c23cefe3df1a757133048bfddadeaa
    commit_date: 2026-08-12
---

# cbBTC

Research was cut short; this records what was read. On-chain reads on
Ethereum, Base and Arbitrum on 2026-09-29, and role history from Blockscout.

## Contract

The token is Circle's `FiatTokenV2_1` from `stablecoin-evm`, behind a
`FiatTokenProxy`, deployed at the same address on the three EVM chains with
the same proxy admin, implementation and owner. It has Circle's full role set:
owner, master minter, minters with allowances, pauser, blacklister, rescuer.

Minting goes through Coinbase's `MintForwarder` (`src/wrapped-tokens/MintForwarder.sol`,
verified): it is the master minter, and each whitelisted caller mints under an
allowance that refills over an interval. One EOA per chain mints (3,500 cbBTC
a day on Ethereum, 1,800 on Base, 450 on Arbitrum). Separate minters with zero
allowance burn redemptions.

## Blacklist

The blacklister has been changed three times since launch and is in use: nine
addresses were blacklisted on Ethereum within an hour on 2026-09-10. A
blacklisted address can't send or receive cbBTC.

## Redemption

Only through a Coinbase account: deposit cbBTC, withdraw BTC.

## Sources

- eth.blockscout.com and base.blockscout.com token and address transaction lists (2026-09-29)
