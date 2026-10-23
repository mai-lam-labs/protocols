---
slug: dzap-swap
name: DZap Core swap
scope: Same-chain swaps through DZap Core (Trade API, api.dzap.io) and DZapDiamond, either sent by the user or gasless through GasLessFacetV2.executeSwap; EVM only. Holds the Diamond's admin and the shared service facts for dzap-bridge
kind: swap
class: unknown
cross_chain: false
chains: unknown                          # DZapDiamond on 60+ EVM chains per the docs' address list; read on Ethereum, Arbitrum, Base, BSC, Polygon, Optimism, Avalanche
source_public: partial                   # contracts verified on Blockscout and in DZapIO/DZapCoreContracts (older than the deployed GasLessFacetV2); APIs not public
inherits: []
updated: 2026-10-08

verification:
  service: partial                       # both APIs probed without a key; fee validator read on-chain
  exit: source-verified                  # a swap is one transaction through DZapDiamond
  actors: source-verified
  admin: source-verified                 # Diamond owner and diamondCut guard read in verified source and on-chain
  data: source-verified
  judgment: partial                      # no screening found in the contracts or at quote time
  incidents: partial                     # web search 2026-10-06 found nothing

exit:
  custody: user_wallet                   # the swap is atomic: tokens are pulled and the output paid in one transaction
  execution: self
  overrides:
    - who: DZapDiamond owner, EOA 0x45679cdf728abdcdfce0f03a8f1d22ba49babc72, the same on every chain checked
      needs: one key; no timelock
      parties: key
      how: diamondCut (guarded only by enforceIsContractOwner) adds a facet that spends any standing approval to the Diamond, the Trade API's "single trusted spender"
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: none                   # nothing to refund: the swap completes or reverts
  exit_bound_seconds: 0
  exit_bound_chosen_by: none
  standing_approval: upgradeable_target  # approvals to DZapDiamond can be re-pointed by diamondCut; a permit or Permit2 witness pull leaves none

actors: []

admin:
  upgradeable: true                      # DZapDiamond is an EIP-2535 diamond
  authority: eoa                         # 0x45679cdf...bc72 on every chain checked
  timelock_seconds: none                 # the security page says "upgrades behind multi-sig + timelock"; the architecture page lists that as "coming next"; on-chain, one EOA with no delay
  immediate_functions:
    - function: DZapDiamond.diamondCut
      caller: owner EOA
      parties: key
      effect: replaces or adds the code that spends users' approvals to the Diamond
  grandfathered: none
  outside_exit_path:
    - what: GasLessFacetV2 fee validator (set in Diamond storage)
      effect: decides which gasless trades can execute; not a power over funds

data_gates: []

judgment:
  screening: []                          # none found in the contracts or at quote time
  freeze_assets: []
  freeze_pooled: false

service:
  integrator_access:
    api_key: optional                    # "Every endpoint on both APIs works without a key"; Trade /v1/quotes confirmed 2026-10-06
    identity: none                       # keys are issued to partners on request (Discord or email)
    revocable: unknown
    rate_limited: true                   # per IP without a key (Trade buildTx 5 requests per 60 s per IP)
  operators:
    - role: Trade API; route building (quotes, buildTx)
      entity: DZap
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: Core gasless fee validator; co-signs every GasLessFacetV2 swap and bridge (handleFeeVerification)
      entity: DZap                       # EOA 0xd370bd3170d1adfe7d376b4c009dc00f84360efb (getFeeValidator() on Ethereum)
      single_operator: true
      source_public: false
      deployment_config_public: false
  screening:
    - kind: "gasless route approval: every GasLessFacetV2 execution needs DZap's fee-validator signature"
      where: GasLessFacetV2 (handleFeeVerification), on every chain
      in_source: true
      enabled_in_production: true        # one EOA can decline to sign any gasless trade; an OFAC-sanctioned address was quoted like any other on 2026-10-06, so no address screening was seen
  bypass: false                          # the user-sent path takes calldata the Trade API builds; the gasless path needs DZap's signature

integration:
  calls: ["POST api.dzap.io/v1/quotes", "POST /v1/buildTx", "user-sent: approve DZapDiamond, sign and send the returned transaction (or POST /v1/broadcast)", "gasless: sign an EIP-2612 permit and the SignedGasLessSwapData intent over the returned hashes, POST /v1/gasless/executeTx", "GET /v1/status"]  # formats under Integration flow
  signatures: ["gasless: EIP-712 SignedGasLessSwapData (domain DZapVerifier, version 1, salt keccak256('DZap-v0.1')), checked ECDSA-only, plus DZap's fee-validator SignedFeeData", "EIP-2612 permit or Permit2 witness"]
  offchain_required:
    - role: Trade API, and DZap's fee signature for gasless
      api_key: optional
      rate_limited: true
  finisher: user                         # user-sent; gasless is submitted by DZap's relay (/v1/gasless/executeTx), the only holder of the fee signature
  gasless_start: [eip2612, permit2_approved, prior_approval]  # only EIP-2612 works from a zero native balance (Core gasless docs)
  monitoring: "status endpoint"
  sdk: "@dzapio/sdk, @dzapio/widget, @dzapio/wallet (TypeScript); MCP server"
  testnet: partial                       # DZapDiamond 0xb3926deF2e0989B0700a57034C9A211bfBcF858B on Sepolia, Arbitrum, Base and Optimism Sepolia with the mainnet GasLessFacetV2, owner and fee validator; the Trade API enables Sepolia and Arbitrum Sepolia, but no same-chain swap route was quoted there (2026-10-08)
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: spot
  holder: none
  strike: signed                         # the minimum output is inside swapData, which the user signs (gasless) or sends
  expiry: user_chosen                    # the gasless intent's deadline
  early_close: free                      # don't sign or send
  premium: none
  terms_fixed_by: calldata
  price_set_by: quote                    # DZap's route over DEXes; no auction
  discipline: unknown
  surplus_to: unknown
  extraction: [public_bound]             # a user-sent swap goes to the public mempool with its bound
  sides: [exact_in]
  rate: unknown                          # whether the route pays out above the signed minimum wasn't read
  quote_validity: unknown
  partial_fill: none                     # one transaction
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: designated
    paid: atomic
    fee: signed
    note: "gasless: any msg.sender holding DZap's fee-validator signature calls GasLessFacetV2.executeSwap and is paid the user-signed executor fee in the same call; the API never returns that signature, so in practice DZap's relay submits. The user-sent path needs native gas"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: Trade API (user-sent)
    form: calldata
    bounds: arbitrary
    verifiable_locally: false
    api_optional: false
    target_admin: key
    note: "calldata to DZapDiamond, re-cut by one EOA"
  - path: gasless (GasLessFacetV2.executeSwap)
    form: typed_data
    bounds: arbitrary
    verifiable_locally: false
    api_optional: false
    target_admin: key
    note: "the user signs swapDataHash and executorFeesHash; buildTx returns the hashes but not swapData or the fee struct, so the minimum output and fee can't be checked before signing (live, 2026-10-08)"

incidents: []                            # none found (web search 2026-10-06)

open_questions:
  - "Quote: rate, quote_validity (CRITERIA.md, Trade)"
  - "Trade: discipline, surplus_to (CRITERIA.md, Trade)"
  - Whether the user-sent swap path also needs a DZap signature, or whether DZapDiamond calldata can be built without the API
  - Who holds owner EOA 0x45679cdf...bc72 and fee validator EOA 0xd370bd...0efb, and when the "multi-sig + timelock" the security page describes will apply
  - Whether DZap would return swapData and the executor-fee struct with a gasless build, so the signed hashes can be checked locally
  - Audit reports for the current Diamond facets
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: dzap-dzapcorecontracts
    url: https://github.com/DZapIO/DZapCoreContracts
    commit: f47dda7326dd187c1d75981949a9357662448401
    commit_date: 2025-09-04
    note: "older than the deployed GasLessFacetV2; see dzap-gaslessfacet-verified"
  - repo: dzap-sdk
    url: https://github.com/DZapIO/sdk
    commit: 776f559af90b38438bc79246c83c95868b001c91
    commit_date: 2026-09-22
  - repo: dzap-audits
    url: https://github.com/DZapIO/audits
    commit: 5845bdbc31f8d7b79cec6480745ffe4549db4adc
    commit_date: 2024-06-25
  - repo: dzap-gaslessfacet-verified     # verified source of the deployed facet, from eth.blockscout.com
    url: https://eth.blockscout.com/address/0xc3584c31f9e7c9c3a1cbfc6b314a4a6446fae896
    commit: "verified 2026-02-27"
    commit_date: 2026-02-27
  - repo: dzap-docs-2026-10-08           # snapshot of docs.dzap.io pages and openapi.yaml
    url: https://docs.dzap.io
    commit: "snapshot"
    commit_date: 2026-10-08
---

# DZap Core swap

**Primitive (one line):** An aggregator's same-chain swap through DZapDiamond. The user sends the route DZap built, or signs a gasless intent that anyone holding DZap's fee signature submits for a signed fee.

## DZap's entries

DZap sells three products on one routing engine (the docs list a fourth, DZap
Earn, with no pages). Each has its own entry:

| Entry | Product | Contract |
|---|---|---|
| this one | Core same-chain swaps (Trade API, `api.dzap.io`), sent or gasless | `DZapDiamond` |
| [dzap-bridge](dzap-bridge.md) | Core bridges, gasless bridges and Ghost Mode | `DZapDiamond` |
| [dzap-fuse](dzap-fuse.md) | Fuse intents (`zap.dzap.io`) | `DZapZapCore`, a separate contract |

Core swap and Core bridge share one contract, one owner, one API and one fee
validator, so those facts live here and `dzap-bridge` points at them
(`same_as`). Fuse shares none of the contract facts and is self-contained.

`DZapDiamond` is `0xF708e11A7C94abdE8f6217B13e6fE39C8b9cC0a6` on most chains
(`0xb3926deF2e0989B0700a57034C9A211bfBcF858B` or
`0xFcf64165772037F9B750F7c9a7391e7e926A8a53` on others, per the docs' address
list).

## Gasless swaps, as deployed (2026-10-08)

Core gasless lives in `GasLessFacetV2`
`0xc3584c31f9e7c9c3a1cbfc6b314a4a6446fae896`, a facet of `DZapDiamond`. The
verified facet (2026-02-27) is newer than the public repo (2025-09-04).

- **Entry points:** `executeSwap`, `executeMultiSwap` and
  `executeMultiSwapWithWitness`, registered on Ethereum, Base and Arbitrum.
  They are `external`, with no caller check, and each pays `_executorFeeInfo`
  to `msg.sender` in the same call. The facet's bridge functions are in
  [dzap-bridge](dzap-bridge.md).
- **Two signatures are needed:**
  - **The user's,** checked by OpenZeppelin `ECDSA.recover` (ECDSA only)
    under `EIP712Domain(string name,string version,uint256 chainId,address verifyingContract,bytes32 salt)`,
    with name `DZapVerifier`, version `1` and salt `keccak256("DZap-v0.1")`.
    It's either
    `SignedGasLessSwapData(bytes32 txId,address user,uint256 nonce,uint256 deadline,bytes32 executorFeesHash,bytes32 swapDataHash)`
    or the Permit2 witness `DZapSwapWitness`.
  - **DZap's fee validator's:** `SignedFeeData(bytes32 txId,address user,uint256 nonce,uint256 deadline,bytes32 feeDataHash,bytes32 dataHash)`,
    checked against `getFeeValidator()`. That's the EOA
    `0xd370bd3170d1adfe7d376b4c009dc00f84360efb` on Ethereum.
- **What the fee validator means:** whoever submits, every Core gasless trade
  (swap or bridge) needs DZap's key to approve it.
- **Tokens are pulled by:** an EIP-2612 permit, a Permit2 witness transfer, or
  a Permit2 approval (`LibAsset.deposit`).
- **Docs:** a $1 minimum per pair, source tokens must be on DZap's per-chain
  gasless list, and only EIP-2612 works from a zero native balance.

**What this means for an integrator.**
- **Keyless:** the Trade API answers without a key (live, 2026-10-06). Keys
  only raise per-IP limits, for example 5 `buildTx` calls per 60 s.
- **The submitter is paid in the same call,** a fee the user signs.
- **A plain EOA's signatures work.** So do a delegated account's, signed with
  its own key, because the check is ECDSA-only. A contract account without a
  key can't sign.
- **But DZap's fee-validator EOA decides whether any gasless trade executes,**
  and the API never hands that signature out, so DZap's relay is in practice
  the only submitter (see Integration flow, step 4).
- **The signed hashes can't be checked.** A gasless build returns
  `swapDataHash` and `executorFeesHash` without their preimages, so the
  minimum output and fee the user signs are DZap's word.
- **The price is the route DZap builds,** a DEX path whose minimum output the
  user signs through `swapDataHash`. There's no auction.

## Integration flow (Trade API)

Base URL `https://api.dzap.io/v1`, JSON bodies. Bridges use the same calls
with a different `toChain` ([dzap-bridge](dzap-bridge.md)). Request and
response shapes are from the SDK types (`source/dzap-sdk`, `src/types/index.ts`)
and the API reference in `source/dzap-docs-2026-10-08` (`api_trade_*.md`,
`cookbook_trade_gasless.md`), checked against live keyless calls on 2026-10-08.

**Keys and limits.** `x-api-key` is optional. Without it, `/quotes` and
`/buildTx` allow 5 requests per 60 s per IP. Past that, the API answers:

```json
{ "error": "Rate limit exceeded", "message": "Too many requests for route /quotes. Try again later.",
  "retryAfter": 60, "resetTime": "2026-10-07T18:40:56.861Z", "limit": 5, "window": 60 }
```

**Discovery.**
- `GET /chains` returns an array of chains. Useful fields: `chainId`, `name`,
  `chainType` (`evm`, `svm`, `bvm`…), `mainnet`, `isEnabled`, `version`
  (`v2` is the gasless router), `contracts.router` (the `DZapDiamond` to
  approve and to sign against), `rpcProviders[]`.
- `GET /token/tokens?chainId=` returns a map of tokens. Each carries
  `permit.eip2612.supported` and `permit.permit2.supported`; the zero-gas path
  needs the first.

1. **Quote:** `POST /quotes`.

   ```json
   {
     "fromChain": 42161,
     "account": "0xUser",
     "gasless": true,
     "data": [{
       "amount": "5000000",
       "srcToken": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "srcDecimals": 6,
       "destToken": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", "destDecimals": 18,
       "toChain": 42161,
       "slippage": 1
     }]
   }
   ```

   - `slippage` is in percent. `data[]` takes several pairs at once.
   - Optional: `private` (Ghost Mode, bridges only), `bridges` and `dexes` as
     `{ allow: [], deny: [] }`, `filter`, `disableEstimation`, and a
     `timingStrategy` for how long to wait for providers.
   - The response is keyed by pair, `"<fromChain>_<srcToken>-<toChain>_<destToken>"`.
     Each pair has `recommendedSource`, `bestReturnSource`, `fastestSource`,
     `quoteRates` (one quote per provider id) and `unavailableRoutes` (per
     provider: `errorType` of `ROUTE`, `AMOUNT`, `SLIPPAGE` or `UNKNOWN`, and a
     reason such as `UNSUPPORTED_PAIR`). A pair with no route comes back as
     `{ "status": "error", "message": "No quotes available for this pair: …" }`.
   - Each quote has `srcAmount`, `destAmount`, `minDestAmount`, the USD values,
     `fee` (`gasFee[]`, `protocolFee[]`, `providerFee[]`, each with `amount`,
     `amountUSD` and `included`), `priceImpactPercent`, `duration`, `gasless`,
     `steps[]`, `path[]` and `additionalInfo`, which must be passed back to the
     build.
   - **Live:** 5 USDC → WETH on Arbitrum, gasless, recommended `uniswap`,
     `destAmount` 1952144829408579, `minDestAmount` 1932591134011644.
     With `gasless: true`, `destAmount` is already net of the executor fee.

2. **Build:** `POST /buildTx`.

   ```json
   {
     "sender": "0xUser",
     "refundee": "0xUser",
     "fromChain": 42161,
     "gasless": false,
     "data": [{
       "amount": "5000000",
       "srcToken": "0xaf88…5831", "srcDecimals": 6,
       "destToken": "0x82aF…Bab1", "destDecimals": 18,
       "toChain": 42161,
       "protocol": "uniswap",
       "recipient": "0xUser",
       "slippage": 1,
       "additionalInfo": {},
       "permitData": "0x…"
     }]
   }
   ```

   - `protocol` is a provider id from the quote. `permitData` is optional; see
     step 3 for its encoding. `hasPermit2ApprovalForAllTokens: true` selects
     the Permit2 batch-witness path. `disableEstimation: true` skips the gas
     simulation, so a build works for an account without allowance or funds.
   - **User-sent response:** `status`, `txId`, `chainId`, `gasless: false`,
     `transaction` (`from`, `to`, `data`, `value`, `gasLimit`), `quotes` (per
     pair: `provider`, `destAmount`, `minDestAmount`), `updatedQuotes`,
     `additionalInfo`, `broadcastViaProvider`, and the same transaction fields
     again at the top level (deprecated). Live, `to` was `DZapDiamond`
     `0xF708…C0a6`. The user approves the Diamond, then signs and sends
     `transaction`, or posts the signed raw transaction to `POST /broadcast`
     as `{ "txId", "chainId", "txData": "0x02f8…" }`, which answers
     `{ "status", "txnHash" }`.
   - **Gasless response** (live, Arbitrum, 2026-10-08):

     ```json
     {
       "status": "success",
       "txId": "0x3078313131312d3131313131312d313739313339383336353231330000000000",
       "gasless": true,
       "onlySwapData": false,
       "transaction": {
         "txType": "swap",
         "executorFeesHash": "0x80ec0fea318a9f208654f19b85a2264b6def13492b278500d0534cc35f891204",
         "swapDataHash": "0xa3886befbcf460d99d524f73b629ae9eb281d0821c1190527fba2030ea7bcc65",
         "value": "0"
       },
       "quotes": { "0xaf88…5831-0x82aF…Bab1": { "provider": "uniswap", "destAmount": "1947100716285612", "minDestAmount": "1927629709122755" } },
       "fees": { "executorFee": [{ "symbol": "USDC", "address": "0xaf88…5831", "decimals": 6, "amount": "21144", "amountUSD": "0.02115", "included": true }] }
     }
     ```

     `txId` is a DZap-assigned bytes32: ASCII `0x1111-111111-1791398365213`
     (pieces of the sender address and a millisecond timestamp), zero-padded.
     The response has no calldata, no `swapData` and no executor-fee struct, so
     neither hash can be recomputed by the client. For a bridge, `txType` is
     `bridge` and `adapterDataHash` appears ([dzap-bridge](dzap-bridge.md)).

3. **Sign (gasless only).** Two signatures, both off-chain:
   - **The token permit:** EIP-2612
     `Permit(owner, spender = contracts.router, value = amount, nonce, deadline)`
     on the token's own domain. The SDK packs it for the v2 router as
     `abi.encode(uint8 0, abi.encode(uint256 deadline, uint8 v, bytes32 r, bytes32 s))`,
     where `0` is `PERMIT` in `DZapPermitMode` (`PERMIT`, `PERMIT2_APPROVE`,
     `PERMIT2_WITNESS_TRANSFER`, `BATCH_PERMIT2_WITNESS_TRANSFER`). Source:
     `src/utils/eip-2612/eip2612Permit.ts`.
   - **The intent:** EIP-712 on the Diamond, domain
     `{ name: "DZapVerifier", version: "1", chainId, verifyingContract: contracts.router, salt: keccak256("DZap-v0.1") }`,
     type
     `SignedGasLessSwapData(bytes32 txId,address user,uint256 nonce,uint256 deadline,bytes32 executorFeesHash,bytes32 swapDataHash)`.
     `nonce` is `getNonce(user)` on the Diamond; the SDK's `deadline` is
     now + 1800 s. These type strings match the typehashes in the verified
     `GasLessFacetV2`.
   - **Permit2 instead:** with a prior Permit2 approval, the user signs one
     `PermitBatchWitnessTransferFrom` whose witness is
     `DZapSwapWitness(bytes32 txId,address user,bytes32 executorFeesHash,bytes32 swapDataHash)`,
     and no separate intent.

4. **Execute (gasless only):** `POST /gasless/executeTx`.

   ```json
   {
     "chainId": 42161,
     "txId": "0x3078…0000",
     "permit": {
       "permitData": [{ "token": "0xaf88…5831", "amount": "5000000", "permit": "0x<step 3 blob>" }],
       "gaslessIntentSignature": "0x…",
       "gaslessIntentNonce": "3",
       "gaslessIntentDeadline": "1753600000"
     }
   }
   ```

   or `"permit": { "batchPermitData": "0x…" }` for the Permit2 path. The answer
   is `{ "status": "success", "txnHash": "0x…" }`. DZap's server holds the
   calldata for `txId`, adds the fee validator's `SignedFeeData` signature and
   submits `executeSwap` itself. Nothing in the API returns that signature, so
   a third party can't submit in DZap's place. Not run live: it needs a funded
   account.

5. **Status:** `GET /status?txHash=&chainId=` (or `?txId=&chainId=`;
   `/status/multi` takes comma-separated lists). The response has `status`
   (`PENDING`, `COMPLETED`, `PARTIAL`, `FAILED`, `REFUNDED`), `gasless`,
   `txHash`, `chainId`, `timestamp`, `type` (`swap`, `bridge`, `zap`) and
   `transactions[]`, each with `source`, `destination` and `expected` (`asset`,
   `amount`, `amountUSD`, `txHash`), `provider` and `allowUserTxOnDestChain`.

## Testnet

`DZapDiamond` `0xb3926deF2e0989B0700a57034C9A211bfBcF858B` is deployed on
Ethereum, Arbitrum, Base and Optimism Sepolia, as the docs list. Read on-chain
on 2026-10-08:
- **The same keys as mainnet:** owner `0x45679cdf728abdcdfce0f03a8f1d22ba49babc72`
  and fee validator `0xd370bd3170d1adfe7d376b4c009dc00f84360efb`.
- **The same gasless code:** all six gasless selectors resolve to
  `GasLessFacetV2` `0xc3584c31f9e7c9c3a1cbfc6b314a4a6446fae896`, the mainnet
  facet address.
- **The Trade API** (`GET /chains`) enables Sepolia, Arbitrum Sepolia, Monad,
  Citrea, Push, Astralis and Arc testnets, and lists Base, Optimism, Unichain
  and MegaETH testnets as disabled. Sepolia has six tokens, including Circle's
  USDC `0x1c7D…7238` (EIP-2612) and WETH `0xfFf9…6B14`.
- **Routes:** a Sepolia USDC → WETH swap returned "No quotes available" (40
  providers, all `UNSUPPORTED_CHAIN`, `UNSUPPORTED_PAIR` or
  `UNSUPPORTED_TOKEN`), with and without `gasless`. So **same-chain swaps
  can't be tested on testnet.** The only testnet route found is the USDC bridge
  in [dzap-bridge](dzap-bridge.md#testnet).

## Docs versus chain

The Security & Audits page lists the trust model for smart contracts as "Audited; upgrades behind multi-sig + timelock." The Smart Contract Architecture page lists "Upgrade timelock + multi-sig policy" under "Coming next".

On-chain, the second is right:
- **Owner.** `DZapDiamond` (`0xF708…C0a6` on Ethereum, Arbitrum, Base, BSC, Polygon, Optimism and Avalanche) is owned by `0x45679cdf728abdcdfce0f03a8f1d22ba49babc72`, which has no code, so it's an EOA.
- **Upgrades.** Its `DiamondCutFacet` (`0x3e9f…a8d8`, verified) guards `diamondCut` only with `LibDiamond.enforceIsContractOwner()`. One key can add or replace facets at once.
- **What that means for users.** The docs call the Diamond the Trade API's "single trusted spender". Any standing approval to it is as safe as that key.

## Access and screening

- **Keys.** The Trade API works without a key, rate-limited per IP; keys are issued to partners on request.
- **Screening.** An OFAC-sanctioned address (the Ronin exploiter, `isSanctioned` true on the Chainalysis oracle) got Trade API quotes like any other address. No screening is documented.

## Sources

1. https://docs.dzap.io/llms.txt and llms-full.txt (smart-contract architecture, contract addresses, security & audits, authentication), retrieved 2026-10-06, and the docs snapshot in `source/dzap-docs-2026-10-08`
2. Verified source from `eth.blockscout.com`: `DZapDiamond` (`0xF708…`), `DiamondCutFacet` (`0x3e9f…`), 2026-10-06; `GasLessFacetV2` in `source/dzap-gaslessfacet-verified`
3. The clones `source/dzap-dzapcorecontracts`, `dzap-sdk` and `dzap-audits`
4. On-chain through publicnode: `owner()`, `facetAddress(diamondCut)`, `facetAddresses()` on seven chains (2026-10-06); `facetAddress(selector)` for the gasless functions and `getFeeValidator()` (2026-10-08)
5. Live Trade API without a key: `api.dzap.io/v1/quotes` from a clean and from a sanctioned address (2026-10-06); `/chains`, `/token/tokens`, `/quotes` and `/buildTx` (user-sent and gasless) on Arbitrum and Sepolia (2026-10-08)
6. Web search "DZap exploit hack", 2026-10-06 — nothing relevant
7. Testnet reads (2026-10-08): `owner()`, `getFeeValidator()`, `facetAddresses()` and `facetAddress(selector)` for the six gasless selectors on the four Sepolia Diamonds
