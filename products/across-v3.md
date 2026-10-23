---
slug: across-v3
name: Across V3
scope: Across V3 SpokePool and HubPool
kind: bridge
class: C
cross_chain: true
chains: unknown
source_public: true
inherits: []
updated: 2026-09-28

verification:
  exit: source-verified
  actors: source-verified
  admin: source-verified
  data: partial
  judgment: spec-only
  incidents: partial

exit:
  custody: escrow
  execution: automatic                   # bundle contents are fixed by UMIP-179; refund leaves execute permissionlessly
  overrides:
    - who: HubPool owner, a 3-of-5 Safe
      needs: 3 of 5 signers; no timelock
      how: relay emergencyDeleteRootBundle and a relayRootBundle without the deposit before its leaf executes; or executeExternalCall; or upgrade the spoke
      reach: one
      bounded: false
      cost: none on-chain
    - who: bundle proposers
      needs: a whitelisted proposer omits the refund, and no one disputes within the 1800 s liveness
      how: a finalised bundle without the refund; later bundle ranges never cover the deposit again
      reach: one
      bounded: false
      cost: none if undisputed; the 0.45 ABT bond if disputed
  refund_trigger: timeout                # fillDeadline, then the bundle whose range covers it
  exit_bound_seconds: unknown            # bundle cadence + 1800 s liveness; cadence not established
  standing_approval: upgradeable_target  # deposits pull from the UUPS SpokePool proxy

actors:
  - role: Bundle proposers (Dataworker), propose the root bundles that carry refunds
    entity: ABT-whitelisted proposers; Risk Labs Foundation the primary
    jurisdiction: [US]
    set: whitelist                       # BondToken.setProposer, owned by the HubPool owner Safe
    independence: single_org
  - role: Disputers, catch a bundle that omits a refund within the 1800 s liveness
    entity: anyone
    jurisdiction: pseudonymous
    set: permissionless                  # disputeRootBundle has no caller check; ABT mints from ETH
    independence: independent
  - role: Cross-domain messengers, relay root bundles to each SpokePool
    entity: unknown                      # each L2's canonical bridge
    jurisdiction: unknown
    set: unknown
    independence: unknown

admin:
  upgradeable: true                      # SpokePools are UUPS; HubPool isn't, but spokes can be re-pointed to a new one
  authority: multisig                    # Gnosis Safe 0xB524735356985d2F267FA010D681f061DfF03715, 3 of 5, no guard; an oSnap module adds a slower governance path
  timelock_seconds: none
  immediate_functions:
    - function: HubPool.setPaused
      caller: HubPool owner
      effect: stops proposing and executing bundles (and liquidity); disputes still work
    - function: HubPool.emergencyDeleteProposal
      caller: HubPool owner
      effect: deletes the pending bundle; its refunds wait for a later one
    - function: HubPool.relaySpokePoolAdminFunction
      caller: HubPool owner
      effect: any SpokePool admin call, below
    - function: SpokePool.emergencyDeleteRootBundle, relayRootBundle
      caller: HubPool owner, via relay
      effect: replace a relayed root with one that leaves a deposit out
    - function: SpokePool.executeExternalCall
      caller: HubPool owner, via relay
      effect: arbitrary call from the spoke
    - function: SpokePool.upgradeTo, upgradeToAndCall
      caller: HubPool owner, via relay
      effect: replaces the spoke holding deposits
    - function: SpokePool.pauseDeposits, pauseFills
      caller: HubPool owner, via relay
      effect: stops new deposits and fills; refund leaves and claims can't be paused
    - function: HubPool.setPoolRebalanceRoute, setCrossChainContracts
      caller: HubPool owner
      effect: can block executing or relaying bundles for a token or chain, stalling all refunds
    - function: HubPool.setBond, setLiveness; BondToken.setProposer
      caller: HubPool owner
      effect: changes who can propose and how long disputers have
  grandfathered: partial                 # fillDeadline is fixed; the refund depends on a later bundle under current admin state
  outside_exit_path: []

data_gates:
  - kind: bundle liveness
    where: HubPool, between proposeRootBundle and executeRootBundle
    trigger: every bundle
    blocks_exit: true
    reset: bounded                       # 1800 s on-chain; a dispute deletes the proposal and anyone whitelisted can re-propose at once
  - kind: token equivalence check
    where: SpokePool.requestSlowFill
    trigger: input and output tokens not equivalent in PoolRebalanceRoutes
    blocks_exit: false                   # the deposit falls back to the standard bundle refund

judgment:
  screening: []                          # no per-depositor blocklist in the contracts; relayers may filter fills, not refunds
  freeze_assets: [USDC, USDT]
  freeze_pooled: true                    # HubPool balances

service:
  integrator_access:
    api_key: optional                    # the contracts need none. The quote API (/suggested-fees, /swap/approval) answered keyless on 2026-09-29 and 2026-10-07, but the docs say production use requires an API key and integrator id and keyless requests "may be rate-limited or rejected"; /swap/gasless returned 403 without one
    identity: unknown                    # docs: a self-serve form issues credentials "instantly"; its fields weren't read (a JS form)
    revocable: unknown
    rate_limited: unknown
    note: "SpokePool.deposit and SpokePoolPeriphery need no key; a key matters only for Across's hosted quotes. outputAmount can be priced from /suggested-fees or computed independently"

integration:                             # not yet researched; see open_questions
  calls: ["SpokePool.deposit from the user's account, or SpokePoolPeriphery (0x97CCDBea4632140639aD5eA9b944aa034eb15fD4, current) depositWithPermit / depositWithPermit2 / depositWithAuthorization submitted by anyone"]
  signatures: ["periphery: EIP-712 DepositData (including submissionFees) plus an EIP-2612 permit, a Permit2 witness transfer, or an EIP-3009 receiveWithAuthorization"]
  offchain_required: unknown
  finisher: unknown
  gasless_start: [eip2612, eip3009, permit2_approved]  # SpokePoolPeriphery: anyone submits the user's signed deposit and is paid submissionFees from the input token in the same call
  monitoring: unknown
  sdk: unknown
  testnet: true                          # SpokePool, MulticallHandler and SpokePoolPeriphery (0x10D8b8DaA26d307489803e10477De69C0492B610, without the *Bytes variants) on Sepolia, Arbitrum Sepolia, Base Sepolia, Optimism Sepolia and Polygon Amoy; testnet.across.to/api answers keyless (2026-10-07)
  steps: unknown

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: anyone                         # any relayer, unless the deposit names an exclusiveRelayer until its exclusivity deadline
  strike: signed                         # outputAmount in the user's deposit
  expiry: unknown
  early_close: none                      # no cancel; only speedUpDeposit, which lowers the output
  premium: none
  terms_fixed_by: signature
  price_set_by: user_bound
  discipline: unknown
  surplus_to: holder                     # both amounts are fixed, so the relayer keeps whatever the market gives beyond them
  extraction: unknown
  sides: unknown
  rate: firm                             # inputAmount and outputAmount are both in the deposit; the depositor can sign a lower output with speedUpDeposit
  quote_validity: unknown
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: anyone
    paid: atomic
    fee: signed
    note: "SpokePoolPeriphery depositWithPermit, depositWithPermit2 or depositWithAuthorization: the user signs DepositData including submissionFees (amount, recipient); the call pulls input plus fee and pays the fee to the recipient, or to msg.sender when the signed recipient is zero (_paySubmissionFees)"
  - action: refund
    performer: anyone
    paid: unknown
    note: refund leaves execute permissionlessly once the bundle passes; whether the executor is paid wasn't read

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: deposit
    form: calldata
    bounds: bounded
    verifiable_locally: true
    api_optional: true
    note: "depositV3 on the SpokePool can be called directly"

incidents:
  - date: 2026-07-17
    duration: hours
    user_funds_lost: false
    exits_blocked: unknown               # deposits paused; transfers completed or refunded the same day
    cause: Off-chain SvmCpiEventsClient didn't check the Anchor event discriminator; forged Solana deposit events drained ~$3.35-4.5M of Risk Labs relayer capital

open_questions:
  - "What the Across API key form asks for (identity, KYB), and whether Across enforces the key on /suggested-fees and /swap/approval"
  - "Whether relayers fill on Across testnets in practice (the testnet API quotes about 10 s)"
  - "Trade: expiry, discipline, extraction (CRITERIA.md, Trade)"
  - "Quote: sides, quote_validity (CRITERIA.md, Trade); these decide which quote modes (exact, atleast, upto) the venue can serve, and who decides a partial fill"
  - "Paid execution, refund step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - Whether independent disputers check every bundle within the 1800 s liveness (RootBundleDisputed history, public validator bots); an omission that survives liveness is never picked up again under the rules
  - Identities of the five Safe signers
  - Full ABT proposer list (ProposerModified events on the bond token)
  - Bundle cadence in normal operation, which sets exit_bound_seconds
  - Per-chain spoke admin configuration (Universal_SpokePool local owner, ADMIN_UPDATE_BUFFER), and whether each deployed implementation matches the pinned commit
  - Whether proposers "soft pausing" one chain selectively would count as griefing under UMIP-157
  - Historical UMA disputes on Across bundles, and EVM-side incidents
  - Whether V4 ZK settlement changes any of this (may need its own entry)
  - Which messenger relays roots to each chain, and who operates it
  - Chains deployed
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: across-contracts
    url: https://github.com/across-protocol/contracts
    commit: d3aace41db6944a523eaa7633e1ab8ea9a9a2227
    commit_date: 2026-09-24
    note: "cloned 2026-09-28; the entry was read on 2026-09-16 at an unrecorded commit, so its line citations need re-checking against this one"
  - repo: umips
    url: https://github.com/UMAprotocol/UMIPs
    commit: 8f2c7101c3321b9e9365535290c94a44c4506992
    commit_date: 2026-07-21
---

# Across V3

**Primitive (one line):** SpokePool escrow on origin, relayer fronts destination fill from own capital, Dataworker aggregates fills into root bundle proposed to UMA-secured HubPool, HubPool relays roots back to SpokePools for permissionless refund execution.

## Gasless deposits through SpokePoolPeriphery (2026-10-07)

`SpokePoolPeriphery` lets anyone submit a deposit the user has only signed.
The current deployment is `0x97CCDBea4632140639aD5eA9b944aa034eb15fD4`, from
`broadcast/deployed-addresses.json`. It's verified on Ethereum Blockscout
(2026-07-29), and its code was confirmed on Ethereum, Arbitrum, Base, Polygon,
Optimism and BNB Chain. It has no proxy and no owner.

- **What the user signs:** `DepositData`, which carries the Across deposit,
  the exact input amount, a nonce and `submissionFees` (an amount and a
  recipient). How it's authorised depends on the entry point:
  - **`depositWithAuthorization`** takes a single EIP-3009
    `receiveWithAuthorization` signature, whose nonce is
    `keccak256(keccak256("BridgeWitness") ‖ abi.encode(depositData))`. The
    deposit terms are bound into the token authorisation. A `*Bytes` variant
    covers ERC-1271 and ERC-6492 signers.
  - **`depositWithPermit`** takes an EIP-2612 permit plus an EIP-712
    signature, with nonces from 1.
  - **`depositWithPermit2`** takes a Permit2 witness transfer.
- **What one call does:** it pulls the input plus the fee and pays the fee
  (`_paySubmissionFees`). A zero recipient means whoever submits is paid. It
  then deposits with `unsafeDeposit`, under a deposit id fixed in advance
  (`getDepositId`).
- **Earlier deployments:** `0x89415a82d909a7238d69094C3Dd1dCC1aCbDa85C` (two-signature EIP-3009) and
  `0x767e4c20F521a829dE4Ffc40C25176676878147f` (no EIP-3009) are earlier versions, still deployed.

## Testnets (2026-10-07)

Across runs a full testnet deployment, including the gasless periphery. All
addresses below are from `broadcast/deployed-addresses.json` and the older
`legacy-addresses.json`, and code was confirmed on each chain.

| Testnet | SpokePool | SpokePoolPeriphery | MulticallHandler |
|---|---|---|---|
| Sepolia (11155111) | `0x5ef6C01E11889d86803e0B23e3cB3F9E9d97B662` | `0x10D8b8DaA26d307489803e10477De69C0492B610` | `0x0F7Ae28dE1C8532170AD4ee566B5801485c13a0E` |
| Arbitrum Sepolia (421614) | `0x7E63A5f1a8F0B4d0934B2f2327DAED3F6bb2ee75` | same | same |
| Base Sepolia (84532) | `0x82B564983aE7274c86695917BBf8C99ECb6F0F8F` | same | same |
| Optimism Sepolia (11155420) | `0x4e8E101924eDE233C13e2D8622DC8aED2872d505` | same | same |
| Polygon Amoy (80002) | `0xd08baaE74D6d2eAb1F3320B2E1a53eeb391ce8e5` | same | same |

- **The testnet periphery** was verified on Sepolia Blockscout on 2026-03-05. It
  signs like mainnet's `0x97CCDBea4632140639aD5eA9b944aa034eb15fD4` (single-signature EIP-3009, permit nonces from
  1, predictable deposit ids), but has no `*Bytes` variants and no ERC-6492
  handling.
- **The API:** `https://testnet.across.to/api` answers without a key.
  - `/available-routes` lists routes.
  - `/suggested-fees` quoted Base Sepolia USDC to Arbitrum Sepolia with an
    estimated 10 s fill.
  - `/swap/approval` returns transactions to the testnet SpokePools, with no
    origin-swap routes.
- **Not checked:** whether relayers fill testnet deposits in practice.
- **Beware the per-chain `deployments/` files.** They still list `0x89415a82d909a7238d69094C3Dd1dCC1aCbDa85C` as
  the Base Sepolia periphery, and there is no code at that address.

## Category 1 — Actor-gated edges

**Actors on exit path (for expired-deposit refund):**
- Actor: Dataworker (bundle proposer)
  - Legal entity: Risk Labs Foundation (primary operator); other whitelisted proposers
  - Jurisdiction: Risk Labs is a US foundation entity [4]
  - Set size: `proposeRootBundle` has no caller check, but the bond must be paid in ABT, whose transfer into the HubPool reverts for a proposer not on its whitelist [3] `HubPool.sol:560-583`, `BondToken.sol:74-79`. `BondToken.setProposer` is `onlyOwner`, and the ABT owner is the HubPool owner Safe [3] `BondToken.sol:55-58`, [12].
  - Independence: Risk Labs is the primary proposer; the whitelist is controlled by the HubPool owner Safe
  - Source: [1], [3], [12]
- Actor: Disputers
  - Anyone can call `disputeRootBundle` within liveness [3] `HubPool.sol:715-717`; the ABT check doesn't apply to disputers, and ABT mints from ETH [3] `BondToken.sol:25`.
  - A bundle that leaves out a valid expired-deposit refund is invalid: every unfilled deposit past `fillDeadline` must be refunded in the bundle whose range covers it [10] UMIP-179:230, :548-556, and the proposed roots must match the ones computed under the rules [9] UMIP-157:374-385. Docs: "Anyone can dispute … You only need one honest validator" [11].
  - Liveness is 1800 s on-chain [12] (7200 s is only the code default, `HubPool.sol:83`). An omission that goes undisputed for that long is final: the next bundle's range starts after this one's [9] UMIP-157:166, :173, so the rules never pick the deposit up again.
- Actor: UMA DVM voters: **not on the exit path.** A dispute deletes the proposal at once [3] `HubPool.sol:797`, and any whitelisted proposer can re-propose; the DVM vote only settles the proposer's and disputer's bonds.
- Actor: HubPool owner: a 3-of-5 Gnosis Safe at 0xB524735356985d2F267FA010D681f061DfF03715 with no guard [12]. It isn't needed for exits; its powers are under Category 2.

**Can one refund be singled out?** Not by the proposers: leaving out one refund is disputable, so after a dispute they can only propose correctly or stall every refund. The HubPool owner can: by relaying `emergencyDeleteRootBundle` and a hand-made `relayRootBundle` that omits one depositor, before the leaf is executed; or through `executeExternalCall`; or by upgrading the spoke [3] `SpokePool.sol:375-428`, `HubPool.sol:249-253`. UMIP-179:634 already describes manual refund bundles "via spoke pool admin function", the same path used the other way.

**Uptime / SLA:** no published SLA; incident-free operation claimed since 2021 launch in marketing [1]. Independent verification required.

**Historical incidents:**
- Date: 2026-07-17, Duration: resolved same day (deposits paused, then restored within hours), Cause: Solana relayer exploit — attacker forged deposit events that never existed on-chain by exploiting a bug in Risk Labs' off-chain SvmCpiEventsClient component, which did not verify the 8-byte Anchor event discriminator. ~$3.35-4.5M drained from a Risk Labs-operated relayer. **No user funds lost** — only Risk Labs' relayer capital was affected. All genuine transfers completed or refunded same day. Team worked with SEAL_911 security response group. Source: [7] CryptoBriefing, [8] Cryptonomist
- Prior to this, Across had processed ~$34B in bridge volume since 2021 with no user fund losses. The Solana exploit was in off-chain relayer code, not in the EVM SpokePool/HubPool contracts analyzed in this entry.
- Note: the original marketing claim of "no user funds ever lost" remains technically true even after the Solana incident, since only Risk Labs' own capital was drained.

**Compellability profile:** proposers are concentrated around one US entity, but can only stall everything, not single out a refund. The per-deposit power sits with the 3-of-5 owner Safe, with immediate effect; signer identities are not yet known.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** HubPool is plain `Ownable`, not upgradeable [3] `HubPool.sol:41`; it can be replaced by re-pointing spokes with `setCrossDomainAdmin`. SpokePools are UUPS proxies [3] `SpokePool.sol:25, :43, :325`. The Ethereum spoke's owner is the HubPool [3] `Ethereum_SpokePool.sol:55`, [12]; L2 spokes accept admin messages from the HubPool via the native bridge, e.g. [3] `Arbitrum_SpokePool.sol:65-68`. `Universal_SpokePool` also has a local-owner path once its light client is stale [3] `Universal_SpokePool.sol:166-172`. The HubPool owner is a 3-of-5 Safe with no guard; an oSnap module (72h Snapshot vote, 172800 s liveness) is an additional path, not a constraint on the signers [12].

**Immediate-effect admin functions** (all `onlyOwner` on the HubPool, or relayed from it to spokes) [3]:
- `setPaused` (`HubPool.sol:218`): stops proposing and executing bundles and liquidity moves; disputes still work.
- `emergencyDeleteProposal` (`HubPool.sol:229-241`): deletes the pending bundle.
- `relaySpokePoolAdminFunction` (`HubPool.sol:249-253`), reaching SpokePool `onlyAdmin` functions: `pauseDeposits` (`:334`), `pauseFills` (`:345`), `relayRootBundle` (`:375`), `emergencyDeleteRootBundle` (`:389`), `executeExternalCall` (`:413-428`), `setCrossDomainAdmin`, `upgradeTo`/`upgradeToAndCall`.
- `setPoolRebalanceRoute` and `setCrossChainContracts` (`HubPool.sol:327-356`): can block executing or relaying bundles for a token or chain, which stalls everything through `noActiveRequests`.
- `setBond`, `setLiveness`, and `BondToken.setProposer`: change who can propose and how long disputers have.
- Refund execution itself can't be paused: `executeRelayerRefundLeaf`, `claimRelayerRefund` and `executeSlowRelayLeaf` have no pause modifier (`SpokePool.sol:1242-1324`). The functions `setPauseSendingBundles` / `setPauseClaims` named in [5] don't exist in current source.

**Grandfathering:** existing deposits' `fillDeadline` is fixed at deposit; however, expired-deposit refund routing depends on future bundles, which are subject to current admin state. In-flight deposits are exposed to admin changes that occur before their refund bundle is executed.

## Category 3 — Data-oracle-gated edges

**Oracles in exit path:**
- Slow-fill token equivalence check: `requestSlowFill` requires input and output tokens to be "equivalent" via `PoolRebalanceRoutes` mapping. If tokens are not equivalent, slow-fill path is unavailable and deposit routes through standard bundle refund. Source: [3] SpokePool.sol.

**Rate limits / circuit breakers / caps:** every bundle waits out the 1800 s liveness before execution [12]. A dispute deletes the proposal rather than holding it for a DVM vote, so a disputed bundle costs a re-proposal, not a voting round [3] `HubPool.sol:797`.

**Historical trigger data:** unknown — requires review of historical dispute activity on Across bundles.

## Category 4 — Judgment-oracle-gated edges

**Risk-scoring service integrations:** none in the contracts; no per-depositor or per-deposit blocklist exists [3]. Relayers may apply their own compliance filters (fills are voluntary); this is out-of-scope for the protocol itself but affects fill probability for specific addresses.

**Stablecoin freeze exposure:**
- USDC pool at HubPool address is subject to Circle freeze — if the HubPool USDC balance is frozen, all USDC-denominated flows halt. Source: [4] Circle USDC blacklist function.
- Same for USDT held.
- A refund to a frozen recipient doesn't block the leaf: the failed transfer is deferred and claimable [3] `SpokePool.sol:1490-1500`.

**Compliance oracle dependencies:** none in the protocol itself.

## Composite

**Stuck-leg failure modes:**
1. Proposers leave the expired deposit out of a bundle and no one disputes within liveness
2. Proposers stop proposing, or keep proposing invalid bundles that are disputed
3. HubPool owner deletes or replaces a bundle or root containing the deposit
4. Cross-domain messenger (Arbitrum inbox, Optimism messenger, etc.) fails to relay `relayRootBundle` message to SpokePool
5. USDC/USDT issuer freezes the SpokePool or HubPool address
6. HubPool paused, or a route or chain disabled

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Undisputed omission | none under the rules; only a manual admin root | [9] UMIP-157:166, :173 |
| Proposers stall | unbounded, affects every refund; owner can add proposers or open proposing with `setBond` | [3] |
| Owner deletes or replaces a root | unbounded, per deposit | [3] |
| Cross-domain messenger failure | unbounded (external dependency on L2 canonical bridges) | protocol design |
| Stablecoin issuer freeze | unbounded | [4] |
| Pause or route disabled | unbounded (owner-controlled) | [3] |

**Cross-protocol correlation:** any USDC-holding protocol fails together for USDC freezes. Any Ethereum L2-dependent protocol fails together for canonical bridge messenger failures.

**Assets / routes most affected:** USDC and USDT flows (highest freeze exposure); L2 destinations with unreliable messengers (higher completion-path failure rate).

## Sources

1. https://docs.across.to/introduction/security — Across security model docs — retrieved 2026-09-16
2. https://blog.uma.xyz/articles/case-study-how-uma-secures-across-protocol — UMA case study — retrieved 2026-09-16
3. https://github.com/across-protocol/contracts (`source/across-contracts`) — `contracts/hub-pool/HubPool.sol`, `contracts/hub-pool/BondToken.sol`, `contracts/spoke-pools/SpokePool.sol`, `Ethereum_SpokePool.sol`, `Arbitrum_SpokePool.sol`, `Universal_SpokePool.sol` — read 2026-09-28
4. https://risklabs.foundation/ — Risk Labs foundation page — retrieved 2026-09-16
5. https://www.openzeppelin.com/news/uma-across-v2-audit-2023 — OpenZeppelin V2 audit noting pause functionality addition — retrieved 2026-09-16
6. https://docs.across.to/introduction/security/validating-root-bundles — validator instructions and bundle validation rules — retrieved 2026-09-28
7. https://cryptobriefing.com/across-protocol-solana-bridge-attack/ — Solana relayer attack confirmation, user funds safe — retrieved 2026-09-16
8. https://en.cryptonomist.ch/2026/07/24/across-solana-relayer-attack/ — technical details of SvmCpiEventsClient bug — retrieved 2026-09-16
9. UMIP-157 (Across bundle validity) in https://github.com/UMAprotocol/UMIPs (`source/umips`) — read 2026-09-28
10. UMIP-179 (Across V3 bundle construction), same repo and commit — read 2026-09-28
11. https://docs.across.to/reference/security-model-and-verification/disputing-root-bundles — dispute docs — retrieved 2026-09-28
12. Ethereum mainnet `eth_call` at latest block, 2026-09-28: HubPool `owner()`, `bondToken()`, `bondAmount()`, `liveness()`, `paused()`; ABT `owner()`, `proposers()`; Safe `getThreshold()`, `getOwners()`, `getGuard()`, modules; spoke `owner()`/`crossDomainAdmin()` and ERC-1967 slots on Ethereum and Arbitrum

## Notes / follow-ups

- The earlier note that the owner is at 0xc186fA914353c44b2E33eBE05f21846F1048bEda was wrong: that is the HubPool itself.
- `across-protocol/relayer` (the dataworker and disputer implementation) isn't publicly clonable; a fork at github.com/informalsystems/across-protocol-relayer is unverified.
- Only the Ethereum and Arbitrum spokes' admin configuration has been checked on-chain.
- Remaining open questions are in the header.
