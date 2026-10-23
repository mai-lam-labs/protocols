---
slug: thorchain
name: THORChain
scope: THORChain cross-chain swap protocol
kind: swap
class: D
cross_chain: true
chains: [BTC, ETH, BSC, AVAX, DOGE, LTC, BCH, XRP]   # partial list
source_public: true
inherits: []
updated: 2026-09-28

verification:
  exit: source-verified
  actors: source-verified
  admin: source-verified
  data: source-verified
  judgment: partial                      # screening checked in source; frozen-asset exposure not
  incidents: reviewed

exit:
  custody: mpc_vault                     # TSS vaults on external chains
  execution: automatic                   # handlers create the refund, consensus picks the vault, unsigned items move vault by rule
  overrides:                             # none by rule: no admin key, blocklist or per-tx mimir
    - who: vault TSS signers
      needs: more than 1/3 of every vault able to fund the outbound (~14 of 40 when one vault can), on modified software
      how: refuse to sign one outbound; it is rescheduled and refused again
      reach: one
      bounded: false                     # MaxOutboundAttempts defaults to 0, unlimited retries
      cost: blame, 2 slash points and a 60-block jail per failed keysign
    - who: validators observing inbounds
      needs: more than 1/3 of active validators
      how: withhold observation of one inbound, so it is never credited
      reach: one
      bounded: false
      cost: none; non-observers are penalised only once consensus is reached
  refund_trigger: on_failure             # failed swap, halted trading, bad memo, limit-swap expiry
  exit_bound_seconds: [6, 108000]        # outbound scheduling at default mimir; signing adds 1800 s per failed attempt
  standing_approval: immutable_target    # RouterV6 has no owner or proxy, and pulls only from the caller

actors:
  - role: Validator set; 2/3 of active validators must observe an inbound before it is credited
    entity: pseudonymous                 # identifiable by bonded RUNE
    jurisdiction: pseudonymous
    set: staked
    independence: independent
  - role: Vault TSS signers; ceil(2/3) of a 40-member Asgard vault sign each outbound
    entity: pseudonymous
    jurisdiction: pseudonymous
    set: staked
    independence: independent

admin:
  upgradeable: true                      # chain upgrades: any validator proposes, 2/3 approve, at any future height
  authority: validators
  timelock_seconds: none                 # mimir applies in the block the deciding vote lands
  immediate_functions:
    - function: HALTSIGNING, HaltSigning<Chain>
      caller: 3 validators (operational mimir)
      effect: stops all outbound signing, refunds included
    - function: HaltChainGlobal, Halt<Chain>Chain
      caller: 3 validators (operational mimir)
      effect: stops observation and signing
    - function: NodePauseChainGlobal
      caller: any single validator, once per churn
      effect: stops observation and signing on every chain for 720 blocks (~72 min); each further node adds 720
    - function: HaltTrading, Halt<Chain>Trading
      caller: 3 validators (operational mimir)
      effect: swaps stop and inbounds are refunded; streaming swaps wait
    - function: PauseLP, PauseLP<Chain>
      caller: 3 validators (operational mimir)
      effect: blocks liquidity withdrawals
    - function: MaxOutboundAttempts
      caller: 3 validators (operational mimir)
      effect: outbounds still unsigned after that many attempts are reverse-swapped, or swapped to RUNE at the treasury address
    - function: COMPROMISEDVAULT-*, StopSolvencyCheck*, MimirUpgradeContract<Chain>
      caller: 3 validators (operational mimir)
      effect: vault handling, solvency checks, router address
    - function: economic mimirs (TxOutDelayRate, TxOutDelayMax, MaxTxOutOffset, fees)
      caller: 2/3 of active validators
      effect: outbound delay and fees
  grandfathered: unknown
  outside_exit_path: []

data_gates:
  - kind: solvency halt
    where: SolvencyHalt<Chain>Chain, set by solvency attestations
    trigger: a vault's gap between record and wallet exceeds $500, attested by more than 1/3 of validators
    blocks_exit: true
    reset: unbounded                     # clears itself once attested solvent, which depends on the gap being fixed
  - kind: vault-deficit and slash halts
    where: HaltSigning<Chain> and Halt<Chain>Trading, set automatically
    trigger: outbound overspend, missing vault, large gas deficit, or a theft slash of at least 100 RUNE
    blocks_exit: true
    reset: unbounded                     # stays until validators vote it off
  - kind: frozen vault
    where: keysign failure handling
    trigger: repeated terminal keysign failures on a vault
    blocks_exit: true
    reset: unbounded                     # clears only when an outbound from that vault is observed
  - kind: outbound delay
    where: CalcTxOutHeight
    trigger: refund or outbound value against the queue's per-block rate
    blocks_exit: true
    reset: bounded                       # at most 18000 blocks (~30 h) at default mimir

judgment:
  screening:
    - kind: per-node address blocklists
      status: proposed                   # nothing in source at the pinned commit
  freeze_assets: unknown
  freeze_pooled: true                    # vaults

service:
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: unknown
    note: "public THORNode and Midgard endpoints; anyone can run a node"

integration:                             # not yet researched; see open_questions
  calls: unknown
  signatures: unknown
  offchain_required: unknown
  finisher: unknown
  gasless_start: unknown
  monitoring: unknown
  sdk: unknown
  testnet: unknown
  steps: unknown

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: spot                        # a swap against the protocol's pools, with an optional limit
  holder: none
  strike: curve
  expiry: none
  early_close: none
  premium: none
  terms_fixed_by: contract
  price_set_by: curve
  discipline: arbitrage
  surplus_to: none
  extraction: []
  sides: [exact_in]                      # the inbound amount is sent; the memo carries the output limit
  rate: floating_above_bound             # the pools pay what they give, above the memo's limit; below it the swap refunds
  quote_validity: 900                    # /quote/swap returned expiry 15 minutes out, 2026-10-07: 'Do not send funds after the expiry'
  partial_fill: user_signed              # only for a streaming swap the memo requests; sub-swaps below the limit are refunded
  partial_remainder: refunded

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: unknown
    note: not researched
  - action: refund
    performer: none
    paid: none
    note: refunds are created by the protocol and sent by its vaults; the user does nothing

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: inbound with memo
    form: calldata
    bounds: bounded
    verifiable_locally: true
    api_optional: true
    note: "the memo format is public; vault addresses come from THORNode"

incidents:
  - date: "2021-07"
    duration: unknown
    user_funds_lost: unknown
    exits_blocked: true                  # network halted
    cause: ~$5M exploit
  - date: "2021-07"
    duration: unknown
    user_funds_lost: unknown
    exits_blocked: true                  # network halted again
    cause: ~$8M exploit
  - date: "2025-01"
    duration: 90 days
    user_funds_lost: unknown
    exits_blocked: true                  # ThorFi lending suspended
    cause: ThorFi insolvency; $200M of defaulted obligations converted to an equity-style token
  - date: 2026-05-15
    duration: days
    user_funds_lost: false               # per THORChain
    exits_blocked: true                  # signing halted within minutes
    cause: Node operator churned in 2 days earlier exploited a GG20 TSS vulnerability; $11M+ across 9 chains

open_questions:
  - "The integration facts (calls, signatures, finisher, gasless_start by token standard); an EVM inbound is a router depositWithExpiry the user sends, so likely none, but not read"
  - Live mimir values on mainnet (MaxOutboundAttempts, OperationalVotesMin, TxOutDelay*, current halts), which may override the defaults used here
  - Whether the deployed router bytecode matches RouterV6.sol on each EVM chain
  - Whether a keysign party proceeds when exactly the threshold is online (JoinPartyWithLeader in the party coordinator)
  - Whether an eBifrost block proposer can suppress one observation beyond a block
  - Which halt stopped the network in May 2026 and how it was cleared (set_mimir events)
  - Which issuer-freezable assets the vaults hold
  - A citable source for the Jan 2025 insolvency (currently "various sources")
  - Full chain list
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: thornode
    url: https://gitlab.com/thorchain/thornode
    commit: 806e61f332a3e6906e48e1e04fb2c5db4379d26a
    commit_date: 2026-09-26
---

# THORChain

**Primitive (one line):** L1 PoS blockchain with TSS-controlled vault addresses on external chains (BTC, ETH, BSC, AVAX, DOGE, LTC, BCH, XRP, etc.); validators observe cross-chain events, reach consensus, and co-sign TSS transactions to move assets; native cross-chain swaps settled by the validator set.

## Category 1 — Actor-gated edges

**Actors on exit path:**
- Actor: THORChain validator set (node operators)
  - Role: observe inbound transactions, reach consensus, co-sign TSS transactions on external chains to send outbound swaps/withdrawals. Required for ALL operations — no user self-service exit from TSS-controlled vaults.
  - Set size: ~100+ active validators (churning in/out)
  - Independence: independent operators, PoS with bonding requirements
  - Source: [1]

- Actor: vault TSS signers
  - Role: each outbound is signed by the vault consensus assigned it; ceil(2/3) of members must sign, and Asgard vaults have 40 members [7] `bifrost/p2p/conversion/conversion.go:202-208`, `constants/constants_v1.go:21`.
  - An inbound is credited only once 2/3 of active validators observe it [7] `x/thorchain/types/type_observed_tx.go:175-199`.
  - Source: [7]

**Can one exit be singled out?** Not by any rule, key or setting. Refunds are created by handlers when a swap fails, trading is halted, or the memo is bad [7] `x/thorchain/helpers.go:115-235`, `handler_observed_tx_helpers.go:441-536`; the source has no admin key, no per-address or per-transaction blocklist, and no mimir that targets one outbound [7]. An outbound left unsigned for `SigningTransactionPeriod` (300 blocks, ~30 min) is moved to another vault by rule, rotating so it doesn't land on the same vault twice [7] `manager_slasher_current.go:278-750`. What remains is collusion below a halt: more than 1/3 of a vault's signers (~14 of 40), running modified software, can refuse to sign one outbound, and would have to hold every vault that can fund it; more than 1/3 of active validators can refuse to observe one inbound, which is then never credited and nobody is slashed [7] `handler_observed_tx_helpers.go:95-151`. Signers who refuse are blamed, slashed and jailed for 60 blocks, but retries are unlimited by default (`MaxOutboundAttempts=0`), so nothing bounds it [7].

**User self-refund:** **NO.** Assets sent to THORChain vault addresses are controlled entirely by the validator set's TSS key. The user cannot sign transactions from the vault address. If validators refuse or fail to process an outbound, the user has no on-chain recourse on the external chain.

**Compellability profile:** validators are pseudonymous but identifiable via bonded RUNE. New validators can churn in (permissionless with sufficient bond). However, a compromised or colluding validator set can steal vault contents.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** any active validator can propose a chain upgrade at any future height; it is scheduled once 2/3 of active validators approve, with no minimum delay [7] `handler_upgrade.go:65-104`, `keeper/v1/keeper_upgrade.go:147-187`.

**Mimir:** accepted only from active validators; there is no admin mimir key at the pinned commit [7] `handler_mimir.go:72, 210-212`. Economic mimirs need 2/3 of active validators; operational ones, which include every `HALT*` and `PAUSE*` key, need only a plurality of at least 3 votes [7] `handler_mimir.go:167-177`, `keeper_mimir.go:106-183`. Any single validator can pause every chain for 720 blocks (~72 min) once per churn with `NodePauseChainGlobal` [7] `handler_node_pause_chain.go:52-105`. Values apply in the block the deciding vote lands; there is no timelock. The halts and what they stop are listed in the header.

**Pause mechanism:** besides the votes above, halts are set automatically (Category 3).

## Category 3 — Data-oracle-gated edges

**Oracles:** no external price oracles. Pricing derived from pool depths (constant product AMM). Bifrost observers watch external chain transactions.

**Automatic halts** [7]:
- Solvency: if more than 1/3 of validators attest that a vault's recorded and actual balances differ by more than $500, `SolvencyHalt<Chain>Chain` is set; it clears itself once a later attestation shows the chain solvent (`handler_solvency_helpers.go:163-196, 275-400`).
- Vault deficit (outbound overspend, missing vault, large gas deficit) and any theft slash of at least 100 RUNE set `HaltSigning<Chain>` and `Halt<Chain>Trading`, which stay until validators vote them off (`handler_observed_tx_helpers.go:1415-1494`, `manager_slasher_current.go:1076-1100`).
- A vault with repeated terminal keysign failures is frozen for that chain until an outbound from it is observed (`handler_tss_keysign.go:180-271`).

**Outbound delay:** refunds and outbounds above 1000 RUNE are spread out by value at 25 RUNE per block, capped at 720 blocks plus up to 17280 blocks' search for room, so at most ~30 h at default mimir (`manager_txout_current.go:1280-1375`, `constants/constants_v1.go:76-79`).

**EVM router:** `THORChain_RouterV6.sol` has no owner, proxy or selfdestruct, and `depositWithExpiry` pulls only from the caller, so an approval to it can't be spent by anyone else. Router changes move thornode to a different address, by operational mimir (`chain/evm/contracts/THORChain_RouterV6.sol:69-77, 205-210`, `router_upgrade_controller.go:53-118`).

## Category 4 — Judgment-oracle-gated edges

**Compliance/sanctions (evolving):**

**Proposed address blocking:** following the Bybit hack laundering, a proposal was introduced allowing node operators to manually maintain blocklists of wallet addresses on their servers. Under this mechanism, each node operator would independently block specific addresses from swapping. This is not yet implemented as of 2026-09-16 but indicates the direction of travel. Source: [6]. At the pinned commit the source has no address or transaction filter in consensus or in bifrost config [7]. Such a list would give operators an individual override the protocol doesn't have today.

THORChain has been used as primary laundering rail for two of the largest crypto hacks on record:
- Bybit hack ($1.5B, Feb 2025) — THORChain facilitated the swap/laundering of a significant portion. Unlike Chainflip, THORChain did not block these flows.
- KelpDAO hack (~$300M, Apr 2026) — again routed through THORChain.
- This has drawn significant regulatory attention and raises questions about whether validators may face future compulsion to filter transactions.

Source: [2][3]

## Historical incidents (EXTENSIVE)

- **2021-07 (first):** ~$5M exploit. Network halted. Source: [2]
- **2021-07 (second):** ~$8M exploit. Network halted again within weeks. Source: [2]
- **2025-01:** ThorFi lending operations suspended amid insolvency allegations. $200M debt crisis resolved by converting defaulted obligations into equity-style token via 90-day validator-approved restructuring. Source: [4]
- **2025-02:** THORChain founder JP Thorbjornsen personally targeted by probable North Korean hackers. Source: [2]
- **2026-05-15:** $11M+ exploit across 9 chains. Attacker was a newly churned node operator who exploited GG20 Threshold Signature Scheme vulnerability 2 days after entering the network. Automatic solvency detection halted signing within minutes. THORChain claimed end user funds not affected. Source: [2][5]
- **Cumulative losses from exploits approach $25M.** Source: [2]

**Laundering activity:**
- Primary rail for Bybit $1.5B hack (Feb 2025). Source: [3]
- Primary rail for KelpDAO ~$300M hack (Apr 2026). Source: [3]

## Composite

**Stuck-leg failure modes:**
1. Validator set halted (manual or automatic) — all operations paused. User funds in vaults inaccessible until restart. **Has happened multiple times.**
2. TSS key compromise by rogue validator — vault funds at risk. **Happened May 2026.**
3. Insolvency event — protocol unable to honor obligations. **Happened Jan 2025.**
4. Regulatory compulsion on validators to freeze/refuse specific transactions — not yet happened but increasingly likely given laundering controversy.

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Chain halt (automatic) | minutes to hours (solvency detection) | May 2026 incident |
| Chain halt (manual/governance) | hours to days | historical halts |
| TSS exploit | unbounded until fix + restart | May 2026: days |
| Insolvency restructuring | 90 days (Jan 2025 precedent) | [4] |
| Validator compulsion | unbounded | hypothetical |

## Sources

1. https://docs.thorchain.org/ — THORChain documentation
2. https://www.trmlabs.com/resources/blog/thorchain-exploit-drains-usd-11m-across-at-least-nine-chains-what-trm-knows-now — TRM Labs May 2026 exploit analysis
3. https://www.dlnews.com/articles/defi/lazarus-laundering-spree-threatens-chainflip-and-thorchain/ — Lazarus Group laundering through THORChain and Chainflip
4. Various sources on Jan 2025 insolvency and 90-day restructuring
5. https://thorchain.org/blog/thorchain-exploit-report-1 — THORChain official exploit report
6. https://99bitcoins.com/news/will-this-proposal-block-crypto-laundering-on-thorchain-after-bybit-hack/ — node operator address blocking proposal
7. https://gitlab.com/thorchain/thornode (`source/thornode`) — refund, txout, keysign, slasher, mimir, halt, solvency and upgrade handlers; `chain/evm/contracts/THORChain_RouterV6.sol` — read 2026-09-28; defaults, not live mimir values

## Notes / follow-ups

- THORChain has the worst incident history of any protocol in this audit — multiple exploits, insolvency, and laundering controversy
- The GG20 TSS vulnerability (May 2026) is particularly concerning because it was exploited by a node operator who churned in only 2 days prior — this suggests the churn mechanism's security screening is insufficient
- The regulatory risk from being a primary laundering rail is a Category 4 concern that could escalate to Category 1 (validators compelled to freeze/refuse transactions)
- Source read 2026-09-28 at the pinned commit; remaining open questions are in the header.
