---
slug: cow-protocol
name: CoW Protocol
scope: CoW Protocol V2 (GPv2) settlement contracts
kind: swap
class: A
cross_chain: false
chains: [Ethereum, Gnosis, Arbitrum, Base, Polygon, Avalanche, BNB Chain, Linea, Plasma, Ink]   # orderbook /api/v1/version answered 200 on each, 2026-10-06; Sepolia too
source_public: true
inherits: []
updated: 2026-10-06

verification:
  service: partial
  exit: source-verified
  actors: source-verified
  admin: source-verified
  data: source-verified
  judgment: source-verified
  incidents: partial

exit:
  custody: user_wallet
  execution: self                        # invalidateOrder, setPreSignature(false), approve(0)
  overrides: []
  refund_trigger: expiry_or_nonce        # validTo, or invalidation by the owner
  exit_bound_seconds: 0                  # funds never leave the wallet
  standing_approval: immutable_target    # GPv2VaultRelayer is non-upgradeable

actors: []

admin:
  upgradeable: false                     # GPv2Settlement, GPv2VaultRelayer
  authority: none
  timelock_seconds: none
  immediate_functions: []
  grandfathered: full
  outside_exit_path:
    - what: GPv2AllowListAuthentication, behind an EIP-1967 proxy; its manager adds and removes solvers
      effect: decides who can fill; cannot block cancellation or change signed limits
      timelock_seconds: unknown

data_gates: []

judgment:
  screening: []
  freeze_assets: []
  freeze_pooled: false                   # tokens are held only inside a settle() transaction

service:                                 # can they decline to serve me; funds stay in the wallet either way
  operators:
    - role: Orderbook API and autopilot; accept orders and run the batch auction solvers bid in
      entity: unknown                    # copyright holders are Gnosis Ltd and Cow Service Lda; who runs api.cow.fi isn't established
      single_operator: unknown
      source_public: true                # cowprotocol/services, MIT / Apache-2.0 / GPL-3.0
      deployment_config_public: unknown  # production settings live in a separate "infra repo"
  screening:                             # owner and receiver checked at order creation, and again for every auction
    - kind: Chainalysis sanctions oracle (on-chain contract)
      where: orderbook order validation, and the autopilot's solvable orders
      in_source: true
      enabled_in_production: true        # used where the oracle is deployed: Ethereum, Arbitrum, Polygon, BSC, Avalanche, Optimism (not Base, Gnosis, Linea), read 2026-10-06
    - kind: Hermod (zeroShadow) sanctioned-address checker; addresses sent HMAC-obfuscated
      where: same
      in_source: true
      enabled_in_production: unknown     # optional config
    - kind: static banned address list
      where: same
      in_source: true
      enabled_in_production: unknown     # config
    - kind: deny-list refusal observed at the quote endpoint
      where: orderbook POST /api/v1/quote
      in_source: true
      enabled_in_production: true        # an OFAC-sanctioned address (Ronin exploiter, isSanctioned = true) got 403 "your account is deny-listed" on mainnet, Base and Gnosis; Base and Gnosis have no oracle, so Hermod or the static list is on there (2026-10-06)
  bypass: false                          # settle() is open only to allowlisted solvers, and they settle the autopilot's auction, which is built from the orderbook; a signed order outside it reaches no solver in practice
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: unknown
    note: "orderbook API answered without a key (2026-09-29)"

integration:
  calls: ["POST api.cow.fi/{network}/api/v1/quote", "sign the order (EIP-712, EIP-1271, or setPreSignature on-chain)", "POST /api/v1/orders", "GET /api/v1/orders/{uid} until traded or expired"]
  signatures: ["EIP-712 GPv2Order", "EIP-1271 for smart accounts", "or PreSign by transaction", "ERC-20 approval to GPv2VaultRelayer (or an EIP-2612 permit in a pre-hook)"]
  offchain_required:
    - role: orderbook API (quotes, order submission) and autopilot
      api_key: false                     # "No API key required for basic operations" (docs); answered without a key on 11 networks, 2026-10-06
      rate_limited: unknown
  finisher: protocol                     # allowlisted solvers settle; the user only signs
  gasless_start: [eip2612, dai_permit]   # the permit goes in the order's pre-hook; other tokens need one approval of the VaultRelayer, by transaction
  monitoring: "GET /api/v1/orders/{uid} status (open, fulfilled, cancelled, expired), or the Trade event on GPv2Settlement"
  sdk: "@cowprotocol/cow-sdk (TypeScript)"
  testnet: true                          # Sepolia orderbook answers
  steps: 3

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: allowlist
  strike: signed
  expiry: user_chosen
  early_close: free_offchain             # off-chain cancel through the API, or invalidateOrder with gas
  premium: none
  terms_fixed_by: signature
  price_set_by: auction
  discipline: allowlist_competition
  surplus_to: user
  extraction: []
  sides: [exact_in, exact_out]           # sell and buy orders (GPv2Order KIND_SELL, KIND_BUY)
  rate: floating_above_bound             # fills at or better than the signed limit; surplus goes to the user
  quote_validity: 120                    # a live quote on 2026-10-07 expired 2 minutes after issue; the order's validTo defaulted to 30 minutes
  partial_fill: user_signed              # only if the signed order sets partiallyFillable; the rest stays open until validTo
  partial_remainder: stays_open

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: designated
    paid: atomic
    fee: signed
    note: an allowlisted solver settles; a permit in the order's pre-hook replaces the approval; the solver is paid from the order within the limit price the user signed
  - action: cancel
    performer: none
    paid: none
    note: "nothing to do: the order expires at validTo"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: order
    form: typed_data
    note: "EIP-712 GPv2Order"

incidents:
  - date: 2023-02-07
    duration: under 24h
    user_funds_lost: false
    exits_blocked: false
    cause: Newly allowlisted Barter solver's SwapGuard contract drained ~$166K of accumulated protocol fees; its bond was slashed (CIP-22)

open_questions:
  - Who operates the orderbook API and autopilot, and whether anyone else runs one solvers would use
  - "Which of Hermod and the static banned list is on (one of them is: the deny-list applies on Base and Gnosis, which have no oracle), and whether the infra repo is public"
  - Which chains have the Chainalysis oracle deployed
  - Authenticator proxy admin identity, and whether it sits behind a timelock (0x2c4c28DDBdAc9C5E7055b4C863b72eA0149D8aFE)
  - Current authenticator manager address
  - Incidents in the last 12 months not yet searched
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: cow-contracts
    url: https://github.com/cowprotocol/contracts
    commit: c07a93e3596194c5e3cf331c755a3f9f0e4a17d8
    commit_date: 2026-09-01
  - repo: cow-services
    url: https://github.com/cowprotocol/services
    commit: 84eed3be324ece58ec27ac89d27d4f54efd975f6
    commit_date: 2026-09-28
---

# CoW Protocol

**Primitive (one line):** User signs EIP-712 order off-chain; funds stay in wallet (or Balancer Vault internal balance); authorized solvers call `settle()` on GPv2Settlement which pulls input tokens via VaultRelayer and delivers output tokens atomically in a single transaction.

## Category 1 — Actor-gated edges

**Actors on exit path:** none. Funds never leave the user's wallet until settlement. There is no exit path because there is no deposit.

**Cancellation mechanisms (user-controlled):**
- On-chain invalidation: `invalidateOrder(bytes calldata orderUid)` on GPv2Settlement — sets `filledAmount[orderUid] = type(uint256).max`, permanently preventing fill. Only callable by order owner (`require(owner == msg.sender)`). Not gated by authenticator or solver status. Immediate, permissionless for owner. Source: [3] `GPv2Settlement.sol:250-255`
- Pre-signature revocation: `setPreSignature(orderUid, false)` on GPv2Settlement — revokes a pre-signed order. Only callable by order owner. Source: [3] `GPv2Signing.sol:88-97`
- ERC20 approval revocation: user can `approve(0)` the VaultRelayer or Settlement contract at any time, preventing token pulls
- Off-chain: simply don't broadcast the signed order to solvers

**Expiry:** `validTo` field (uint32 timestamp) in order struct. Enforced in `computeTradeExecution`: `require(order.validTo >= block.timestamp, "GPv2: order expired")`. Source: [3] `GPv2Settlement.sol:349`, `GPv2Order.sol:12-24`

**Actors involved in filling (not exit):**
- Actor: Solver
  - Role: calls `settle()` to execute batched trades. Must be on allowlist checked via `authenticator.isSolver(msg.sender)`.
  - Legal entity: multiple independent solver teams participate in the solver auction
  - Jurisdiction: varies per solver
  - Set size: allowlisted set, managed by CoW DAO via the authenticator contract manager
  - Independence: multiple independent operators
  - Source: [3] `GPv2Settlement.sol:87-90` (`onlySolver` modifier)
- Actor: Authenticator manager
  - Role: adds/removes solvers from allowlist
  - Legal entity: CoW DAO (governance-controlled)
  - Source: [3] `GPv2AllowListAuthentication.sol:86-100`

**Uptime / SLA:** N/A — no actor required for exit.

**Historical incidents:**
- Date: 2023-02-07, Duration: resolved within 24h, Cause: Barter Solver exploit — a newly whitelisted solver ("The Barter Solver") approved a malicious SwapGuard contract that drained ~$166K (551 BNB) in accumulated protocol fees from the settlement contract. **User funds were NOT at risk** — only protocol fee accruals were taken. The solver bonding pool mechanism (CIP-7, $500K cUSDC + 1.5M COW collateral) was used to recover losses; Barter solver bond was slashed the next day. CoW DAO governance proposal CIP-22 formalized the slashing. Root cause: solver's SwapGuard contract had a public arbitrary-call function. Source: [5] CoW Protocol post-mortem, [6] CIP-22 slashing proposal
- No user fund losses or exit-path failures identified. The exploit validates the settlement contract's design — immutable limit price enforcement meant user trade execution was never compromised, only accumulated fees were at risk.

**Compellability profile:** N/A for exit path. Solver allowlist manager (CoW DAO) and proxy admin are governance-controlled. Individual solvers declining to fill does not create stuck-leg conditions.

## Category 2 — Modification-gated edges (in-window effect)

**GPv2Settlement contract:**
- Who: no admin, no owner. Contract is non-upgradeable.
- `authenticator`, `vault`, `vaultRelayer` are all `immutable`.
- No `onlyOwner` or admin functions on the settlement contract itself.
- Source: [3] `GPv2Settlement.sol:32-39` (immutable declarations), constructor at line 73-77

**GPv2VaultRelayer contract:**
- Who: non-upgradeable. `creator` is `immutable` (= GPv2Settlement address).
- Only function callable externally: `transferFromAccounts` and `batchSwapWithFee`, both `onlyCreator` (Settlement only).
- No admin surface.
- Source: [3] `GPv2VaultRelayer.sol:17-22`

**GPv2AllowListAuthentication contract (upgradeable):**
- Who: behind EIP-1967 proxy. Proxy admin can upgrade implementation and call `setManager`. Manager can `addSolver`/`removeSolver`.
- Proxy admin: stored at EIP-1967 admin slot. Identity is CoW DAO-controlled (verify on-chain at 0x2c4c28DDBdAc9C5E7055b4C863b72eA0149D8aFE).
- Timelock: unknown — requires checking whether proxy admin is behind a timelock or is a direct multisig/DAO.
- Source: [3] `GPv2AllowListAuthentication.sol:11-108`, `GPv2EIP1967.sol:4-33`

**Immediate-effect admin functions:**
- Function: `addSolver(address)` / `removeSolver(address)`, Caller: manager, Effect: immediately changes which addresses can call `settle()`. Does not affect in-flight signed orders directly — orders remain valid and cancellable regardless. Source: [3] `GPv2AllowListAuthentication.sol:86-100`
- Function: `setManager(address)`, Caller: manager or proxy admin, Effect: changes who controls solver allowlist. Source: [3] `GPv2AllowListAuthentication.sol:74-78`
- Function: proxy upgrade (EIP-1967), Caller: proxy admin, Effect: replaces authenticator implementation entirely. Could theoretically change `isSolver()` logic. Source: [3] `GPv2EIP1967.sol`

**Impact analysis of authenticator compromise:**
Even if the authenticator is fully compromised (upgraded to malicious code or all solvers replaced):
- Settlement contract enforces limit prices immutably (`order.sellAmount.mul(sellPrice) >= order.buyAmount.mul(buyPrice)` — [3] `GPv2Settlement.sol:368-371`)
- Signature verification is immutable in Settlement
- `invalidateOrder` is NOT gated by authenticator — user can always cancel
- `validTo` expiry is enforced immutably in Settlement
- Interactions explicitly cannot target VaultRelayer (`require(interaction.target != address(vaultRelayer), "GPv2: forbidden interaction")` — [3] `GPv2Settlement.sol:453-456`)
- Worst case: rogue solver fills at limit price when better execution was available (MEV extraction bounded by limit-price spread, not fund theft)

**Grandfathering:** N/A — no in-flight state. Each settlement is atomic. Authenticator changes take effect on the next `settle()` call but cannot retroactively affect signed orders.

## Category 3 — Data-oracle-gated edges

**Oracles in exit path:** none.

**Oracles in fill path:** none. Clearing prices are set by the solver in the `settle()` calldata, not read from external oracles. Limit price enforcement is pure arithmetic against signed order parameters. Source: [3] `GPv2Settlement.sol:121-143`

**Rate limits / circuit breakers / caps:** none on settlement contracts.

**Historical trigger data:** N/A (no oracle gates).

## Category 4 — Judgment-oracle-gated edges

**Risk-scoring service integrations:** none identified in protocol contracts. Individual solvers may apply compliance filters; this is voluntary and out-of-scope (solver declining to include an order ≠ stuck leg).

**Stablecoin freeze exposure:** minimal. Settlement contract holds tokens only transiently during `settle()` execution (single tx, atomic). However:
- Users maintain outstanding ERC20 approvals to VaultRelayer address (0xC92E8bdf79f0507f65a392b0ab4667716BFE0110). A stablecoin issuer freezing the VaultRelayer address would cause all fills to revert for that token, but user funds remain in wallet and approvals are revocable.
- Accumulated fees held in the Settlement contract (solver fees) could be frozen if the Settlement address is blacklisted.
- Source: [3] `GPv2Settlement.sol:99-143` (fee accumulation in settlement)

**Compliance oracle dependencies:** none identified.

## Composite

**Stuck-leg failure modes:**
1. Order not filled before `validTo` — user retains all funds in wallet. Not a stuck-leg event.
2. All solvers removed from allowlist or authenticator upgraded maliciously — orders simply don't get filled, user retains funds. Not a stuck-leg event.
3. Stablecoin issuer freezes user's wallet — protocol-independent.
4. Rogue solver fills at limit price when better execution was available — bounded value extraction, not stuck-leg.

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Order unfilled | instant (funds never left wallet) | [3] Class A architecture |
| Solver unavailability | instant (funds never left wallet) | [3] |
| Authenticator compromise | instant for exit (cancel/revoke); fill quality degraded | [3] immutable settlement limits |
| Wallet-level freeze | unbounded (issuer-dependent) | protocol-independent |

**Cross-protocol correlation:** none protocol-specific. Balancer Vault dependency exists for users using Vault internal balances — a Balancer Vault issue would affect those users but not users using direct ERC20 approvals. CoW Swap has integration with multiple other DEXes via solver routing, but these are fill-side dependencies only.

**Assets / routes most affected:** none. Class A architecture means no asset-specific stuck-leg exposure.

## Sources

1. https://docs.cow.fi/cow-protocol/concepts/how-it-works — CoW Protocol concepts — retrieved 2026-09-16
2. https://docs.cow.fi/cow-protocol/reference/contracts/core — core contracts reference, deployed addresses, security notes — retrieved 2026-09-16
3. https://github.com/cowprotocol/contracts — source repo; specifically:
   - `src/contracts/GPv2Settlement.sol` — settlement logic, onlySolver, invalidateOrder, trade computation, interaction restrictions (lines 21-488)
   - `src/contracts/GPv2AllowListAuthentication.sol` — upgradeable solver allowlist, manager/owner roles (lines 11-108)
   - `src/contracts/GPv2VaultRelayer.sol` — immutable relayer, onlyCreator token pulling (lines 11-85)
   - `src/contracts/mixins/GPv2Signing.sol` — signature schemes (EIP-712, EthSign, EIP-1271, PreSign), pre-signature management (lines 10-335)
   - `src/contracts/libraries/GPv2Order.sol` — order struct (validTo, sellAmount, buyAmount, kind), UID encoding (lines 8-243)
   - `src/contracts/libraries/GPv2EIP1967.sol` — EIP-1967 admin slot access (lines 4-33)
   — cloned and read 2026-09-16

5. https://blog.cow.fi/cow-swap-solver-exploit-post-mortem-07-02-2023-2faa9f918e29 — Barter Solver exploit post-mortem — retrieved 2026-09-16
6. https://forum.cow.fi/t/cip-22-slashing-of-the-barter-solver-responsible-for-a-hack-causing-cow-dao-a-loss-of-1-week-fee-accrual/1440 — CIP-22 slashing proposal — retrieved 2026-09-16
7. https://github.com/cowprotocol/services (`source/cow-services`) — `crates/configs/src/banned_users.rs:15-60`, `crates/shared/src/order_validation.rs:760-770`, `crates/autopilot/src/run.rs:466-487`, `crates/autopilot/src/solvable_orders.rs:441-512`, `crates/order-validation/src/banned/mod.rs`, `banned/cached.rs:20` — read 2026-09-28
- https://docs.cow.fi/cow-protocol/integrate/api ("No API key required for basic operations") and `GET api.cow.fi/{network}/api/v1/version` on 11 networks, 2026-10-06
- Censorship test, 2026-10-06: `POST api.cow.fi/{mainnet,base,xdai}/api/v1/quote` with `from` = 0x098B716B…2f96 (Ronin exploiter, `isSanctioned` true on the Chainalysis oracle 0x40C57923…8fb) returned 403 "Forbidden, your account is deny-listed" on all three; the same request from an unflagged address returned a quote. Oracle code read on nine chains.

## Notes / follow-ups

- Verify authenticator proxy admin identity and whether it's behind a timelock — check on-chain at 0x2c4c28DDBdAc9C5E7055b4C863b72eA0149D8aFE
- Verify current manager address on the authenticator contract
- Review CoW DAO governance process for solver allowlist changes
- EIP-1271 signature replay risk across Safe wallets (noted in CoW security docs) — relevant to fill-path correctness but not to exit-path/stuck-leg analysis
- CoW Protocol is expanding cross-chain via CoW Hooks and cross-chain intents — if/when that launches, it would need a separate entry as the custody model may differ
- Accumulated fees in the Settlement contract could be a target for stablecoin issuer freeze — quantify typical fee balance if relevant
