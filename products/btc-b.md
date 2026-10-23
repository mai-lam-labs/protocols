---
slug: btc-b
name: BTC.b (Lombard, formerly Avalanche Bridge)
scope: BTC.b on Avalanche C-Chain, after Lombard took over its infrastructure. Other chains are listed under issuance
kind: token
cross_chain: false
chains: [Avalanche, Ethereum, MegaETH, Monad, Stable, Katana]
source_public: true                       # BTC.b token verified; Lombard contracts in lombard-evm (not yet read)
inherits: []
updated: 2026-09-29
depth: basics

verification:
  exit: spec-only
  actors: partial                         # consortium read on-chain
  admin: partial
  data: unknown
  judgment: spec-only
  incidents: partial

backing:
  kind: signer_set
  holders:
    - entity: Lombard, keys in Cubist CubeSigner HSMs, approved by the Lombard Security Consortium
      jurisdiction: unknown
  keys: 14                                # consortium validators on Avalanche, epoch 22
  threshold: 10
  reserve_check: Chainlink Proof of Reserve (feed address not found)

issuance:
  - chain: Avalanche
    contract: "0x152b9d0FdC40C096757F570A51E494bd4b943E50"
    native: true
    mint_authority: "bridge role: Lombard adapter 0x85d1d52e11290f174444d21c2a167bedbe36e4d2 (upgradeable proxy)"
    freeze_authority: none
    supply: 2001.24
  - chain: Ethereum
    contract: "0xB0F70C0bD6FD87dbEb7C10dC692a2a6106817072"
    native: true                          # Lombard NativeLBTC contract, symbol BTC.b; the hub for other chains
    mint_authority: "AssetRouter 0x9ece5fb1ab62d9075c4ec814b321e24d8ea021ac (MINTER_ROLE)"
    freeze_authority: unknown
    supply: 71.71
  - chain: [MegaETH, Monad, Stable, Katana]
    native: true
    bridge: Chainlink CCIP via Ethereum    # Katana deprecated 2026-09-16; bridge-out until 2026-12-10

redemption:
  eligible: any holder                    # redeemForBTC on the AssetRouter, naming a BTC address
  kyc: false                              # "except sanctioned jurisdictions" per Lombard
  minimum: unknown
  fee: unknown
  bound_seconds: unknown
  steps: 1

exit:
  custody: mpc_vault
  execution: unknown                      # whether release is automatic once the consortium signs, or needs Lombard
  overrides:
    - who: Lombard Security Consortium
      needs: 10 of 14
      how: not approving a release
      reach: unknown
      bounded: unknown
      cost: unknown
    - who: Lombard (key custody in CubeSigner)
      needs: unknown
      how: unknown
      reach: unknown
      bounded: unknown
      cost: unknown
  refund_trigger: unknown
  exit_bound_seconds: unknown
  standing_approval: none

actors:
  - role: approve mints and releases
    entity: "Lombard Security Consortium: OKX, Galaxy, DCG, Wintermute, Figment, Kiln, Antpool, F2Pool, Kraken and others"
    jurisdiction: unknown
    set: m_of_n
    independence: unknown                 # per membership; not verified per key

admin:
  upgradeable: true                       # the token isn't, but the adapter that holds its mint role is
  authority: multisig
  roles:
    token: "BridgeToken; not upgradeable, no pause, no blacklist; one bridge role, movable by its holder"
    adapter_owner: "TimelockController 0xe4b5166b1d60c2208a934176522461c470a37d56 (86400 s)"
    timelock_proposer: "Safe 0xaa4bc534bc7be0e28a0686ab6910a9b21dfdc2b1 (3 of 5)"
    adapter_proxy_admin: "ProxyAdmin 0x813dd65fc4db761d0cc1799a769dcb1e9518b1b7"
    consortium_owner: timelock
    asset_router_owner: timelock
  timelock_seconds: 86400
  immediate_functions: unknown            # pause roles on the adapter not read
  grandfathered: unknown
  outside_exit_path: []

data_gates: unknown

judgment:
  screening:
    - kind: sanctioned jurisdictions
      status: active
    - kind: transaction flagging by the bridge (Ava Labs era)
      status: unknown                     # one 2024 report; whether Lombard does the same is not known
  freeze_assets: none                     # the Avalanche token has no blacklist
  freeze_pooled: false

service:
  integrator_access:
    api_key: unknown
    identity: unknown
    revocable: unknown
    rate_limited: unknown
    note: "Lombard's SDK takes a partner ID; whether minting or redeeming needs one is unknown"
  operators:
    - role: minting and redemption app, SDK
      entity: Lombard
      single_operator: true
      source_public: unknown
  bypass: unknown

integration:
  calls: [transfer, approve]
  signatures: [approval]                  # BridgeToken has no permit
  offchain_required: []
  finisher: user
  gasless_start: none
  monitoring: none for holding
  sdk: Lombard SDK
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
    note: unwrap through Lombard; who pays for the release wasn't read

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: mint / redeem
    form: unknown

incidents:
  - date: 2024-06-10
    duration: unknown
    funds_lost: unknown
    exits_blocked: true
    cause: "a user's BTC deposit was flagged and held by the Avalanche Bridge's security model (bitcointalk report; unresolved)"
  - date: 2026-01-28
    duration: unknown
    funds_lost: false
    exits_blocked: false
    cause: "old bridge's unwrap deadline; operations moved to Lombard. The old unwrap() is deprecated"

open_questions:
  - "Paid execution, redeem step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - "Does the adapter or AssetRouter have a pauser or any role that acts without the timelock?"
  - "Who owns the adapter's ProxyAdmin 0x813d…: the Safe, or the timelock?"
  - "What does redeemForBTC do on-chain, and what bounds the release: read lombard-evm"
  - "Can Lombard or CubeSigner refuse one release without the consortium?"
  - "Minimums, fees and redemption time"
  - "Who are all 14 consortium members, and which keys belong to which?"
  - "What is the Safe 0x10fa7a47… (2 of 11) for?"
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: lombard-evm
    url: https://github.com/lombard-finance/evm-smart-contracts
    commit: 7fe83e56f2265c0c281747c8dd3bb141d3022c46
    commit_date: 2026-08-05
    note: "cloned for BTC.b; not yet read"
---

# BTC.b

Research was cut short; this records what was read. On-chain reads on
Avalanche and Ethereum on 2026-09-29.

## Who runs it

Lombard announced the acquisition of BTC.b from Ava Labs on 2025-10-30. The
Avalanche token contract, name and address stayed the same; Ava Labs' SGX
"warden" bridge was retired, with a final deadline to redeem from it of
2026-01-28. Minting and redemption now run on Lombard's infrastructure: keys
held in Cubist CubeSigner HSMs, releases approved by the Lombard Security
Consortium, and cross-chain transfers through Chainlink CCIP via Ethereum.

## On Avalanche

`BridgeToken` (Solidity 0.8.11, not a proxy) has one privileged role, the
bridge role, which mints and can hand itself on. It has no pause and no
blacklist. `unwrap` is the old redemption path and is deprecated.

The bridge role is now held by Lombard's adapter `0x85d1…`, an upgradeable
proxy owned by a timelock with a one-day delay; a 3-of-5 Safe proposes. The
consortium contract read 14 validators with a threshold of 10.

## Sources

- https://www.theblock.co/post/376974/lombard-finance-acquires-btc-b-avalanche-bridged-bitcoin-asset-ava-labs (2026-09-29)
- https://www.avalanche.com/about/blog/btc-b-technical-transition-to-lombards-architecture (2026-09-29)
- https://www.lombard.finance/blog/btcb-technical-transition-to-lombard-architecture/ (2026-09-29)
- https://cubist.dev/blog/avalanche-transitions-btcb-to-lombard-with-cubist-tech-underpinning-bridge-operations (2026-09-29)
- https://docs.lombard.finance/use/bridging (2026-09-29)
- https://bitcointalk.org/index.php?topic=5499523.0 (2026-09-29)
- https://x.com/AvaLabs/status/2016654034187538549 (2026-09-29, 403)
