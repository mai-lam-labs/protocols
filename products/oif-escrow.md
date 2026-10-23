---
slug: oif-escrow
name: OIF Escrow Settler
framework: true                          # a framework: each deployment picks its oracle, settlers and order server; LI.FI Intent is one deployment
scope: Open Intents Framework reference contracts, InputSettlerEscrow and OutputSettlerSimple, and the oracles in oif-contracts; the reference deployment at 0x1CC9260E... / 0x52602D7c... LI.FI's production deployment is in lifi-intent
kind: settlement
class: B
cross_chain: true
chains: [Ethereum, Arbitrum, Base, Optimism, Linea, Scroll, zkSync Era, Katana, BSC, Polygon]   # per DEPLOYMENTS.md; not checked on-chain
source_public: true
inherits: []
updated: 2026-10-04

verification:
  service: source-verified               # no off-chain service in the framework
  exit: source-verified                  # refund, finalise, _validateFills, _resolveLock read
  actors: source-verified
  admin: partial                         # no owner or proxy in source; the reference deployment's bytecode wasn't compared
  data: source-verified
  judgment: source-verified
  incidents: not-reviewed

exit:
  custody: escrow                        # InputSettlerEscrow holds every open order's inputs
  execution: self                        # refund(order) after expires has no caller check and pays order.user
  overrides:
    - who: whoever controls the oracle named in the order (inputOracle); per order, chosen by the order's creator
      needs: depends on the oracle; Polymer is one sequencer key (see lifi-intent), Wormhole a guardian quorum, Hyperlane the receiving ISM, Bitcoin a PoW light client
      how: attest a fill that didn't happen; finalise then pays the inputs to the forger, and refund() reverts. Works while the order is still deposited, including after expires
      reach: one
      bounded: false
      cost: depends on the oracle
  refund_trigger: timeout                # refund() once block.timestamp > expires
  exit_bound_seconds: unknown            # expires is a uint32 in the signed order with no cap in the contract; there's no reference order flow to measure
  exit_bound_chosen_by: order creator
  standing_approval: immutable_target    # approve or Permit2 to the escrow, which isn't upgradeable; ERC-3009 needs no approval

actors: []                               # refund() needs no one but a caller, who can be the depositor

admin:
  upgradeable: false                     # no proxy, no delegatecall, no initializer
  authority: none                        # no owner on the escrow or output settler; ChainMap (oracle chain-id map) is Ownable but each entry is set once
  timelock_seconds: none
  immediate_functions: []
  grandfathered: full                    # nothing mutable reaches an open order
  outside_exit_path:
    - what: ChainMap / *OracleMapped chain-id mapping
      effect: maps chain ids for oracles; one-time per chain (AlreadySet), so it can't be changed after use
      caller: mapping owner

data_gates: []                           # refund() checks only block.timestamp > expires, which is the exit bound itself

judgment:
  screening: []
  freeze_assets: unknown                 # any ERC-20; depends on the orders
  freeze_pooled: true                    # every open order's inputs sit at the one escrow address

service:
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: false
    note: "contracts only; order distribution and solvers are up to whoever deploys or uses them"
  operators: []
  screening: []
  bypass: true

integration:
  calls: ["open(StandardOrder) after approve, or openFor(order, sponsor, sig)", "solver: OutputSettlerSimple.fill on the destination, oracle relay, finalise on the origin", "refund(order) after expires if still deposited"]
  signatures: ["Permit2 witness transfer (prefix 0x00) or ERC-3009 receiveWithAuthorization (prefix 0x01) for openFor"]
  offchain_required:
    - role: order distribution to solvers; the framework has none of its own
      api_key: unknown
      rate_limited: unknown
  finisher: anyone
  gasless_start: [permit2_approved, eip3009] # openFor can be submitted by anyone
  monitoring: "Open / OutputFilled / Finalised / Refunded events keyed by orderId"
  sdk: unknown
  testnet: true                          # DEPLOYMENTS.md lists ten testnets
  steps: 3

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: unknown                        # the deployment's choice
  strike: signed
  expiry: unknown
  early_close: none
  premium: none
  terms_fixed_by: signature
  price_set_by: unknown
  discipline: unknown
  surplus_to: unknown
  extraction: unknown
  sides: unknown
  rate: firm                             # limit and exclusive-limit outputs pay exactly the signed amount; Dutch types decay (OutputSettlerSimple._resolveOutput)
  quote_validity: unknown
  partial_fill: none                     # the output settler pays the exact output and the escrow releases the whole input
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: anyone
    paid: deferred
    note: "openFor with an EIP-3009 authorisation, submitted by anyone; the solver is paid only when the order is finalised later"
  - action: refund
    performer: user
    paid: none
    gas_on: funds_chain
    note: refund(order) after expires has no caller check but pays its caller nothing

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: order
    form: self_built

incidents: []                            # not reviewed

open_questions:
  - "Trade: holder, expiry, price_set_by, discipline, surplus_to, extraction (CRITERIA.md, Trade)"
  - "Quote: sides, quote_validity (CRITERIA.md, Trade); these decide which quote modes (exact, atleast, upto) the venue can serve, and who decides a partial fill"
  - Whether anyone routes orders to the reference deployment 0x1CC9260E...; none of 400 LI.FI orders did
  - Trust in each shipped oracle (Hyperlane, Wormhole, Bitcoin/Citrea, Broadcaster) at the level done for Polymer in lifi-intent
  - Whether the deployed bytecode at the reference addresses matches the pinned source
  - Incident history
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: oif-contracts
    url: https://github.com/openintentsframework/oif-contracts
    commit: 8e38b9bb0e4467a154b1e95b7b6d995ad3a9e518
    commit_date: 2026-08-20
---

# OIF Escrow Settler

**Primitive (one line):** User deposits input tokens into `InputSettlerEscrow` via `open()`; solver fills outputs on destination chain and proves via modular oracle; solver calls `finalise()` to claim escrowed inputs; if unfinalised after `order.expires`, anyone can call `refund()` to return tokens to user.
**Product scope of this entry:** Open Intents Framework escrow settler (cross-chain intent settlement)

## Category 1 — Actor-gated edges

**Actors on exit path (refund):**
- None required. `refund()` is callable by **anyone** (`external`, no access control) after `order.expires`. Tokens always return to `order.user`. Source: [3] `InputSettlerEscrow.sol:408-417`

**Refund and finalise race.** `finalise()` has no expiry guard (NatSpec: "Finalise is not blocked after the expiry of orders"). After `expires`, whichever of `refund()` and `finalise()` runs first wins, through `_resolveLock`. Source: [3] `InputSettlerEscrow.sol:408-466`

This doesn't cost the user anything when the oracle is honest. `finalise` still runs `_validateFills`, which needs every output proven filled through the order's oracle and rejects fills after `fillDeadline` (`FilledTooLate`). A late `finalise` therefore means the user received the outputs before `fillDeadline`. (Corrected 2026-10-04: the earlier version of this entry called the race the key risk, as if the user could lose inputs without being paid.)

What the race does mean is that a **dishonest oracle** keeps its window open after `expires` until someone calls `refund()`. See "Oracles" below.

**Cancellation mechanisms:**
- No pre-expiry cancellation exists. Once deposited, the order can only be resolved by `finalise()` (solver claims) or `refund()` (after expiry). Source: [3] state machine at line 88-93

**Expiry:** `expires` field (uint32 Unix timestamp), user-specified at deposit time. Must be >= `fillDeadline`. Both enforced at deposit: `_validateFillDeadlineBeforeExpiry`. Source: [3] `StandardOrderType.sol:6-15`, `InputSettlerBase.sol:109-113`, `InputSettlerEscrow.sol:147`

**Actors involved in happy path:**
- Actor: Solver/Filler
  - Role: fills outputs on destination chain, proves fills via oracle, calls `finalise()` to claim inputs
  - Set size: permissionless — anyone can fill
  - Source: [3] `InputSettlerEscrow.sol:448-466`
- Actor: Oracle (modular, user-chosen)
  - Role: proves cross-chain fills. Called via `IInputOracle.efficientRequireProven()` during finalization.
  - Options: Hyperlane, Polymer, Wormhole, Bitcoin, Broadcaster
  - Source: [3] oracle implementations in `src/oracles/`
- Actor: Purchaser (optional)
  - Role: can buy a solver's right to claim inputs via `purchaseOrder()` — capital rotation mechanism
  - Source: [3] `InputSettlerPurchase.sol`

**Uptime / SLA:** oracle liveness affects finalization (solver claiming) but NOT refund — refund only requires `block.timestamp > order.expires`.

**Compellability profile:** no compellable actors on refund path. Oracle is user-chosen and varies.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** none. No proxy, no UUPS, no `delegatecall`, no `initializer`. Deployed via CREATE2 at deterministic addresses across chains. Source: [3] full source review, DEPLOYMENTS.md

**Immediate-effect admin functions:** none on escrow or output settler contracts. The only `Ownable` pattern in the codebase is `ChainMap.sol` (oracle chain ID mapping helper) — one-time-set per chain, reverts with `AlreadySet` if already mapped. Does not affect escrow. Source: [3] `ChainMap.sol:45-59`

**Grandfathering:** N/A — each order is independent. No protocol-wide parameter changes can affect existing deposits.

## Category 3 — Data-oracle-gated edges

**Oracles in exit path (refund):** none. `refund()` only checks `block.timestamp > order.expires` and `status == Deposited`. No oracle consulted. Source: [3] `InputSettlerEscrow.sol:408-417`

**Oracles in finalization path (solver claims):** yes — modular, user-chosen oracle validates cross-chain fills. If oracle is unavailable, solver cannot finalize, but user can still refund after expiry. Source: [3] oracle integration in finalise path

**Oracles are the override.** Whoever can make the order's oracle attest a fill that didn't happen can finalise the order and take the inputs. The user's own refund then reverts. The order fixes the oracle (`inputOracle`, `outputs[].oracle`), so this risk is chosen per order. LI.FI's production orders use Polymer, whose `CrossL2ProverV2` accepts a state root signed by one sequencer key (see [lifi-intent.md](lifi-intent.md)). The other shipped oracles (Hyperlane, Wormhole, Bitcoin/Citrea, Broadcaster) have not been reviewed to that depth.

**Rate limits / circuit breakers:** none.

## Category 4 — Judgment-oracle-gated edges

**Risk-scoring service integrations:** none identified.

**Stablecoin freeze exposure:** InputSettlerEscrow holds user deposits. If the escrow contract address (0x1CC9260E285C2C8AC8D2E7102F3978056Ec1d0a8) is frozen by a stablecoin issuer, all escrowed funds in that asset are stuck. This is a real risk for USDC/USDT flows.

**Compliance oracle dependencies:** none.

## Composite

**Stuck-leg failure modes:**
1. Solver fills destination but fails to prove or finalize before user calls refund — solver loses; user gets refund. Not a user stuck-leg.
2. Solver finalizes after expiry before anyone calls refund. With an honest oracle the user already got the outputs, since fills must land before `fillDeadline`. With a dishonest oracle, this is how the inputs are taken. Calling `refund()` promptly at `expires` closes the window.
3. Oracle unavailable — solver cannot finalize; user can refund after expiry. Bounded.
4. Stablecoin issuer freezes escrow address — all deposits in that asset stuck. Unbounded.
5. Nobody calls refund after expiry — tokens sit in escrow until either refund or finalise is called. No automatic unwinding.

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Normal refund after expiry | bounded by `order.expires` (user-set) | [3] |
| Post-expiry finalise race | none with an honest oracle (the outputs were delivered); with a dishonest oracle, until refund is called | [3] NatSpec, `_validateFills` |
| Oracle unavailable | bounded by `order.expires` + refund call | [3] |
| Stablecoin freeze on escrow | unbounded | issuer-dependent |

**Cross-protocol correlation:** oracle-dependent. All orders using the same oracle (e.g., Hyperlane) fail together if that oracle fails. But refund path is oracle-independent.

## Sources

1. https://docs.hyperlane.xyz/docs/protocol/intents/overview — OIF documentation (returned 404; spec read from repo instead) — attempted 2026-09-16
2. `source/oif-contracts/audits/` — two OpenZeppelin audits (October 2025, May 2026)
3. https://github.com/openintentsframework/oif-contracts — source repo; specifically:
   - `src/input/escrow/InputSettlerEscrow.sol` — escrow logic, open/finalise/refund, state machine (lines 88-93, 140-163, 408-417, 448-466)
   - `src/input/InputSettlerBase.sol` — validation helpers, expiry checks (lines 98-113)
   - `src/input/types/StandardOrderType.sol` — order struct (fillDeadline, expires) (lines 6-15)
   - `src/output/simple/OutputSettlerSimple.sol` — output settlement
   - `src/oracles/ChainMap.sol` — only Ownable contract in codebase (one-time-set)
   - `DEPLOYMENTS.md` — deterministic CREATE2 addresses
   — cloned and read 2026-09-16

## Notes / follow-ups

- **The oracle in the order is the most important choice.** Calling `refund()` promptly after `expires` limits how long a dishonest oracle has, but it can't stop one before `expires`.
- The modular oracle design means per-order oracle risk varies — routing engine should evaluate oracle choice per order
- `purchaseOrder()` mechanism (solver underwriting) could be relevant for capital efficiency analysis
- Verify whether any frontend/SDK auto-calls refund after expiry
