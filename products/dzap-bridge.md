---
slug: dzap-bridge
name: DZap Core bridge
scope: Cross-chain transfers through DZap Core (Trade API) and DZapDiamond, sent by the user or gasless through GasLessFacetV2 executeBridge / executeMultiBridge, including Ghost Mode (private relays); EVM origin only. The exit is the chosen bridge's (Across, Mayan, CCTP and others)
kind: aggregator
class: unknown                           # inherits the chosen bridge's class
cross_chain: true
chains: unknown
source_public: partial
inherits: [dzap-swap]
updated: 2026-10-08

verification:
  service: partial
  exit: spec-only                        # per bridge
  actors: spec-only
  admin: source-verified                 # see dzap-swap
  data: spec-only
  judgment: partial
  incidents: partial

exit:
  custody: unknown                       # the bridge's
  execution: unknown                     # the bridge's
  overrides: unknown
  refund_trigger: unknown                # the bridge's; the quote's refundee receives refunds
  exit_bound_seconds: unknown
  exit_bound_chosen_by: none
  standing_approval: upgradeable_target  # approvals to DZapDiamond; see dzap-swap

actors: unknown

admin:
  same_as: dzap-swap

data_gates: unknown

judgment:
  same_as: dzap-swap

service:
  same_as: dzap-swap

integration:
  calls: ["POST api.dzap.io/v1/quotes with toChain (private: true for Ghost Mode)", "POST /v1/buildTx", "user-sent: approve DZapDiamond, sign and send (or POST /v1/broadcast)", "gasless: sign an EIP-2612 permit and the SignedGasLessBridgeData / SignedGasLessSwapBridgeData intent, POST /v1/gasless/executeTx", "GET /v1/status until COMPLETED, PARTIAL, FAILED or REFUNDED"]  # formats in dzap-swap, Integration flow
  signatures: ["gasless: EIP-712 SignedGasLessBridgeData / SignedGasLessSwapBridgeData (domain DZapVerifier), plus DZap's fee-validator signature"]
  offchain_required:
    - role: Trade API, DZap's fee signature for gasless, and the bridge's own services
      api_key: optional
      rate_limited: true
  finisher: unknown                      # the bridge's
  gasless_start: [eip2612, permit2_approved, prior_approval]
  monitoring: "status endpoint, step-level"
  sdk: "@dzapio/sdk"
  testnet: true                          # Sepolia → Arbitrum Sepolia USDC through cctpV1 and cctpV2, quoted user-sent and gasless, and a gasless buildTx returned the hashes (keyless, 2026-10-08); no other testnet pair quoted
  steps: unknown

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: inherited
  holder: unknown
  strike: unknown
  expiry: unknown
  early_close: unknown
  premium: none
  terms_fixed_by: calldata
  price_set_by: quote
  discipline: unknown
  surplus_to: unknown
  extraction: [public_bound]             # unless Ghost Mode's private relays are used
  sides: [exact_in]
  rate: unknown
  quote_validity: unknown
  partial_fill: unknown
  partial_remainder: unknown

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: designated
    paid: atomic
    fee: signed
    note: "gasless: any msg.sender holding DZap's fee-validator signature calls GasLessFacetV2.executeBridge and is paid the user-signed executor fee in the same call; the API never returns that signature, so in practice DZap's relay submits"
  - action: exit
    performer: none
    paid: none
    inherited: true
    note: the bridge's

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: Trade API bridge
    form: calldata
    bounds: arbitrary
    verifiable_locally: false
    api_optional: false
    target_admin: key
    note: "calldata to DZapDiamond, re-cut by one EOA"
  - path: gasless (GasLessFacetV2.executeBridge)
    form: typed_data
    bounds: arbitrary
    verifiable_locally: false
    api_optional: false
    target_admin: key
    note: "the user signs adapterDataHash (and swapDataHash for swap-bridge) and executorFeesHash; buildTx returns the hashes, not the data, so the bridge, recipient and minimum can't be checked before signing (live, 2026-10-08)"

incidents: []

open_questions:
  - "Trade: holder, strike, expiry, early_close, discipline, surplus_to (CRITERIA.md, Trade)"
  - "Quote: rate, quote_validity, partial_fill, partial_remainder (CRITERIA.md, Trade)"
  - Ghost Mode's private relays and its "permissioned" solver pool (docs), who runs them, and whether they can refuse
  - Which bridges each route uses, recorded per route
---

# DZap Core bridge

**Primitive (one line):** An aggregator's cross-chain transfer through DZapDiamond. The bridge the route picks carries and refunds the funds, so this entry inherits that bridge's exit.

Core bridge runs on the same `DZapDiamond`, API and fee validator as
[dzap-swap](dzap-swap.md), so its admin, judgment and service facts are
`same_as: dzap-swap` and are described there (owner EOA, `diamondCut` with no
timelock, keyless Trade API, no screening seen). This page covers what is
specific to bridging.

## Gasless bridges, as deployed (2026-10-08)

- **Entry points:** `GasLessFacetV2` `executeBridge`, `executeMultiBridge` and
  `executeMultiBridgeWithWitness`, on `DZapDiamond`. Registered on Ethereum,
  Base and Arbitrum, and confirmed on Polygon, Optimism and BNB Chain. They are
  `external`, with no caller check, and pay `_executorFeeInfo` to `msg.sender`
  in the same call.
- **The user signs** `SignedGasLessBridgeData` or `SignedGasLessSwapBridgeData`
  (the swap types plus `adapterDataHash`, which binds the bridge leg), or the
  Permit2 witness
  `DZapBridgeWitness(bytes32 txId,address user,bytes32 executorFeesHash,bytes32 swapDataHash,bytes32 adapterDataHash)`.
  Same domain as swaps, checked ECDSA-only.
- **DZap's fee validator co-signs** `SignedFeeData`, as for swaps. Without it
  no gasless bridge executes.
- **What happens after the source call** is the chosen bridge's: delivery,
  refunds and their timing are inherited, which is why Exit, Actors, Data gates
  and Judgment show as route-dependent.

## Integration flow

The calls and formats are Core's, documented step by step in
[dzap-swap, Integration flow](dzap-swap.md#integration-flow-trade-api). What
differs for a bridge:

- **Quote:** `toChain` differs from `fromChain`. `"private": true` asks for
  Ghost Mode. `bridges: { allow, deny }` restricts the bridges considered, and
  the pair also gets a `fastestSource`. Provider ids seen: `cctpV1`, `cctpV2`.
- **Build:** `recipient` is on the destination chain. `refundee` must be an
  address you control on the source chain, because a failed destination leg
  refunds there.
- **Gasless build response:** `transaction.txType` is `"bridge"`, with
  `adapterDataHash` (the bridge leg) and `executorFeesHash`, plus
  `swapDataHash` when the route swaps first. Live on Sepolia (2026-10-08):

  ```json
  {
    "status": "success",
    "txId": "0x3078313131312d3131313131312d313739313339383537373037370000000000",
    "gasless": true,
    "onlySwapData": false,
    "transaction": {
      "txType": "bridge",
      "executorFeesHash": "0x9f7f7b426d270855c210bdd5ceb9048861f7a7643b8edf168aade149e591d6dc",
      "adapterDataHash": "0x9a4f6ffa08a174fa87d6aadf732795478566e8cd69d446720425a333eda7861f",
      "value": "0"
    },
    "quotes": { "11155111_0x1c7D…7238-421614_0x75fa…AA4d": { "provider": "cctpV2", "destAmount": "4942497", "minDestAmount": "4942398" } },
    "fees": { "executorFee": [{ "symbol": "USDC", "amount": "1737" }] }
  }
  ```

  As with swaps, the hashes come without their preimages: the bridge, the
  recipient and the minimum can't be checked against what is signed.
- **Intent type:** with no `swapDataHash`, sign
  `SignedGasLessBridgeData(bytes32 txId,address user,uint256 nonce,uint256 deadline,bytes32 executorFeesHash,bytes32 adapterDataHash)`;
  with one,
  `SignedGasLessSwapBridgeData(bytes32 txId,address user,uint256 nonce,uint256 deadline,bytes32 executorFeesHash,bytes32 swapDataHash,bytes32 adapterDataHash)`.
  Same domain as swaps. The Permit2 path signs the witness
  `DZapBridgeWitness` instead.
- **Status:** poll `GET /status?txHash=&chainId=` (source chain) until it
  leaves `PENDING`. `PARTIAL` and `REFUNDED` are terminal alongside
  `COMPLETED` and `FAILED`; `transactions[].destination.txHash` is the
  bridge's delivery, and `allowUserTxOnDestChain` says whether the user must
  act on the destination.

## Testnet

The Sepolia Diamonds carry the mainnet gasless facet, owner and fee validator
([dzap-swap, Testnet](dzap-swap.md#testnet)). One route quoted on 2026-10-08,
keyless:

| From | To | Providers | 5 USDC in → out |
|---|---|---|---|
| Sepolia USDC `0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238` | Arbitrum Sepolia USDC `0x75faf114eafb1BDbe2F0316DF893fd58CE46AA4d` | `cctpV1`, `cctpV2` | 4.944729 (user-sent), 4.942985 (gasless) |

- A gasless `buildTx` for it returned the hashes above, so the whole gasless
  flow can be exercised on testnet with test USDC (EIP-2612) and no ETH. The
  final `executeTx` hasn't been run: it needs a funded test account.
- The Garden test USDC pair (`0xadDD…EDc2` → `0xC90A…c829`) returned "No
  quotes available".

## Ghost Mode

Ghost Mode is Core's private bridging: `private: true` on the quote and build
requests routes the transaction through private relays (Flashbots,
MEV-Blocker, or chain-native private mempools) instead of the public mempool.
The docs list its trade-offs as full front-running protection, slightly higher
latency, a "permissioned pool" of solvers instead of an open one, and a slight
fee premium. Who runs the relays and the solver pool wasn't found. Source: the
docs snapshot in `source/dzap-docs-2026-10-08` (`products_dzap-core_ghost-mode.md`).

## Sources

- The verified `GasLessFacetV2` in `source/dzap-gaslessfacet-verified`
  (`contracts__Shared__Facets__GasLessFacetV2.sol`).
- On-chain `facetAddress(selector)` for the bridge functions on six chains,
  2026-10-08.
- The docs snapshot in `source/dzap-docs-2026-10-08`.
- Live Trade API, keyless (2026-10-08): `/quotes` and gasless `/buildTx`,
  Sepolia → Arbitrum Sepolia.
