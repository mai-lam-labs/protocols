---
slug: uniswapx
name: UniswapX
scope: UniswapX reactors (Dutch V1, Exclusive Dutch, Dutch V2, Dutch V3, Priority, Limit; the V4 modular Reactor is in source but no deployment is listed) and the Uniswap Labs order services in front of them
kind: swap
class: A
cross_chain: false                       # same-chain only; no cross-chain reactor in source
chains: [Ethereum, Arbitrum, Base, Optimism, BNB, Unichain, Polygon, Monad, XLayer, Worldchain, Soneium, Tempo, Robinhood, Arc, Celo, Avalanche, Blast, Zora, Ink]   # reactors deployed; the order services don't serve every one yet
source_public: true                      # contracts, order service and parameterization API; the Trading API isn't
inherits: [Permit2]
updated: 2026-10-06

verification:
  service: partial                       # order service and parameterization API read; Trading API not public
  exit: source-verified
  actors: source-verified
  admin: source-verified                 # owners and fee controllers read on-chain for Ethereum, Arbitrum and Base only
  data: source-verified
  judgment: source-verified
  incidents: partial

exit:
  custody: user_wallet                   # Permit2 pulls input only inside a fill transaction
  execution: self                        # Permit2.invalidateUnorderedNonces, or let the deadline pass
  overrides: []                          # nonce bitmap is keyed by msg.sender; no one else can cancel or block a cancel
  refund_trigger: expiry_or_nonce        # order deadline, or nonce invalidation by the swapper
  exit_bound_seconds: 0                  # funds never leave the wallet; a signed order stays fillable until its deadline or until the cancel lands
  standing_approval: immutable_target    # ERC-20 approval to Permit2: no owner, no proxy; each pull needs a fresh swapper signature bound to the reactor

actors: []

admin:
  upgradeable: false                     # no proxy in source; ERC-1967 implementation slot empty on the Ethereum reactors
  authority: dao                         # reactor owner on Ethereum is a Timelock (172800 s delay); Arbitrum owner is its L1 alias
  timelock_seconds: none                 # nothing on the exit path to delay
  immediate_functions: []
  grandfathered: full                    # a signed order's terms are fixed; the fee controller can only add outputs the filler pays, capped at 5 bps
  outside_exit_path:
    - what: setProtocolFeeController on every reactor (solmate Owned, onlyOwner)
      effect: sets the contract that adds fee outputs to each fill, capped at 5 bps per token; the controller is called during execute, so a controller that reverts stops fills, for everyone or for chosen swappers; cannot touch cancellation or wallet funds
      caller: reactor owner; the Uniswap governance Timelock on Ethereum; aliased L1 Timelock on Arbitrum, Unichain, XLayer, Soneium, Robinhood; other chains per deployments.md
      timelock_seconds: 172800           # Ethereum Timelock delay(); other chains not established
      current: feeController is address(0) on the Ethereum V2, V3 and Exclusive Dutch reactors, and the Arbitrum V3, Base V3 and Base Priority reactors
    - what: Cosigner (V2 and V3 Dutch orders, optional for Priority), named by the swapper in the signed order
      effect: sets decay start, exclusive filler and override bps, and can only improve amounts; without its cosignature a V2 or V3 order can't be filled; no power over cancellation

data_gates: []                           # deadline and Permit2 nonce only; nothing that can hold a cancel shut

judgment:
  screening: []                          # none in the reactors or in Permit2
  freeze_assets: []
  freeze_pooled: false                   # reactors hold tokens only inside a fill transaction

service:                                 # can they decline to serve me; funds stay in the wallet either way
  operators:
    - role: Trading API (api.uniswap.org); fronts order submission, builds orders, sets the cosigner to Uniswap Labs
      entity: Uniswap Labs
      single_operator: true
      source_public: unknown             # referenced as b/packages/services/trading in the UniswapX playbook; no public repo found
      deployment_config_public: false    # feature flags live in an internal config-service
    - role: Order service ("Gouda", uniswapx-service); validates and stores signed orders, serves them to fillers at GET /orders, cosigns Priority orders with a KMS key
      entity: Uniswap Labs
      single_operator: true
      source_public: true                # Uniswap/uniswapx-service, GPL-3.0
      deployment_config_public: partial  # CDK stacks are in the repo; env values (LABS_COSIGNER, API keys, RPC) are not
    - role: Parameterization API; runs the RFQ among quoters and cosigns V2/V3 orders (exclusive filler, start amounts)
      entity: Uniswap Labs
      single_operator: true
      source_public: true                # Uniswap/uniswapx-parameterization-api, GPL-3.0
      deployment_config_public: false    # quoter endpoints come from an S3 config
  screening:
    - kind: TRM Labs risk screening and OFAC list
      where: Uniswap Labs App (web interface)
      in_source: false
      enabled_in_production: true        # per the 2022 blog; whether it also applies to Trading API and order-service submissions is not established
    - kind: per-swapper disable_uniswapx flag
      where: Trading API feature flags (config-service)
      in_source: false                   # described in the UniswapX repo's playbook/NEW_CHAIN.md, not in public code
      enabled_in_production: unknown
    - kind: swapper address sent to RFQ quoters, who are "permissioned, vetted by Uniswap Labs" and may decline to quote
      where: parameterization API webhook request
      in_source: true
      enabled_in_production: true        # swapper is part of the published quote request schema
    - kind: issuer pre-transfer check for permissioned tokens
      where: order service, before accepting an order whose input is a permissioned token
      in_source: true                    # the check itself is in @uniswap/uniswapx-sdk, not read
      enabled_in_production: unknown
  bypass: partial                        # the reactors let anyone fill any valid signed order, and a swapper may name their own cosigner; but the order service only accepts the Labs cosigner, and no public order feed besides api.uniswap.org is known
  integrator_access:
    api_key: true                        # Trading API returned 401 without a key (2026-10-06); posting to api.uniswap.org/v2/order without one returned ACCESS_DENIED
    identity: signup                     # self-serve key from developers.uniswap.org/dashboard
    revocable: unknown
    rate_limited: true
    note: "reading orders works without a key (2026-09-29); quoting and posting need one (2026-10-06); per-IP WAF limits and 5 open orders per swapper"

integration:
  calls: ["POST trade-api.gateway.uniswap.org/v1/quote with x-api-key", "approve Permit2 if needed", "sign the Permit2 witness order", "POST /order", "GET /orders until filled, expired or cancelled"]
  signatures: ["Permit2 PermitWitnessTransferFrom with the reactor order as witness", "ERC-20 approval to Permit2 (one-time)"]
  offchain_required:
    - role: Uniswap Trading API (quotes, order submission, cosigning)
      api_key: true                      # docs: "All requests require an API key"; /v1/quote without one returned 401 Unauthenticated, 2026-10-06
      rate_limited: true
  finisher: protocol                     # fillers execute; the swapper only signs
  gasless_start: [permit2_approved]      # fillers pay gas, but the input token must be approved to Permit2 once, by transaction
  monitoring: "GET /orders by orderHash or swapper (open, filled, expired, cancelled, error), or the Fill event on the reactor"
  sdk: "@uniswap/uniswapx-sdk (TypeScript)"
  testnet: unknown
  steps: 3

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: exclusive                      # an exclusive filler first on Exclusive Dutch orders, then anyone
  strike: decaying
  expiry: api_chosen
  early_close: gas_same_chain
  premium: none
  terms_fixed_by: signature
  price_set_by: decaying_auction
  discipline: open_competition
  surplus_to: holder
  extraction: [exclusive_window]
  sides: [exact_in, exact_out]           # either the input or the outputs decay, never both (InputAndOutputDecay)
  rate: decaying
  quote_validity: api_chosen             # the Trading API that issues quotes is closed; the order deadline comes from it
  partial_fill: none                     # no partial fill in any reactor
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: the input token must be approved to Permit2 by transaction before a filler can pull it
  - action: cancel
    performer: none
    paid: none
    note: "nothing to do: the order expires at its deadline"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: order
    form: typed_data
    note: "Permit2 witness over the reactor order"

incidents:
  - date: unknown
    duration: ~24h
    user_funds_lost: false
    exits_blocked: false                 # order submission failed; wallets and cancellation unaffected
    cause: Order service PostOrder blocked by a noNetwork error from a bad RPC, unnoticed until later (comment in uniswapx-service bin/stacks/lambda-stack.ts)

open_questions:
  - Whether the Trading API or order service screens swapper addresses (TRM or otherwise) for UniswapX orders; the API Terms of Use page returned 403 and the 2022 screening post names only the web app
  - What disable_uniswapx does exactly (per-swapper block, or a request-level opt-out) and who sets it
  - Whether any filler or order feed outside api.uniswap.org serves UniswapX orders, which would make bypass real in practice
  - Who controls the reactor owners on chains other than Ethereum and Arbitrum (Base owner 0x31FAfd4889FA1269F7a13A66eE0fB458f27D72A9 is a contract whose control wasn't established)
  - Whether the V4 Reactor and TokenTransferHook are deployed anywhere, and with what owner
  - Which tokens the uniswapx-sdk treats as permissioned, and what the pre-transfer check calls
  - Date of the ~24h PostOrder outage, and any other order-service or cosigner outages
  - Whether deployed bytecode on each chain matches the pinned source (XLayer, Robinhood and Arc are not explorer-verified per deployments.md)
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: UniswapX
    url: https://github.com/Uniswap/UniswapX
    commit: eb7ce077036258b9510b42ad37aa920cf3aaf308
    commit_date: 2026-09-04
  - repo: uniswapx-service
    url: https://github.com/Uniswap/uniswapx-service
    commit: 5cd9d591b23d6137d4b9e043e6affd28aff6343e
    commit_date: 2026-09-24
  - repo: uniswapx-parameterization-api
    url: https://github.com/Uniswap/uniswapx-parameterization-api
    commit: 91b9ab2b4c0731a155dd4826f8f8a466e7cc61d0
    commit_date: 2026-09-28
  - repo: permit2
    url: https://github.com/Uniswap/permit2
    commit: cc56ad0f3439c502c246fc5cfcc3db92bb8b7219
    commit_date: 2023-09-29
---

# UniswapX

**Primitive (one line):** Swapper signs an EIP-712 order as a Permit2 witness; funds stay in the wallet until a filler calls `execute()` on the reactor, which pulls the input via `permitWitnessTransferFrom` and checks every output is delivered, all in one transaction.

Reactor variants in the pinned source: `DutchOrderReactor` (V1), `ExclusiveDutchOrderReactor`, `V2DutchOrderReactor` (time-based decay, cosigned), `V3DutchOrderReactor` (block-based nonlinear decay, cosigned, gas adjustment), `PriorityOrderReactor` (priority-fee auctions, optional cosigner), `LimitOrderReactor`, and the V4 modular `src/v4/Reactor.sol` with auction-resolver plugins and hooks. The docs list Ethereum on Dutch V2 and Arbitrum, Arc, Avalanche, Base, BNB, Ink, Monad, Robinhood, Tempo and Unichain on Dutch V3 [6]; the repo lists V3 reactors on 18 chains, plus Base's Priority reactor [3] `deployments.md`, `README.md`. No V4 deployment is listed.

## Category 1 — Actor-gated edges

**Actors on exit path:** none. Funds never leave the swapper's wallet until a fill; there is no deposit to recover.

**Getting out (swapper-controlled):**
- Permit2 nonce invalidation: `invalidateUnorderedNonces(wordPos, mask)` sets bits in `nonceBitmap[msg.sender]` [7] `src/SignatureTransfer.sol:130-133`. Only the swapper can set their own bits, and nothing can unset them, so no one can cancel for the swapper or stop a cancel short of censoring the transaction on-chain. Priority orders also check the bitmap before resolving [3] `PriorityOrderReactor.sol:130-137`.
- Deadline expiry: Permit2 rejects any pull after `permit.deadline`, which the reactors set from `info.deadline` [7] `SignatureTransfer.sol:60`, [3] `src/lib/Permit2Lib.sol`. V3, Priority and V4 also check the deadline in the reactor (`DeadlineReached`, `InvalidDeadline`, `DeadlinePassed`) [3] `V3DutchOrderReactor.sol:155-157`, `PriorityOrderReactor.sol:77-79`, `src/v4/Reactor.sol:172-174`; Dutch V1, Exclusive Dutch, V2 and Limit rely on Permit2's check alone.
- Until the cancel lands or the deadline passes, a signed order can still be filled on the terms signed. That is the trade the swapper agreed to, not a hold on their funds. The order service caps deadlines at one day for Dutch and Priority orders and one year for limit orders [9] `lib/handlers/post-order/index.ts:34`, `lib/handlers/post-limit-order/index.ts:23`.

**Standing approval:** the swapper approves Permit2, which has no owner, no proxy (the ERC-1967 implementation slot is empty) and no admin functions [7] `src/Permit2.sol`, [12]. A signature-transfer pull needs a fresh swapper signature over the token, amount, nonce, deadline, order witness and spender, and the spender is bound to `msg.sender`, so only the reactor named in the order can use it [7] `src/libraries/PermitHash.sol:93`, `SignatureTransfer.sol:51-68`. The reactor also checks `info.reactor == address(this)` [3] `src/lib/ResolvedOrderLib.sol:13-16`. Any AllowanceTransfer allowances the swapper has granted other spenders through Permit2 are separate from UniswapX.

**Actors involved in filling (not exit):**
- Filler: `execute`, `executeBatch` and their callback variants have no caller check [3] `src/reactors/BaseReactor.sol:31-88`. Docs: non-exclusive fillers are "Permissionless, no vetting" [8].
- Exclusive filler: during exclusivity only the named filler may fill, or others may if they improve outputs by `exclusivityOverrideBps`. With override 0 (strict), others are refused, but only until `exclusivityEnd`; after that `hasFillingRights` returns true for everyone [3] `src/lib/ExclusivityLib.sol:56-97`. On V2 and V3 the exclusive filler and the end of exclusivity (decay start) are set by the cosigner [3] `V2DutchOrderReactor.sol`, `V3DutchOrderReactor.sol:74-79`. On Ethereum exclusivity is "about 24 seconds, or 2 blocks" [8].
- RFQ quoters: "this set of market makers is permissioned and known to Labs", and quoters who fade can be ignored for a time [6], [10] `lib/cron/fade-rate-v2.ts`.
- Cosigner (V2, V3; optional on Priority): the swapper signs the cosigner's address into the order, and the cosigner signs `(orderHash, [chainid,] cosignerData)` [3] `src/lib/V3DutchOrderLib.sol:26, 215-216`, `src/lib/CosignerLib.sol`. It can only lower the input and raise outputs [3] `V3DutchOrderReactor.sol:94-116`, `V2DutchOrderReactor.sol`. It does choose when decay starts and who gets exclusivity, so it can move an order to the swapper's signed floor price at once; the floor is still what the swapper signed. On Priority orders it can only bring the auction start forward, not later [3] `PriorityOrderReactor.sol:87-99`. "Currently, the Uniswap Interface and Uniswap API set the cosigner to Uniswap Labs" [6]. Without a valid cosignature a V2 or V3 order can't be filled, but it also can't move funds.

**Uptime / SLA:** not needed for exit.

**Historical incidents:** no exit-path or fund-loss incidents found [13]. The order service's own comments record a PostOrder outage of about 24 hours from a bad RPC [9] `bin/stacks/lambda-stack.ts:575`. Unfilled orders are a recurring UX problem ("Your swap couldn't be filled at this time") [4]; funds stay in the wallet.

**Compellability profile:** none on the exit path. The fill path runs through Uniswap Labs (see Service).

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** none. No proxy, `delegatecall` or `selfdestruct` in `src/` [3], and the ERC-1967 implementation slot is empty on the Ethereum V2 and V3 reactors [12].

**Admin functions:** the only owner function on any reactor is `setProtocolFeeController` [3] `src/base/ProtocolFees.sol:103`, `src/v4/base/ProtocolFees.sol:118`. It is outside the exit path:
- The controller's `getFeeOutputs` is called inside `execute`, and its fee outputs are appended to the order, capped at `MAX_FEE_BPS = 5` of that token's order value [3] `ProtocolFees.sol:30, 41-98`. The filler has to deliver them. Because the controller is an external call, one that reverts would stop fills, for everyone or selectively by swapper. It can't touch cancellation or wallet balances.
- Owners, read on-chain [12]: all three Ethereum reactors (V2 `0x00000011F84B…`, V3 `0x0000000015757c…`, Exclusive Dutch `0x6000da47…`) are owned by `0x1a9C8182C09F50C8318d769245beA52c32BE35BC`, a Timelock with `delay()` 172800 s and `admin()` `0x408ED6354d4973f66138C91495F2f2FCbd8724C3` (not inspected further). The Arbitrum V3 reactor is owned by `0x2bad8182…46cd`, which has no code and is `0x1a9C…35BC` plus the Arbitrum L1→L2 alias offset. The Base V3 and Priority reactors are owned by `0x31FAfd48…`, a contract whose controller wasn't established. New V3 reactors take their owner from each chain's v4 `PoolManager.owner()` [3] `deployments.md`.
- `feeController()` returns `address(0)` on all six reactors read, so no protocol fee is taken there today [12].

Sample executors (`src/sample-executors/`) have owner and caller whitelists, but they belong to fillers, not swappers.

**Grandfathering:** full for the exit. Terms are fixed by the swapper's signature; only the fee outputs a filler must add can change, within the 5 bps cap.

## Category 3 — Data-oracle-gated edges

**Oracles on exit path:** none. Cancellation is a Permit2 bitmap write; expiry is `block.timestamp`.

**Oracles on fill path (not exit):**
- `block.basefee`: V3 adjusts input and outputs by the gas change since `startingBaseFee`, bounded by the swapper-signed `maxAmount`/`minAmount` [3] `V3DutchOrderReactor.sol:118-148`.
- `tx.gasprice - block.basefee`: Priority orders scale amounts by the priority fee [3] `PriorityOrderReactor.sol:114-124`.
- `additionalValidationContract` (V1–V3) and pre/post hooks (V4): named in the signed order; can reject fillers [3] `ResolvedOrderLib.sol:18-20`, `src/v4/Reactor.sol:160-183`.

**Rate limits / circuit breakers / caps:** none in the reactors. The order service limits each swapper to 5 open orders (a few canary and test addresses get 200) and applies per-IP WAF rate limits; no geo rule appears in its WAF [9] `lib/handlers/constants.ts:3-15`, `lib/services/UniswapXOrderService.ts`, `bin/stacks/api-stack.ts:130-395`.

## Category 4 — Judgment-oracle-gated edges

**On the exit:** none. Permit2 and the reactors have no blocklist or screening hook [3], [7].

**Stablecoin freeze exposure:** none pooled. Reactors hold tokens only inside one `execute()` [3] `BaseReactor.sol:90-129`. A frozen swapper wallet is frozen whatever the protocol.

## Service

Whether a swapper can get an order filled depends on Uniswap Labs' order pipeline, even though the exit doesn't:

- **Submission:** `POST` orders are "fronted by the Trading API"; the public edge `api.uniswap.org/v2` maps to the order service [9] `README.md`. The playbook names the Trading API's code as `b/packages/services/trading`, and no public repo was found. Its config-service holds `uniswapx_disabled_chains`, a `uniswapx_v3_rollout` percentage, and "`disable_uniswapx` … a per-swapper kill switch" [3] `playbook/NEW_CHAIN.md` §3.6.
- **Order service** (Uniswap/uniswapx-service, public): accepts V2 and V3 orders only if the cosigner is `LABS_COSIGNER`, and Priority orders only with `LABS_PRIORITY_COSIGNER`, whose cosignature it adds with a KMS key [9] `lib/util/field-validator.ts:223-231`, `lib/services/UniswapXOrderService.ts`. Its validation checks format, reactor, deadline, nonce, cosigner, on-chain simulation and, for permissioned tokens, an issuer pre-transfer check. No address screening appears in its source. Fillers poll `GET /orders` [8], [9].
- **Parameterization API** (Uniswap/uniswapx-parameterization-api, public): sends each RFQ request, including the `swapper` address, to quoter webhooks loaded from an S3 config, and cosigns the winning parameters [10] `README.md`, `lib/providers/webhook/s3.ts`. No address screening appears in its source.
- **Screening:** Uniswap Labs screens the web app with TRM Labs and the OFAC list; the 2022 post says this applies to the app, not the protocol [5]. Whether the Trading API applies it to UniswapX orders isn't established, and the API Terms of Use page couldn't be fetched (403) [11].
- **Bypass:** on-chain, anyone can fill any valid signed order, and a swapper can name any cosigner address, including their own. Dutch V1, Exclusive, Limit and uncosigned Priority orders need no cosigner [3]. In practice the order service won't take a non-Labs cosigner, and no other public order feed is known, so bypass depends on the swapper finding a filler directly.

## Composite

**Stuck-leg failure modes:** none that hold funds.
1. Order not filled before deadline: funds stay in the wallet.
2. Cosigner or order service unavailable, or the swapper refused by Uniswap Labs: order not filled; funds stay in the wallet.
3. Fee controller set to one that reverts: fills stop on that reactor; funds stay in the wallet.
4. Issuer freezes the swapper's own wallet: not protocol-specific.

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Order unfilled | none needed; funds never left | [3] |
| Cancel before deadline | one transaction by the swapper | [7] `SignatureTransfer.sol:130-133` |
| Service refuses or is down | none needed for funds; fills unbounded | [9] |
| Wallet-level freeze | issuer-dependent | not protocol-specific |

**Cross-protocol correlation:** shares Permit2 with other Uniswap products; an order-service or Labs outage stops UniswapX fills on every chain at once.

**Assets / routes most affected:** none for custody.

## Sources

1. https://developers.uniswap.org/contracts/uniswapx/overview — overview docs (now redirects to developers.uniswap.org/docs/liquidity/uniswapx/overview) — retrieved 2026-09-16, re-read 2026-09-28
2. https://blog.uniswap.org/uniswapx-protocol — UniswapX announcement — retrieved 2026-09-16
3. https://github.com/Uniswap/UniswapX (`source/UniswapX`) — `src/reactors/*.sol`, `src/base/ProtocolFees.sol`, `src/base/ReactorStructs.sol`, `src/lib/{ExclusivityLib,CosignerLib,ResolvedOrderLib,Permit2Lib,V2DutchOrderLib,V3DutchOrderLib,PriorityOrderLib}.sol`, `src/v4/Reactor.sol`, `src/v4/base/ProtocolFees.sol`, `src/v4/hooks/TokenTransferHook.sol`, `deployments.md`, `README.md`, `playbook/NEW_CHAIN.md`, `playbook/chains/README.md` — read 2026-09-28
4. https://support.uniswap.org/hc/en-us/articles/17515489874189 — "Why can my swap not be filled?" — retrieved 2026-09-16
5. https://blog.uniswap.org/trm — Uniswap Labs Address Screening Update (April 2022) — retrieved 2026-09-28
6. http://developers.uniswap.org/llms.mdx/docs/liquidity/uniswapx/concepts/auction-types — auction types, permissioned quoters, Labs cosigner, per-chain reactor types — retrieved 2026-09-28
7. https://github.com/Uniswap/permit2 (`source/permit2`) — `src/Permit2.sol`, `src/SignatureTransfer.sol`, `src/AllowanceTransfer.sol`, `src/libraries/PermitHash.sol` — read 2026-09-28
8. http://developers.uniswap.org/llms.mdx/docs/liquidity/uniswapx/filling/overview — filler overview: orders endpoint, permissioned quoters, permissionless non-exclusive fillers — retrieved 2026-09-28
9. https://github.com/Uniswap/uniswapx-service (`source/uniswapx-service`) — `README.md`, `lib/services/UniswapXOrderService.ts`, `lib/util/OffChainUniswapXOrderValidator.ts`, `lib/util/field-validator.ts`, `lib/handlers/constants.ts`, `lib/handlers/post-order/index.ts`, `lib/handlers/post-limit-order/index.ts`, `bin/stacks/api-stack.ts`, `bin/stacks/lambda-stack.ts` — read 2026-09-28
10. https://github.com/Uniswap/uniswapx-parameterization-api (`source/uniswapx-parameterization-api`) — `README.md`, `lib/providers/webhook/s3.ts`, `lib/cron/fade-rate-v2.ts` — read 2026-09-28
11. https://support.uniswap.org/hc/en-us/articles/43018872248589-API-Terms-of-Use and https://support.uniswap.org/hc/en-us/articles/8671777747597-Address-Screening-Guide — both returned 403 on 2026-09-28; contents not read
12. `eth_call` / `eth_getStorageAt` at latest block, 2026-09-28 (Ethereum block ~26076100, publicnode RPCs): `owner()`, `feeController()`, `permit2()` on the Ethereum V2, V3 and Exclusive Dutch reactors, Arbitrum V3, Base V3 and Base Priority reactors; `admin()` and `delay()` on `0x1a9C…35BC`; ERC-1967 implementation slot on Permit2 and the Ethereum V2/V3 reactors; code size of Permit2 and the owner addresses
13. Web search "UniswapX exploit OR outage OR incident 2025 2026 reactor" — no UniswapX incident found — 2026-09-28
14. http://developers.uniswap.org/llms.mdx/docs/liquidity/uniswapx/concepts/architecture — architecture page; nothing on the order API or screening — retrieved 2026-09-28
- https://docs.uniswap.org/contracts/uniswapx/overview — listed in the original protocol index; not yet retrieved
- https://developers.uniswap.org/docs/get-started/quickstart ("All requests require an API key"; self-serve key from the dashboard); `POST trade-api.gateway.uniswap.org/v1/quote` without a key returned 401, `POST api.uniswap.org/v2/order` returned ACCESS_DENIED, 2026-10-06

## Notes / follow-ups

- Corrected from the earlier entry: strict exclusivity lasts only until `exclusivityEnd`, not until the deadline; Dutch V1, Exclusive Dutch, V2 and Limit reactors don't check the deadline themselves (Permit2 does); `setProtocolFeeController` isn't an immediate-effect function on the exit path, and on Ethereum it sits behind a 2-day Timelock; the V4 Reactor has no listed deployment.
- The earlier "Route flags" section is replaced by the header.
- Remaining open questions are in the header.
