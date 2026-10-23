---
slug: chainflip
name: Chainflip
scope: Chainflip swaps between native assets (BTC, ETH, SOL, DOT, USDC, USDT, ...) through deposit channels and the EVM Vault; custody in threshold-signature vaults run by the validator set of the Chainflip state chain. The Ethereum Vault and KeyManager were read on-chain; the state chain wasn't
kind: swap
class: D
cross_chain: true
chains: [Chainflip, Bitcoin, Ethereum, Arbitrum, Solana, Polkadot, Tron]   # per docs; Tron involved in the 2026-09 exploit
source_public: true                      # chainflip-backend (Rust) and contracts; not read
inherits: []
updated: 2026-10-04

verification:
  service: spec-only
  exit: spec-only                        # refund and broadcast logic on the state chain not read
  actors: spec-only
  admin: partial                         # Ethereum Vault and KeyManager read on-chain; state-chain governance from docs and incidents
  data: spec-only
  judgment: spec-only
  incidents: partial

exit:
  custody: mpc_vault                     # TSS vaults controlled by the authority set's aggregate key
  execution: automatic                   # the state chain decides the swap or refund; validators sign the outbound
  overrides:
    - who: Chainflip validators (authority set, ~150)
      needs: unknown                     # the signing threshold wasn't read; docs describe a supermajority
      parties: quorum
      independent: unknown
      how: decline to sign one outbound or refund, or sign one that wasn't decided
      reach: one
      bounded: false
      cost: stake at risk only if slashed
    - who: Chainflip state-chain governance
      needs: unknown                     # governance council membership and threshold not read
      parties: unknown
      how: a runtime upgrade that blocks chosen transactions, as in the February 2025 Bybit response (1.7.10)
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: on_failure             # a swap below its minimum, or otherwise failed, refunds to the refund address
  exit_bound_seconds: unknown
  exit_bound_chosen_by: none
  standing_approval: unknown             # deposit channels take plain transfers; the EVM Vault path needs approval to a non-proxy Vault

actors:
  - role: Validators; witness deposits, run the state chain and threshold-sign outbound transactions
    entity: about 150 staked operators
    jurisdiction: unknown
    set: staked
    independence: unknown

admin:
  upgradeable: true                      # the state chain upgrades by runtime upgrade under governance
  authority: multisig                    # Ethereum: governance key a 3-of-6 Safe, community key a 5-of-9 Safe; state-chain governance not read
  timelock_seconds: unknown
  immediate_functions:
    - function: Vault.suspend / resume (Ethereum)
      caller: governance Safe (3 of 6)
      effect: suspends the Ethereum Vault
    - function: state-chain pause and runtime upgrade
      caller: governance
      effect: stopped all swaps during both 2025-02 and 2026-09 incidents; 1.7.10 blocked specific transactions
  grandfathered: none
  outside_exit_path:
    - what: Vault.govWithdraw (Ethereum)
      effect: withdraws every token from the Vault, but only with the governance Safe, after the community Safe (5 of 9) disables the community guard, while suspended, and after the emergency timeout since the aggregate key last validated
      caller: governance and community Safes together

data_gates:
  - kind: solvency and network safety pauses
    where: state chain
    trigger: incident response
    blocks_exit: true
    reset: unknown

judgment:
  screening:
    - kind: blocking of specific funds by runtime upgrade (Bybit, February 2025)
      status: unknown                    # a one-off response; whether deposits are screened continuously isn't established
  freeze_assets: [USDC, USDT]
  freeze_pooled: true                    # vault addresses hold everyone's assets

service:
  integrator_access:
    api_key: unknown
    identity: unknown
    revocable: unknown
    rate_limited: unknown
  operators:
    - role: Brokers; open deposit channels for users
      entity: many (Chainflip's own and third parties)
      single_operator: false
      source_public: unknown
      deployment_config_public: false
  screening: unknown
  bypass: unknown

integration:
  calls: ["request a deposit channel from a broker (SDK or API)", "send the input to the channel address, or call the EVM Vault", "track the swap by channel id"]
  signatures: ["none; plain transfers to the deposit address"]
  offchain_required:
    - role: broker
      api_key: unknown
      rate_limited: unknown
  finisher: protocol
  gasless_start: none
  monitoring: "Chainflip SDK / explorer swap status"
  sdk: "@chainflip/sdk (TypeScript)"
  testnet: true
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: none
  strike: off_chain                      # the minimum price set when the channel is opened
  expiry: none
  early_close: none
  premium: none
  terms_fixed_by: api
  price_set_by: curve
  discipline: oracle_check               # PriceLimits.max_oracle_price_slippage, when set, checks against Chainflip's oracle price
  surplus_to: user
  extraction: []
  sides: [exact_in]                      # the deposited amount is swapped
  rate: floating_above_bound             # PriceLimits.min_price floors the rate; output above it goes to the user
  quote_validity: user_chosen            # the swap retries until refund_block, then refunds
  partial_fill: user_signed              # only with DCA chunks the user requested; chunks failing the price limit are refunded
  partial_remainder: refunded

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: "send the input to the deposit channel address, or call the EVM Vault"
  - action: refund
    performer: none
    paid: none
    note: the state chain decides the refund and validators sign it; the user does nothing

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: deposit channel
    form: unknown
    note: "broker-issued deposit address; whether it can be checked against the state chain not established"

incidents:
  - date: "2025-02-22"
    duration: "about 2 days"
    user_funds_lost: false
    exits_blocked: true
    cause: "frontend closed and upgrade 1.7.10 shipped to block Bybit-hack funds"
  - date: "2026-09-12"
    duration: unknown
    user_funds_lost: true
    exits_blocked: true
    cause: "Tron USDT memo exploit, 736,442 USDT in 6 unauthorised refund payouts; network paused; users to be made whole"

open_questions:
  - The validator signing threshold and how refunds are decided and broadcast, from chainflip-backend
  - State-chain governance membership, threshold and any delay on runtime upgrades
  - Whether deposits are screened continuously since the Bybit response
  - The emergency timeout value in the Ethereum KeyManager / Vault
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: chainflip-backend              # sparse: state-chain/primitives and the swapping pallet (price limits, refunds, DCA)
    url: https://github.com/chainflip-io/chainflip-backend
    commit: ba40667b58df5fdef0ae02143804bce7200b069d
    commit_date: 2026-10-01
---

# Chainflip

**Primitive (one line):** L1 substrate-based blockchain with ~150 validators; TSS-controlled vault addresses on external chains (BTC, ETH, DOT, etc.); validators observe deposits, reach consensus, and co-sign TSS transactions for outbound swaps; JIT AMM for pricing.
**Product scope of this entry:** Chainflip cross-chain swap protocol

## Category 1 — Actor-gated edges

**Actors on exit path:**
- Actor: Chainflip validator set (~150 validators)
  - Role: observe deposits, reach consensus, co-sign TSS transactions on external chains. Required for all operations.
  - Set size: ~150 active validators (permissioned via staking FLIP tokens)
  - Source: [1]

**User self-refund:** **NO.** Assets deposited to Chainflip vault addresses are controlled by the validator TSS key. No user self-service exit. One pending swap (115,654 USDT) was stuck during the Sep 2026 incident and described as "recoverable after a secure restart" — implying recovery requires validator action.

## Category 2 — Modification-gated edges (in-window effect)

**Pause mechanism:** confirmed — network was fully paused during both the Feb 2025 Bybit response and Sep 2026 TRON exploit. Pause blocks all operations.

**Upgrade authority:** governance-controlled chain upgrades. Emergency upgrades shipped within days (1.7.10 upgrade to block Bybit hackers in Feb 2025).

## Category 4 — Judgment-oracle-gated edges

**Compliance actions (confirmed):**
- **Feb 2025:** Chainflip detected Bybit hack laundering attempt on Feb 22, immediately closed swap.chainflip.io frontend, and shipped emergency upgrade 1.7.10 on Feb 24 to block illicit transactions and protect LPs from exposure to stolen funds. This was a voluntary compliance action — "refusing to facilitate what is not merely a monumental theft event, but a matter of national security and geopolitical significance." Source: [3][4]
- This demonstrates Chainflip's willingness and technical capability to block specific transactions/addresses at the protocol level, which is a Category 4 finding — the protocol can and will exercise judgment-based blocking.

## Historical incidents

- **2025-02:** Bybit hack ($1.5B) laundering attempt — Chainflip detected and blocked within hours, shipped emergency upgrade. No funds lost from Chainflip itself. Source: [3][4]
- **2026-09-12:** TRON USDT memo exploit — attacker attached new memos to already-signed transactions, tricking the protocol into issuing refunds for fake failed swaps. 736,442 USDT lost via 6 unauthorized payouts. 1 pending swap (115,654 USDT) stuck but recoverable. Network fully paused. Users to be made whole. Source: [2][5]

## Composite

**Stuck-leg failure modes:**
1. Network paused (manual response to incidents) — all operations halted. **Has happened twice in 2025-2026.**
2. TSS signing exploit — attacker manipulates memo/transaction to trigger invalid payouts. **Happened Sep 2026.**
3. Regulatory/compliance blocking — Chainflip has demonstrated willingness to block specific flows at the protocol level. **Happened Feb 2025.**
4. Validator set failure — if insufficient validators online, TSS cannot sign. Unbounded.

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Network pause (incident response) | days (Sep 2026: paused until fix deployed) | [2] |
| Emergency upgrade | 2 days (Feb 2025 Bybit upgrade) | [3] |
| TSS exploit | days (requires fix + restart) | [2] |

## Ethereum Vault and KeyManager (on-chain, 2026-10-04)

- **Vault** `0xF5e1…2Bcc` is verified on Blockscout. Its KeyManager is `0xcd35…08Be`.
- **Keys:**
  - Governance key: Safe `0x38a4…34db`, 3 of 6.
  - Community key: Safe `0x5795…0762`, 5 of 9.
  - The aggregate key last validated at timestamp 1791125951, which is recent.
- **State:** the community guard is enabled and the Vault isn't suspended.
- **Emergency withdrawal is gated.** `govWithdraw` requires `onlyGovernor`, `onlyCommunityGuardDisabled`, `onlySuspended` and `timeoutEmergency`. Draining the Vault therefore needs both Safes, a suspension, and the validators' key to have gone silent for the emergency timeout.
- **Suspension isn't.** The governance Safe alone can `suspend`.

## Sources

1. https://docs.chainflip.io/ — Chainflip documentation
2. https://crypto.news/chainflip-loses-736442-usdt-in-tron-exploit/ — Sep 2026 TRON exploit details
3. https://cointelegraph.com/news/chainflip-blocks-bybit-hacker-funds-security-upgrade — Feb 2025 Bybit blocking
4. https://ape.law/blog/chainflip — Chainflip vs THORChain comparison on laundering response
6. Vault verified source (Blockscout) and KeyManager / Vault getters on Ethereum, 2026-10-04
5. https://blockfence.io/chainflip-loses-736k-in-tron-usdt-memo-exploit-pauses-network-wide-swaps/ — exploit technical details
6. https://github.com/chainflip-io/chainflip-backend — source repo (not yet read)
