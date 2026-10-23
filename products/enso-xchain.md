---
slug: enso-xchain
name: Enso Shortcuts (cross-chain)
scope: cross-chain shortcuts, where a bridge delivers tokens to an Enso receiver on the destination chain, which runs a shortcut through EnsoRouter. Covers the LayerZero, Stargate V2 and CCIP receivers; the bridges themselves are separate entries
kind: aggregator
cross_chain: true
chains: unknown
source_public: true
inherits: [enso, stargate, layerzero-oft]  # plus Chainlink CCIP, which has no entry yet
service: {same_as: enso}
updated: 2026-09-29
depth: basics

verification:
  exit: source-verified                   # LayerZeroReceiver.sol, EnsoCCIPReceiver.sol
  actors: partial
  admin: partial                          # owners read on Ethereum only
  data: partial
  judgment: partial
  incidents: not-reviewed

exit:
  custody: in_flight_message              # the bridge's, until the receiver runs
  execution: automatic                    # the receiver runs the shortcut when the bridge delivers; on failure it pays the receiver address
  overrides:
    - who: receiver owner
      needs: one party (a 2-of-4 Safe on the LayerZero and CCIP receivers; an EOA on the Stargate V2 receiver)
      how: "sweep (LayerZeroReceiver) or recoverTokens (EnsoCCIPReceiver) sends tokens held by the receiver to the owner, or anywhere. sweep also marks the message executed, so it can't be retried. Its comment says this is to refund the user, by hand"
      reach: one
      bounded: false
      cost: none on-chain
    - who: CCIP receiver owner
      needs: one party (2-of-4 Safe)
      how: pause; while paused, incoming messages are refunded to the receiver address rather than executed
      reach: all
      bounded: false
      cost: none on-chain
  refund_trigger: on_failure              # a failed shortcut sends the bridged tokens to the receiver address named in the message
  exit_bound_seconds: unknown             # the bridge's delivery time
  standing_approval: immutable_target

actors:
  - role: bridge delivery
    entity: the bridge's own (see its entry)
    jurisdiction: unknown
    set: unknown
    independence: unknown

admin:
  upgradeable: false                      # receivers are not proxies
  authority: multisig
  roles:
    layerzero_receiver: "0xbf7773ad9d1abcc0a01981e3bff7e6408a775939, owner Safe 0x4e3f2d3a840f602b132e1d4dc4709a13ef43bf2c (2 of 4)"
    ccip_receiver: "0x46d0ff229e0a0ea5c4dcc639ce8f5cf75967122d, owner the same Safe; not paused when read"
    stargate_v2_receiver: "0xa57eb4bc3143da32941aaaef7832fb48897ac0f6, owner 0x826e0BB2276271eFdF2a500597f37b94f6c153bA (EOA)"
  timelock_seconds: none
  immediate_functions:
    - function: sweep / recoverTokens
      caller: receiver owner
      effect: takes tokens held by the receiver
    - function: setRegistrar, then setOFTs / removeOFTs
      caller: owner, then registrars
      effect: decides which OFT pools the LayerZero receiver accepts; a message from an unlisted one reverts in lzCompose
    - function: pause
      caller: CCIP receiver owner
      effect: incoming messages refunded instead of executed
  grandfathered: none
  outside_exit_path: []

data_gates:
  - kind: gas check
    where: LayerZeroReceiver.lzCompose
    trigger: less gas than the message's estimatedGas, or msg.value below its nativeDrop
    blocks_exit: true                     # lzCompose reverts and the tokens stay in the receiver until the compose is retried or swept
    reset: unbounded                      # retry is permissionless in LayerZero; nothing obliges anyone to

judgment:
  screening: []
  freeze_assets: unknown                  # depends on the bridged asset
  freeze_pooled: false

integration:
  calls: ["bridge send with a compose or CCIP message carrying (receiver, nativeDrop, estimatedGas, shortcut)"]
  signatures: [approval]
  offchain_required:
    - role: route API
      api_key: true
      rate_limited: unknown
  finisher: protocol                      # the bridge's executor calls the receiver
  gasless_start: none
  monitoring: "ShortcutExecutionSuccessful / ShortcutExecutionFailed events on the destination receiver"
  sdk: "@ensofinance/sdk (TypeScript)"
  testnet: unknown
  steps: 3

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: inherited
  holder: unknown
  strike: unknown
  expiry: unknown
  early_close: unknown
  premium: none
  terms_fixed_by: calldata
  price_set_by: quote
  discipline: unknown
  surplus_to: unknown
  extraction: []
  sides: inherited                       # the bridge decides what arrives; the shortcut then has its own minimum
  rate: inherited
  quote_validity: inherited
  partial_fill: inherited
  partial_remainder: inherited

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: "the bridge send carrying the shortcut, from the user's account"
  - action: exit
    performer: none
    paid: none
    inherited: true
    note: the bridge's

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: cross-chain shortcut
    form: calldata
    bounds: arbitrary
    verifiable_locally: false
    api_optional: false
    target_admin: none

incidents: []

open_questions:
  - "Trade: holder, strike, expiry, early_close, discipline, surplus_to (CRITERIA.md, Trade)"
  - "Receiver owners were read on Ethereum only; are they the same on other chains?"
  - "Who are the four signers of Safe 0x4e3f…?"
  - "Why is the Stargate V2 receiver still owned by an EOA, and is it still in use?"
  - "How often do lzCompose calls revert and get swept, and how are users refunded then?"
  - "Which CCIP errors go to TO_ESCROW, and how long do quarantined funds wait?"
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: enso-shortcuts
    url: https://github.com/EnsoBuild/shortcuts-client-contracts
    commit: 044b3c97eb4af56437eae135b35b4907c0e8e060
    commit_date: 2026-09-28
---

# Enso Shortcuts (cross-chain)

Source: the `enso-shortcuts` clone (`src/bridge/LayerZeroReceiver.sol`,
`src/bridge/EnsoCCIPReceiver.sol`), deployment broadcasts under `broadcast/`,
and on-chain reads on Ethereum on 2026-09-29.

## Exit

A bridge (a LayerZero OFT, Stargate V2 or CCIP) delivers tokens to an Enso
receiver with a message naming a `receiver` address and a shortcut. The
receiver tries the shortcut through `EnsoRouter`; if it fails, the tokens go
to `receiver`. That part is automatic and good.

Two paths are not:

- **The receiver call itself reverts.** In `lzCompose`: the sending OFT isn't
  on the allow-list, the gas is below the message's estimate, or `msg.value`
  is below its native drop. The tokens stay in the receiver. LayerZero lets
  anyone retry the compose, but nothing makes anyone do it.
- **The owner sweeps.** `sweep` sends tokens held by the receiver to the owner
  and marks the message executed so it can't be retried. The code comment
  says this is "to refund user", so the refund is by hand. The CCIP receiver
  has `recoverTokens` to any address, and a quarantine ("TO_ESCROW") for
  malformed messages.

## Owners

The LayerZero and CCIP receivers on Ethereum are owned by a 2-of-4 Safe. The
Stargate V2 receiver is still owned by the deployer EOA.

## Sources

- https://docs.enso.build/ (2026-09-16)
