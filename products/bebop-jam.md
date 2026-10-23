---
slug: bebop-jam
name: Bebop Aggregation API (JAM)
scope: Bebop's Aggregation API (formerly marketed as JAM; the endpoint is still /jam/{network}/v2/quote) and its contracts JamSettlement 0xbeb0b0623f66bE8cE162EbDfA2ec543A522F4ea6 and JamBalanceManager 0xC5a350853E4e36b73EB0C24aaA4b8816C9A3579a, same-chain (zkSync Era uses other addresses)
kind: swap
class: A
cross_chain: false
chains: [Ethereum, Arbitrum, Base]       # same address and code on these three (2026-10-04); others not checked
source_public: true                      # bebop-jam-contracts is public now; deployed code verified on Blockscout
inherits: [permit2]
updated: 2026-10-04

verification:
  service: partial                       # authentication and approvals from docs.bebop.xyz (2026-10-06)
  exit: source-verified                  # verified source on Blockscout; no owner, proxy or pause
  actors: source-verified
  admin: source-verified                 # code and ERC-1967 slot read on Ethereum, Arbitrum, Base
  data: source-verified
  judgment: partial                      # API-side screening not reviewed
  incidents: partial

exit:
  custody: user_wallet                   # settlement is one atomic transaction; nothing is held
  execution: self                        # don't sign, let expiry pass, or cancelLimitOrder(nonce) for a limit order
  overrides: []
  refund_trigger: expiry_or_nonce
  exit_bound_seconds: 0
  exit_bound_chosen_by: none
  standing_approval: immutable_target    # JamBalanceManager (only caller: the settlement, immutable) or Permit2

actors: []

admin:
  upgradeable: false
  authority: none                        # no owner or admin in the verified source
  timelock_seconds: none
  immediate_functions: []
  grandfathered: full
  outside_exit_path: []

data_gates: []

judgment:
  screening: []                          # none in the contracts; the API may refuse quotes
  freeze_assets: []
  freeze_pooled: false

service:
  integrator_access:
    api_key: true                        # production needs a key; without one, quotes are demo-mode (widened, heavily rate limited)
    identity: signup                     # keys are requested through Bebop support and provisioned by the team
    revocable: unknown                   # Bebop issues and rotates keys; revoking one integrator isn't documented
    rate_limited: true                   # per key
  operators:
    - role: JAM API and solvers (quotes, routing, submission)
      entity: Bebop
      single_operator: true
      source_public: false
      deployment_config_public: false
  screening: unknown
  bypass: false                          # orders need a counterparty signature obtained through the API

integration:
  calls: ["GET /jam/{network}/v2/quote with the API key", "sign the JamOrder (Permit2 batch or approval to JamBalanceManager)", "the solver or user submits settle"]
  signatures: ["EIP-712 JamOrder, or a Permit2 PermitBatchTransferFrom bound to it"]
  offchain_required:
    - role: Bebop API
      api_key: true
      rate_limited: true
  finisher: user
  gasless_start: unknown                 # disputed: whether gasless mode works for a token not yet approved to JamBalanceManager; see open_questions
  monitoring: "transaction receipt, or the Bebop order status endpoint"
  sdk: "Bebop Python SDK; TypeScript examples"
  testnet: unknown
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: counterparty_writes         # the solver's quote; the user signs it and the solver or user submits
  holder: exclusive                      # JamOrder.executor alone may settle until exclusivityDeadline, then anyone (JamValidation.sol:138)
  strike: quoted
  expiry: api_chosen                     # JamOrder.expiry, from the quote, signed by the user
  early_close: free
  premium: none
  terms_fixed_by: signature
  price_set_by: quote
  discipline: unknown
  surplus_to: holder                     # the executor chooses filledAmounts at or above the signed floor
  extraction: [exclusive_window]
  sides: [exact_in]                      # sellAmounts fixed; buyAmounts are a floor (validateFilledAmounts: filled >= signed)
  rate: floating_above_bound             # the executor chooses filledAmounts at or above the signed buyAmounts
  quote_validity: unknown
  partial_fill: none                     # settle always transfers the full sellAmounts
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: designated
    paid: unknown
    fee: signed
    note: the solver or Bebop submits settle in gasless mode and is paid from the trade; whether this works without a prior approval transaction is disputed (open question)
  - action: cancel
    performer: none
    paid: none
    note: "nothing to do: the order expires; cancelLimitOrder is only for limit orders"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: JAM order
    form: typed_data
    note: "EIP-712 JamOrder; executorFeesHash-style bindings in the order"

incidents: []

open_questions:
  - "Trade: discipline (CRITERIA.md, Trade)"
  - "Quote: quote_validity (CRITERIA.md, Trade); these decide which quote modes (exact, atleast, upto) the venue can serve, and who decides a partial fill"
  - "Paid execution, start step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - "Whether gasless mode starts from an account holding no gas for a token not yet approved to JamBalanceManager: does the API accept an EIP-2612 permit or Permit2 signature in the taker permits for a fresh token? Settled by a live gasless quote and order for a permit token from a zero-balance account"
  - Whether the Aggregation API screens takers
  - Whether Bebop can revoke a single integrator's key
  - Whether the deployed code matches bebop-jam-contracts at the pinned commit (the repo is a year older than some deployments)
sources:
  - repo: bebop-jam-contracts
    url: https://github.com/bebop-dex/bebop-jam-contracts
    commit: d12ec63e99e671ccfd74a7883ea8b1f9ac22493f
    commit_date: 2025-06-26
---

# Bebop JAM

**Primitive (one line):** User requests quote from solvers via Aggregation API; solver finds optimal route across DEX liquidity; user signs and broadcasts settlement transaction; JamSettlement contract verifies signatures, enforces minimums, and transfers tokens atomically.
**Product scope of this entry:** Bebop JAM / Aggregation API + JamSettlement contract (same-chain only)

## Category 1 — Actor-gated edges

**Actors on exit path:** none. Same custody model as Bebop RFQ — "Bebop never takes custody of user tokens" [1]. Atomic settlement. No deposit, no escrow.

**Cancellation mechanisms:**
- Off-chain: do not broadcast the settlement transaction
- On-chain: unknown — source not public
- ERC20 approval revocation: user revokes approval to Balance Manager / `approvalTarget` (0xC5a350853E4e36b73EB0C24aaA4b8816C9A3579a). Note: approving JamSettlement directly instead of Balance Manager causes fund loss per docs [3].

**Expiry:** unknown — requires source verification.

**Actors involved in filling (not exit):**
- Actor: Solvers
  - Role: algorithmic agents that find optimal execution paths across DEX liquidity. Compete to provide best pricing.
  - Legal entity: multiple independent solver operators
  - Set size: multiple
  - Independence: independent operators
  - Source: [1]

**Uptime / SLA:** N/A — no actor required for exit.

**Historical incidents:** no exit-path incidents possible by construction. Source: [1][2]

**Compellability profile:** N/A for exit path.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** none. The source is now public (bebop-dex/bebop-jam-contracts), and the verified code at both addresses has no owner, proxy or pause. Dual-contract architecture (Balance Manager at 0xC5a350853E4e36b73EB0C24aaA4b8816C9A3579a + JamSettlement at 0xbeb0b0623f66bE8cE162EbDfA2ec543A522F4ea6) requires Etherscan verification for proxy patterns.

**Immediate-effect admin functions:** unknown — requires source read.

**Grandfathering:** N/A — no in-flight state (atomic settlement).

## Category 3 — Data-oracle-gated edges

**Oracles in exit path:** none (no deposit).

**Rate limits / circuit breakers / caps:** unknown.

**Historical trigger data:** N/A.

## Category 4 — Judgment-oracle-gated edges

**Risk-scoring service integrations:** unknown.

**Stablecoin freeze exposure:** minimal — no persistent contract balances (atomic settlement). However, the Balance Manager contract holds token approvals — if this address is frozen by a stablecoin issuer, all JAM trades for that asset would revert, but user funds remain in wallet.

**Compliance oracle dependencies:** unknown.

## Composite

**Stuck-leg failure modes:**
1. Solver declines to route or quote — user retains funds. Not stuck-leg.
2. Settlement reverts — atomic, user retains funds. Not stuck-leg.
3. Balance Manager address frozen by stablecoin issuer — fills revert, funds stay in wallet. Not stuck-leg.

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Order unfilled | instant (funds never left wallet) | [1] Class A |
| Settlement revert | instant (atomic) | [2] |

**Cross-protocol correlation:** none protocol-specific.

**Assets / routes most affected:** none. Class A.

## Naming (2026-10-06)

Bebop's current docs don't use the name "JAM" for a product. Solver-routed trades are the **Aggregation API**. It still settles through `JamSettlement` and approves `JamBalanceManager` at the addresses above, on every supported EVM chain except zkSync Era, and its quote endpoint is `GET /jam/{network}/v2/quote`. So the product was renamed, not deprecated. The JAM contracts are what the Aggregation API uses today. Source: docs.bebop.xyz `core-concepts/settlement-smart-contracts`, `aggregation-api/introduction`, retrieved 2026-10-06.

**Approval warning (docs):** takers must approve the balance manager, not the settlement contract. "Approving the settlement contract will lead to loss of funds."

## Source and on-chain state (2026-10-04)

- **Source:** `bebop-dex/bebop-jam-contracts` is public now.
  - `JamBalanceManager` has one immutable `operator`, the settlement, set in the constructor. It pulls from takers only inside `settle`, by approval or Permit2.
  - `JamSettlement` checks `expiry` and nonces. Limit orders can be cancelled with `cancelLimitOrder(nonce)` (`base/JamValidation.sol:110`).
  - Neither contract has an owner, pause or upgrade path.
- **Deployed code:** both are verified on Blockscout as `JamSettlement` and `JamBalanceManager` (solc 0.8.27). They have the same code size at the same addresses on Ethereum, Arbitrum and Base, and no ERC-1967 implementation.

## Sources

1. https://docs.bebop.xyz/how-bebop-works — architecture overview — retrieved 2026-09-16
2. https://docs.bebop.xyz/core-concepts/settlement-smart-contracts — contract addresses, dual-contract architecture — retrieved 2026-09-16
3. https://docs.bebop.xyz/core-concepts/token-approvals — approval target warning for JAM — retrieved 2026-09-16
4. https://docs.bebop.xyz/audits — audit history — retrieved 2026-09-16

## Notes / follow-ups

- All same follow-ups as bebop-rfq — source is private, Cat 2 unknowns
- The separation of Balance Manager from JamSettlement is an interesting design choice — verify whether Balance Manager has any admin/owner functions
- JAM's solver routing means on-chain execution path varies per trade (routing through Uniswap, Curve, etc.) — this doesn't affect custody model but does affect gas cost and MEV exposure
