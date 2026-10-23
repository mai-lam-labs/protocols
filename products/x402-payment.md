---
slug: x402-payment
name: x402 (payment leg)
framework: true                          # a standard: each deployment picks its facilitator, scheme, payTo and network; rate deployments as their own entries
scope: The x402 standard on EVM, same-chain, as far as the standard and its reference contracts fix it (EIP-3009 transferWithAuthorization, x402ExactPermit2Proxy, x402UptoPermit2Proxy, erc20ApprovalGasSponsoring). Facilitator, scheme, payTo and network are chosen per deployment and aren't rated here. Service delivery isn't covered
kind: payment
class: A                                 # for the reference exact and upto schemes only
cross_chain: false
chains: [Ethereum, Base, Arbitrum, Polygon, Optimism]   # both proxies have code at the same addresses on these (2026-10-04); other chains not checked
source_public: true
inherits: [permit2]
updated: 2026-10-06

verification:
  service: partial                       # reference facilitator read; facilitators differ per deployment
  exit: source-verified
  actors: source-verified
  admin: source-verified                 # no owner in source; code present and no proxy slot on five chains
  data: source-verified
  judgment: source-verified
  incidents: partial

exit:
  custody: user_wallet                   # tokens stay with the payer until the facilitator settles
  execution: self                        # the payer can cancelAuthorization (EIP-3009) or invalidateUnorderedNonces (Permit2), or let validBefore / deadline pass
  overrides:
    - who: the deployment's scheme and payTo, chosen by the resource server and its facilitator
      needs: unknown                     # outside the reference schemes, a deployment can route payment into its own contracts, with their own custody and admin
      parties: unknown
      how: a non-reference scheme or a payTo contract that holds funds, or approvals to contracts other than Permit2
      reach: one
      bounded: false
      cost: unknown
  refund_trigger: expiry_or_nonce
  exit_bound_seconds: 0                  # nothing to recover; an unsettled authorisation lapses at validBefore (60 s exact, 300 s upto by default)
  exit_bound_chosen_by: none
  standing_approval: unknown             # reference schemes: none (EIP-3009) or canonical Permit2 (immutable); other schemes can ask for anything

actors: []

admin:
  upgradeable: false                     # no proxy, no owner, no admin functions
  authority: none
  timelock_seconds: none
  immediate_functions: []
  grandfathered: full
  outside_exit_path: []

data_gates: []

judgment:
  screening: []                          # none in the contracts; hosted facilitators may screen, which only refuses service
  freeze_assets: []                      # a freeze of the payer's own USDC is the token's risk, not this protocol's
  freeze_pooled: false

service:
  integrator_access:                     # per facilitator; the reference one needs nothing, hosted ones (Coinbase CDP and others) set their own terms
    api_key: unknown
    identity: unknown
    revocable: unknown
    rate_limited: unknown
  operators:
    - role: Facilitator; verifies the payment and submits settlement
      entity: per deployment             # the resource server (merchant) picks it, not the payer
      single_operator: unknown
      source_public: unknown             # the reference implementation is public; hosted ones may not be
      deployment_config_public: false
  screening: unknown                     # per facilitator; some screen payers
  bypass: unknown                        # anyone can run a facilitator, but the payer can only use the one the merchant accepts

integration:
  calls: ["client signs an EIP-3009 authorisation or a Permit2 witness transfer and sends it in the X-PAYMENT header", "facilitator calls transferWithAuthorization or x402ExactPermit2Proxy.settle / x402UptoPermit2Proxy.settle"]
  signatures: ["EIP-3009 TransferWithAuthorization (USDC and similar)", "Permit2 PermitWitnessTransferFrom", "optional: a signed approve(Permit2) transaction for erc20ApprovalGasSponsoring"]
  offchain_required:
    - role: facilitator
      api_key: unknown
      rate_limited: unknown
  finisher: protocol                     # the facilitator settles
  gasless_start: [eip3009, permit2_approved] # the payer only signs; the gas-sponsoring extension covers the Permit2 approval
  monitoring: "facilitator settle response, or the token Transfer event"
  sdk: "x402 TypeScript and Python packages (Apache-2.0)"
  testnet: true
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: authorisation
  holder: designated                     # the payee, through its facilitator
  strike: signed
  expiry: user_chosen
  early_close: gas_same_chain
  premium: none
  terms_fixed_by: signature
  price_set_by: quote                    # the price the resource server posts
  discipline: none
  surplus_to: none
  extraction: []
  sides: [exact_out]                     # the payer authorises a fixed amount (exact) or a cap (upto)
  rate: par
  quote_validity: user_chosen            # validBefore: 60 s for exact, 300 s for upto by default
  partial_fill: counterparty_chooses     # the upto scheme lets the payee settle any amount up to the signed cap; exact settles the full amount
  partial_remainder: in_wallet

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: designated
    paid: deferred
    note: "the facilitator submits the EIP-3009 authorisation; it is paid by the resource server, not from the payment"
  - action: cancel
    performer: none
    paid: none
    note: "nothing to do: the authorisation expires"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: payment
    form: unknown
    note: "reference schemes are typed data (EIP-3009, Permit2 witness); other schemes are per deployment"

incidents: []

open_questions:
  - Which hosted facilitators support erc20ApprovalGasSponsoring, on which networks, and whether they screen payers
  - Which x402 deployments matter for routes, each to be rated as its own entry (facilitator, scheme, payTo contracts)
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: x402
    url: https://github.com/coinbase/x402
    commit: dd927a26cfefc98c24b3ec38b3a8f204dad0c60d
    commit_date: 2026-04-21
---

# x402 (payment leg)

**This entry rates the standard, not a deployment.** The reference contracts are immutable and the reference schemes leave funds in the payer's wallet. But every x402 deployment chooses its own facilitator, scheme, `payTo` and network. Some facilitators screen payers or need keys, and some schemes route payment into contracts with custody and admin of their own. The payer can't choose the facilitator; the merchant does. Ratings for a specific facilitator or merchant setup belong in their own entries, inheriting from this one.

**Primitive (one line):** HTTP 402-based payment protocol; client signs EIP-3009 `TransferWithAuthorization` (for USDC-like tokens) or Permit2 `PermitWitnessTransferFrom` (universal ERC-20 fallback); facilitator settles on-chain by calling the token/Permit2 contract; tokens stay in client wallet until settlement.
**Product scope of this entry:** x402 payment authorization and settlement (payment leg only — no service delivery enforcement; same-chain)

## Category 1 — Actor-gated edges

**Actors on exit path:** none. Tokens remain in user's wallet. Signed authorization is a permission to transfer, not a deposit. If facilitator never submits, or expiry passes, authorization expires unused and nothing happens. Source: [3] contracts + spec

**Cancellation mechanisms:**
- **EIP-3009 path:** `cancelAuthorization(from, nonce, v, r, s)` exists on the token contract (e.g., USDC). x402 SDK does NOT expose this — user would call USDC contract directly. Source: [3] `eip3009ABI` in constants.ts
- **Permit2 path:** `invalidateUnorderedNonces(wordPos, mask)` on Permit2 contract. x402 SDK does NOT expose this — user would call Permit2 directly. Source: [3] Permit2 standard
- **ERC-20 approval revocation:** `approve(Permit2, 0)` or `approve(recipient, 0)` prevents transfers. Source: [3] e2e test scripts
- **Passive:** do not share the signed authorization with the facilitator

**Expiry:**
- EIP-3009: `validBefore` timestamp (typically now + 60s for exact, now + 300s for upto). `validAfter` sets earliest execution time. Source: [3] `eip3009.ts:29`
- Permit2: `deadline` timestamp on PermitTransferFrom struct. `validAfter` in Witness struct. Source: [3] `x402BasePermit2Proxy.sol:130`, `ISignatureTransfer.sol:21-29`

**Actors involved in settlement (not exit):**
- Actor: Facilitator
  - Role: verifies payment authorization, settles on-chain, signals to resource server. Cryptographically bound in upto-amount mode (`facilitator` field in Witness).
  - Source: [3] `x402UptoPermit2Proxy.sol:41-45`

**Uptime / SLA:** N/A — no actor required for exit.

**Historical incidents:** N/A — no exit-path incidents possible by construction.

**Compellability profile:** N/A for exit path.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** none. Contracts are immutable. Deployed via CREATE2 with deterministic addresses. No proxy pattern, no `delegatecall`, no `Initializable`. `PERMIT2` address stored as `immutable`. Contracts README: "Immutable: No upgrade mechanism, no owner, no admin functions." Source: [3] `Deploy.s.sol`, contract source

**Immediate-effect admin functions:** none. Zero `onlyOwner`, `Ownable`, `Pausable`, or admin patterns in any contract. The word `owner` appears only as a parameter name meaning "token owner (payer)". Source: [3] grep of all .sol files

**Grandfathering:** N/A — no in-flight state.

## Category 3 — Data-oracle-gated edges

**Oracles in exit path:** none.

**Rate limits / circuit breakers / caps:** none.

## Category 4 — Judgment-oracle-gated edges

**Risk-scoring service integrations:** none in contracts.

**Stablecoin freeze exposure:** depends on underlying token. For EIP-3009 path on USDC: USDC contract has `blacklister` role and `pause()` function — these are token-level controls, not x402 controls. If user's address is blacklisted on USDC, the `transferWithAuthorization` call reverts, but user retains tokens (they're frozen at the token level, not by x402).

**Compliance oracle dependencies:** none.

## Composite

**Stuck-leg failure modes:**
1. Facilitator doesn't settle before expiry — authorization expires, user retains funds. Not stuck-leg.
2. User wants to cancel after signing — must call `cancelAuthorization` (EIP-3009) or `invalidateUnorderedNonces` (Permit2) directly on the respective contract. x402 doesn't wrap these. Risk window = time between signing and expiry (typically 60-300s).
3. Token-level freeze — protocol-independent.

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Authorization unsettled | instant (funds never left wallet) | [3] Class A |
| Cancel before expiry | immediate (on-chain call to token/Permit2) | [3] |
| Token-level freeze | unbounded | token-dependent |

**Cross-protocol correlation:** none. x402 has no shared infrastructure with other intent protocols.

**Assets / routes most affected:** USDC is primary asset (EIP-3009 support). Other ERC-20s use Permit2 path.

## Extension: `erc20ApprovalGasSponsoring`

**What it does:** gasless onboarding to the Permit2 path for tokens without EIP-2612 (USDT, WETH, etc.). The client signs, but does not broadcast, a normal EVM transaction `token.approve(Permit2, amount)` (typically MaxUint256) and puts the raw RLP hex in `extensions.erc20ApprovalGasSponsoring.info.signedTransaction`. The facilitator funds the client's native-gas deficit if any, broadcasts the signed approve, then calls `x402ExactPermit2Proxy.settle()` (or the upto proxy). Normative text exists. Source: [4] `specs/extensions/erc20_gas_sponsoring.md`

**Scope is Permit2 only:** facilitator validation rejects any approve whose spender isn't canonical Permit2 (`ErrErc20ApprovalSpenderNotPermit2`, `ErrErc20ApprovalTxWrongSpender`), checks `to == asset`, the `approve` selector, and that the recovered signer is the payer. It does not check the approve amount, nonce or fee fields, although the spec says the facilitator must check nonce and fees. A facilitator will not sponsor an approve to any other spender (e.g. CoW's GPv2VaultRelayer), so the extension only helps routes that pull through Permit2. Source: [2] `mechanisms/evm/src/shared/erc20approval.ts`

**Atomicity is claimed, not delivered:** the spec says funding → approve → settle "must be executed using an atomic batch transaction". The reference flow leaves this to an operator-supplied `sendTransactions()`. The e2e TypeScript facilitator runs it sequentially: send funding, wait for receipt, `sendRawTransaction`, wait, send settle, wait. Upstream main (751590a, 2026-10-02) documents both: "one hash per request for sequential execution, or one hash for an atomic bundle". A user-signed EOA transaction and facilitator transactions can only be made atomic with a builder bundle, which most L2 sequencers don't offer. Source: [2] `e2e/facilitators/typescript/index.ts:263-304`; [5] `mechanisms/evm/src/exact/extensions.ts`

**Revocability effect on the user:** none adverse. Before broadcast, the signed approve is bound to the user's current nonce, so any transaction the user sends first invalidates it. After broadcast, the result is a standing approval to Permit2, which is immutable, and every pull still needs a fresh Permit2 signature. Exit stays Class A. The funding transfer and the sequential window are the facilitator's risk: the user can consume the nonce with another transaction after funding lands, and the loss is bounded at one approve's gas.

**Adoption:** CDP (Coinbase) facilitator reported to support it; per-network coverage not established. Source: [6]

## Sources

1. https://x402.org/ — protocol overview and specification — retrieved 2026-09-16
2. https://github.com/coinbase/x402 — source repo (development fork; canonical at x402-foundation/x402); specifically:
   - `contracts/evm/src/x402BasePermit2Proxy.sol` — shared settlement logic, ReentrancyGuard, validAfter check (line 130)
   - `contracts/evm/src/x402ExactPermit2Proxy.sol` — exact amount Permit2 proxy, Witness struct (lines 33-36)
   - `contracts/evm/src/x402UptoPermit2Proxy.sol` — upto amount Permit2 proxy, facilitator-bound Witness (lines 41-45)
   - `contracts/evm/src/interfaces/ISignatureTransfer.sol` — Permit2 structs (lines 21-29)
   - `contracts/evm/script/Deploy.s.sol` — CREATE2 deployment
   - `typescript/packages/mechanisms/evm/src/exact/client/eip3009.ts` — EIP-3009 payload construction
   - `typescript/packages/mechanisms/evm/src/exact/facilitator/eip3009.ts` — EIP-3009 verification and settlement
   - `typescript/packages/mechanisms/evm/src/constants.ts` — EIP-3009 ABI, EIP-712 types
   — cloned and read 2026-09-16
3. `specs/schemes/exact/scheme_exact_evm.md` in repo — EIP-3009 as recommended method — read 2026-09-16
4. `specs/extensions/erc20_gas_sponsoring.md` and `docs/extensions/erc20-approval-gas-sponsoring.mdx` at pinned dd927a2; spec text unchanged at x402-foundation/x402 main 751590a — read 2026-10-03
5. https://github.com/x402-foundation/x402 at 751590a (2026-10-02) — diff of `typescript/packages/mechanisms/evm/src/exact/{extensions.ts,facilitator/permit2.ts}` against the pin — read 2026-10-03
7. eth_getCode and the ERC-1967 implementation slot for both proxies on Ethereum, Base, Arbitrum, Polygon and Optimism, 2026-10-04: code present (2,913 and 3,142 bytes) and no proxy
6. https://www.coinbase.com/developer-platform/discover/launches/x402-ERC20 — CDP launch post (403 to fetch; claim taken from search snippet, unverified) — 2026-10-03

## Notes / follow-ups

- x402 SDK does not expose cancellation functions (cancelAuthorization, invalidateUnorderedNonces) — users must call underlying contracts directly. This is a UX gap, not a protocol gap.
- Short default expiry windows (60-300s) mitigate the cancellation gap in practice
- Cross402 (multi-chain x402 facilitator) is a separate protocol that introduces cross-chain settlement — it inherits intent-protocol revocability concerns and is listed separately in the index
- Canonical repo has moved to x402-foundation/x402 — update INDEX if needed
