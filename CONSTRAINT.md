# The revocability constraint

## Statement

At the moment a party commits assets or state, they must be able to evaluate: *given the contract as it exists now, and given every actor whose action is required for exit, can any of them — individually or in compellable combination — prevent exit within the committed window?* If yes, the commitment is unsafe.

Every deposit, escrow, or lock must have a **self-executing, time-bounded, non-discretionary refund path exercisable by the depositor alone, against contract state inspectable at commit time, without requiring action from any actor compellable within the exit window.**

This is a **per-instance evaluation** performed at commit time. Contract upgradeability, admin key changes, or future policy shifts are out of scope for a transaction already committed under known state — they are the next commit's problem. What matters is whether the specific contract-and-actor-set that governs your in-flight funds can prevent your exit before you exit.

## Root cause: unbounded edges

The intent platform is a state machine. Every edge — every transition between states in which user funds may sit — carries a duration bound, and to that bound is ascribed cost (theta on locked capital, vega on price-sensitive positions, opportunity cost, execution risk). Given bounded edges throughout the graph, aggregate cost is bounded and the system can be reasoned about, priced, and hedged.

An edge without a duration bound breaks this. Cost goes to infinity, and every path passing through it becomes uncomputable. A single unbounded edge poisons every strategy that crosses it — pricing, bonding, hedging, and commitment all fail because the terminal cost is undefined.

Being stuck with one leg after having filled the other is a bounded-loss / unknown-delay event: loss magnitude is capped at the filled-leg value, but delay before recovery (if any) is not bounded. Expected loss per commitment is `V × p × (1-q)` where V is the leg at risk, p is the probability of getting stuck, and q is the probability of recovery within acceptable horizon. Because fees per commitment are small relative to V, protocol viability requires very small allowed failure rates. Correlated tail events — one incident affecting many in-flight commitments simultaneously — dominate the loss distribution.

## Four categories of unbounded edges

Four distinct mechanisms produce unbounded exit-edge duration. Same terminal effect, different mitigation profiles, different modelability.

### Category 1 — Actor-gated edges

An identified actor's action is required to progress the exit. Unboundedness arises from their inaction: economic (they gain from delay), operational (they fail), or compelled (they're ordered to withhold).

Sub-mechanisms:
- **Counterparty inaction as unlimited option** — exit requires a counterparty with discretion; their forbearance is a perpetual American option written by the user
- **Committee or operator liveness failure** — m-of-n threshold or specific operational service; persistent failure is an unbounded edge
- **Regulatory compulsion** — any identifiable actor is legally reachable and can be compelled to freeze, block, or delay specific transactions regardless of their preference

Data required:
- Identity of each actor with live-path power over exit
- Legal entity and jurisdiction
- Set size and independence between members
- Historical uptime / SLA / incident data
- Compellability profile (unilateral / m-of-n / broadly distributed)

Modelability: partial. Uptime and incident data give a base rate for operational failure. Compellability is Bayesian — prior probability of a specific actor being compelled in a specific transaction is low but not modelable from historical data alone.

### Category 2 — Modification-gated edges with in-window effect

Governance or admin authority can change the rules that govern in-flight commitments during the exit window, retroactively affecting the transaction. Distinct from ordinary upgradeability, which affects only future commitments.

Sub-mechanisms:
- Upgrade authority (multisig, DAO vote, admin key) with no timelock or timelock shorter than exit window
- Pause switches with immediate effect on in-flight commitments
- Parameter changes (fee rates, whitelists, blacklists) with immediate effect
- Emergency withdrawal / emergency-delete functions

Data required:
- Upgrade authority: keyholders, multisig configuration
- Timelock duration on upgrades
- Enumeration of admin functions with immediate effect on in-flight commitments
- Grandfathering rules (do existing commitments retain original terms?)

Modelability: high. Static analysis against on-chain state at commit time; verdict for a specific commitment is deterministic once exit window and admin surface are known.

### Category 3 — Data-oracle-gated edges

An on-chain conditional reads external market or state data and gates the exit edge on that data. Unboundedness arises from the external condition persisting in a gate-triggering value for arbitrary duration. Circuit breakers, rate limits, TVL caps, liquidity-conditional execution, cross-chain finality gating.

The gate fires automatically; no actor exercises judgment on your specific transaction. Code executes deterministically against a data feed with an off-graph terminal condition.

Data required:
- Oracle dependencies in exit path
- Trigger conditions (threshold values, formulas)
- Historical trigger frequency (how often has this state been entered?)
- Historical trigger persistence distribution (once entered, how long until exit?)
- Fallback behavior if oracle is stale or unavailable
- Correlation with market stress conditions

Modelability: high for trigger conditions (deterministic given oracle values), moderate for duration (fittable from historical time series but tails may be heavy).

### Category 4 — Judgment-oracle-gated edges

An on-chain conditional consults an off-chain classification or scoring service whose output is generated by opaque criteria — off-chain heuristics, ML models, address-cluster analysis, continuously-updated proprietary rulesets. The service can reclassify an address or transaction at any moment for reasons not published in advance.

Sub-mechanisms:
- Address risk-scoring services (Chainalysis KYT, TRM Labs, Elliptic) integrated as claim-gating oracles
- Stablecoin issuer freeze functions consulting central blocklists
- Compliance-oracle-gated withdrawals routed through vendor APIs
- Reputation systems where score determines protocol access

Data required:
- Risk-scoring service dependencies (which services, at which decision points)
- Stablecoin freeze exposure per asset routed
- Compliance oracle dependencies and their scope
- Classification categories that trigger action

Modelability: low. Generating process is discretionary and its criteria may change without notice, so historical incidence is not representative of future risk. Best characterization is scope of judgment: which classes of transactions the service claims authority to freeze or delay.

## Architectural classification

Orthogonal axis capturing the shape of the exit path itself:

- **Class A** — signature-only, pull-based (no deposit). User signs; funds stay in wallet until settlement pull. All edges bounded by signature expiry or nonce invalidation.
- **Class B** — deposit into escrow with depositor-callable timeout refund. Contract exposes `refund()` / `cancel()` callable by depositor after `deadline`. Passes structurally; other categories may still apply.
- **Class C** — deposit into escrow, but refund requires third-party invocation. Solver, operator, oracle, validator quorum, or bundle-processor required. Exit duration bounded by third party's willingness and ability.
- **Class D** — MPC-vault or committee custody. Refund requires threshold signature. Exit duration bounded by committee liveness and cooperation.
- **Class E** — path-explicit bridge (not intents). Atomic on happy path; when messaging layer stalls, funds have no bounded exit.

Class determines default posture on Category 1. Categories 2, 3, and 4 must be evaluated separately per protocol regardless of class.
