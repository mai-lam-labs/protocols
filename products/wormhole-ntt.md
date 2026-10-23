---
slug: wormhole-ntt
name: Wormhole NTT
framework: true                          # a framework: each token issuer deploys and owns its NttManager
scope: The Native Token Transfers framework on EVM (NttManager, WormholeTransceiver) as each token issuer deploys it, verified by Wormhole Guardians. Owners, pausers, thresholds and limits are per deployment and none is read here
kind: bridge
class: C
cross_chain: true
chains: unknown                          # per token deployment
source_public: true
inherits: []
updated: 2026-10-04

verification:
  service: spec-only
  exit: source-verified                  # NttManager, ManagerBase, RateLimiter, WormholeTransceiver read
  actors: spec-only                      # guardian set from docs
  admin: partial                         # functions read in source; no deployment's owner read
  data: source-verified
  judgment: partial
  incidents: partial

exit:
  custody: in_flight_message             # locked or burned on the source by NttManager until a VAA is delivered
  execution: automatic                   # Guardians sign; anyone can deliver the VAA through receiveMessage
  overrides:
    - who: Wormhole Guardians
      needs: 7 of 19 decline to sign one message (quorum is 13); 13 of 19 to sign a forged one
      parties: quorum
      independent: unknown
      how: withhold the VAA for one transfer, or sign a transfer that wasn't made
      reach: one
      bounded: false
      cost: none on-chain
    - who: the deployment's NttManager owner
      needs: unknown                     # per deployment: an EOA, a multisig or a timelock
      parties: unknown
      how: upgrade the NttManager, or setPeer / setTransceiver / setThreshold so one inbound transfer is rejected or a forged one accepted
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: none                   # no refund for a sent transfer; only a rate-limited outbound transfer still in the queue can be cancelled by its sender
  exit_bound_seconds: unknown            # source finality and Guardian signing, plus up to rateLimitDuration (24 h by default) if the inbound limit queues it
  exit_bound_chosen_by: none
  standing_approval: upgradeable_target  # users approve the NttManager, an ERC-1967 proxy

actors:
  - role: Wormhole Guardians; sign the VAA for the transfer
    entity: 19 institutional validators
    jurisdiction: unknown
    set: m_of_n                          # 13 of 19
    independence: unknown                # by docs; not checked
  - role: Relayer; delivers the VAA to the destination transceiver
    entity: anyone
    jurisdiction: pseudonymous
    set: permissionless
    independence: independent

admin:
  upgradeable: true                      # ERC-1967 proxies; upgrade(address) by the owner
  authority: unknown                     # per deployment
  timelock_seconds: unknown              # none in the framework; a deployment's owner may itself be a timelock
  immediate_functions: unknown           # upgrade, pause, setThreshold, setTransceiver / removeTransceiver, setPeer and limits are owner functions; whether they are immediate depends on who the owner is
  grandfathered: none
  outside_exit_path:
    - what: setOutboundLimit
      effect: how much can leave the source per window

data_gates:
  - kind: inbound rate limit
    where: NttManager on the destination, before minting or unlocking
    trigger: the transfer exceeds remaining inbound capacity
    blocks_exit: true
    reset: bounded                       # queued; completeInboundQueuedTransfer after rateLimitDuration (24 h default, fixed at deployment)
  - kind: source finality
    where: Guardians before signing
    trigger: the source block isn't final
    blocks_exit: true
    reset: bounded

judgment:
  screening: []                          # none in the contracts; Guardians' own policies unknown
  freeze_assets: unknown                 # depends on the token
  freeze_pooled: true                    # in locking mode, the hub NttManager holds every locked token

service:
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: unknown
    note: "contracts and VAAs are public; Wormholescan and relayers are optional"
  operators: []
  screening: []
  bypass: true

integration:
  calls: ["NttManager.transfer on the source", "relay the VAA to the destination transceiver (automatic relayer or manual)", "completeInboundQueuedTransfer if queued"]
  signatures: ["ERC-20 approval to the NttManager"]
  offchain_required:
    - role: Wormhole Guardian network (VAA signing)
      api_key: false
      rate_limited: false
  finisher: anyone
  gasless_start: none
  monitoring: "Wormholescan by sequence, or TransferSent / TransferRedeemed events"
  sdk: "@wormhole-foundation/sdk (TypeScript)"
  testnet: true
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: delivery
  holder: none
  strike: par
  expiry: none
  early_close: none
  premium: none
  terms_fixed_by: contract
  price_set_by: par
  discipline: none
  surplus_to: none
  extraction: []
  sides: [exact_in]
  rate: par                              # same asset across chains, less any fee
  quote_validity: none
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: "NttManager.transfer, paying the relayer in native gas if automatic"
  - action: deliver
    performer: anyone
    paid: deferred
    note: "the automatic relayer, paid in advance, or a manual relay paid by no one"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: transfer
    form: self_built

incidents: []                            # the 2022 exploit was the legacy Token Bridge, not NTT

open_questions:
  - Owners, pausers, thresholds and limits of specific NTT deployments that matter to routes (the framework entry can't rate admin)
  - Guardian identities and jurisdictions, and whether any Guardian screens
  - Time from transfer to delivery in practice
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: wormhole-ntt
    url: https://github.com/wormhole-foundation/example-native-token-transfers
    commit: 250d810d42b005526e4fb7e3aea75d2d2ab8fdbb
    commit_date: 2026-07-30
---

# Wormhole NTT

**Primitive (one line):** Native Token Transfers; tokens locked (or burned) on source chain by NttManager; Wormhole Guardians (13/19 threshold) produce VAA attesting to the transfer; VAA relayed to destination where NttManager unlocks (or mints) tokens. Rate limiter can queue transfers. User can only self-refund outbound queued transfers.
**Product scope of this entry:** Wormhole NTT EVM contracts

## Category 1 — Actor-gated edges

**Actors on exit path:**
- Actor: Wormhole Guardians
  - Role: produce VAA (Verified Action Approval) attesting to cross-chain transfers. Required for all completions. 13/19 supermajority.
  - Set size: 19 institutionally-run validators
  - Source: [3] `WormholeTransceiver.sol:147-148`

**User self-refund:**
- `cancelOutboundQueuedTransfer(uint64 messageSequence)` — ONLY for transfers queued by the rate limiter. Original sender only (`queuedTransfer.sender != msg.sender` check). **Gated by `whenNotPaused`** — admin pause blocks even this. Source: [3] `NttManager.sol:369-390`
- **No self-refund for in-flight (non-queued) transfers.** Once tokens are locked/burned and sent, there is no cancellation. Tokens remain locked until Guardians produce the VAA.
- `NttManagerNoRateLimiting` variant: ALL queue functions revert with `NotImplemented()` — no self-refund at all.

**If Guardians offline:** tokens locked/burned on source with no way to release on destination. No refund mechanism. Funds stuck until Guardians return. **Unbounded.**

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** full ERC1967 proxy upgradeability. Owner can call `upgrade(address)` to replace entire implementation. Source: [3] `ManagerBase.sol:332`, `Implementation.sol:80-97`

**Immediate-effect admin functions:**
- `pause()` by owner or pauser — **halts ALL operations** including transfer, attestation, execution, queue completion, AND `cancelOutboundQueuedTransfer`. Source: [3] `ManagerBase.sol:338`
- `unpause()` by owner ONLY. Source: [3] `ManagerBase.sol:342`
- `setThreshold(uint8)` — changes attestation threshold. Source: [3] `ManagerBase.sol:409`
- `setTransceiver`/`removeTransceiver` — add/remove verification layers. Source: [3] `ManagerBase.sol:362,390`
- `setOutboundLimit`/`setInboundLimit` — change rate limits. Source: [3] `NttManager.sol:138,146`
- `setPeer` — set peer NttManager on another chain. Source: [3] `NttManager.sol:104`

**Rate limiter (can delay refunds):**
- Default 24-hour duration (configurable, immutable at deployment). Source: [3] `RateLimiter.sol:15`
- Linear capacity replenishment. Source: [3] `RateLimiter.sol:181-196`
- Inbound transfers exceeding limit are automatically queued. Must wait `rateLimitDuration` then call `completeInboundQueuedTransfer()`. Source: [3] `NttManager.sol:292-314`

## Category 3 — Data-oracle-gated edges

**Oracles:** Wormhole Guardian VAA is the oracle. No external price oracles.

## Category 4 — Judgment-oracle-gated edges

**Guardian discretion:** Guardians can theoretically refuse to attest to specific messages.
**Stablecoin freeze:** if tokens are locked in NttManager (LOCKING mode), issuer freeze on the NttManager address would affect all locked tokens of that asset.

## Historical incidents

- Feb 2022 Wormhole bridge exploit ($326M) was the **legacy Token Bridge**, NOT NTT. NTT launched 2024 and is architecturally distinct.
- No known NTT exploits. 7 audit reports. $5M bug bounty.

## Sources

1. https://wormhole.com/docs/build/contract-integrations/native-token-transfers/ — NTT docs
2. https://github.com/wormhole-foundation/example-native-token-transfers — source repo
3. Source files: `NttManager.sol` (cancel lines 369-390), `ManagerBase.sol` (pause 338, upgrade 332, threshold 409), `RateLimiter.sol` (duration line 15, capacity 181-196), `WormholeTransceiver.sol` (VAA verify 147-148) — cloned and read 2026-09-16
