---
slug: lifi-intent
name: LI.FI Intent
scope: LI.FI's OIF deployment on EVM (InputSettlerEscrowLIFI, OutputSettlerSimple, PolymerOracleMapped, the same addresses on every chain) and the order.li.fi order server in front; the escrow path. The Compact path is in the-compact, Tron and Solana aren't covered
kind: bridge
class: B
cross_chain: true
chains: [Ethereum, BSC, Base, Arbitrum, Polygon, Avalanche, Gnosis]   # contracts on all seven (eth_getCode 2026-10-03); Gnosis has no solver routes; 23 more chains are listed by /chains/supported and not checked
source_public: true                      # contracts (catalystsystem/lifi-intent, matched on Sourcify); the order server isn't
inherits: [oif-escrow, the-compact]
updated: 2026-10-06

verification:
  service: partial                       # live API used; order server source not public
  exit: source-verified                  # refund() and refundOnNonFill read; deployed escrow source diffed against the repo
  actors: source-verified
  admin: source-verified                 # owner, fee state read by eth_call on every chain in the table
  data: source-verified
  judgment: partial                      # contracts read; order-server screening unknown
  incidents: not-reviewed

exit:
  custody: escrow                        # InputSettlerEscrowLIFI 0x00fC00edbe7C003b006f870068c548940000223e holds every open order's inputs
  execution: self                        # refund(order) after expires has no caller check and pays order.user; the depositor can call it, as can anyone
  overrides:
    - who: Polymer sequencer key 0x4632e987c6F31d6351e39324Dec6f1404Af56209 (an EOA), the one signer CrossL2ProverV2 0x95cceae71605c5d97a0ac0ea13013b058729d075 accepts; the same prover and key behind PolymerOracleMapped on all seven chains
      needs: one key                     # SEQUENCER is an immutable in the prover; the prover has no owner, no proxy and no other check on the state root
      parties: key
      how: sign a state root containing a fabricated OutputFilled event from the output settler; PolymerOracle.receiveMessage records it, and finalise pays the order's inputs to whoever the forger names. refund() then reverts. Works for any order still deposited, before or after expires
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: timeout                # refund() after expires; the faster refundOnNonFill needs a Polymer proof of non-fill (timeout_proof)
  exit_bound_seconds: [503, 172799]      # expires minus submit time across 399 escrow orders from /orders, 2026-10-04 (median 172788); no cap in the contract
  exit_bound_chosen_by: order creator    # expires is a uint32 in the signed order; the order server sets it for orders it builds
  standing_approval: immutable_target    # approve or Permit2 to the escrow, which isn't upgradeable; ERC-3009 needs no approval

actors: []                               # refund() needs no one but a caller, who can be the depositor; refundOnNonFill needs a relayer (permissionless) and Polymer, but it's not the backstop

admin:
  upgradeable: false                     # no proxy
  authority: eoa                         # Solady Ownable owner 0xab483d44705af49a83553821a1f7aad8bbc70576, the same on every chain checked
  timelock_seconds: 604800               # governance fee changes wait 7 days (applyGovernanceFee)
  immediate_functions: []
  grandfathered: full                    # the fee is charged on finalise, never on refund; nothing else is mutable
  outside_exit_path:
    - what: setGovernanceFee
      effect: fee on the solver's payout at finalise, at most 5%; 0 on every chain checked, nothing pending (nextGovernanceFeeTime = uint64.max)
      caller: owner EOA
      timelock_seconds: 604800

data_gates: []                           # refund() checks only block.timestamp > expires, which is the exit bound itself

judgment:
  screening: []                          # none in the contracts
  freeze_assets: [USDC, USDT]            # most routes are USDC/USDT
  freeze_pooled: true                    # every open order's inputs sit at the one escrow address

service:
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: false
    note: "quote and order endpoints work without a key; LI.FI documents no rate limit"
  operators:
    - role: Order server (order.li.fi); quotes, picks the solver, can open signed orders gaslessly via /orders/submit
      entity: LI.FI
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: Solvers; fill on the destination, prove through Polymer, finalise on the origin
      entity: unknown                    # 11 EVM addresses seen in 400 settled orders, the top three filling two-thirds; names not published
      single_operator: false
      source_public: unknown
      deployment_config_public: false
    - role: Refund keeper; calls refundOnNonFill about 170 s after fillDeadline
      entity: LI.FI                      # EOA 0xc7dd6725037229bce71aa5f7d1aa72454e316304 through smart account 0xa84b6be6af0750916074f1e43e0b94358681dcc6
      single_operator: true
      source_public: false
      deployment_config_public: false
  screening:
    - kind: address screening at quote request
      where: order.li.fi /quote/request
      in_source: false
      enabled_in_production: false       # an OFAC-sanctioned user address (Ronin exploiter) was quoted like any other, 2026-10-06
    - kind: screening at order submission or by solvers
      where: /orders/submit and solver fill decisions
      in_source: false
      enabled_in_production: unknown     # needs a signed order from a flagged address to test
  bypass: unknown                        # open() and openFor() are permissionless and fill() is open to anyone, but whether LI.FI-registered solvers fill orders opened outside the order server isn't established; refund() needs nothing

integration:
  calls: ["POST order.li.fi/quote/request", "open(StandardOrder) or openFor(order, sponsor, sig) on the escrow, or POST /orders/submit", "GET /orders/status", "refund(order) after expires if still deposited"]
  signatures: ["Permit2 witness transfer (sig prefix 0x00) or ERC-3009 receiveWithAuthorization (prefix 0x01) for openFor; none for open after approve"]
  offchain_required:
    - role: quotes and solver selection
      api_key: false
      rate_limited: false
  finisher: anyone                       # solvers finalise; refunds are permissionless, LI.FI's keeper runs refundOnNonFill
  gasless_start: [permit2_approved, eip3009] # openFor, submitted by anyone or by the order server
  monitoring: "/orders/status meta.orderStatus, or Open / OutputFilled / Finalised / Refunded events keyed by orderId"
  sdk: unknown
  testnet: true                          # Sepolia, Base Sepolia, Arbitrum Sepolia; one dev route, so effectively no testnet solver liquidity
  steps: 3                               # quote, sign or open, track; plus a refund call if nobody fills

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: exclusive                      # quotes carry exclusiveFor the selected solver (verified live 2026-10-03)
  strike: signed
  expiry: api_chosen
  early_close: none
  premium: none
  terms_fixed_by: signature
  price_set_by: quote
  discipline: single_holder
  surplus_to: holder
  extraction: [exclusive_window]
  sides: [exact_in, exact_out]           # swapType exact-input or exact-output in the quote request
  rate: firm                             # OutputSettlerSimple pays exactly the signed output for limit and exclusive-limit orders; the Dutch types decay
  quote_validity: api_chosen             # validUntil on each quote
  partial_fill: none                     # the output settler pays the exact output and the escrow releases the whole input
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: anyone
    paid: deferred
    note: "openFor with an EIP-3009 authorisation, submitted by the order server or a solver, who is paid only when the order is finalised later"
  - action: refund
    performer: user
    paid: none
    gas_on: funds_chain
    note: refund(order) after expires has no caller check but pays its caller nothing

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: order
    form: calldata
    bounds: bounded
    verifiable_locally: true
    api_optional: true
    note: "StandardOrder is public; open(order) can be built and sent without the order server"

incidents: []                            # not reviewed

open_questions:
  - Who holds Polymer's sequencer key 0x4632e987..., and whether Polymer has said how it is held (HSM, MPC, one operator)
  - Whether order submission or the solvers screen (quotes don't), and whether solvers fill orders opened outside the order server
  - The /orders/submit body for oif-escrow-v0 (only the Compact template is documented)
  - refundOnNonFill and OutputSettlerBase.emitNotFilled end to end, for the fast refund path
  - Who controls the owner EOA 0xab483d44...0576 and the solver addresses
  - Incident history
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: lifi-intent
    url: https://github.com/catalystsystem/lifi-intent
    commit: 7e32479a48ddcc9e01e5205334a9220f323bae53
    commit_date: 2026-07-29
    note: "cloned 2026-09-28; the entry was read on 2026-09-16 at an unrecorded commit, so its line citations need re-checking against this one"
---

# LI.FI Intent

**Primitive (one line):** LI.FI's production deployment of the Open Intents Framework. The user escrows inputs on the origin chain in `InputSettlerEscrowLIFI`. A solver pays the outputs on the destination through `OutputSettlerSimple`. A Polymer proof of the fill releases the inputs to the solver. A Polymer proof of non-fill, or the passing of `expires`, returns them to the user, and either refund is permissionless.
**Product scope of this entry:** LI.FI Intents order server (`order.li.fi`) and the EVM contracts it routes to. Tron and Solana deployments exist but are not covered.

## Inherits from

- **OIF escrow settler**: see [oif-escrow.md](oif-escrow.md) for the base escrow analysis. The deployed LI.FI escrow adds `refundOnNonFill`, a governance fee and `openForAndFinalise` on top of it (below).
- **The Compact**: see [the-compact.md](the-compact.md) for the Compact path.

## Contracts (EVM, same address on every chain)

| Contract | Address | Verified as (Sourcify, Base) |
| - | - | - |
| Input settler, escrow | `0x00fC00edbe7C003b006f870068c548940000223e` | `InputSettlerEscrowLIFI` |
| Input settler, Compact | `0x0000000000cd5f7fDEc90a03a31F79E5Fbc6A9Cf` | `InputSettlerCompactLIFI` |
| Output settler | `0x75220B7600c300005038432a0000f308e0000068` | `OutputSettlerSimple` |
| Polymer oracle (mainnet) | `0x008C3800F3Ad9b3B662d002E90Cc00000000eE17` | `PolymerOracleMapped` |
| Polymer oracle (testnet) | `0xC401b53377b8A71A7cEB820e6a4dC53832343a90` | not checked |
| The Compact | `0x00000000000000171ede64904551eeDF3C6C9788` | (Uniswap) |
| Permit2 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` | (Uniswap, canonical) |

Source: [1] architecture/overview, intents-api/compact-orders. The escrow at `0x00fC…` has the same source as `src/input/escrow/InputSettlerEscrowLIFI.sol` in [3] (diffed file by file).

**Not these:** `0x1CC9260E…` (escrow) and `0x52602D7c…` (output settler) in the repo's `DEPLOYMENTS.md` are the plain OIF reference deployment. No orders were seen using them. All 392 recent EVM orders sampled from `/orders` used `0x00fC…` with the Polymer oracle (one order used another oracle, `0x6a50…`).

### Deployment by chain (eth_getCode, 2026-10-03)

| Chain | Escrow | Output settler | Polymer oracle | Compact settler | Order-server routes |
| - | - | - | - | - | - |
| Ethereum | ✅ | ✅ | ✅ mainnet | ✅ | 424 same-chain; cross-chain to all below |
| BSC | ✅ | ✅ | ✅ mainnet | ❌ | 697 same-chain; cross-chain |
| Base | ✅ | ✅ | ✅ mainnet | ✅ | 119 same-chain; cross-chain |
| Arbitrum | ✅ | ✅ | ✅ mainnet | ✅ | 10 same-chain; cross-chain |
| Polygon | ✅ | ✅ | ✅ mainnet | ❌ | none same-chain; cross-chain |
| Avalanche | ✅ | ✅ | ✅ mainnet | ❌ | none same-chain; cross-chain |
| Gnosis | ✅ | ✅ | ✅ mainnet | ❌ | **none**: deployed and listed in `/chains/supported`, but no solver quotes |
| Sepolia, Base Sepolia, Arbitrum Sepolia | ✅ | ✅ | ✅ testnet | ✅ | 1 route on the dev server (Sepolia → Sepolia) |
| BSC Testnet, Polygon Amoy, Avalanche Fuji, Gnosis Chiado | ❌ | ❌ | ❌ | ❌ | — |

`/chains/supported` also lists Optimism, Unichain, Ink, World Chain, Mantle, Celo, Monad, HyperEVM, Plasma, Katana, Soneium, Robinhood, Arc, Tempo, Stable, Pharos, Injective, Tron and Solana. These were not checked on-chain.

## Testnets

- Order server: `https://order-dev.li.fi`. Solver UI: `https://devintents.li.fi`. Source: [1] authentication, api-overview
- Contracts are deployed on Sepolia, Base Sepolia and Arbitrum Sepolia, using the **testnet** Polymer oracle `0xC401…`. The dev server also lists Optimism Sepolia, Arc Testnet and Solana Testnet/Devnet, which were not checked.
- **There is effectively no testnet solver liquidity.** `GET https://order-dev.li.fi/routes` returned a single route on 2026-10-03. Testnet orders will only fill if the integrator runs its own filler. Filling is permissionless: call `OutputSettlerSimple.fill`, prove through Polymer, then call `finalise`.
- LI.FI's own solver onboarding tests on **mainnet** with `exclusiveFor` set to the solver under test, via lintent.org or the MCP server. Source: [1] for-solvers/testing-integration

## Integration flow (escrow path)

1. **Quote:** `POST https://order.li.fi/quote/request` (no API key, no rate limits).

   ```json
   {
     "user": "<ERC-7930 addr>",
     "intent": {
       "intentType": "oif-swap",
       "inputs":  [{ "user": "<ERC-7930>", "asset": "<ERC-7930 token on origin>", "amount": "100000000" }],
       "outputs": [{ "receiver": "<ERC-7930 on dest>", "asset": "<ERC-7930 token on dest>", "amount": null }],
       "swapType": "exact-input"
     },
     "supportedTypes": ["oif-escrow-v0"]
   }
   ```

   - `exact-output` instead sets `inputs[].amount: null` and fixes the output.
   - `intent.metadata.exclusiveFor: [addr…]` restricts quotes to the listed solvers.
   - `supportedTypes` takes `"oif-resource-lock-v0"` only if the Compact path is supported.
   - Response: `quotes[]`, best first. Each quote has `quoteId`, `validUntil`, `preview.outputs[].amount`, `metadata.exclusiveFor` (the selected solver), `partialFill` and `failureHandling`.
   - **Verified live 2026-10-03:** 100 USDT (Ethereum) → 99.907081 USDC (Base), `exclusiveFor = 0xfc03…8a88`, `failureHandling: "refund-automatic"`.

   **ERC-7930 address encoding:** `0x0001 | 0000 | <len(chainRef)> | <chainRef big-endian> | 14 | <20-byte address>`. Examples:
   - Ethereum `0x00010000010114…`
   - Base `0x0001000002210514…`
   - Arbitrum `0x0001000002A4B114…`

   A V1 endpoint, `POST /api/v1/integrator/quote/request`, takes CAIP-2 chain IDs plus native addresses instead.

2. **Fund the escrow.** ⚠️ **Docs bug:** the quickstart calls `open(bytes)` with an ABI-encoded order. The deployed escrow has no such function: selector `0x382f431b` is absent from its bytecode. The real function is `open(StandardOrder)`, which takes the struct and is `payable`, with selector `0x7515fd56`. `orderIdentifier(StandardOrder)` (`0x609dbfa0`) is an external view, so compute the orderId on-chain to check client encoding. There are four ways:
   - `approve(escrow)` then `open(order)`. The user pays gas.
   - `openFor(order, sponsor, sig)` with `sig = 0x00 ‖ Permit2 witness signature`. Anyone can submit it, so the user needs no gas once Permit2 is approved. The Permit2 `deadline` is `order.fillDeadline`.
   - `openFor` with `sig = 0x01 ‖ ERC-3009 receiveWithAuthorization signature`, for USDC-style tokens. No approve is needed; the nonce is the orderId and `validBefore` is `fillDeadline`.
   - **Gasless escrow through the order server:** submit the signed order with `POST /orders/submit`, and LI.FI or a solver opens it on-chain.

   Source: [3] `InputSettlerEscrow.sol:216-264`; [1] create-and-submit

3. **Order construction** (`StandardOrder`, [oif-escrow.md](oif-escrow.md)):
   - `inputOracle` and every `outputs[].oracle` must be the same network: the Polymer mainnet oracle (`0x008C…`), left-padded to bytes32 in the outputs.
   - `outputs[].settler` is the output settler (`0x7522…`), also bytes32.
   - `context = 0x` gives a plain limit order. For exclusivity, use `0xe0 ‖ solver(32 bytes) ‖ exclusiveUntil(uint32)`; the docs suggest about 60 s.
   - `fillDeadline` must be before `expires`. The quickstart uses 30 min and 1 h. Orders the server created had `expires − fillDeadline` of about 172,200 s (about 2 days; median of 50 refunded orders).
   - `nonce` must be unique per user.
   - `user` is the refund recipient. It must be able to receive the token on the origin chain.
   - If there are several outputs, put the most valuable first. Filling only the first output is a DoS vector, and the first output's filler is the canonical solver.
   - `call` (callbackData): the recipient must be a contract implementing `outputFilled(bytes32,uint256,bytes)`. If the callback reverts, the order can't be filled at all.

   Source: [1] create-and-submit, request-quote

4. **Track:** `GET /orders/status?onChainOrderId=…` or `?catalystOrderId=…`.
   - `meta.orderStatus` is one of `Submitted | Open | Signed | Delivered | Settled | Refunded`. There is no `Expired` status; check `meta.expiredAt` instead.
   - `meta` also includes `solverAddress`, `refundTxHash`, `orderDeliveredTxHash`, `orderSettledTxHash` and the timestamps.
   - `GET /orders?user=&status=&exclusiveFor=&limit=&offset=` lists orders (`limit` at most 50, `offset` at most 1000).
   - On-chain events, with the orderId as topic1: `Open`, `OutputFilled` (output settler), `Finalised`, `Refunded`. The orderId is `keccak256(abi.encodePacked(chainid, settler, user, nonce, expires, fillDeadline, inputOracle, keccak256(inputs), abi.encode(outputs)))`.

   Source: [1] track-status; live API

5. **Same-chain:** `openForAndFinalise()` on the LIFI escrow opens and settles in one transaction. The output settler acts as its own oracle via `setAttestation`. Source: [3] `InputSettlerEscrowLIFI.sol:84`; [1] architecture/overview

## Refund paths (what the implementor must handle)

| Path | When | Who can call | Depends on | Pays |
| - | - | - | - | - |
| `refundOnNonFill(order, outputIndex)` | after `fillDeadline`, once any output is proven unfilled | anyone | `OutputSettlerSimple.emitNotFilled` on the destination after `fillDeadline`, then a Polymer proof of the `OutputNotFilled` event delivered to the origin oracle | full inputs → `order.user` |
| `refund(order)` | after `expires` | anyone | nothing but the timestamp | full inputs → `order.user` |

- **Fast path:** a non-fill is permanent because `fill` reverts after `fillDeadline`. The proof is bound to the signed `fillDeadline`, and `_resolveLock` lets only one of `finalise` and refund succeed. Source: [3] `InputSettlerEscrow.sol:449-475`, `InputSettlerBase.sol:233-243`, `PolymerOracle.sol:82-86`
- **Observed:** LI.FI runs a refund keeper. All 34 sampled refund transactions with readable RPC were sent by EOA `0xc7dd6725037229bce71aa5f7d1aa72454e316304` through smart account `0xa84b6be6af0750916074f1e43e0b94358681dcc6` (`execute`, selector `0xe9ae5c53`). Each called `refundOnNonFill`, about 170 s after `fillDeadline` (median). `failureHandling: "refund-automatic"` in the quote refers to this keeper, which is a service and not a guarantee.
- **The implementor should run its own fallback.** Call `refund(order)` after `expires` for any order that is still `Deposited`. This needs no oracle and no LI.FI involvement. Optionally run the `emitNotFilled` → Polymer → `refundOnNonFill` path too, to avoid waiting for `expires`.
- **The refund race is inherited:** `finalise` has no expiry check, so a solver that really filled can still claim after `expires` if nobody has refunded first. The user is paid either way. See [oif-escrow.md](oif-escrow.md).
- **Choosing `expires` is a trade-off:** the backstop exit bound is `expires`. A short window protects the user but gives solvers less time to deliver the Polymer proof and `finalise`, which may reduce quoting. The server-created orders sampled used about 2 days.

## Route discovery

- `GET https://order.li.fi/chains/supported`: 30 chains, testnets included.
- `GET https://order.li.fi/routes`: solver standing quotes. Each row gives from chain and token, to chain and token, and `minAmount` / `maxAmount` in input-token base units; `fee` and `gasFee` were 0 on every row. On 2026-10-03 there were 3,139 active routes.
  - On the seven chains above, every cross-chain pair among Ethereum, BSC, Polygon, Base, Arbitrum and Avalanche had routes.
  - They are mostly USDC/USDT, with caps of about $240k per route and up to about $436k into Ethereum USDT.
  - ETH/WETH routes between Ethereum, Arbitrum and Base go up to about 122 ETH. ETH into BSC (as Binance-peg ETH) and Avalanche (as WETH.e) is capped at about 1 ETH.
  - USDC/USDT can be swapped into native BNB or WBNB on BSC, up to about $13.5k.
  - Many token addresses carry no symbol in LI.FI's data.
- The route list says a route exists and how large it can be. Prices come only from `/quote/request`.

## Solvers

- **Permissioned at the order server, permissionless on-chain.** To quote through `order.li.fi`, a solver registers at intents.li.fi, gets an API key, registers signed addresses, and passes a mainnet `exclusiveFor` test "before being whitelisted for the LI.FI API". Quotes go to `POST /quotes/submit` (up to 200k per batch). The server picks solvers on price plus reputation (fill reliability and fill speed). Anyone can still fill an on-chain order directly through `OutputSettlerSimple`, and some solvers find orders on-chain on their own. Source: [1] for-solvers/intro, reputation, testing-integration, authentication
- **Named in LI.FI's docs index:** "LI.FI Solver, Enso, Propeller Heads, Bungee, and a growing solver network". No mapping from these names to addresses is published. Source: [2]
- **Solver addresses seen** in 400 settled orders, 2026-10-03 08:30–11:17 UTC, by number of fills:

  | Address | Fills |
  | - | - |
  | `0x734713ed06d87b623c11ded486cfcec5728cd691` | 161 |
  | `0x7bb2b9b2cf209b88850cb744d9e38297905549c9` | 74 |
  | `0xfc03bb2f5b429a7d1d0ae57e316ba2d34f118a88` | 52 |
  | `0x94807fe4300d15909c1a4fd39f76c61d68aee11e` | 48 |
  | `0x6cd1b8cfcd2ca2bcdb46a2d96bd22b92e16ba427` | 21 |
  | `0xc3c7ea35456420b834a17e895718e1d2ddf6d1d7` | 13 |
  | `0xa3c62f08a9f19857c66da30b6e064b3af3297051` | 11 |
  | `0x42f741dd356404df0fb5ab6160cec7a10834e55e` | 6 |
  | `0x81fc3bd06d58cc7fc191fccad9a6f344f050b520` | 4 |
  | `0xa84b6be6af0750916074f1e43e0b94358681dcc6` | 1 (also the refund keeper's account) |
  | `0xaa45171ef0bd047f62b9e9267b8685de2a0fef6f` | 1 |
  | Solana `9XC5r5sy…` | 8 |

  Pull fresh data with `GET /orders?status=Settled` (field `meta.solverAddress`).
- The three or four largest addresses handle most of the flow. Two-thirds of fills came from the top three.

## Category 1–4 deltas vs [oif-escrow.md](oif-escrow.md)

- **Category 1:** no actor is needed for `refund()` after `expires`. The fast `refundOnNonFill` path needs the Polymer prover to be live and someone to relay the proof. That's permissionless, and LI.FI's keeper does it in practice.
- **Category 2:**
  - The escrow is not upgradeable and has no proxy.
  - Its owner is a Solady `Ownable` **EOA**, `0xab483d44705af49a83553821a1f7aad8bbc70576`, the same on every chain checked. The owner's only power is `setGovernanceFee`: at most 5%, taking effect only after a 7-day delay (`applyGovernanceFee`), and charged on finalise, never on refund.
  - Current state on every chain checked: `governanceFee = 0`, `nextGovernanceFee = 0`, `nextGovernanceFeeTime = uint64.max` (no change pending).
  - There is no pause, and no owner function touches deposits.

  Source: [3] `GovernanceFee.sol`, `InputSettlerEscrowLIFI.sol:33-37,225`; eth_call
- **Category 3:** `refund()` uses no oracle. Polymer gates solver payment and the fast refund. The Polymer oracle contract has no owner and holds an immutable pointer to Polymer's `CrossL2ProverV2` at `0x95cceae71605c5d97a0ac0ea13013b058729d075`, the same on Ethereum, Arbitrum, BSC, Polygon, Avalanche, Gnosis and Base (bytecode read 2026-10-04).
  - **The prover trusts one key.** `validateEvent` checks one ECDSA signature over the state root against `SEQUENCER`, an immutable set at deployment to `0x4632e987c6F31d6351e39324Dec6f1404Af56209`, an EOA, then checks the event's membership under that root. There is no owner, no proxy and no second signer. Source: [8] `CrossL2ProverV2.sol` (`SequencerSignatureVerifierV2._verifySequencerSignature`, `CrossL2ProverV2.validateEvent`)
  - **So one key can take any open order.** A root signed with that key can contain any `OutputFilled` event. The oracle records it, `finalise` pays the inputs to whoever the forger names, and `refund()` then fails because the order is no longer deposited. The window is every moment an order is still deposited, including after `expires` until someone calls `refund()`. Forging a non-fill only triggers an early refund to the user, which costs the user nothing.
  - The oracle is part of the signed order (`inputOracle`, `outputs[].oracle`), so this follows from choosing Polymer. LI.FI's solvers quote only for Polymer orders.
- **Category 4:** no screening in the contracts. The order server can decline to quote for or forward an order. That's a service dependency, not an exit-path one.

## Sources

1. https://docs.li.fi/lifi-intents/ (pages fetched as markdown 2026-10-03): quickstart, intents-api/{api-overview, request-quote, create-and-submit, compact-orders, track-status}, architecture/{overview, oracle-systems}, authentication, for-solvers/{intro, reputation, testing-integration}
2. https://docs.li.fi/llms.txt (docs index, "Last updated: May 2026"), retrieved 2026-10-03
3. https://github.com/catalystsystem/lifi-intent @ 7e32479 (2026-07-29; same as `main` on 2026-10-03): `src/input/escrow/{InputSettlerEscrow,InputSettlerEscrowLIFI}.sol`, `src/input/InputSettlerBase.sol`, `src/libs/{GovernanceFee,MandateOutputEncodingLib}.sol`, `src/integrations/oracles/polymer/PolymerOracle.sol`
4. Sourcify v2 (`sourcify.dev/server/v2/contract/8453/<addr>`): full match for `0x00fC…` (InputSettlerEscrowLIFI, solc 0.8.30), `0x7522…` (OutputSettlerSimple), `0x008C…` (PolymerOracleMapped), `0x0000000000cd…` (InputSettlerCompactLIFI). Also matched on chains 1 and 42161 for the escrow.
5. Public RPC eth_getCode / eth_call / eth_getTransactionByHash on the chains in the deployment table (publicnode, drpc), 2026-10-03
6. Live order server: `order.li.fi` `/chains/supported`, `/routes`, `/orders`, `/quote/request`; `order-dev.li.fi` `/chains/supported`, `/routes`, 2026-10-03
7. https://www.openzeppelin.com/news/oif-contracts-diff-audit-1 — OpenZeppelin diff audit (flags the finalise/refund race)

8. `CrossL2ProverV2` verified source from Base Blockscout (`base.blockscout.com/api/v2/smart-contracts/0x95cceae7…`, verified 2026-09-10, solc 0.8.15), retrieved 2026-10-04; constructor args `clientType "proof_api"`, `sequencer 0x4632e987…`, `chainId 0x1bc`. Not on Sourcify for chains 1, 10, 8453 or 42161. Oracle and prover bytecode read on seven chains through publicnode, 2026-10-04
10. Censorship test, 2026-10-06: `POST order.li.fi/quote/request` with user 0x098B716B…2f96 (OFAC-sanctioned, `isSanctioned` true on the Chainalysis oracle) returned quotes as for an unflagged address
9. `order.li.fi/orders?status=Settled|Refunded`, 400 orders, 2026-10-04, for the `expires` distribution

## Notes / follow-ups

- LI.FI Intent is "the official foundation of the Open Intents Framework". It has been live since May 2026, with Jumper and Rabby as launch integrators.
- Not reviewed: `refundOnNonFill` and `emitNotFilled`. They don't appear in [oif-escrow.md](oif-escrow.md)'s source, so they are LI.FI additions; read `OutputSettlerBase.emitNotFilled` and the Polymer non-fill proof end to end before relying on the fast path.
- The `/orders/submit` gasless-escrow body for `oif-escrow-v0` isn't documented; only the `CatalystCompactOrder` template is. The live OpenAPI is at `https://order.li.fi/docs`, which is JS-rendered, so the spec JSON URL wasn't found.
- Solver identities behind the addresses are not published. Ask LI.FI if attribution matters.
- The header's `sources` pins lifi-intent at 7e32479, which matches the deployed escrow source.
