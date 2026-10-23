---
slug: tbtc
name: Threshold tBTC v2
scope: tBTC on Ethereum (token, TBTCVault, Bridge, RedemptionWatchtower, WalletRegistry). L2 copies not covered
kind: token
cross_chain: false
chains: [Ethereum]
source_public: true
inherits: []
updated: 2026-09-29
depth: basics

verification:
  exit: partial                           # parameters read on-chain; redemption code not traced
  actors: partial
  admin: partial
  data: partial
  judgment: partial
  incidents: not-reviewed

backing:
  kind: signer_set
  holders:
    - entity: tBTC wallet signers (threshold ECDSA)
      jurisdiction: pseudonymous
  keys: unknown                           # signers per wallet; the sortition pool held 20 operators when read
  threshold: unknown
  reserve_check: on-chain                 # wallets are Bitcoin addresses tracked by the Bridge

issuance:
  - chain: Ethereum
    contract: "0x18084fbA666a33d37592fA2633fD49a74DD93a88"
    native: true
    mint_authority: "TBTCVault 0x9C070027cdC9dc8F82416B2e5314E11DFb4FE3CD, on swept deposits proven to the Bridge"
    freeze_authority: none

redemption:
  eligible: any holder                    # request through the Bridge with a Bitcoin output script
  kyc: false
  minimum: unknown
  fee: unknown
  bound_seconds: unknown                  # redemption timeout not read
  steps: 1                                # request on-chain; signers pay out; anyone proves it

exit:
  custody: mpc_vault
  execution: automatic                    # signers are selected by sortition and act by protocol rules
  overrides:
    - who: RedemptionWatchtower guardians
      needs: unknown number of guardians
      how: veto a redemption request during its delay (900 s default; 8 h and 24 h levels for larger amounts)
      reach: one
      bounded: false                      # a vetoed redemption is frozen for 2592000 s and charged a 5% penalty
      cost: none known
    - who: wallet signers
      needs: enough signers to withhold the threshold signature
      how: not signing the payout
      reach: all                          # every redemption from that wallet
      bounded: unknown                    # redemption timeout and slashing not read
      cost: stake slashed (not verified)
  refund_trigger: unknown
  exit_bound_seconds: unknown
  standing_approval: none

actors:
  - role: sign BTC payouts
    entity: stakers in the sortition pool
    jurisdiction: pseudonymous
    set: staked
    independence: unknown
  - role: veto redemptions
    entity: guardians, set by the watchtower manager
    jurisdiction: unknown
    set: whitelist
    independence: unknown

admin:
  upgradeable: true                       # Bridge is a TransparentUpgradeableProxy
  authority: multisig
  roles:
    vault_owner: "Threshold Council 0x9F6e831c8F8939DC0C830C6e492e7cEf4f9C2F5f (6 of 9)"
    watchtower_owner: Threshold Council
    watchtower_manager: "0x87F005317692D05BAA4193AB0c961c69e175f45f (also the Bridge treasury)"
    bridge_governance: "BridgeGovernance 0xcBCFA3eb5E067173b262ACe62f9dD87f1D2Cc0Cf"
    bridge_proxy_admin: "0x16a76d3cd3c1e3ce843c6680d6b37e9116b5c706"
  timelock_seconds: unknown               # BridgeGovernance has a governance delay; not read
  immediate_functions: unknown
  grandfathered: unknown
  outside_exit_path: []

data_gates:
  - kind: optimistic minting pause
    where: TBTCVault.isOptimisticMintingPaused
    trigger: set by the Council; true when read
    blocks_exit: false                    # deposits wait for the sweep proof instead
    reset: unbounded
  - kind: redemption delay
    where: RedemptionWatchtower
    trigger: every redemption; 900 s default, 28800 s and 86400 s levels by amount
    blocks_exit: true
    reset: bounded

judgment:
  screening:
    - kind: redemption veto by guardians
      status: active                      # enabled 2024-03-19, lifetime 93312000 s (to about 2027-03)
  freeze_assets: none
  freeze_pooled: false

service:
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: false
    note: "deposits and redemptions are contract calls"
  operators:
    - role: dApp, SDK and relay maintainers
      entity: Threshold / Thesis
      single_operator: false
      source_public: true
  bypass: true                            # deposits and redemptions are contract calls

integration:
  calls: [transfer, approve]
  signatures: [EIP-2612 permit]
  offchain_required: []
  finisher: user
  gasless_start: [eip2612]               # tBTC has permit
  monitoring: none for holding; a redemption needs the Bitcoin payout watched
  sdk: "@keep-network/tbtc-v2.ts (TypeScript)"
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
    note: "an ordinary transfer; permit lets a spender pull, but pays no submitter"
  - action: redeem
    performer: designated
    paid: unknown
    note: redemption by the signers

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: deposit
    form: self_built
    note: "the deposit script and address are derived client-side from public parameters"

incidents: []

open_questions:
  - "Paid execution, redeem step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - "What are the redemption timeout, minimum and fee, and what does a holder get when the timeout passes?"
  - "How many signers per wallet and what threshold, and how independent are the operators?"
  - "Who are the watchtower guardians, and how many does a veto need?"
  - "What is BridgeGovernance's delay, and what can change without it?"
  - "Who controls the Bridge proxy admin 0x16a7…?"
  - "Why is optimistic minting paused, and since when?"
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: tbtc-v2
    url: https://github.com/keep-network/tbtc-v2
    commit: 40a11d1dcdcf82d3962e430067cfe3f97be81483
    commit_date: 2026-09-11
  - repo: keep-core
    url: https://github.com/keep-network/keep-core
    commit: 4c9b65ec40f19723b44d418425c8d9f93ffedcb5
    commit_date: 2026-09-17
  - repo: thesis-solidity-contracts
    url: https://github.com/thesis/solidity-contracts
    commit: c315b9d5f0c39253428898474e97552f5e5b9046
    commit_date: 2023-03-07
    note: "tBTC token base contracts"
---

# tBTC

Research was cut short; this records what was read. The `tbtc-v2` clone
(`solidity/deployments/mainnet/` for addresses), and on-chain reads on
Ethereum on 2026-09-29.

## Holding and redeeming

Anyone can redeem: burn tBTC through the Bridge with a Bitcoin output script,
and a signer wallet pays the BTC. The wallets are threshold-ECDSA groups drawn
by sortition from staked operators; 20 operators were in the pool when read.

## The watchtower

`RedemptionWatchtower.sol` is enabled on mainnet. Each redemption waits a
delay: 900 s by default, 8 h or 24 h at higher levels, and requests up to
5 BTC are waived (`waivedAmountLimit`). During the delay guardians can veto it.
A vetoed redemption is frozen for 30 days and charged 1/20 (5%). The watchtower
was switched on 2024-03-19 with a lifetime of 1,080 days, so it expires around
March 2027 unless extended.

This is an individual override on an otherwise automatic exit: under
CRITERIA's Exit rules it makes the petal red while it is active.

## Admin

The Threshold Council (6 of 9) owns the TBTCVault and the watchtower. The
Bridge is upgradeable, governed through BridgeGovernance. Optimistic minting
was paused when read.

## Sources

- On-chain reads, Ethereum, 2026-09-29
