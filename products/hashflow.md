---
slug: hashflow
name: Hashflow
scope: Hashflow same-chain EVM RFQ (HashflowRouter, HashflowPool, HashflowFactory); X-Chain trades are in hashflow-xchain
kind: swap
class: A
cross_chain: false
chains: [ethereum, arbitrum, optimism, polygon, bnb, avalanche, base]   # EVM deployments listed in the repo; Solana program not covered
source_public: true                      # contracts only, marked UNLICENSED; the API is not public
inherits: []
updated: 2026-10-06

verification:
  service: spec-only
  exit: source-verified
  actors: partial                        # market maker set and guardian identities not read on-chain
  admin: source-verified                 # owners read on-chain on all seven chains
  data: source-verified
  judgment: partial
  incidents: partial

exit:
  custody: user_wallet
  execution: self                        # don't submit (RFQ-T), let the quote expire, or revoke the approval (RFQ-M)
  overrides: []                          # tokens move only inside the atomic trade
  refund_trigger: expiry_or_nonce        # quoteExpiry; RFQ-T nonce per effectiveTrader per pool; RFQ-M txid
  exit_bound_seconds: 0                  # funds never leave the wallet
  standing_approval: immutable_target    # HashflowRouter has no proxy; pulls only from msg.sender (RFQ-T) or a trader-signed quote (RFQ-M)

actors: []

admin:
  upgradeable: false                     # router, factory and pool implementation; pools are ERC-1167 clones of a fixed implementation
  authority: eoa                         # 0xac6a83b29e5ff66fd558171ead7ed9d619b055d0 owns router, factory and messengers; EIP-7702-delegated on Ethereum
  timelock_seconds: none
  immediate_functions: []                # none touch funds in a same-chain trade
  grandfathered: full                    # nothing is in flight between trades
  outside_exit_path:
    - what: HashflowRouter.killswitchPool (router owner)
      effect: stops new trades and removeLiquidity on one pool; does not stop destination fills (fillXChain) or the pool's approveToken
      timelock_seconds: none
    - what: HashflowRouter.forceUnauthorizePool (router owner)
      effect: one pool can no longer start trades; destination fills still pass (fillXChain doesn't check authorizedPools)
      timelock_seconds: none
    - what: HashflowRouter.updateLimitOrderGuardian (router owner)
      effect: sets who co-signs limit orders; unset (zero) on every chain read, so limit orders can't execute
      timelock_seconds: none
    - what: HashflowFactory.updatePoolCreatorAuthorization (factory owner)
      effect: decides which market makers may create pools
      timelock_seconds: none
    - what: HashflowRouter.withdrawFunds (router owner)
      effect: sweeps tokens left in the router; the router holds none between trades
      timelock_seconds: none

data_gates: []                           # quoteExpiry and the nonce cap gate the trade, not the exit

judgment:
  screening: []                          # no trader allowlist or blocklist in the contracts
  freeze_assets: []
  freeze_pooled: false                   # trader tokens never rest at a protocol address

service:
  integrator_access:
    api_key: true
    identity: signup
    revocable: true
    rate_limited: true
    note: "credentials issued by Hashflow on request; single-wallet keys bound to one wallet; revocable per Hashflow; market makers rate-limit per trader"
  operators:
    - role: Hashflow RFQ API (api.hashflow.com/taker/v3) and market-maker WebSocket (maker-ws.hashflow.com); collects RFQs, returns MM-signed quotes, relays RFQ-M trades
      entity: unknown                    # "the Hashflow team"; no operating entity named in the docs read
      single_operator: true
      source_public: false               # not among hashflownetwork's public repositories
      deployment_config_public: false
  screening:
    - kind: API credentials issued on request; single-wallet keys bound to one wallet; revocable
      where: taker API access
      in_source: false
      enabled_in_production: true        # docs; revocation per Hashflow's reply to audit HASH-5
    - kind: per-trader rate_limit set by a market maker, with expiry
      where: MM responses; published at /taker/v3/restrictions; the API routes to other makers meanwhile
      in_source: false
      enabled_in_production: true
    - kind: per-RFQ 'compliance' refusal by a market maker, who sees trader and effectiveTrader
      where: each MM's quoting engine
      in_source: false
      enabled_in_production: unknown     # the error code exists; its use isn't published
    - kind: network block at Cloudflare's edge, before any credential check
      where: api.hashflow.com and app.hashflow.com; www.hashflow.com and docs.hashflow.com answered normally
      in_source: false
      enabled_in_production: true        # "Sorry, you have been blocked" (HTTP 403) on 2026-09-29, from two different networks, with curl and with Python using a browser user agent; again on 2026-10-06 ("Attention Required", 403) for /, /taker/v3/chains and app.hashflow.com
    - kind: sanctions screening by Hashflow
      where: unknown
      in_source: false
      enabled_in_production: unknown
  bypass: unknown                        # the contracts need only the MM's signature (and the trader's for RFQ-M); no direct-to-MM channel is documented

integration:
  calls: ["GET api.hashflow.com/taker/v3/market-makers with Authorization", "POST /taker/v3/rfq", "RFQ-T: the trader sends tradeRFQT to HashflowRouter", "RFQ-M: the trader signs the quote and Hashflow or a market maker relays it"]
  signatures: ["EIP-712 trader signature over the quote (RFQ-M)", "market maker's EIP-191 quote signature (comes with the quote)", "ERC-20 approval to HashflowRouter"]
  offchain_required:
    - role: Hashflow taker API v3
      api_key: true                      # every request needs the Authorization credential issued by Hashflow; single-wallet keys are bound to one wallet
      rate_limited: true
  finisher: user                         # RFQ-T; for RFQ-M a relayer (Hashflow or the MM) submits
  gasless_start: none                   # RFQ-M is relayed, but the router approval needs a transaction
  monitoring: "transaction receipt, or the Trade event on the pool"
  sdk: "taker-py (Python, MIT); no current official TypeScript taker SDK found"
  testnet: unknown
  steps: 3

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: counterparty_writes
  holder: user
  strike: quoted
  expiry: counterparty_chosen
  early_close: free
  premium: none
  terms_fixed_by: signature
  price_set_by: quote
  discipline: allowlist_competition      # the API asks several market makers
  surplus_to: none
  extraction: []
  sides: [exact_in]
  rate: firm                             # the quote's rate is preserved for any effectiveBaseTokenAmount up to the maximum
  quote_validity: counterparty_chosen    # quoteExpiry, set by the market maker
  partial_fill: user_chooses             # RFQ-T: the trader submits effectiveBaseTokenAmount up to the quote's maximum; RFQ-M signs fixed amounts and fills whole
  partial_remainder: in_wallet

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: "RFQ-T: the trader sends tradeRFQT; RFQ-M is relayed, but the router approval needs a transaction"
  - action: cancel
    performer: none
    paid: none
    note: "nothing to do: the quote expires"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: RFQ trade
    form: calldata
    bounds: bounded
    verifiable_locally: true
    api_optional: false
    note: "the router checks the market maker's signed quote; quote fields are readable"

incidents:
  - date: 2023-06-14
    duration: days
    user_funds_lost: true                # ~$40K taken by others after a whitehat rescued ~$600K; Hashflow promised to make users whole
    exits_blocked: false
    cause: Approvals left on retired Hashflow contracts let anyone move approved tokens; not the current x-protocol router or pools

open_questions:
  - "Is the Cloudflare block on api.hashflow.com and app.hashflow.com aimed at non-browser clients, or at particular countries or networks? Either way the API refused every request made to it on 2026-09-29"
  - Who operates the Hashflow API and relayer, under which entity and jurisdiction, and whether it screens traders (sanctions, geography) beyond MM rate limits
  - Whether any market maker quotes outside the Hashflow API, which would make bypass real
  - Market maker list per chain (CreatePool and UpdatePoolCreatorAuthorization events) and who controls each pool's `operations`
  - Who holds the owner EOA 0xac6a83b2…, and what its EIP-7702 delegation on Ethereum permits beyond the key itself
  - Whether each deployed router, pool and messenger matches the pinned source
  - "Solana program (CRhtqXk98ATqo1R8gLg7qcpEMuvoPzqD5GNicPPqLMD): not in this repo; Solana remotes are not configured on the Ethereum or Arbitrum messengers"
  - Whether Hashflow completed reimbursement after the June 2023 exploit, and the exact contract involved
  - Same-chain incidents in the last 12 months not yet searched
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: hashflow-contracts
    url: https://github.com/hashflownetwork/x-protocol
    commit: e41cfaadac7d9bacfa368be904a93bd98b5a2df6
    commit_date: 2025-02-15
---

# Hashflow

**Primitive (one line):** RFQ swap. Market makers (MMs) sign quotes (EIP-191); the trader either submits the trade itself (RFQ-T) or signs an EIP-712 quote that a third party relays (RFQ-M). `HashflowRouter` pulls the trader's tokens straight into the MM's pool (or its external account) and the pool pays the quote token in the same transaction. X-Chain trades are a separate entry, `hashflow-xchain.md`.

References are to `source/hashflow-contracts` (hashflownetwork/x-protocol), `evm/contracts/` unless stated.

## Category 1 — Actor-gated edges

### Same-chain RFQ

**Actors on exit path:** none. Funds stay in the trader's wallet until the trade, and the trade is atomic: `_executeRFQTTrade` pulls the base token from `msg.sender` to the pool or external account, then calls the pool, which checks the MM signature and pays the quote token to `quote.trader` (`HashflowRouter.sol:543-580`, `pools/HashflowPool.sol:112-163`). If anything fails, the whole transaction reverts.

**Getting out before a trade:**
- **RFQ-T:** the trader signs the transaction, so not submitting it is enough. Pool nonces are strictly increasing per `effectiveTrader` and capped at `(block.timestamp + 180) * 1000` (`HashflowPool.sol:463-469`, `HashflowRouter.sol:532-535`).
- **RFQ-M:** the trader signs an EIP-712 quote over txid, trader, pool, external account, tokens, amounts and expiry (`HashflowRouter.sol:55-58, 881-903`) and anyone may relay it. There is no on-chain cancel; the signed quote is live until `quoteExpiry` (`:584-603`). Revoking the ERC-20 approval to the router stops it at once. The signature fixes the price, so a late fill honours what the trader signed.
- **Limit orders:** the trader's signature covers only txid, tokens, amounts and expiry; the pool and external account are bound by a second signature from `limitOrderGuardian` (`HashflowRouter.sol:61-64, 631-652, 934-954`). The guardian is unset (zero address) on all seven chains read, so limit orders can't currently execute.

**Standing approval:** the trader approves `HashflowRouter`, which has no proxy (`HashflowRouter.sol:24-30`, constructor plus `initialize`; the ERC-1967 implementation slot is empty on Ethereum) and states it is not upgradeable (`interfaces/IHashflowRouter.sol:27-29`). It pulls only from `msg.sender` (RFQ-T) or from a trader whose signature is checked with `SignatureChecker`, so ERC-1271 wallets work (RFQ-M, `:605-616`). The one arbitrary call, in `fillXChain` (`:354-358`), runs only for a callee that has registered its caller and messenger itself (`:387-448`); a token contract can't do that, which was the fix for audit HASH-1.

**Actors in filling (not exit):**
- Market makers: a pool can be created only by an address the factory owner allows (`HashflowFactory.sol:42-75`); the docs say to ask the Hashflow team to be added. Each pool has an `operations` address (the MM) and a signer key (`HashflowPool.sol:58-93, 423-436`).
- Relayers for RFQ-M: anyone; the interface says "The 3rd party can be the Market Maker itself" (`IHashflowRouter.sol:17-20`).

**Compellability profile:** same-chain exit needs no one.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** none of the core contracts is a proxy. The factory's pool implementation can be set only once (`HashflowFactory.sol:103-116`), and pools are ERC-1167 clones of it (`:91`); on zkSync the factory deploys full pools (`HashflowFactoryZkSync.sol`). Changing behaviour means deploying a new router and new pools.

**Owner:** router, factory and Wormhole messenger all use `Ownable2Step` and can't renounce ownership (`HashflowRouter.sol:514-517`, `HashflowFactory.sol:118-121`, `HashflowWormholeMessenger.sol:420-425`). On Ethereum, Arbitrum, Optimism, Polygon, BNB, Avalanche and Base, `owner()` of router and messenger is 0xac6a83b29e5ff66fd558171ead7ed9d619b055d0, with no pending owner. It is also the Ethereum factory owner and the deployer of router and factory. It has no code on the other six chains, so it is a plain EOA. On Ethereum it carries an EIP-7702 delegation to 0x63c0c19a…dae32b, whose `NAME()` is "EIP7702StatelessDeleGator" and `VERSION()` "1.3.0". It is not a multisig, and there is no timelock.

**Immediate-effect functions** (router owner unless noted):
- `killswitchPool(pool, enabled)` (`HashflowRouter.sol:479-485` → `HashflowPool.sol:439-449`): flips the pool's `enabled` flag, which stops RFQ-T, RFQ-M, X-Chain source legs and `removeLiquidity`. It doesn't stop `fillXChain` or the MM's `approveToken`, so it neither blocks destination payouts nor fully locks MM funds.
- `forceUnauthorizePool(pool)` (`:451-460`): stops new trades on a pool; destination fills continue.
- `updateLimitOrderGuardian`, `withdrawFunds` (`:488-512`).
- Factory owner: `updatePoolCreatorAuthorization` (`HashflowFactory.sol:42-53`).

None of these can move tokens from a trader's wallet or change a signed quote's terms; for same-chain trades they can only stop a trade from happening. Quantstamp listed them all under HASH-3 (acknowledged).

**Grandfathering:** nothing is in flight between trades.

## Category 3 — Data-oracle-gated edges

**Oracles:** none. Prices come from signed quotes; there is no on-chain price feed.

**Gates:** `quoteExpiry`, the RFQ-T nonce cap and pool authorisation gate the trade, not an exit.

## Category 4 — Judgment-oracle-gated edges

**In the contracts:** no trader allowlist, blocklist or screening. `effectiveTrader` is used only for nonces (`IQuote.sol`).

**Off-chain:** MMs see `trader` and `effectiveTrader` in every RFQ and can answer `compliance` or `rate_limit` (with an expiry); traders' current restrictions are published at `/taker/v3/restrictions` and the API routes around them. No sanctions or geo screening by Hashflow itself is documented in the pages read. These govern whether a trader gets a quote, not what happens to funds.

**Stablecoin freeze exposure:** none; trader tokens never rest at a protocol address.

## Service

The Hashflow API is the only documented way to reach market makers. Takers need credentials from Hashflow; single-wallet keys are bound to one wallet, and Hashflow says keys "can be revoked if malicious behavior is observed" (audit HASH-5 reply). MMs connect to Hashflow's WebSocket and get the trader's address with every RFQ, so each MM can decline a specific address, and Hashflow can decline to issue or keep a key. The API's source is not in hashflownetwork's public repositories. On-chain nothing requires Hashflow: RFQ-T needs only the MM's signature, RFQ-M adds the trader's. Bypass would need an MM that quotes outside the API, and none is documented.

## Historical incidents

- **2023-06-14:** approvals that users had left on retired Hashflow contracts let anyone move approved tokens, on Ethereum, Arbitrum, Avalanche, BNB Chain and Polygon (revoke.cash). A whitehat moved ~$600K into a recovery contract users could claim from; about $40K was taken by others. Hashflow said all affected users "will be made whole" and that "The Hashflow DEX was in no way impacted" (The Block). The Block reported it "appears to refer to the firm's bridge contract". The current router and pools weren't involved.

## Composite

**Stuck-leg failure modes:**
1. Same-chain quote not filled or pool killswitched: trade reverts, funds never left. Not a stuck leg.
2. Signed RFQ-M quote the trader wants to withdraw: no cancel; wait for `quoteExpiry` or revoke the approval.

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Same-chain trade fails | immediate; funds never left | `HashflowRouter.sol`, `HashflowPool.sol` |
| RFQ-M withdrawal | `quoteExpiry`, or an approval revoke | `HashflowRouter.sol:584-603` |

**Cross-protocol correlation:** none beyond the chain.

## Sources

- https://github.com/hashflownetwork/x-protocol (`source/hashflow-contracts`): `evm/contracts/HashflowRouter.sol`, `pools/HashflowPool.sol`, `HashflowFactory.sol`, `HashflowFactoryZkSync.sol`, `interfaces/IQuote.sol`, `interfaces/IHashflowRouter.sol`, `xchain/HashflowXChainMessengerBase.sol`, `xchain/HashflowWormholeMessenger.sol`, `xchain/HashflowLayerZeroMessenger.sol`, `evm/deployed-contracts/*.json`, `evm/README.md`, `aggregator-evm/contracts/SwapFacade.sol` (a separate aggregator, not covered here) — read 2026-09-28
- Quantstamp, "Hashflow Protocol 3" audit, 2023-05-22 to 2023-06-16, in the same repo at `evm/audits/2023-06-16-Quantstamp.pdf` (HASH-1, -3, -4, -5, -7, -10) — read 2026-09-28
- On-chain `eth_call`, `eth_getCode`, `eth_getStorageAt` at latest block, 2026-09-28: router `owner()`, `pendingOwner()`, `factory()`, `limitOrderGuardian()` and messenger `owner()`, `router()` on Ethereum, Arbitrum, Optimism, Polygon, BNB, Avalanche, Base; on Ethereum also factory `owner()`/`_poolImpl()`, messenger `wormholeEndpoint()`, consistency levels, `permissionedRelayers`, `xChainRemotes`, chain-ID mappings, owner code and delegate `NAME()`/`VERSION()`, router/factory deployment receipts; on Arbitrum the messenger's endpoint, consistency levels and remotes
- https://docs.hashflow.com/hashflow/llms.txt — docs index — retrieved 2026-09-28
- https://docs.hashflow.com/hashflow/taker/getting-started-api-v3.md — taker credentials, `/restrictions`, X-Chain via Wormhole — retrieved 2026-09-28
- https://docs.hashflow.com/hashflow/market-making/getting-started-api-v3.md — pool creator allowlist, WebSocket, RFQ fields, `compliance`/`rate_limit` errors, external accounts — retrieved 2026-09-28
- https://api.github.com/orgs/hashflownetwork/repos — public repositories (no API server) — retrieved 2026-09-28
- https://wormhole.com/docs/protocol/infrastructure/guardians/ — 19 guardians, quorum 13 — retrieved 2026-09-28
- https://wormhole.com/docs/products/reference/consistency-levels/ — levels 1 (finalized) and 200 (instant), via search summary — retrieved 2026-09-28
- https://revoke.cash/exploits/hashflow — June 2023 exploit — retrieved 2026-09-28
- https://www.theblock.co/post/234671/trading-firm-hashflow-faces-ongoing-exploit-with-600000-lost-so-far-peckshield — June 2023 exploit — retrieved 2026-09-28
- https://github.com/liqtags/crypto-rekts/blob/main/rekts/Hashflow.md — June 2023 exploit summary — retrieved 2026-09-28
- https://gov.hashflow.com/tos — forum terms naming "Hashflow Foundation" (template text; says nothing about the API) — retrieved 2026-09-28
- https://hashflow.com/terms — JavaScript-only, no content retrieved — 2026-09-28
- https://www.certik.com/blog/post-mortem-hashflow, https://medium.com/neptune-mutual/how-was-hashflow-exploited-514b47b32785 — both returned 403 on 2026-09-28; cited by the previous version of this entry
- https://docs.hashflow.com/hashflow/taker/getting-started-api-v3.md (credentials from the Hashflow team; `Authorization` header on every request; wallet-bound keys for single-wallet traders), 2026-10-06

## Notes / follow-ups

- Corrections to the previous version: the killswitch and `forceUnauthorizePool` do not stop destination fills; LayerZero isn't shown to be deployed; the owner is an EOA, not a team multisig; limit orders are disabled (guardian unset); the June 2023 details (unverified auxiliary contract, selector `0x1ce5`, full reimbursement) aren't supported by the sources that could be read; nonces apply to RFQ-T, not RFQ-M.
- X-Chain trades moved to `hashflow-xchain.md` on 2026-09-28.
- Remaining open questions are in the header.
