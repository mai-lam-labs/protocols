---
slug: arrakis-hot
name: Arrakis HOT
scope: Arrakis public vault over a Valantis HOT pool, rated for a liquidity provider (the party whose funds sit in it); a trader's swap against the pool is atomic and described in the text, not rated
status: deprecated                       # deposits paused on Ethereum and Arbitrum, last rebalance May 2025; pools hold ~$450 on Ethereum, under $10 on Arbitrum and Base (2026-10-06)
kind: vault
class: unknown                           # a liquidity venue, not an intent protocol
cross_chain: false
chains: [Ethereum, Arbitrum, Base]       # read on-chain; deployments/100.json also lists Gnosis, not read
source_public: partial                   # HOT and valantis-core are public; the Arrakis modular contracts are verified on Etherscan/Blockscout but their repo is private
inherits: []
updated: 2026-10-06

verification:
  service: source-verified               # no API or operator in the burn path
  exit: source-verified                  # burn -> module.withdraw -> HOT.withdrawLiquidity -> pool, read in verified source
  actors: source-verified
  admin: source-verified                 # owners, manager, executors, beacons, timelocks read on Ethereum, Arbitrum, Base; timelock proposers and Base's executor not identified
  data: source-verified
  judgment: source-verified
  incidents: not-reviewed

exit:
  custody: pooled                        # tokens sit in the Sovereign Pool; the LP holds vault shares
  execution: self                        # ArrakisMetaVaultPublic.burn(shares, receiver) has no access check and no pause; module.withdraw and HOT.withdrawLiquidity aren't paused either
  overrides: []                          # nothing singles out one LP's burn
  refund_trigger: none
  exit_bound_seconds: 0
  exit_bound_chosen_by: none
  standing_approval: upgradeable_target  # deposit pulls tokens from the LP via the module, a beacon proxy

actors: []

admin:
  upgradeable: true                      # each module is a beacon proxy, and the manager is an ERC-1967 proxy
  authority: multisig                    # vault manager actions run through 4-of-11 Safes; upgrades and module whitelisting through 2-day timelocks
  timelock_seconds: 172800               # beacons and manager proxy owned by TimelockController 0xAf6f…0b7f; vault owner is TimelockController 0xcfad…9117; both minDelay 2 days
  immediate_functions:
    - function: ArrakisStandardManager.rebalance (calls module.swap, setPriceBounds and other module functions)
      caller: the vault's executor; a 4-of-11 Safe on Ethereum and Arbitrum, a contract owned by the 4-of-11 Safe on Base
      parties: unknown                   # Safe signers not identified; falls back to authority
      effect: each call may lose up to maxSlippagePIPS (2%) of vault value against the Chainlink oracle; the cooldown is 60 s, so the loss is bounded per call but not in total
    - function: ArrakisStandardManager.setModule
      caller: the vault's executor
      parties: unknown
      effect: moves all funds to another module, but only one the vault owner (2-day timelock) has whitelisted; one other is whitelisted on each chain, not read
  grandfathered: none
  outside_exit_path:
    - what: Pauser (guardian) pause of the module, by pausers the 4-of-11 Safe whitelists
      effect: stops deposits and manager swaps; burn and withdraw aren't gated by it
    - what: HOT manager (the 2-day timelock) setPause, setSigner, fees, limits
      effect: whether and at what terms the pool trades; LP withdrawals aren't paused

data_gates: []                           # the oracle is read on deposit and rebalance, not on withdraw

judgment:
  screening: []
  freeze_assets: [USDC]
  freeze_pooled: true                    # USDC sits in the pool for every LP

service:
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: false
  operators: []                          # burn is a direct contract call
  screening: []
  bypass: true

integration:
  calls: ["ArrakisMetaVaultPublic.burn(shares, receiver)", "ArrakisMetaVaultPublic.mint(shares, receiver) (paused on Ethereum and Arbitrum)"]
  signatures: []
  offchain_required: []
  finisher: user
  gasless_start: none
  monitoring: "transaction receipt"
  sdk: unknown
  testnet: unknown
  steps: 1

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: short_vol
  holder: anyone
  strike: curve
  expiry: none
  early_close: gas_same_chain
  premium: swap fees
  terms_fixed_by: contract
  price_set_by: curve
  discipline: oracle_check               # HOT quotes and AMM price bounded by oracle deviation
  surplus_to: holder
  extraction: [arbitrage]
  sides: none
  rate: none
  quote_validity: none
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: mint on the vault (paused on Ethereum and Arbitrum)
  - action: withdraw
    performer: user
    paid: none
    gas_on: funds_chain
    note: "burn(shares, receiver); no one else can or need do it"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: burn
    form: self_built

incidents: []

open_questions:
  - Proposers and executors of the two timelocks (0xAf6f…0b7f for beacons, HOT and manager proxy; 0xcfad…9117 for vault ownership); role events weren't fetched
  - Signers of the 4-of-11 Safes, and who can call Base's executor contract 0x0c3a…9464
  - The second whitelisted module on each vault (e.g. 0xb48d…85f1 on Ethereum) and what a setModule into it could do
  - The Gnosis deployment in deployments/100.json
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: arrakis-hot
    url: https://github.com/ValantisLabs/valantis-hot
    commit: 8c8da4e65679910bfcd5242ff6de9bc35ec4d5e7
    commit_date: 2024-11-25
  - repo: valantis-core                  # the SovereignPool that HOT plugs into (HOT's lib/valantis-core submodule commit)
    url: https://github.com/ValantisLabs/valantis-core
    commit: e377e7eca375f398769f92e99f2d86232b4c1bff
    commit_date: 2024-05-10
---

# Arrakis HOT

**Primitive (one line):** Managed liquidity vault (Arrakis MetaVault) with dual execution: permissionless AMM swaps and signer-issued EIP-712 RFQ quotes for solvers; LPs deposit/withdraw via share-based vault; pool holds custody.
**Product scope of this entry:** Arrakis HOT module (Valantis HOT) — deprecated after ~6 months, ~$6M TVL, ~$300M cumulative volume

## Rated party: the liquidity provider

A trader's swap is atomic. The trader's `amountOutMin` and `deadline` bound it,
and no verifier module can gate it, so a trader never holds anything here to
exit. Rating the trader would give six green petals to any AMM. The people
whose funds sit in HOT are the liquidity providers, so this entry rates them.

**Exit path.** `ArrakisMetaVaultPublic.burn(shares, receiver)` has no access
check and no pause. It calls the module's `withdraw` (`onlyMetaVault`, not
`whenNotPaused`), which calls `HOT.withdrawLiquidity` (`onlyLiquidityProvider`,
not paused), which calls `SovereignPool.withdrawLiquidity` (no verifier
module). No oracle is read on the way out. An LP can leave in one transaction
even with the module paused, as it is on Ethereum and Arbitrum.

**What can reach LP funds without a timelock.** The vault's manager is
`ArrakisStandardManager`. Its `rebalance` lets the vault's executor call any
module function except `setManagerFeePIPS`, including `swap` with an arbitrary
router and payload. Each call is checked against the Chainlink oracle: the
vault's value may not fall by more than `maxSlippagePIPS`, set to 20000 (2%),
and the pool price must stay within `maxDeviation` (2%). The cooldown is 60
seconds. So one call can lose at most 2%, but nothing caps repeated calls.
`setModule` can move all funds to another module, but only one the vault owner
has whitelisted.

**What needs two days.** Module code (beacons), the manager proxy and the HOT
manager role all belong to TimelockController `0xAf6f…0b7f`. Vault ownership
(whitelisting modules) belongs to TimelockController `0xcfad…9117`. Both have a
2-day `minDelay`. An LP who watches the timelocks can leave first.

## Status on-chain (2026-10-06)

Read by `eth_call`. Addresses come from the HOT repo's `deployments/` and from
following the vault and module pointers.

| | Ethereum | Arbitrum | Base |
|---|---|---|---|
| SovereignPool | `0xd9a4…8202` | `0xc0c8…0838` | `0x159d…fb08` |
| Pool reserves | 319.47 USDC, 0.0502 WETH | 0.00048 WETH, 6.08 USDC | 0.00103 WETH, 2.45 USDC |
| Pool `verifierModule` | none | none | none |
| HOT `isPaused` / signer | false / EOA `0x498c…765C` | same | same |
| Vault (ArrakisMetaVaultPublic) | `0xf790…ad83` | same address | same address |
| Vault owner | Timelock `0xcfad…9117`, 2 days | same | same |
| Module (beacon proxy) | `0x505f…17E5` | `0x06aa…5D4a` | `0xE783…226B` |
| Module `paused` | true | true | false |
| Beacon owner | Timelock `0xAf6f…0b7f`, 2 days | same | same |
| Manager | ArrakisStandardManager `0x2e6e…3bda`, proxy admin `0xAf6f…0b7f` | same | same |
| Executor | Safe 4 of 11 `0x5108…de58` | Safe 4 of 11 `0x77ba…0df7` | contract `0x0c3a…9464`, owner Safe 4 of 11 `0x25cf…3823` |
| maxSlippage / maxDeviation / cooldown | 2% / 2% / 60 s | same | same |
| Last rebalance | 2025-04-30 | 2025-05-01 | 2025-05-18 |

The vaults are drained and deposits are paused on two chains, so the entry is
marked deprecated and ranks after every live product.

## Reclassification note

Originally listed as Class A ("hybrid AMM/RFQ, signed quotes"). Source verification reveals this is a **managed liquidity vault**, not an intent/order protocol:
- Users are LPs who `mint(shares, receiver)` and `burn(shares, receiver)` on the vault — standard deposit/withdraw
- The "signed quotes" are signer-to-solver RFQ quotes (the signer role signs EIP-712 quotes for solvers), NOT user-signed intents
- Traders swap against pool liquidity, neither party signs intent-style orders
- Custody: pool-custodied (tokens sit in the Sovereign Pool)

This protocol is a **liquidity venue** that intent-protocol solvers route through, not itself an intent protocol. Included for completeness since it was in the original index.

## Category 1 — Actor-gated edges

**Actors on exit path (LP withdrawal):**
- Actor: `liquidityProvider` (Arrakis vault address)
  - Role: only address that can call `withdrawLiquidity()`. Set immutably at construction.
  - Source: [3] `HOT.sol:717-744`, `onlyLiquidityProvider` modifier
- Note: end-user LPs interact via the Arrakis MetaVault (`burn(shares)`), not directly with HOT. The vault is the `liquidityProvider`.

**Actors on exit path (trader):** none — traders are not depositing; swaps are atomic.

**Uptime / SLA:** depends on Arrakis vault operator for LP withdrawal; swaps are permissionless (AMM path) or signer-dependent (HOT path).

**Compellability profile:** `manager` role has pause power — see Category 2.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** HOT itself has no proxy pattern, no delegatecall and no UUPS; it is immutable once deployed. Source: [3] grep of source for proxy/upgrade patterns returned no results. The Arrakis layer above it is upgradeable: each module is a beacon proxy and the manager is an ERC-1967 proxy, both behind a 2-day timelock (see Rated party, above).

**Immediate-effect admin functions (manager role):**
- Function: `setPause(bool)`, Caller: manager, Effect: **pauses all swaps and deposits immediately**. Withdrawals are NOT paused (safety feature). Source: [3] `HOT.sol:503`, `onlyUnpaused` modifier at line 203
- Function: `setSigner(address)`, Caller: manager, Effect: changes who can sign HOT quotes. Source: [3] `HOT.sol:407`
- Function: `setHotFeeInBips(uint16)`, Caller: manager, Effect: changes HOT swap fee (capped at 100 bips). Source: [3] `HOT.sol:447`
- Function: `setMaxTokenVolumes(uint256, uint256)`, Caller: manager, Effect: changes max quotable volume per HOT swap. Source: [3] `HOT.sol:435`
- Function: `setMaxOracleDeviationBips(uint16, uint16)`, Caller: manager, Effect: changes allowed price deviation bounds. Source: [3] `HOT.sol:482`
- Function: `setMaxAllowedQuotes(uint8)`, Caller: manager, Effect: changes max HOT quotes per block. Source: [3] `HOT.sol:465`

**Note:** Source comments state "It assumes that `manager` implements a timelock" and "It assumes that `liquidityProvider` implements sufficient internal protection". The contract doesn't enforce this. On-chain the manager is an OpenZeppelin TimelockController with a 2-day `minDelay` on Ethereum, Arbitrum and Base (read 2026-10-06); its proposers weren't found. Source: [3] HOT.sol comments; on-chain reads above.

**Grandfathering:** N/A — no in-flight intent state. LP positions are affected by parameter changes (fee changes, pause) but can always withdraw (withdrawal not paused).

## Category 3 — Data-oracle-gated edges

**Oracles in exit path:**
- Oracle: Chainlink AggregatorV3Interface (two feeds: token0/USD and token1/USD)
  - Consulted at: deposit, HOT swap validation, price bound changes
  - Staleness check: `block.timestamp - updatedAt > maxOracleUpdateDuration` reverts with `stalePrice`
  - Effect of stale oracle: blocks deposits and HOT swaps that require oracle checks
  - **Withdrawals are NOT gated by oracle** — `withdrawLiquidity` does not check oracle
  - Source: [3] `HOTOracle.sol:99-146`

**Rate limits / circuit breakers:** `maxAllowedQuotes` limits HOT quotes per block; dynamic AMM fees increase after each HOT swap as a circuit breaker.

## Category 4 — Judgment-oracle-gated edges

**Risk-scoring service integrations:** none identified.

**Stablecoin freeze exposure:** pool holds reserves — if pool address is frozen by stablecoin issuer, all LP funds in that asset are stuck. Source: standard issuer-controlled blacklist risk.

**Compliance oracle dependencies:** none identified.

## Composite

**Stuck-leg failure modes (LP perspective):**
1. Manager pauses contract — withdrawals still work (not paused). Not stuck.
2. Chainlink oracle stale — withdrawals still work (not oracle-gated). Not stuck.
3. Stablecoin issuer freezes pool address — LP funds in that asset stuck. Unbounded.
4. `liquidityProvider` (vault) contract bug or admin lock — LP cannot withdraw. Unbounded.

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Manager pause | immediate (withdrawals not paused) | [3] HOT.sol |
| Oracle stale | immediate for withdrawals | [3] HOTOracle.sol |
| Stablecoin freeze | unbounded | issuer-dependent |
| Vault contract failure | unbounded | depends on Arrakis vault implementation |

## Sources

1. https://docs.arrakis.finance/ — Arrakis docs — retrieved 2026-09-16
2. https://github.com/ArrakisFinance — Arrakis GitHub org (arrakis-modular repo appears private) — retrieved 2026-09-16
3. https://github.com/ValantisLabs/valantis-hot — HOT source repo; specifically:
   - `src/HOT.sol` — main contract, swap logic (lines 631-998), admin functions (lines 396-594), pause (line 503), deposit/withdraw (lines 664-744)
   - `src/HOTOracle.sol` — Chainlink integration, staleness check (lines 99-146)
   - `src/structs/HOTStructs.sol` — HybridOrderType struct
   — cloned and read 2026-09-16
4. https://github.com/ValantisLabs/valantis-core at `e377e7e` (HOT's submodule commit) — `src/pools/SovereignPool.sol`: swap (lines 662-800), verifier module (157, 303, 695), setSwapFeeModule (534), setALM (553) — cloned and read 2026-10-06
5. Verified source on eth.blockscout.com, 2026-10-06: ArrakisMetaVaultPublic `0xf790…ad83`, ValantisModulePublic implementation `0x9ac1…dde3`, ArrakisStandardManager implementation `0xd6a0…7f9c`, Pauser `0x6f1e…e268`
6. On-chain reads by `eth_call` on Ethereum, Arbitrum and Base, 2026-10-06 (see Status on-chain)

## Notes / follow-ups

- Protocol is deprecated: pools are live but drained (see Status on-chain). Further work only if it informs a successor product
- The Arrakis MetaVault layer (arrakis-modular) is where end-user LP interaction happens — that repo appears private; verify whether vault contract has additional admin surface
- Consider removing from intent protocol index since it's a liquidity venue, not an intent protocol — or move to a separate "liquidity venues" section
