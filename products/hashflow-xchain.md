---
slug: hashflow-xchain
name: Hashflow X-Chain
scope: Hashflow X-Chain RFQ over HashflowWormholeMessenger; same-chain RFQ is in hashflow
kind: swap
class: C                                 # no refund path at all once the source leg settles; closest to C
cross_chain: true
chains: ['ethereum', 'arbitrum', 'optimism', 'polygon', 'bnb', 'avalanche', 'base']
source_public: true
inherits: [hashflow, wormhole]           # same contracts, API and market makers as hashflow
updated: 2026-09-28

verification:
  service: spec-only
  exit: source-verified
  actors: partial                        # market maker set and guardian identities not read on-chain
  admin: source-verified
  data: source-verified
  judgment: partial
  incidents: partial

exit:
  custody: in_flight_message           # source tokens are paid to the MM's srcPool or srcExternalAccount; the trader holds a Wormhole message
  execution: permissionless            # the finalized VAA can be relayed by anyone; it only succeeds if the MM's destination side pays
  overrides:
    - who: the quoting market maker (destination pool `operations`)
      needs: one party
      how: leave the destination pool or external account short, drop the external account's allowance, or de-authorise the messenger or source pool, so fillXChain reverts; it can restore them around its own relays so other trades still fill
      reach: one
      bounded: false
      cost: none on-chain; it already holds the trader's source tokens
    - who: HashflowWormholeMessenger owner (the same EOA as the router)
      needs: one key
      how: updateWormhole on the destination messenger to an endpoint that rejects one VAA and passes the rest; or change remotes or chain-ID mappings (reach all)
      reach: one
      bounded: false
      cost: none on-chain
    - who: Wormhole guardians
      needs: 7 of 19 decline to sign one message (quorum is 13)
      how: no VAA exists, so nothing can be delivered
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: none                 # no source-side refund in any contract; quoteExpiry is checked only on the source chain
  exit_bound_seconds: unbounded        # a failed destination fill has no refund; normal delivery waits for source finality
  standing_approval: immutable_target
actors:
  - role: Market maker that quoted; pays the destination leg from its pool or external account
    entity: unknown                    # KYC'd per Hashflow's reply to audit HASH-4; names not published
    jurisdiction: unknown
    set: single                        # the one MM whose pool took the source tokens; MMs are admitted by the factory owner
    independence: single_org
  - role: Wormhole guardians; sign the VAA for the trade message
    entity: unknown                    # guardian identities not read for this entry
    jurisdiction: unknown
    set: m_of_n                        # 13 of 19
    independence: unknown
  - role: Relayer; submits the VAA to wormholeReceive on the destination
    entity: anyone for the finalized message; one EOA (0x90634e87…) for the fast message
    jurisdiction: pseudonymous
    set: permissionless                # the finalized message has no permissionedRelayer
    independence: independent
admin:
  upgradeable: false                   # messengers aren't proxies, but every setting below is live
  authority: eoa
  timelock_seconds: none
  immediate_functions:
    - function: HashflowWormholeMessenger.updateWormhole
      caller: messenger owner
      effect: replaces the endpoint that verifies VAAs; can drop chosen messages or accept forged ones (forged fills pay out of MM pools that authorised the messenger)
    - function: HashflowXChainMessengerBase.updateXChainRemoteAddress, updateWormholeChainIdForHashflowChainId
      caller: messenger owner
      effect: can make every in-flight message from a chain undeliverable
    - function: updateWormholeConsistencyLevel, updateWormholeConsistencyLevelFast, updatePermissionedRelayer
      caller: messenger owner
      effect: changes finality for new messages and who may relay fast ones
    - function: HashflowPool.removeLiquidity, updateXChainMessengerAuthorization, updateXChainPoolAuthorization, approveToken/decreaseTokenAllowance
      caller: the market maker's `operations` address
      effect: can leave a trade whose source leg has settled unfillable (the override above)
  grandfathered: none                  # the destination fill runs under whatever settings apply when it's relayed
data_gates:
  - kind: source finality
    where: Wormhole guardians observing HashflowWormholeMessenger.publishMessage
    trigger: consistency level 1 (finalized) for the permissionless message; 200 (instant) for the fast message, relayable only by the permissioned relayer
    blocks_exit: true
    reset: bounded
judgment:
  screening: []
  freeze_assets: unknown
  freeze_pooled: true                  # the destination leg is paid from the MM's pool or external account; a freeze there stops the fill

service:
  same_as: hashflow                      # the same API, credentials and market makers

integration:                             # not yet researched; see open_questions
  calls: unknown
  signatures: unknown
  offchain_required: unknown
  finisher: unknown
  gasless_start: unknown
  monitoring: unknown
  sdk: unknown
  testnet: unknown
  steps: unknown

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: counterparty_writes
  holder: user
  strike: quoted
  expiry: counterparty_chosen
  early_close: unknown
  premium: none
  terms_fixed_by: signature
  price_set_by: quote
  discipline: unknown
  surplus_to: none
  extraction: []
  sides: [exact_in]
  rate: firm
  quote_validity: counterparty_chosen    # quoteExpiry, checked on the source chain only
  partial_fill: user_chooses             # the trader submits effectiveBaseTokenAmount up to the quote's maximum (XChainRFQTQuote)
  partial_remainder: in_wallet

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: unknown
    note: not researched
  - action: claim
    performer: anyone
    paid: unknown
    note: the finalized VAA can be relayed by anyone; whether they are paid wasn't read

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: X-Chain RFQ trade
    form: calldata
    bounds: bounded
    verifiable_locally: true
    api_optional: false

incidents: []                            # none found in which an X-Chain trade went unfilled; not searched thoroughly

open_questions:
  - "Trade: early_close, discipline (CRITERIA.md, Trade)"
  - "Paid execution, claim step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - "The integration facts (calls, signatures, finisher, gasless_start by token standard), from the X-Chain router"
  - Whether Hashflow or its MMs have ever left an X-Chain trade unfilled, and how it was settled (the audit's HASH-4 reply points to KYC and law enforcement, not to a contract path)
  - Market maker list per chain (CreatePool and UpdatePoolCreatorAuthorization events) and who controls each pool's `operations`
  - Which messengers each pool has authorised on the router (UpdateXChainMessengerAuthorization events); no LayerZero messenger is listed in the repo's deployments
  - Who holds the owner EOA 0xac6a83b2…, and what its EIP-7702 delegation on Ethereum permits beyond the key itself
  - Whether each deployed router, pool and messenger matches the pinned source
  - Wormhole guardian identities and independence; whether the Wormhole Governor applies to non-token-bridge emitters like this messenger
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: hashflow-contracts
    url: https://github.com/hashflownetwork/x-protocol
    commit: e41cfaadac7d9bacfa368be904a93bd98b5a2df6
    commit_date: 2025-02-15
---

# Hashflow X-Chain

**Primitive (one line):** RFQ swap across chains. The trader's tokens go to the market maker's pool (or external account) on the source chain, a Wormhole message carries the trade, and the MM's pool on the destination chain pays out when that message is relayed. Same-chain RFQ, the API and the market-maker set are in `hashflow.md`; this entry covers what differs once a trade crosses chains.

References are to `source/hashflow-contracts` (hashflownetwork/x-protocol), `evm/contracts/` unless stated.

## Category 1 — Actor-gated edges

**What happens:** `tradeXChainRFQT` / `tradeXChainRFQM` move the trader's tokens to the source pool or its external account, the pool checks the MM signature, and the router asks the messenger to send the trade (`HashflowRouter.sol:690-837`). On the destination chain, `wormholeReceive` verifies the VAA, checks the remote, and calls `router.fillXChain`, which calls `pool.fillXChain` to pay the trader from the pool or the MM's external account (`xchain/HashflowWormholeMessenger.sol:275-387`, `HashflowRouter.sol:316-359`, `HashflowPool.sol:254-279`).

**No refund.** Nothing in the contracts returns source tokens: there is no timeout, and `quoteExpiry` is "Only enforced on the source chain" (`interfaces/IQuote.sol`). If the destination fill reverts, the Wormhole VAA can be retried by anyone later (the messenger's own comment: "Wormhole VAAs are non-blocking", `HashflowWormholeMessenger.sol:290-292`), but it only succeeds once the MM's side can pay. Quantstamp raised this as HASH-4 ("Failure to Send Message to Destination Chain Leads to Loss of User Funds on Source Chain") and recommended a return path; Hashflow acknowledged it without one, replying that "all Market Makers on Hashflow undergo a KYC process. This means that Law Enforcement can be engaged … Furthermore, the Hashflow API implementation checks that enough tokens have been deposited at the time of RFQ" (`evm/audits/2023-06-16-Quantstamp.pdf`).

**Can one X-Chain trade be singled out?**
- **The quoting MM, alone.** Its `operations` address can empty the destination pool (`removeLiquidity`, `HashflowPool.sol:381-408`), cut the external account's allowance (the account's own ERC-20 approval, or `decreaseTokenAllowance`), or de-authorise the messenger or source pool (`:312-339`, via `HashflowRouter.sol:363-433`). Any of these makes `fillXChain` revert. Because the destination fill can be retried by anyone at any time, holding back one trade while others fill means restoring funds only around its own relays; nothing on-chain prevents that. The MM already holds the trader's source tokens.
- **The messenger owner, alone.** `updateWormhole` replaces the contract that verifies VAAs (`HashflowWormholeMessenger.sol:118-125`); an endpoint that rejects one VAA and passes others holds back one trade. Changing remotes or chain-ID mappings (`HashflowXChainMessengerBase.sol:39-46`, `HashflowWormholeMessenger.sol:390-418`) holds back every trade from a chain. The same owner can make the messenger accept forged fills, which would be paid out of MM pools, not traders' wallets.
- **Wormhole guardians, in collusion.** A VAA needs 13 of 19 guardian signatures, so 7 declining to sign one message leaves it undeliverable.
- Not an override: the killswitch and `forceUnauthorizePool` don't stop destination fills. `pool.fillXChain` doesn't check `signerConfiguration.enabled`, and `router.fillXChain` doesn't check `authorizedPools` (`HashflowPool.sol:254-265`, `HashflowRouter.sol:316-344`).

**Relaying:** the finalized message carries no `permissionedRelayer`, so anyone can submit it (`HashflowWormholeMessenger.sol:226-246, 320-332`); Hashflow's reply to audit HASH-7 says "Hashflow relays are permissionless and the app will allow for self relay". A second "fast" message at consistency level 200 can only be relayed by the permissioned relayer. On Ethereum that is EOA 0x90634e878d282658cd742a3f72f2d8fe5a918799 for every destination chain.

**LayerZero:** `xchain/HashflowLayerZeroMessenger.sol` exists in source (retryable payloads anyone can retry; owner `forceResumeReceive` and `setConfig`), but the repo lists no LayerZero deployment and the taker docs name only Wormhole. Pools opt into messengers one by one (`HashflowRouter.sol:415-433`; audit HASH-10), so whether any pool uses LayerZero is open.
**Market makers:** admitted by the factory owner, as described in `hashflow.md`.

**Compellability profile:** once its source leg settles, a trade depends on one market maker (whose identity isn't public) and one owner key for the messengers.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** none of the core contracts is a proxy. The factory's pool implementation can be set only once (`HashflowFactory.sol:103-116`), and pools are ERC-1167 clones of it (`:91`); on zkSync the factory deploys full pools (`HashflowFactoryZkSync.sol`). Changing behaviour means deploying a new router and new pools.

**Owner:** router, factory and Wormhole messenger all use `Ownable2Step` and can't renounce ownership (`HashflowRouter.sol:514-517`, `HashflowFactory.sol:118-121`, `HashflowWormholeMessenger.sol:420-425`). On Ethereum, Arbitrum, Optimism, Polygon, BNB, Avalanche and Base, `owner()` of router and messenger is 0xac6a83b29e5ff66fd558171ead7ed9d619b055d0, with no pending owner. It is also the Ethereum factory owner and the deployer of router and factory. It has no code on the other six chains, so it is a plain EOA. On Ethereum it carries an EIP-7702 delegation to 0x63c0c19a…dae32b, whose `NAME()` is "EIP7702StatelessDeleGator" and `VERSION()` "1.3.0". It is not a multisig, and there is no timelock.

**Immediate-effect functions on trades in flight:**
- Messenger owner: `updateWormhole`, `updateXChainRemoteAddress`, `updateWormholeChainIdForHashflowChainId`, consistency levels, `updatePermissionedRelayer`, `withdrawFunds` (`HashflowWormholeMessenger.sol:118-172, 390-418`, `HashflowXChainMessengerBase.sol:39-51`). These act on X-Chain trades already in flight.
- Not stopping fills: `killswitchPool` and `forceUnauthorizePool` stop new trades and source legs, but destination fills continue (`HashflowRouter.sol:451-485`, `HashflowPool.sol:439-449`).

**Grandfathering:** none. The destination fill runs under whatever messenger and pool settings apply when it is relayed.

## Category 3 — Data-oracle-gated edges

**Gates:** the permissionless message is published at Wormhole consistency level 1 (finalized) and the fast one at 200 (instant), read on the Ethereum and Arbitrum messengers. That delay has a known limit.

## Category 4 — Judgment-oracle-gated edges

**In the contracts:** no trader allowlist, blocklist or screening. `effectiveTrader` is used only for nonces (`IQuote.sol`).

**Stablecoin freeze exposure:** the destination leg is paid from the MM's pool or external account, so a freeze of that address stops the fill while the trader's source tokens are already gone.

## Service

The same API, credentials and market makers as `hashflow.md`.

## Historical incidents

- No incident found in which an X-Chain trade went unfilled; not yet searched thoroughly.

## Composite

**Stuck-leg failure modes:**
1. Destination fill fails because the MM's pool or external account can't pay, or it has de-authorised the path: source tokens are with the MM, anyone can retry, and there is no refund.
2. Messenger reconfigured by its owner: messages from a chain, or chosen ones, become undeliverable.
3. Wormhole guardians don't produce a VAA: undeliverable.
4. Issuer freeze on the MM's destination pool or external account: fill fails.

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| X-Chain fill fails (MM side) | unbounded; no refund path | `HashflowPool.sol:254-279`; audit HASH-4 |
| Messenger owner change | unbounded | `HashflowWormholeMessenger.sol:118-125` |
| No VAA | unbounded | Wormhole guardian quorum |

**Cross-protocol correlation:** fails together with anything relying on Wormhole guardians.

## Sources

- https://github.com/hashflownetwork/x-protocol (`source/hashflow-contracts`): `evm/contracts/HashflowRouter.sol`, `pools/HashflowPool.sol`, `HashflowFactory.sol`, `HashflowFactoryZkSync.sol`, `interfaces/IQuote.sol`, `interfaces/IHashflowRouter.sol`, `xchain/HashflowXChainMessengerBase.sol`, `xchain/HashflowWormholeMessenger.sol`, `xchain/HashflowLayerZeroMessenger.sol`, `evm/deployed-contracts/*.json`, `evm/README.md`, `aggregator-evm/contracts/SwapFacade.sol` (a separate aggregator, not covered here) — read 2026-09-28
- Quantstamp, "Hashflow Protocol 3" audit, 2023-05-22 to 2023-06-16, in the same repo at `evm/audits/2023-06-16-Quantstamp.pdf` (HASH-1, -3, -4, -5, -7, -10) — read 2026-09-28
- On-chain `eth_call`, `eth_getCode`, `eth_getStorageAt` at latest block, 2026-09-28: router `owner()`, `pendingOwner()`, `factory()`, `limitOrderGuardian()` and messenger `owner()`, `router()` on Ethereum, Arbitrum, Optimism, Polygon, BNB, Avalanche, Base; on Ethereum also factory `owner()`/`_poolImpl()`, messenger `wormholeEndpoint()`, consistency levels, `permissionedRelayers`, `xChainRemotes`, chain-ID mappings, owner code and delegate `NAME()`/`VERSION()`, router/factory deployment receipts; on Arbitrum the messenger's endpoint, consistency levels and remotes
- https://docs.hashflow.com/hashflow/taker/getting-started-api-v3.md — taker credentials, `/restrictions`, X-Chain via Wormhole — retrieved 2026-09-28
- https://wormhole.com/docs/protocol/infrastructure/guardians/ — 19 guardians, quorum 13 — retrieved 2026-09-28
- https://wormhole.com/docs/products/reference/consistency-levels/ — levels 1 (finalized) and 200 (instant), via search summary — retrieved 2026-09-28

## Notes / follow-ups

- Split from `hashflow.md` on 2026-09-28; the analysis was done there.
- Corrections to the earlier combined entry: the killswitch and `forceUnauthorizePool` do not stop destination fills; LayerZero isn't shown to be deployed; the owner is an EOA, not a team multisig.
- Remaining open questions are in the header.
