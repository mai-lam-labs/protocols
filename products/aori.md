---
slug: aori
name: Aori
scope: Aori v0.3.1 Aori.sol on ten EVM chains (one contract per chain, LayerZero OApp) and the Aori API in front; cross-chain and single-chain orders
kind: bridge
class: B
cross_chain: true
chains: [Ethereum, Base, Arbitrum, Optimism, BSC, Plasma, Monad, Stable, MegaETH, Rootstock]   # docs.aori.io/protocol/deployments; owner read on all ten, 2026-10-04
source_public: true                      # contracts; the API and solver infrastructure aren't
inherits: [layerzero-oft]                # LayerZero messaging, not OFT itself
updated: 2026-10-04

verification:
  service: spec-only
  exit: source-verified                  # cancel, _cancel, validateCancel, validateSourceChainCancel, emergency functions read
  actors: partial                        # DVN set from Aori's docs; endpoint config not read on-chain
  admin: source-verified                 # owner and paused read on all ten chains; deployed bytecode not compared with source
  data: partial
  judgment: partial                      # contracts read; API screening unknown
  incidents: partial                     # a web search found nothing (2026-09-16)

exit:
  custody: escrow                        # Aori.sol holds locked balances per offerer
  execution: self                        # after endTime the offerer cancels: on the source chain for single-chain orders, on the destination chain for cross-chain ones, which sends a LayerZero message back
  overrides:
    - who: owner EOA 0x941327e206b8d8cfe1014a8a95b05e1536dfd00d, the same on all ten chains
      needs: one key; no timelock
      parties: key
      how: emergencyCancel(orderId, recipient) sends a chosen order's inputs to any address; emergencyWithdraw(token, amount, user, isLocked, recipient) takes any user's locked balance
      reach: one
      bounded: false
      cost: none on-chain
    - who: the same owner, as LayerZero OApp owner and delegate
      needs: one key; no timelock
      parties: key
      how: setPeer, or endpoint config (receive library, DVNs) as delegate, so that a forged settlement for an order is accepted or its cancellation never is
      reach: one
      bounded: false
      cost: none on-chain
    - who: any one of the 4 or 5 DVNs on the pathway (LayerZero Labs, Nethermind, Google Cloud, Horizen, Canary)
      needs: one party; Aori requires every configured DVN to attest
      parties: organisation
      how: withhold attestation of one cancellation message; the order stays locked on the source, and it can't be re-sent because the destination has already marked it cancelled
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: timeout                # cancel after order.endTime; whitelisted solvers can cancel any time
  exit_bound_seconds: unknown            # endTime is set per order; cross-chain adds LayerZero delivery, not measured
  exit_bound_chosen_by: order creator
  standing_approval: immutable_target    # deposit pulls from the offerer by transferFrom into Aori.sol, which isn't upgradeable; only whitelisted solvers can call deposit, with the offerer's signature

actors:
  - role: LayerZero DVNs; attest the cancellation message from the destination to the source (cross-chain orders only)
    entity: LayerZero Labs, Nethermind, Google Cloud, Horizen, Canary (4 or 5 per pathway)
    jurisdiction: unknown
    set: m_of_n                          # n of n: unanimous
    independence: independent
  - role: LayerZero executor; calls lzReceive on the source once verified
    entity: anyone
    jurisdiction: pseudonymous
    set: permissionless
    independence: independent

admin:
  upgradeable: false
  authority: eoa                         # 0x941327e2...d00d on all ten chains (no code)
  timelock_seconds: none
  immediate_functions:
    - function: pause / unpause
      caller: owner
      effect: cancel, withdraw and _lzReceive are whenNotPaused, so every exit stops while paused
    - function: emergencyCancel(orderId, recipient)
      caller: owner
      effect: an active order's inputs go to any recipient
    - function: emergencyWithdraw(token, amount)
      caller: owner
      effect: any token balance of the contract to the owner, without updating user balances
    - function: emergencyWithdraw(token, amount, user, isLocked, recipient)
      caller: owner
      effect: any user's locked or unlocked balance to any recipient
    - function: setPeer, setDelegate (LayerZero OAppCore)
      caller: owner
      effect: which remote contracts and which DVN configuration the source trusts for settlement and cancellation
    - function: removeSupportedChain
      caller: owner
      effect: unknown whether it blocks cancellation messages from that chain
  grandfathered: none
  outside_exit_path:
    - what: addAllowedSolver / removeAllowedSolver, addAllowedHook / removeAllowedHook
      effect: who can deposit, fill and settle

data_gates: []                           # none automatic known; pause is an admin decision, rated above

judgment:
  screening: []                          # none in the contracts
  freeze_assets: unknown
  freeze_pooled: true                    # every order's inputs sit at the one contract per chain

service:
  integrator_access:
    api_key: false                       # api.aori.io /chains and POST /quote answered with no key (2026-10-07)
    identity: unknown
    revocable: unknown
    rate_limited: unknown
  operators:
    - role: Aori API (quote, swap, status, websocket stream)
      entity: Aori
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: Solvers; deposit the user's signed order, fill and settle
      entity: unknown
      single_operator: unknown
      source_public: false
      deployment_config_public: false
  screening: unknown
  bypass: false                          # deposit is onlySolver: an order can't be opened without a whitelisted solver

integration:
  calls: ["POST /quote, POST /swap with the signed order", "a whitelisted solver calls deposit and fill", "track via /data/status or the websocket", "after endTime: cancel(orderId) on the source (single-chain) or cancel(orderId, order, options) on the destination with LayerZero fee (cross-chain)"]
  signatures: ["EIP-712 order signed by the offerer"]
  offchain_required:
    - role: Aori API and its solvers
      api_key: unknown
      rate_limited: unknown
  finisher: protocol                     # solvers settle over LayerZero
  gasless_start: none                   # the offerer must approve Aori.sol first; a cross-chain cancel needs native gas and the LayerZero fee on the destination
  monitoring: "/data/status, websocket stream, or Deposit / Fill / Settle / Cancel events"
  sdk: "@aori/aori-ts (TypeScript)"
  testnet: unknown
  steps: 3

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: allowlist                      # whitelisted solvers
  strike: signed
  expiry: api_chosen
  early_close: none                      # cancel only after endTime; solvers can cancel any time
  premium: none
  terms_fixed_by: signature
  price_set_by: quote
  discipline: unknown
  surplus_to: holder                     # any surplus from the solver's hook goes to the solver (Aori.sol:420, :542)
  extraction: []
  sides: [exact_in]                      # POST /quote takes inputAmount
  rate: firm                             # the recipient gets exactly outputAmount
  quote_validity: 90                     # the quoted order's endTime was 90 s after startTime (live 2026-10-07); cancel opens only after endTime
  partial_fill: none                     # the full inputAmount is deposited and the recipient gets exactly outputAmount
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: the offerer approves Aori.sol by transaction before a whitelisted solver deposits the signed order
  - action: cancel
    performer: user
    paid: none
    gas_on: other_chain
    note: "after endTime a cross-chain order is cancelled on the destination chain, which needs native gas and the LayerZero fee there"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: order
    form: typed_data
    note: "EIP-712 order signed by the offerer"

incidents: []                            # none found (web search 2026-09-16)

open_questions:
  - "Trade: discipline (CRITERIA.md, Trade)"
  - Who controls owner EOA 0x941327e2...d00d
  - The DVN configuration as set on each endpoint, rather than as documented
  - Whether removeSupportedChain stops cancellation messages from that chain from being received
  - Whether the Aori API needs a key, who it serves, and whether it screens
  - Whether deployed bytecode matches the pinned source on each chain (Ethereum is at a different address from the others)
  - exit_bound_seconds in practice (endTime set by the API, plus LayerZero delivery)
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: aori
    url: https://github.com/aori-io/aori
    commit: 1c70cd2476f77d9dec6831f23796009aa0d7c9e0
    commit_date: 2025-12-18
---

# Aori

**Primitive (one line):** Off-chain orderbook matching with on-chain escrow settlement; whitelisted solver calls `deposit()` to escrow user tokens via signed EIP-712 order; solver fills on destination chain; LayerZero message proves fills; user can `cancel()` after `endTime` to recover escrowed tokens.
**Product scope of this entry:** Aori v0.3.1 (cross-chain via LayerZero)

## Category 1 — Actor-gated edges

**Actors on exit path (cancellation/refund):**
- **Single-chain orders:** user (offerer) can call `cancel(orderId)` after `order.endTime`. Returns tokens to offerer. Source: [3] `Aori.sol:761`, `AoriUtils.sol:155`
- **Cross-chain orders:** user can cancel from destination chain after `endTime`, which sends LayerZero message back to source to execute `_cancel()`. Requires paying LayerZero gas. Source: [3] `Aori.sol:786`, `AoriUtils.sol:117-121`
- **Whitelisted solvers** can cancel any active order at any time (no expiry requirement). Source: [3] `Aori.sol` cancel validation

**CRITICAL: Owner can block cancellation via pause.** `cancel()` has `whenNotPaused` modifier — if owner pauses, users cannot cancel or withdraw, trapping funds. Source: [3] `Aori.sol:116-126`

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** none — not upgradeable, no proxy pattern. Mitigating factor.

**Immediate-effect admin functions (owner):**
- Function: `pause()`/`unpause()`, Caller: owner, Effect: **pauses ALL operations including cancel and withdraw**. This is the critical risk — user funds are trapped when paused. Source: [3] `Aori.sol:116-126`
- Function: `emergencyCancel(orderId, recipient)`, Caller: owner, Effect: cancels any order and sends tokens to **any recipient** (not necessarily the offerer). Can redirect user funds. Source: [3] `Aori.sol:213`
- Function: `emergencyWithdraw(token, amount)`, Caller: owner, Effect: extracts tokens from contract to owner. **Does not update user balances** — breaks accounting. Source: [3] `Aori.sol:243-258`
- Function: `emergencyWithdraw(user, token, amount, locked, recipient)`, Caller: owner, Effect: extracts tokens from a **specific user's balance** (locked or unlocked) to any recipient. Updates accounting but lets owner drain any user's funds. Source: [3] `Aori.sol:267-288`
- Function: `addAllowedSolver`/`removeAllowedSolver`, Caller: owner, Effect: controls solver whitelist. Source: [3] `Aori.sol:151-162`

## Category 3 — Data-oracle-gated edges

**Oracles:** LayerZero DVNs (Decentralized Verifier Networks) for cross-chain settlement messages. All configured DVNs must unanimously attest. Source: [3] LayerZero OApp inheritance

## Category 4 — Judgment-oracle-gated edges

**Risk-scoring integrations:** none in contracts. Solver whitelist controlled by owner.

**Stablecoin freeze exposure:** contract holds escrowed user tokens — freeze on contract address affects all escrowed funds in that asset.

## Composite

**Stuck-leg failure modes:**
1. Owner pauses contract — **cancel and withdraw blocked**, all escrowed funds trapped. Unbounded.
2. Owner calls emergencyWithdraw — user funds drained. Irreversible.
3. Owner calls emergencyCancel with wrong recipient — user funds redirected. Irreversible.
4. LayerZero DVN failure — cross-chain settlement stuck; user can cancel after `endTime` on destination chain (if not paused). Bounded by endTime.
5. Solver does not fill before endTime — user cancels and recovers. Bounded.

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Normal cancel after endTime | bounded by user-set endTime | [3] |
| Owner pause | unbounded (owner controls unpause) | [3] |
| Owner emergencyWithdraw | irreversible (funds drained) | [3] |
| LayerZero failure | bounded by endTime + cancel | [3] |

## Sources

1. https://docs.aori.io/ — Aori documentation
2. https://github.com/aori-io — GitHub org
3. Source at `source/aori/contracts/`:
   - `Aori.sol` — main contract (1048 lines): deposit (337), cancel (761-842), pause (116-126), emergencyCancel (213), emergencyWithdraw (243-288), solver whitelist (151-162)
   - `AoriUtils.sol` — validation: validateCancel (106-158), endTime checks
   - `IAori.sol` — interface
   — cloned and read 2026-09-16

4. https://docs.aori.io/protocol/deployments and /protocol/dvn-configuration, retrieved 2026-10-04
5. `owner()` and `paused()` by eth_call on all ten chains through public RPCs, 2026-10-04

## On-chain state (2026-10-04)

- **Owner:** `0x941327e206b8d8cfe1014a8a95b05e1536dfd00d` on all ten chains. It has no code, so it is an EOA: one key, with no multisig or timelock.
- **Paused:** false on all ten chains.
- **DVNs (from the docs):** each pathway names 4 or 5 DVNs and requires all of them, unanimously. Any one DVN can therefore stop a given cross-chain cancellation from arriving. The docs present unanimity as protection against forged messages, which it is, but it also makes every DVN a veto on exits.

## Incident search (2026-09-16)

No exploits, hacks, or specific user complaints found in web search for Aori protocol (2024-2026). However, the admin surface (pause-blocks-cancel, emergencyWithdraw) means the absence of incidents is not evidence of safety — the owner retains the technical capability to drain funds at any time.

## Notes / follow-ups

- **Aori's admin surface is the most dangerous in the Class B batch.** The combination of pause-blocks-cancel + emergencyWithdraw-can-drain is equivalent to full custodial control by the owner.
- Not upgradeable is the only mitigating factor — owner cannot change the rules, only exercise the existing emergency powers.
- Deployed across 10 chains — verify owner address consistency across deployments
- For routing engine: flag Aori routes with high admin risk; consider whether the admin surface exceeds acceptable thresholds per DESIGN_IMPLICATIONS.md "per-route exposure analysis"
