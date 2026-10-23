---
slug: the-compact
name: The Compact
scope: The Compact V1
kind: settlement
class: B
cross_chain: false                       # a lock on one chain; cross-chain use pairs it with a settlement system
chains: [Ethereum, Base, Arbitrum, Optimism, Polygon, BNB Chain, Avalanche, Gnosis, Unichain, Sonic, Mantle]   # same 23,406-byte code at 0x00000000000000171ede64904551eeDF3C6C9788, 2026-10-06; none on Linea, Scroll, Blast
source_public: true
inherits: []
updated: 2026-10-06

verification:
  exit: source-verified
  actors: source-verified
  admin: source-verified
  data: source-verified
  judgment: source-verified
  incidents: reviewed

exit:
  custody: escrow
  execution: self                        # forcedWithdrawal
  overrides: []                          # the allocator has no say over forcedWithdrawal
  refund_trigger: timeout                # resetPeriod after enabling forced withdrawal
  exit_bound_seconds: [1, 2592000]
  exit_bound_chosen_by: depositor        # resetPeriod is fixed in the lockTag at deposit
  standing_approval: immutable_target    # ownerless, no proxy

actors: []

admin:
  upgradeable: false
  authority: none
  timelock_seconds: none
  immediate_functions: []
  grandfathered: full                    # lockTag is immutable per lock
  outside_exit_path:
    - what: Allocator, chosen per lock at deposit, co-signs claims
      effect: can withhold claims; no power over forcedWithdrawal

data_gates: []

judgment:
  screening: []
  freeze_assets: [USDC, USDT]            # any issuer-freezable token locked
  freeze_pooled: true                    # every lock of an asset is held at The Compact's address

service:
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: false
    note: "on-chain only; no off-chain service needed"
  operators: []                          # nothing off-chain is needed to deposit or to exit; claims use the allocator the sponsor chose
  screening: []
  bypass: true

integration:
  calls: ["deposit: depositNative / depositERC20 with a lockTag (allocator, scope, resetPeriod), or depositERC20ViaPermit2", "register or sign a compact for the arbiter", "the arbiter calls claim with the allocator's authorisation", "exit: enableForcedWithdrawal(id), wait resetPeriod, forcedWithdrawal(id, recipient, amount)"]
  signatures: ["EIP-712 Compact / BatchCompact / MultichainCompact by the sponsor", "allocator authorisation for claims and allocated transfers", "optional Permit2 signature for depositERC20ViaPermit2"]
  offchain_required:
    - role: allocator chosen by the sponsor, for claims and allocated transfers only; the forced withdrawal needs none
      api_key: false
      rate_limited: false
  finisher: anyone                       # the arbiter or claimant claims; the sponsor withdraws by itself
  gasless_start: none                   # depositERC20ViaPermit2 can be submitted by anyone, but only after a Permit2 approval, which is a transaction
  monitoring: "Claim, ForcedWithdrawalStatusUpdated and Transfer events, keyed by lock id"
  sdk: unknown
  testnet: true                          # Sepolia, Base Sepolia, Arbitrum Sepolia
  steps: 3

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: designated                     # the arbiter and claimant the compact names
  strike: signed
  expiry: user_chosen
  early_close: gas_same_chain            # forcedWithdrawal, after the reset period
  premium: none
  terms_fixed_by: signature
  price_set_by: user_bound
  discipline: inherited
  surplus_to: inherited
  extraction: []
  sides: inherited                       # the arbiter's settlement system sets the amounts
  rate: inherited
  quote_validity: inherited
  partial_fill: inherited
  partial_remainder: inherited

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: "depositERC20ViaPermit2 can be sent by anyone, but only after a Permit2 approval by transaction"
  - action: claim
    performer: designated
    paid: atomic
    fee: signed
    note: "the arbiter or claimant claims, paid by the claim itself"
  - action: withdraw
    performer: user
    paid: none
    gas_on: funds_chain
    note: forcedWithdrawal by the sponsor after the reset period

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: deposit
    form: self_built

incidents: []

open_questions:
  - Incident history is short (deployed 2025); revisit for empirically-observed
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: the-compact
    url: https://github.com/Uniswap/the-compact
    commit: ac25e50dbfd51358f206919e649ff79b042a5dab
    commit_date: 2025-10-14
---

# The Compact

**Primitive (one line):** ERC6909-based reusable resource lock; sponsor deposits, allocator co-signs claims against compacts, `forcedWithdrawal` provides unilateral exit after `resetPeriod`.

## Category 1 — Actor-gated edges

**Actors on exit path (for `forcedWithdrawal`):**
- None. Verified against `src/lib/WithdrawalLogic.sol` [source 3]: `_processForcedWithdrawal` requires only `msg.sender` (sponsor) and `withdrawableAt <= block.timestamp`. Allocator has no live-path power over the exit.

**Actors on claim path (not exit, but relevant to bond design):**
- Actor: Allocator
  - Legal entity: varies per allocator implementation
  - Jurisdiction: varies
  - Set size: one allocator per resource lock, registered at deposit time via `allocatorId` in `lockTag`
  - Independence: allocator addresses are chosen by sponsor at deposit
  - Source: [1] docs.uniswap.org/contracts/the-compact/reference/allocators

**Uptime / SLA:** N/A — no actor required for exit.

**Historical incidents:** none identified — protocol deployed 2025; no exit-path failure incidents reported in [1][2].

**Compellability profile:** N/A for exit path. Allocator compellability affects claim authorization only, not sponsor's ability to withdraw via forced-withdrawal path.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** none. TheCompact.sol is explicitly "ownerless" (line 33: "The Compact is an ownerless ERC6909 contract"). No proxy pattern — no `delegatecall`, no `UUPS`, no `TransparentProxy`, no `Initializable` (beyond Permit2 integration). No `Ownable`, no `Pausable`. Grep of entire `src/` for admin patterns returned zero results. Source: [3] `TheCompact.sol:33-36`, full source grep.

**Immediate-effect admin functions:** none. No `onlyOwner`, no `admin`, no `pause` functions exist anywhere in the contract. The only access control is per-resource-lock: the allocator co-signs claims, and the sponsor controls forced withdrawal. These are per-lock roles, not protocol-wide admin. Source: [3] `TheCompact.sol` full source, `WithdrawalLogic.sol`.

**Grandfathering:** the `lockTag` (bytes12) is immutable per resource lock, encoding `allocatorId`, `scope`, and `resetPeriod` (see `src/lib/IdLib.sol` [3]). Existing locks are bound to their original parameters; any protocol upgrade cannot change these for existing deposits without redeploying to a new contract.

## Category 3 — Data-oracle-gated edges

**Oracles in exit path:** none identified in `WithdrawalLogic.sol`. The only condition on `forcedWithdrawal` is `withdrawableAt <= block.timestamp`, which is a pure timestamp check against contract-stored state.

**Rate limits / circuit breakers / caps:** none identified on exit path.

**Historical trigger data:** N/A (no oracle gates identified).

## Category 4 — Judgment-oracle-gated edges

**Risk-scoring service integrations:** none identified on exit path. Requires full contract enumeration to confirm.

**Stablecoin freeze exposure:** applies to underlying tokens held. If a sponsor locks USDC, the underlying USDC held by The Compact contract is subject to Circle's freeze capability. The Compact contract's address itself could theoretically be blacklisted by an issuer, freezing all locks denominated in that asset. Source: [4] Circle USDC contract has issuer-controlled blacklist function.

**Compliance oracle dependencies:** none identified.

## Composite

**Stuck-leg failure modes:**
1. Underlying token issuer freezes The Compact contract address (Category 4) — affects only that asset's locks
2. `resetPeriod` chosen too long for sponsor's exit window at commit — self-inflicted, avoidable at deposit
3. Ethereum L1 halts (out of scope — substrate failure)

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Token issuer freeze | unbounded (depends on issuer action to unfreeze) | [4] |
| Reset period too long | bounded by chosen `resetPeriod` (max 30d per enum) | [3] IdLib.sol |
| L1 halt | protocol-independent | N/A |

**Cross-protocol correlation:** any protocol holding the same underlying token asset would be simultaneously affected by an issuer freeze. Compact-specific failure modes are minimal.

**Assets / routes most affected:** USDC and USDT locks carry issuer-freeze exposure; ETH and other permissionless assets do not.

## Sources

1. https://docs.uniswap.org/contracts/the-compact/overview — official docs — retrieved 2026-09-16
2. https://docs.uniswap.org/contracts/the-compact/reference/allocators — allocator role reference — retrieved 2026-09-16
3. https://github.com/Uniswap/the-compact — source repo; specifically `src/lib/WithdrawalLogic.sol` (functions `_enableForcedWithdrawal`, `_processForcedWithdrawal`), `src/lib/IdLib.sol` (`toSeconds`), `src/types/ResetPeriod.sol` (enum), `src/TheCompact.sol` lines 254-267 (external entry points) — cloned and read 2026-09-16
4. https://etherscan.io/address/0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48#code — USDC contract with `blacklister` role and `blacklist` function — retrieved 2026-09-16
- `eth_getCode` at 0x00000000000000171ede64904551eeDF3C6C9788 on 14 mainnets and 3 testnets, 2026-10-06

## Notes / follow-ups

- Category 2 verified: ownerless, no admin, no pause, no proxy, no upgradeability (TheCompact.sol full source read 2026-09-16)
- Category 4 confirmation: no external risk-scoring or compliance oracle calls found in claim/withdrawal paths (source grep 2026-09-16)
- No incident history to review — protocol is recent enough that empirical modeling is not yet possible; upgrade tier to `empirically-observed` once 12+ months of operation are available
- Incident search (2026-09-16): no exploits, hacks, or stuck-fund incidents found. Two independent security reviews by OpenZeppelin and Spearbit Cantina completed. Upcoming inclusion in Uniswap Labs Bug Bounty Program on Cantina.
