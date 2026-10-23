---
slug: garden-finance
name: Garden Finance
scope: Garden atomic swaps through the v2 API (create order, then PATCH /orders/{id} for gasless HTLC actions), settled with HTLCs on each chain; rated for an EVM or Bitcoin source. The v2 API generates and holds the order's preimage (the One-Click model); SDK integrations that keep the secret on the user's side differ, see the text
kind: swap
class: B
cross_chain: true
chains: [Bitcoin, Ethereum, Arbitrum, Base, BNB Chain, Solana, Starknet, Litecoin, Lightning, Spark, HyperEVM, Hypercore, Ink, Robinhood, Arc, Tempo]   # /v2/assets, 2026-10-06
source_public: true                      # garden.js SDK, garden-sol (2024), deployed v3 HTLC verified on Blockscout; API, orderbook and preimage manager not public
inherits: []
updated: 2026-10-06

verification:
  service: partial                       # assets, policy and liquidity read live; quotes failed for every pair tried
  exit: source-verified                  # v3 HTLC refund / instantRefund / redeem read in verified source; preimage handling from docs and the OpenAPI spec
  actors: source-verified
  admin: source-verified                 # no owner, proxy or pause; code read on four Ethereum HTLCs
  data: source-verified
  judgment: partial
  incidents: partial                     # two solver incidents found by search; not traced on-chain

exit:
  custody: escrow                        # one HTLC contract per token per chain holds every locked order; Bitcoin uses a per-order HTLC script
  execution: self                        # refund(orderID) after the timelock has no caller check and pays the initiator
  overrides:
    - who: Garden's preimage manager together with the order's solver (Garden runs one of the two solvers with liquidity, garden-solver)
      needs: one organisation where Garden's own solver fills; Garden and the other solver together otherwise
      parties: organisation
      how: the v2 API generates and holds the preimage; given early to the solver, it redeems the user's source HTLC and lets its own destination HTLC expire, so the user is paid nothing
      reach: one
      bounded: false
      cost: the solver's stake (SEED) if slashed; none on-chain
  refund_trigger: timeout                # refund after the HTLC timelock; instantRefund earlier only with the solver's signature
  exit_bound_seconds: 86400              # docs examples: 144 Bitcoin blocks, 7200 Ethereum blocks for a source HTLC; chosen per order by the API
  exit_bound_chosen_by: order creator    # the timelock in the HTLC; the API sets it
  standing_approval: immutable_target    # approve the HTLC, which has no owner or proxy; gasless initiation uses an EIP-712 signature over this one order

actors: []                               # the refund needs no one; on Bitcoin the user signs the refund path themselves

admin:
  upgradeable: false                     # v3 HTLC: no owner, no proxy, no pause; initialise(token) is one-time
  authority: none
  timelock_seconds: none
  immediate_functions: []
  grandfathered: full
  outside_exit_path:
    - what: route policy (open by default, with a pair blacklist), solver selection, preimage manager
      effect: which swaps the API offers and who fills them; off-chain

data_gates: []                           # refund checks only the block-number timelock

judgment:
  screening: []                          # screening stops the solver from initiating, but the user's own refund after expiry is untouched
  freeze_assets: [USDC, USDT, WBTC, cbBTC]
  freeze_pooled: true                    # each token's HTLC contract holds every locked order of that token

service:
  integrator_access:
    api_key: true                        # docs: "Most endpoints require a garden-app-id header"; /assets and /policy answered without one, 2026-10-06
    identity: signup                     # key from the Integrator Portal (portal.garden.finance)
    revocable: unknown
    rate_limited: unknown
  operators:
    - role: Garden API, orderbook and auction; picks the solver
      entity: Garden
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: Preimage manager; generates and holds each v2 order's preimage and redeems for the user
      entity: Garden
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: Solvers (garden-solver, maestro-solver with liquidity on 2026-10-06)
      entity: Garden and a third party
      single_operator: false
      source_public: false
      deployment_config_public: false
  screening:
    - kind: TRM Labs, ZeroShadow, Bybit and Binance screening of connecting and depositing addresses; flagged swaps aren't initiated by solvers
      where: Garden interface and API; Bitcoin depositing addresses
      in_source: false
      enabled_in_production: true        # docs, address-screening page
  bypass: false                          # solvers act on orders the orderbook matched; an HTLC created directly reaches no solver

integration:
  calls: ["GET /v2/quote", "POST /v2/orders (returns a deposit address or signing data)", "PATCH /v2/orders/{id}?action=initiate with the EIP-712 / Solana / Starknet signature (gasless), or initiate on-chain", "GET /v2/orders/{id} until destination_swap.redeem_tx_hash", "refund after the timelock, by PATCH ?action=refund or directly"]
  signatures: ["EIP-712 Initiate(redeemer, timelock, amount, secretHash) for gasless initiation", "solver's EIP-712 signature for instantRefund", "Bitcoin: a transaction to the HTLC address"]
  offchain_required:
    - role: Garden API (quotes, orders, preimage manager, relayer)
      api_key: true
      rate_limited: unknown
  finisher: protocol                     # the preimage manager redeems for the user; the solver redeems the source
  gasless_start: [prior_approval, fee_from_asset] # initiateWithSignature, relayed by Garden, once the token is approved to the HTLC; Bitcoin sources pay their own fee
  monitoring: "GET /v2/orders/{id} status and swap states"
  sdk: "@gardenfi/core, @gardenfi/orderbook, @gardenfi/react-hooks (TypeScript)"
  testnet: true                          # testnet.api.garden.finance
  steps: 4

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: mutual
  holder: unknown
  strike: signed
  expiry: contract                       # the HTLC timelock, 86400 s
  early_close: none                      # instantRefund needs the solver's signature
  premium: none
  terms_fixed_by: contract
  price_set_by: auction
  discipline: unknown
  surplus_to: holder                     # both amounts are fixed, so the solver keeps whatever the market gives beyond them
  extraction: []
  sides: unknown
  rate: firm                             # both HTLCs lock fixed amounts
  quote_validity: unknown
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: "initiateWithSignature is relayed by Garden, but only once the token is approved to the HTLC by transaction"
  - action: refund
    performer: user
    paid: none
    gas_on: funds_chain
    note: refund(orderID) after the timelock has no caller check but pays its caller nothing

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: initiate
    form: typed_data
    note: "EIP-712 Initiate(redeemer, timelock, amount, secretHash); the hashlock itself comes from Garden, rated under Exit path"

incidents:
  - date: "2025-10"
    duration: unknown
    user_funds_lost: unknown             # reported as solver funds; about $10.8-11M drained across Arbitrum, Ethereum, Solana and others
    exits_blocked: unknown
    cause: "compromised solver; part of the proceeds moved to Tornado Cash"
  - date: "2026-07-27"
    duration: unknown
    user_funds_lost: false               # per Garden: only solver-owned assets
    exits_blocked: false                 # the app was halted; HTLC refunds need no one
    cause: "attackers injected fake entries into a solver's off-chain database, so it released about $450K USDT for swaps never funded (Ethereum, Base, Arbitrum, BNB Chain)"

open_questions:
  - "Trade: holder, discipline (CRITERIA.md, Trade)"
  - "Quote: sides, quote_validity (CRITERIA.md, Trade); these decide which quote modes (exact, atleast, upto) the venue can serve, and who decides a partial fill"
  - Whether any route still lets the user supply their own secret hash (the v2 create-order schema has no field for it; the SDK has a client-side SecretManager)
  - Who runs maestro-solver, and how the assets' listed solver addresses (0x18e489f2... on EVM) map to garden-solver and maestro-solver
  - Whether the v2 API serves quotes without a key (every quote tried failed with "No order pair found", with and without the docs' test key)
  - Bitcoin HTLC script and refund path, read from the SDK
  - Whether the October 2025 incident cost any users funds, from a post-mortem
sources:
  - repo: garden.js
    url: https://github.com/gardenfi/garden.js
    commit: 162bd5a842cff04afd44eb0b3b4fc791f7cef48a
    commit_date: 2025-07-11
  - repo: garden-sol
    url: https://github.com/gardenfi/garden-sol
    commit: 9af4e68004b7a8f6219488f33e55a44d35c41f50
    commit_date: 2024-06-26
    note: "older HTLC; the deployed v3 HTLC was read as verified source on Blockscout"
---

# Garden Finance

**Primitive (one line):** An HTLC atomic swap. The user locks funds on the source chain under a hash of a secret. A solver locks on the destination under the same hash. Revealing the secret to redeem on the destination lets the solver claim the source. Either side refunds after its timelock.

## The contracts are sound

The v3 EVM HTLC is verified on Blockscout as `src/swap/HTLC.sol` (solc 0.8.28). The same 8,452-byte code is at Ethereum USDC `0x5fA5…F17E`, WBTC `0xD781…fe95`, USDT `0xCF5E…4A19` and cbBTC `0xe35d…eC04`. Its properties:

- No owner, no proxy, no pause. `initialise(token)` can run only once.
- **`refund(orderID)`**: anyone can call it once `initiatedAt + timelock < block.number`, and it pays only the initiator.
- **`instantRefund`**: earlier, but only with the redeemer's (solver's) EIP-712 signature, and it too pays only the initiator.
- **`redeem`**: checks `sha256(secret)` against an order ID bound to chain, initiator, redeemer, timelock, amount and contract.

So the user's exit needs no one but the user, within the order's timelock. Screening doesn't touch it: a flagged deposit just isn't matched by a solver, and the user refunds after expiry.

## The preimage is Garden's, not the user's

An HTLC protects the user only if the user alone knows the secret until the solver has locked its side. The v2 API's `create-order` request (`POST /v2/orders`) has no `secret_hash` field. The hashlock comes from Garden's **preimage manager**, which the One-Click docs describe: it "generate[s] the preimage, hold[s] it until the solver initiate[s] on the Destination chain", and then redeems for the user.

That puts Garden inside the atomicity guarantee:
- If the preimage manager gave the secret to the solver early, the solver could redeem the user's source HTLC and simply never lock, or let its own destination HTLC expire.
- Garden runs one of the two solvers with liquidity (`garden-solver`). For orders it fills, one organisation could take the user's funds.
- The contracts can't stop this; only the separation of secret holder and solver can.

The older SDK has a client-side `SecretManager` that keeps the secret with the user. Integrations built that way don't carry this override. Whether the current API still allows it isn't clear: the v2 schema has no field for it.

## Solvers and routes

- **Solvers.** The docs describe "an open network of solvers" chosen by auction and staker score. On 2026-10-06, `/v2/liquidity` listed two: `maestro-solver` (about $221k) and `garden-solver` (about $71). `/v2/assets` names one solver address per chain family: `0x18e4…a3a9` for all 19 EVM assets, plus one each for Solana, Starknet, Bitcoin, Lightning and Litecoin.
- **Routes.** `/v2/policy` is "open" by default, with a pair blacklist.
- **Quotes.** I couldn't get a quote: every pair tried returned "No order pair found", with or without the docs' testing key.

## Access and screening

- **API key.** The docs say most endpoints need a `garden-app-id` key from the Integrator Portal. `/v2/assets` and `/v2/policy` answered without one.
- **Screening.** Garden screens connecting and depositing addresses with TRM Labs, ZeroShadow, Bybit and Binance. Flagged swaps aren't initiated, and orders via the SDK and API go through the same process (docs, Address Screening).

## Incidents

- **October 2025:** about $10.8–11M drained through a compromised solver across Arbitrum, Ethereum, Solana and other chains; part moved to Tornado Cash.
- **27 July 2026:** attackers injected fake entries into a solver's off-chain database, and the solver released about $450K USDT for swaps never funded, on Ethereum, Base, Arbitrum and BNB Chain. Garden halted the app and says only solver-owned funds were lost.

Both match the design: a solver can lose its own funds, but the HTLC doesn't let an outsider take a user's. Neither involved the preimage manager.

## Sources

1. https://garden.finance/docs/llms.txt and llms-full.txt (order lifecycle, contracts overview, atomic swaps, intent flow, One-Click swaps, address screening), and the OpenAPI spec `/docs/api-reference/openapi.json`, retrieved 2026-10-06
2. https://garden.finance/docs/api-reference/endpoint/orders/patch — gasless HTLC actions, retrieved 2026-10-06
3. Verified `HTLC` source from `eth.blockscout.com` for `0x5fA5…` and `0xD781…`; `token()`, code size and the ERC-1967 slot on four Ethereum HTLCs, 2026-10-06. Arbitrum and Base Blockscout returned a Cloudflare challenge.
4. Live API, 2026-10-06: `/v2/assets`, `/v2/policy`, `/v2/liquidity` (without a key); `/v2/quote` and `POST /v2/orders` (errors as above)
5. https://github.com/gardenfi/garden.js (`packages/core`, `SecretManager`) and https://github.com/gardenfi/garden-sol
6. [Crypto Briefing: $11M hack via compromised solver](https://cryptobriefing.com/garden-finance-bridge-11m-hack/); [AMBCrypto: exploiter moves $6.65M to Tornado Cash](https://ambcrypto.com/garden-finance-exploiter-moves-6-65m-to-tornado-cash-after-10-8m-hack/); [The Crypto Times: app halted after $450K exploit](https://www.cryptotimes.io/2026/07/27/garden-finance-halts-app-after-450k-usdt-exploit-hits-four-blockchains/); [Parameter: solver database hack](https://parameter.io/garden-finance-halts-operations-following-450k-solver-database-hack/) — retrieved 2026-10-06
