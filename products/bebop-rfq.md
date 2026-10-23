---
slug: bebop-rfq
name: Bebop RFQ
scope: Same-chain RFQ fills against private market makers through BebopSettlement 0xbbbbbBB520d69a9775E85b458C58c648259FAD5F and the BebopRouter 0xBeb0009ACa35087ce7cCF11637E24dd1Aad3bf2A that now wraps it, with the Bebop RFQ API in front
kind: swap
class: A
cross_chain: false
chains: [Ethereum, Arbitrum, Base]       # same address and code on these three (2026-10-04); others not checked
source_public: true                      # BebopSettlement verified on Blockscout; BebopRouter in bebop-dex/bebop-rfqa
inherits: [permit2]
updated: 2026-10-04

verification:
  service: partial                       # authentication and router migration from docs.bebop.xyz (2026-10-06)
  exit: source-verified                  # verified source on Blockscout; no owner, proxy or pause
  actors: source-verified
  admin: source-verified                 # code and ERC-1967 slot read on Ethereum, Arbitrum, Base; BebopRouter owner and routerSigner read
  data: source-verified
  judgment: partial                      # API-side screening not reviewed
  incidents: partial

exit:
  custody: user_wallet                   # settlement is one atomic transaction; nothing is held
  execution: self                        # don't sign, let expiry pass, or let the quote's expiry pass (orders revert with OrderExpired after it)
  overrides: []
  refund_trigger: expiry_or_nonce
  exit_bound_seconds: 0
  exit_bound_chosen_by: none
  standing_approval: immutable_target    # BebopRouter, BebopSettlement or Permit2, per the quote's approvalTarget; none is upgradeable, and the router pulls only with the taker's call or signature

actors: []

admin:
  upgradeable: false
  authority: eoa                         # BebopSettlement has no owner; BebopRouter's owner is EOA 0x1f0fafa9...ca63, whose only power is setRouterSigner
  timelock_seconds: none
  immediate_functions: []
  grandfathered: full
  outside_exit_path:
    - what: BebopRouter.setRouterSigner
      effect: which key co-signs router orders; it can stop router trades but can't move a taker's tokens without the taker's own call or signature
      caller: "owner EOA 0x1f0fafa95eb550405e738966a961eb7b4bd6ca63 (router signer today, EOA 0x00677f20...6727)"

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
    - role: RFQ API and market makers (quotes, maker signatures)
      entity: Bebop
      single_operator: true
      source_public: false
      deployment_config_public: false
  screening: unknown
  bypass: false                          # orders need a counterparty signature obtained through the API

integration:
  calls: ["request a quote from the RFQ API", "sign the order (or a Permit2 permit)", "submit the settlement transaction, or let Bebop submit it in gasless mode"]
  signatures: ["EIP-712 SingleOrder / MultiOrder / AggregateOrder; maker signatures come with the quote"]
  offchain_required:
    - role: Bebop API
      api_key: true
      rate_limited: true
  finisher: user
  gasless_start: unknown                 # disputed: whether gasless mode works for a token not yet approved to the Bebop contracts; see open_questions
  monitoring: "transaction receipt, or the Bebop order status endpoint"
  sdk: "Bebop Python SDK; TypeScript examples"
  testnet: unknown
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: counterparty_writes
  holder: user                           # the taker_address the maker signed for
  strike: quoted
  expiry: counterparty_chosen            # the quote's expiry
  early_close: free
  premium: none
  terms_fixed_by: signature
  price_set_by: quote
  discipline: unknown
  surplus_to: none
  extraction: []
  sides: [exact_in]                      # the maker signs taker_amount and maker_amount; whether the API also quotes by output wasn't read
  rate: firm                             # maker_amount for taker_amount, signed by the maker (BebopSettlement Single)
  quote_validity: counterparty_chosen    # the maker signs the order's expiry
  partial_fill: submitter_chooses        # gasless settleSingle has no caller check and takes filledTakerAmount from the caller; the taker's signature covers taker_amount and maker_amount but not the fill (hashSingleOrder). swapSingle, sent by the taker, lets the taker choose instead
  partial_remainder: in_wallet

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: designated
    paid: unknown
    fee: signed
    note: Bebop submits settle in gasless mode and is paid from the trade; whether this works without a prior approval transaction is disputed (open question)
  - action: cancel
    performer: none
    paid: none
    note: "nothing to do: the quote expires"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: RFQ order
    form: typed_data
    note: "EIP-712 order; router orders also need the user call or signature"

incidents: []

open_questions:
  - "Trade: discipline (CRITERIA.md, Trade)"
  - "Paid execution, start step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - "Whether gasless mode starts from an account holding no gas for a token not yet approved to the Bebop contracts (EIP-2612 or Permit2 in the order); settled the same way as for JAM"
  - Whether the RFQ API screens takers
  - Whether Bebop can revoke a single integrator's key
sources:
  - repo: bebop-rfqa
    url: https://github.com/bebop-dex/bebop-rfqa
    commit: cde98215e8522c36f410c4c75649a71208cb1f5b
    commit_date: 2026-07-29
---

# Bebop RFQ

**Primitive (one line):** User requests quote from PMMs (private market makers) via RFQ API; receives a complete settlement transaction; signs and broadcasts; BebopSettlement contract verifies trade terms and executes token transfers atomically in a single transaction.
**Product scope of this entry:** Bebop RFQ API + BebopSettlement contract (same-chain only)

## Category 1 — Actor-gated edges

**Actors on exit path:** none. "Bebop never takes custody of user tokens" [1]. Settlement is atomic — "If any condition fails, the entire transaction reverts" [2]. No deposit, no escrow.

**Cancellation mechanisms:**
- Off-chain: do not broadcast the settlement transaction (user controls broadcast)
- On-chain: unknown — source not public; nonce or deadline-based invalidation likely but unverified
- ERC20 approval revocation: user can revoke approval to BebopSettlement (0xbbbbbBB520d69a9775E85b458C58c648259FAD5F) or BebopRouter (0xBeb0009ACa35087ce7cCF11637E24dd1Aad3bf2A)

**Expiry:** unknown — likely timestamp-based (standard for RFQ) but requires source verification.

**Actors involved in filling (not exit):**
- Actor: Private Market Makers (PMMs)
  - Role: quote firm prices from proprietary on-chain inventory; co-sign the settlement transaction
  - Legal entity: multiple professional trading firms
  - Set size: multiple independent PMMs
  - Independence: independent firms
  - Source: [1]

**Uptime / SLA:** N/A — no actor required for exit.

**Historical incidents:** no exit-path incidents possible by construction (Class A). Source: [1][2]

**Compellability profile:** N/A for exit path.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** none. The verified source of `BebopSettlement` has no owner, proxy or pause. Contract at 0xbbbbbBB520d69a9775E85b458C58c648259FAD5F requires Etherscan verification to determine proxy pattern. Multiple audits exist [4] but audit reports may cover historical versions.

**Immediate-effect admin functions:** unknown — requires source read or Etherscan verified source inspection.

**Grandfathering:** N/A — no in-flight state (Class A, atomic settlement).

## Category 3 — Data-oracle-gated edges

**Oracles in exit path:** none (no exit path — no deposit).

**Rate limits / circuit breakers / caps:** unknown — requires source verification.

**Historical trigger data:** N/A.

## Category 4 — Judgment-oracle-gated edges

**Risk-scoring service integrations:** unknown — requires source verification. PMMs may apply their own compliance filters; this is voluntary and out-of-scope.

**Stablecoin freeze exposure:** minimal — no persistent contract balances (atomic settlement, no custody). Source: [1]

**Compliance oracle dependencies:** unknown.

## Composite

**Stuck-leg failure modes:**
1. PMM declines to quote or co-sign — order not created, user retains funds. Not a stuck-leg event.
2. Settlement transaction reverts on-chain — atomic, user retains funds. Not a stuck-leg event.
3. Stablecoin issuer freezes user wallet — protocol-independent.

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Order unfilled | instant (funds never left wallet) | [1] Class A |
| Settlement revert | instant (atomic) | [2] |
| Wallet-level freeze | unbounded | protocol-independent |

**Cross-protocol correlation:** none protocol-specific.

**Assets / routes most affected:** none. Class A, no asset-specific exposure.

## BebopRouter (2026-10-06)

Bebop's docs (`rfq-api/guides/router-migration-guide`) say RFQ quotes may now target **BebopRouter** `0xBeb0009A…bf2A`, which wraps `BebopSettlement`. Integrators should approve the quote's `approvalTarget`, which is the router, the settlement contract or Permit2.

Source is `bebop-dex/bebop-rfqa` `contracts/BebopRouter.sol`:
- It is OpenZeppelin `Ownable` and not upgradeable.
- Its only owner function is `setRouterSigner`. Every order needs the router signer's EIP-712 signature.
- **Pulling a taker's tokens is bound to the taker.** `swap` pulls from `msg.sender`, so the taker calls it. `settle`, for gasless trades, needs the taker's own EIP-712 or Permit2 signature over the order (`BebopRouter.sol:182-210`). A compromised owner or router signer can stop router trades, but can't spend standing approvals.

On-chain (Ethereum, Arbitrum, Base):
- Same code (18,974 bytes) at the same address, and no proxy.
- `owner()` is `0x1f0fafa95eb550405e738966a961eb7b4bd6ca63`, an EOA.
- `routerSigner()` is `0x00677f201e2f4a30d1d5b4e0ebbf672caf336727`, an EOA.

## Partial fills: who decides (2026-10-07)

- **The submitter decides in gasless mode, not the taker.** `settleSingle` and
  its permit variants have no caller check. The caller passes
  `filledTakerAmount`. `_executeSingleOrder` fills that much of the order
  (or all of it, if the value is 0 or above `taker_amount`), and scales
  `maker_amount` pro rata.
- **The taker's signature doesn't cover the fill size.** It covers
  `hashSingleOrder`: partner, expiry, taker, maker, nonce, both tokens,
  `taker_amount`, `maker_amount`, receiver and commands. So whoever submits a
  gasless order (Bebop, the maker, or anyone holding both signatures) can fill
  any part of it at the signed rate.
- **The rest can't be filled by the same quote.** The unfilled part stays in the
  taker's wallet, but the maker's nonce is consumed.
- **With `swapSingle`, the taker decides.** It requires
  `msg.sender == taker_address`, so the taker chooses the size.

This matters most to a gasless taker. A
signed order for an exact amount can come back partly filled, leaving the
remainder to route again. Source: BebopSettlement `0xbbbb…FAD5F`,
`settleSingle`, `_validateTakerSignatureForSingleOrder`, `hashSingleOrder`,
`_executeSingleOrder`.

## Source and on-chain state (2026-10-04)

`BebopSettlement` is verified on Blockscout (solc 0.8.19).
- **No admin:** it has no owner or admin role. Its state-changing functions are settlement plus two self-service registrations, `registerPartner` and `registerAllowedOrderSigner`.
- **Expiry:** every order type carries `expiry`, and settlement reverts with `OrderExpired` once it has passed.
- **Deployments:** the same code size is at the same address on Ethereum, Arbitrum and Base, with no ERC-1967 implementation.

## Sources

1. https://docs.bebop.xyz/how-bebop-works — architecture overview, "Bebop never takes custody" — retrieved 2026-09-16
2. https://docs.bebop.xyz/core-concepts/settlement-smart-contracts — contract addresses, atomic settlement guarantee — retrieved 2026-09-16
3. https://docs.bebop.xyz/core-concepts/token-approvals — approval targets per API — retrieved 2026-09-16
4. https://docs.bebop.xyz/audits — 9 audits from Zellic, MixBytes, Pessimistic, Decurity, ABDK, Nethermind, Offside Labs, Cyfrin (2022–2026) — retrieved 2026-09-16

## Incident search (2026-09-16)

No exploits, hacks, or stuck-fund incidents found in web search for Bebop DEX (2024-2025). Nine audits from reputable firms (2022-2026) provide some assurance, though source is private and cannot be independently verified.

## Notes / follow-ups

- Source repo is private — all Cat 2 fields are unknown and require either Etherscan verified source read or direct engagement with Bebop team
- Verify BebopSettlement proxy pattern on Etherscan at 0xbbbbbBB520d69a9775E85b458C58c648259FAD5F
- Verify BebopRouter proxy pattern on Etherscan at 0xBeb0009ACa35087ce7cCF11637E24dd1Aad3bf2A
- Check whether Permit2 is used for RFQ (docs mention "Permit2 for self-execution" in BebopRouter context)
- Audits listed may cover historical versions per docs disclaimer
- Bebop also supports Solana settlement — different architecture, not covered here
