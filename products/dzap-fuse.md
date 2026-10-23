---
slug: dzap-fuse
name: DZap Fuse
scope: DZap Fuse (zap.dzap.io) single-signature intents through DZapZapCore 0xCE2541ce645A1B232fF2fead53dcD9f369E86bA4, user-sent (zap) or gasless (executeZap); same-chain zaps settle atomically, cross-chain legs ride the bridge the route picks
kind: aggregator
class: unknown
cross_chain: true
chains: unknown                          # DZapZapCore read on Ethereum, Arbitrum, Base, Polygon, Optimism, BNB Chain
source_public: partial                   # DZapIO/DZapZappingContracts and verified source; APIs and solvers not public
inherits: []
updated: 2026-10-08

verification:
  service: partial
  exit: spec-only                        # cross-chain exits are the bridge's
  actors: spec-only
  admin: source-verified                 # DZapZapCore source and on-chain owner, verifier, pause
  data: spec-only
  judgment: partial
  incidents: partial

exit:
  custody: unknown                       # same-chain: user wallet; cross-chain: the bridge's
  execution: unknown
  overrides: unknown
  refund_trigger: on_failure             # docs: destination failure refunds to the refundee set at quote time, through the bridge
  exit_bound_seconds: unknown
  exit_bound_chosen_by: none
  standing_approval: immutable_target    # DZapZapCore isn't a proxy, and its token-moving selectors are permanently blocked

actors: unknown

admin:
  upgradeable: false                     # DZapZapCore is not a proxy
  authority: eoa                         # owner 0x45679cdf728abdcdfce0f03a8f1d22ba49babc72 on all six chains read
  timelock_seconds: none
  immediate_functions: []                # the owner's powers change future zaps only; see outside_exit_path
  grandfathered: full
  outside_exit_path:
    - what: pause, whitelistAdapters, blockSelectors, setVerifier, addAdmin (owner; pause also admins)
      effect: stops or reshapes future zaps; can't unblock the transfer and approve selectors, so it can't spend approvals
    - what: recoverToken / recoverERC721 / recoverERC1155
      effect: tokens held by the contract itself, not users' approvals
    - what: diamondCut on DZapDiamond (dzap-swap), by the same owner EOA, no timelock
      effect: Fuse same-chain swaps run a step that calls DZapDiamond ("DZap Aggregator", live buildTx 2026-10-08); a re-cut changes the code that handles a zap's in-flight funds, though not standing approvals to DZapZapCore

data_gates: unknown

judgment:
  screening: []
  freeze_assets: []
  freeze_pooled: false

service:
  integrator_access:
    api_key: optional                    # "Every endpoint on both APIs works without a key"; Fuse /v1/quote confirmed 2026-10-06
    identity: none
    revocable: unknown
    rate_limited: true                   # Fuse quote and buildTx 3 requests per second per IP without a key
  operators:
    - role: Fuse API and relay (POST /v1/bundle)
      entity: DZap
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: zap verifier; co-signs every zap, gasless or not (_handleZapVerification)
      entity: DZap                       # EOA 0x92e5d0beef9793c49051481630db2392fed55c89 on all six chains read
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: Fuse solvers; submit signed intents
      entity: unknown                    # docs: "Permissionless"; on-chain, anyone may submit, but only routes the zap verifier signed
      single_operator: unknown
      source_public: false
      deployment_config_public: false
  screening:
    - kind: "route approval: every zap needs DZap's zap-verifier signature"
      where: DZapZapCore (_handleZapVerification), in zap() and executeZap()
      in_source: true
      enabled_in_production: true        # one EOA can decline to sign any zap; no address screening was seen at quote time (2026-10-06)
  bypass: false

integration:
  calls: ["POST zap.dzap.io/v1/quote", "POST /v1/buildTx", "approve each approvalData entry", "sign and send each steps[] transaction (zap() on DZapZapCore, verifier signature embedded), or POST /v1/broadcast", "GET /v1/status?chainId&txnHash"]  # formats under Integration flow; the API has no gasless path
  signatures: ["gasless: EIP-712 DZapGaslessZapData or Permit2 witness DZapGaslessZapWitness (domain DZapVerifier, version 1, salt keccak256('DZap-v0.1')), checked ECDSA-only", "DZap's zap-verifier DZapSignedZapData"]
  offchain_required:
    - role: Fuse API and DZap's verifier signature
      api_key: optional
      rate_limited: true
  finisher: user                         # the API builds zap() for the user to send; no solver path was reachable (2026-10-08)
  gasless_start: [eip2612, permit2_approved]  # the contract: executeZap takes a per-token EIP-2612 permit, Permit2 approval or Permit2 witness (LibAsset.depositErc20). The API doesn't build it: buildTx with gasless true still returns zap() (2026-10-08)
  monitoring: "getZapTxnStatus, step-level"
  sdk: "@dzapio/sdk (getZapQuote, signGaslessDzapUserIntent)"
  testnet: false                         # DZapZapCore is deployed on Sepolia (same verifier and owner), but the Fuse API answers "srcChainId 11155111 is not supported" and lists no testnets (2026-10-08)
  steps: 3

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: inherited
  holder: unknown
  strike: unknown
  expiry: user_chosen                    # the intent's deadline
  early_close: unknown
  premium: none
  terms_fixed_by: signature              # zap data, fees and executor fees are hashed into the user's intent
  price_set_by: quote
  discipline: unknown
  surplus_to: holder                     # docs: "Solvers earn the spread between user-facing output and best on-chain output"
  extraction: []
  sides: [exact_in]                      # zap.dzap.io/v1/quote fixes the input (live 2026-10-07)
  rate: firm                             # the quote's output minAmount equalled its amount, with slippage 1 requested; the signed intent's terms weren't read
  quote_validity: unknown
  partial_fill: unknown
  partial_remainder: unknown

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: designated
    paid: atomic
    fee: signed
    note: "gasless (contract only): any msg.sender holding DZap's verifier signature calls executeZap and is paid the user-signed executor fee in the same call. The Fuse API only builds the user-sent zap(), which needs native gas"
  - action: exit
    performer: none
    paid: none
    inherited: true
    note: the bridge's, for cross-chain legs

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: Fuse API
    form: calldata
    bounds: bounded
    verifiable_locally: true
    api_optional: false
    note: "DZapZapCore blocks transfer and approve selectors permanently; gasless needs the user's EIP-712 intent"

incidents: []

open_questions:
  - "Trade: holder, strike, early_close, discipline (CRITERIA.md, Trade)"
  - "Quote: quote_validity, partial_fill, partial_remainder (CRITERIA.md, Trade)"
  - Who the Fuse solvers are, and who holds the zap verifier key (EOA 0x92e5d0beef9793c49051481630db2392fed55c89)
  - "How a gasless Fuse intent can be obtained on EVM: /v1/bundle is 404, /v1/execute is Solana-only, buildTx ignores gasless, and the SDK has no DZapGaslessZapData signer"
  - Audit reports for the current DZapZapCore
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: dzap-dzapzappingcontracts
    url: https://github.com/DZapIO/DZapZappingContracts
    commit: 961b5157e925e31094e29336dca2f99893602bbc
    commit_date: 2025-09-04
  - repo: dzap-sdk
    url: https://github.com/DZapIO/sdk
    commit: 776f559af90b38438bc79246c83c95868b001c91
    commit_date: 2026-09-22
  - repo: dzap-audits
    url: https://github.com/DZapIO/audits
    commit: 5845bdbc31f8d7b79cec6480745ffe4549db4adc
    commit_date: 2024-06-25
  - repo: dzap-docs-2026-10-08           # snapshot of docs.dzap.io pages and openapi.yaml
    url: https://docs.dzap.io
    commit: "snapshot"
    commit_date: 2026-10-08
---

# DZap Fuse

**Primitive (one line):** Single-signature intents (swap, bridge, swap-and-bridge, zaps into positions) settled through DZapZapCore. Every zap, gasless or not, needs DZap's verifier signature, and anyone holding it may submit a gasless one for the signed executor fee.

Fuse is a separate product from DZap Core ([dzap-swap](dzap-swap.md),
[dzap-bridge](dzap-bridge.md)): its own API (`zap.dzap.io`), its own contract
and its own co-signing key. The only thing it shares with Core is the owner
EOA.

## The contract

A live Fuse quote (USDC Arbitrum → WETH Base) asked for approval to
`DZapZapCore` `0xCE2541ce645A1B232fF2fead53dcD9f369E86bA4` (verified, 20,880
bytes). The same address is deployed on Ethereum, Arbitrum, Base, Polygon,
Optimism and BNB Chain.

- **Not a proxy.** Its owner is `0x45679cdf728abdcdfce0f03a8f1d22ba49babc72`,
  the same EOA that owns Core's Diamond, but here the owner's powers are
  limited: pause, adapter whitelist, verifier, admins, and selector blocking.
  None of them can spend users' approvals.
- **Token calls stay blocked.** The token-moving selectors (`transfer`,
  `transferFrom`, `approve` and their ERC-721/1155 equivalents) are blocked at
  construction, and `unblockSelectors` refuses them as protected. That's the
  defence that would have stopped the LI.FI and Socket injection exploits.
  Compared with Core, where one key can re-cut the Diamond that holds the
  approvals, this is the better-built contract.
- **Four entry points,** all requiring DZap's zap-verifier signature
  (`_handleZapVerification`):

| Function | Who sends | Pulls tokens from | How |
|---|---|---|---|
| `zap` | the user | `msg.sender` | per token: EIP-2612 permit, Permit2 approval, or Permit2 witness |
| `zapWithBatchDeposit` | the user | `msg.sender` | one Permit2 batch transfer |
| `executeZap` | anyone | `_user`, with the user's intent signature | per token, as `zap` |
| `executeZapWithWitness` | anyone | `_user` | one Permit2 batch witness transfer, the witness being the intent |

## Gasless, as deployed (2026-10-08)

- **The user signs** `DZapGaslessZapData(bytes32 txId,address user,address dustReceiver,uint256 nonce,uint256 deadline,bytes32 zapDataHash,bytes32 feeDataHash,bytes32 executorFeeDataHash,bytes32 crosschainDataHash,bytes32 sweepDataHash)`
  for `executeZap`, or the Permit2 witness `DZapGaslessZapWitness` for
  `executeZapWithWitness`. The domain is
  `EIP712Domain(string name,string version,uint256 chainId,address verifyingContract,bytes32 salt)`
  with name `DZapVerifier`, version `1` and salt `keccak256("DZap-v0.1")`.
  `DZapVerification._verifySignature` uses OpenZeppelin `ECDSA.recover` only,
  so a contract account can't sign the intent; a plain EOA, or a 7702-delegated
  account signing with its own key, can.
- **What the intent binds:** the zap steps, the protocol and integrator fees,
  the executor fee, the cross-chain data, the dust tokens and their receiver,
  the user's nonce and a deadline. A submitter can't change any of them.
- **DZap's zap verifier also signs** `DZapSignedZapData(txId, user, nonce,
  deadline, zapDataHash, feeDataHash)` over the same zap. On all six chains
  read, `zapVerifier()` is the EOA `0x92e5d0beef9793c49051481630db2392fed55c89`.
- **`executeZap` is external, with no caller check.** It pulls the user's
  tokens, runs the zap, takes fees, pays `_executorFeeInfo` to `msg.sender`
  and sweeps dust to `dustReceiver`, all in one call.
- **Starting with no gas:** EIP-2612 tokens can be pulled by a permit inside
  `executeZap`. Other tokens need a prior Permit2 approval, which costs gas.
- **The docs' "permissionless" solvers:** anyone may submit and be paid, but
  only routes DZap's verifier signed.
- **But the API doesn't offer it on EVM** (live, 2026-10-08). The docs say to
  post the signed intent to `POST zap.dzap.io/v1/bundle`, which returns 404.
  `POST /v1/execute` answers "execute only supported for Solana". `buildTx`
  with `gasless: true` still returns a user-sent `zap()`. The docs' gasless
  page signs Core's intent types (`SignedGasLessSwapData` and the rest, with
  the Diamond as spender), which `DZapZapCore` doesn't check, and the SDK
  has no `DZapGaslessZapData` signer. So `executeZap` exists on-chain with no
  way to get the verifier signature it needs.

**What this means for an integrator.**
- **Keyless:** the Fuse API answers without a key (live, 2026-10-06); keys
  only raise the per-IP limit of 3 requests per second.
- **Gasless isn't available today** (above). Through the API, Fuse on EVM is
  a user-sent transaction that needs native gas.
- **The calldata is checkable.** `buildTx` returns the full `zap()` calldata,
  so the zap steps, minimums and recipient can be decoded before sending, and
  the contract can't be re-cut under a standing approval.
- **Same-chain swaps still run through Core's Diamond.** The swap step's
  `callTo` is `DZapDiamond` ("DZap Aggregator"), which the owner EOA can
  re-cut at once. That code handles the zap's funds in flight, though it never
  holds an approval.
- **But DZap's verifier EOA decides whether any zap executes,** gasless or
  not, and DZap builds the route. There's no auction.
- **Cross-chain legs** ride the bridge the route picks, so delivery and refunds
  are that bridge's.

## Integration flow (Fuse API)

Base URL `https://zap.dzap.io/v1`, JSON bodies. Without `x-api-key`, the limit
is 3 requests per second per IP. Request shapes are from the SDK
(`src/types/zap/*.ts`) and the API reference in
`source/dzap-docs-2026-10-08` (`api_fuse_*.md`), checked live on 2026-10-08.
The `openapi.yaml` in the same snapshot describes a different API (`quoteId`,
`expectedOutput`, `signedIntent`, `/v1/jobs`) that doesn't match what the
server answers, so don't build against it.

**Discovery.** `GET /config/chains` returns a map keyed by chain id (25
chains on 2026-10-08, Solana included, no testnets). `GET /config/providers`
lists the protocols.

1. **Quote:** `POST /quote`.

   ```json
   {
     "srcToken": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "srcChainId": 42161,
     "destToken": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", "destChainId": 42161,
     "amount": "5000000",
     "slippage": 1,
     "account": "0xUser", "recipient": "0xUser", "refundee": "0xUser"
   }
   ```

   - `slippage` is in percent. Native tokens are `0xEeee…EEeE`. `destToken`
     can be an LP or vault token, with `poolDetails` (`lowerTick`,
     `upperTick`) or `positionDetails` (`nftId`) for positions.
   - Optional: `allowedBridges[]`, `allowedDexes[]`, `permitData`, and
     `integrator` `{ id, feeBps, wallet }`.
   - The response is `{ "status": "success", "data": { … } }`, with the same
     fields as the build except `steps`.

2. **Build:** `POST /buildTx`, the same body with `account`, `recipient` and
   `refundee` required. `estimateGas: false` skips the simulation; with it on,
   an account without allowance gets `"ERC20: transfer amount exceeds
   allowance"`. The response `data` (live, 5 USDC → WETH on Arbitrum):
   - `approvalData[]`: `{ "callTo": "0xaf88…5831", "approveTo": "0xCE25…6bA4", "amount": "5000000" }`,
     the approvals to send first.
   - `steps[]`: `{ "action": "execute", "data": { "type": "evm", "txnId": "0x3131…", "callTo": "0xCE2541ce645A1B232fF2fead53dcD9f369E86bA4", "callData": "0xe10ea0d7…", "value": "0", "estimatedGas": "0" } }`.
     `0xe10ea0d7` is `zap(bytes32,bytes,bytes,uint256,address,(address,uint256,bytes)[],(address,(address,uint256,uint256)[]),(address,address,bytes,bool,uint256,(uint8,uint8,address,uint256,uint256)[],(uint8,uint8,address,address,uint96,uint256,uint256)[])[],address[])`,
     with DZap's verifier signature already embedded. The user sends it.
   - `output[]`: `asset`, `amount` 1955824825721886, `minAmount`
     1951915131895267, `amountUSD`.
   - `path[]`: per step, `action` (`swap`, `bridge`, `deposit`, `withdraw`…),
     `protocol` (here `{ "id": "dzap", "name": "DZap Aggregator" }`), and
     `input[]` and `output[]`.
   - `fees[]` and `refund[]` (dust and rent given back), both empty here.

   The calldata decodes against the `DZapZapCore` ABI, so a client can check
   each `ZapData` step's `callTo`, `outputTokens[].minReturn` and recipient
   before signing.

3. **Send:** approve, then sign and send each step. Alternatively post the
   signed raw transaction to `POST /broadcast` as
   `{ "txId": "<steps[].data.txnId>", "chainId": 42161, "txData": "0x02f8…" }`,
   which answers `{ "status": "success", "data": { "txnHash", "txnId" } }`.

4. **Status:** `GET /status?chainId=&txnHash=`. The response has `status`
   (`PENDING`, `COMPLETED`, `FAILED`, `REFUNDED`), `account`, `recipient`,
   `input[]`, `output[]`, `timestamp`, `completedAt`, and `steps[]`, each with
   `chainId`, `hash`, `status`, `action`, `protocol`, `input[]` and `output[]`.

**Bundles.** `POST /bundle/quote` and `POST /bundle/buildTx` take
`{ actions[], account, recipient, refundee, slippage }`. Each action is
`{ action, srcToken: { address, amount } | [...], srcChainId, destToken?, destChainId?, protocol?, poolDetails?, positionDetails? }`.
The output is the same `approvalData` and `steps` shape.

**Gasless.** None on EVM through this API (see Gasless, as deployed). The
contract's `executeZap` would need the user's `DZapGaslessZapData` signature
and a verifier signature over the same zap, and nothing serves the second.

## Testnet

None usable. `DZapZapCore` is deployed at the mainnet address on Ethereum
Sepolia, with the same verifier and owner, unpaused, and Permit2 at the
canonical address. But the Fuse API lists no testnets, and a Sepolia quote
answers `"srcChainId 11155111 is not supported."` (2026-10-08). The contract
isn't on Arbitrum, Base or Optimism Sepolia.

## Access and screening

An OFAC-sanctioned address (the Ronin exploiter, `isSanctioned` true on the
Chainalysis oracle) got Fuse quotes like any other address (2026-10-06). No
screening is documented. The verifier signature is the point where DZap could
refuse.

## Sources

- `source/dzap-dzapzappingcontracts` (`DZapZapCore.sol`, `DZapCoreBase.sol`,
  `DZapVerification.sol`, `shared/libraries/LibAsset.sol`), and the verified
  `DZapZapCore` on `eth.blockscout.com`.
- The docs snapshot in `source/dzap-docs-2026-10-08` (Fuse execution flow,
  bundle, gasless).
- On-chain `zapVerifier()`, `owner()`, `paused()` and `permit2()` on Ethereum,
  Arbitrum, Base, Polygon, Optimism and BNB Chain (2026-10-08).
- Live Fuse API without a key, 2026-10-06 and 2026-10-07:
  `zap.dzap.io/v1/config/chains` and `zap.dzap.io/v1/quote`, from a clean and
  from a sanctioned address. On 2026-10-08: `/buildTx` (with and without
  `gasless`), `/quote` on Sepolia, and empty-body probes of `/bundle` (404),
  `/execute`, `/bundle/quote`, `/bundle/buildTx` and `/broadcast`.
- `source/dzap-sdk` `src/types/zap/` and `src/zap/constants/urls.ts`, and the
  API reference pages `api_fuse_*.md` added to the docs snapshot on
  2026-10-08.
- Sepolia `DZapZapCore` reads (`zapVerifier()`, `owner()`, `paused()`,
  `permit2()`, code size), 2026-10-08.
