---
slug: stargate
name: Stargate
scope: Stargate V2 pools (StargatePoolUSDC read on Ethereum, Arbitrum, Base) and the TokenMessaging OApp that carries transfers over LayerZero; rated for a taxi or bus transfer of a pooled asset. Hydra (OFT) paths aren't covered
kind: bridge
class: E
cross_chain: true
chains: unknown                          # many; read on Ethereum, Arbitrum, Base
source_public: true                      # verified on Blockscout; github.com/stargate-protocol
inherits: [layerzero-oft]                # LayerZero messaging and DVNs
updated: 2026-10-04

verification:
  service: spec-only
  exit: source-verified                  # StargateBase receive, retry and pause paths read from verified source
  actors: partial                        # DVN addresses read; two of three not identified
  admin: source-verified                 # owner, planner, treasurer, TokenMessaging owner and delegate read on Ethereum
  data: partial
  judgment: spec-only
  incidents: partial

exit:
  custody: pooled                        # the user's tokens join the source pool; the destination pool pays out
  execution: automatic                   # DVNs verify, the executor delivers; a failed delivery is stored in unreceivedTokens and anyone can retryReceiveToken
  overrides:
    - who: OneSig 0xbe634b030feaab661300667eaf82510a3a025413 (5 of 7), owner of the Ethereum pool and of TokenMessaging, and its endpoint delegate
      needs: 5 of 7 signers; who they are isn't read
      parties: unknown
      how: setAddressConfig to make itself tokenMessaging and call receiveTokenTaxi to pay any receiver from the pool; or change TokenMessaging's DVN configuration or peers so one message is never verified, or a forged one is
      reach: one
      bounded: false
      cost: none on-chain
    - who: any one of the three required DVNs on the pathway (Arbitrum to Ethereum)
      needs: one party; 3 of 3 required, no optional DVNs
      parties: organisation
      how: withhold verification of one transfer; it stays undelivered with no refund path
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: none                   # no refund once sent; delivery can only be retried
  exit_bound_seconds: unknown            # 20 source confirmations, DVN verification, then the executor; bus mode also waits for the bus to be driven
  exit_bound_chosen_by: none
  standing_approval: immutable_target    # approve the pool, which isn't a proxy; but its owner can redirect payouts (above)

actors:
  - role: DVNs; verify the TokenMessaging message (3 required, Arbitrum to Ethereum)
    entity: LayerZero Labs (0x589dedbd...), and two not identified (0xa4fe5a5b..., 0xa59ba433...)
    jurisdiction: unknown
    set: m_of_n                          # 3 of 3
    independence: unknown
  - role: Executor; delivers the verified message (lzReceive)
    entity: anyone                       # LayerZero's executor normally; lzReceive on the endpoint is permissionless once verified
    jurisdiction: pseudonymous
    set: permissionless
    independence: independent

admin:
  upgradeable: false                     # pools and TokenMessaging are not proxies
  authority: multisig                    # LayerZero OneSig, 5 of 7, per chain (different addresses)
  timelock_seconds: none
  immediate_functions:
    - function: StargateBase.setAddressConfig
      caller: owner (OneSig 5 of 7)
      effect: replaces tokenMessaging, the only caller allowed to pay out of the pool
    - function: setPause
      caller: planner, an EOA (0xe37f7c80...88b5 on Ethereum)
      effect: receives, retries and LP redeems all revert while paused
    - function: TokenMessaging setPeer, and endpoint setConfig / setReceiveLibrary as delegate
      caller: OneSig
      effect: which messages are accepted as transfers
  grandfathered: none
  outside_exit_path:
    - what: withdrawTreasuryFee, addTreasuryFee, recoverToken (not the pool token)
      effect: treasury and stray tokens
      caller: treasurer contract 0x1041d127...

data_gates:
  - kind: source confirmations
    where: DVNs before verifying
    trigger: fewer than 20 confirmations on Arbitrum
    blocks_exit: true
    reset: bounded

judgment:
  screening: unknown
  freeze_assets: [USDC]
  freeze_pooled: true                    # the pool holds every LP's and in-flight user's USDC

service:
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: false
    note: "contracts are called directly; quotes are on-chain (quoteSend / quoteOFT)"
  operators: []
  screening: unknown
  bypass: true

integration:
  calls: ["quoteSend / quoteOFT on the pool", "approve the pool and call send (taxi) or send with bus options", "track by LayerZero guid; retryReceiveToken if delivery stored it as unreceived"]
  signatures: ["ERC-20 approval or permit"]
  offchain_required: []
  finisher: anyone
  gasless_start: none
  monitoring: "LayerZero Scan by guid, or OFTSent / OFTReceived / UnreceivedTokenCached events"
  sdk: unknown
  testnet: unknown
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: delivery
  holder: none
  strike: par
  expiry: none
  early_close: none
  premium: none
  terms_fixed_by: contract
  price_set_by: par
  discipline: none
  surplus_to: none
  extraction: []
  sides: [exact_in]
  rate: par                              # same asset across chains, less any fee
  quote_validity: none
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: "approve the pool and call send, paying the LayerZero fee in native gas"
  - action: retry
    performer: user
    paid: none
    gas_on: other_chain
    note: "if delivery was stored as unreceived, retryReceiveToken on the destination pays its caller nothing"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: send
    form: self_built

incidents: []                            # no direct exploit found (2026-09-16)

open_questions:
  - Who signs each OneSig, and whether the owner and planner differ per chain
  - Identities of DVNs 0xa4fe5a5b... and 0xa59ba433..., and the configuration on other pathways
  - Who holds the planner EOA 0xe37f7c80...88b5
---

# Stargate

**Primitive (one line):** Omnichain pooled native asset bridge using Delta algorithm for unified cross-chain shared liquidity pools; LayerZero provides cross-chain messaging; "Instant Guaranteed Finality" — once committed, protocol guarantees delivery by absorbing liquidity risk.
**Product scope of this entry:** Stargate V2 (LayerZero pooled bridge)

## Category 1 — Actor-gated edges

**Actors on exit path:**
- LayerZero messaging (DVN verification) required for cross-chain coordination
- StargateDAO governance + community multisig for protocol changes

**User self-refund:** **NO.** "Instant Guaranteed Finality" means once committed, the protocol guarantees delivery. No user-initiated cancellation mid-flight. If liquidity depletes, Delta algorithm increases fees and incentivizes rebalancing — typically resolves within hours.

## Category 2 — Modification-gated edges

**Upgrade authority:** StargateDAO via veSTG governance + trusted community multisig. Contracts are upgradeable (V1→V2 migration occurred). Pausable at contract and LayerZero endpoint level.

## Historical incidents

No direct exploit of Stargate bridge. Used as routing path by BNB Chain bridge exploiter (2022) to move stolen funds — Stargate itself was not the victim. STG token reissued after Alameda/FTX collapse exposed 10% supply held by Alameda (2023).

## Source and on-chain state (2026-10-04)

Source is the verified `StargatePoolUSDC` on Ethereum (`0xc026…89C7`, Blockscout), with `StargateBase` and `StargatePool`. The pool isn't a proxy, and the same 23,555-byte code is on Arbitrum and Base. This replaces Category 2's "StargateDAO via veSTG governance" for the contracts read.

**Who can do what:**
- **Payouts.** Only `tokenMessaging` can call `receiveTokenTaxi` and `receiveTokenBus`, which pay out of the pool.
- **The owner** can change `tokenMessaging` with `setAddressConfig`, immediately (`StargateBase.sol:140`).
- **The planner** can `setPause`. While paused, every receive, `retryReceiveToken` and `redeem` reverts (`nonReentrantAndNotPaused`).
- **Failed deliveries** are cached in `unreceivedTokens`. Anyone can retry them, and there is no refund on the source.

**On Ethereum:**
- **Pool owner:** OneSig `0xbe63…5413`, 5 of 7 (`threshold()`, `getSigners()`, OneSig v0.0.1). Arbitrum and Base have their own OneSigs.
- **Planner:** `0xe37f…88b5`, an EOA.
- **Treasurer:** a contract.
- **TokenMessaging:** `0x6d66…a980`. Its owner and its endpoint delegate are the same OneSig.
- **Pathway Arbitrum → Ethereum:** the receive library is `0xc02a…24c2` (not the default). It requires 20 confirmations and **3 of 3 required DVNs** (`0x589d…236b` LayerZero Labs, `0xa4fe…c2cd`, `0xa59b…0ba5`), with no optional DVNs.

## Sources

1. https://stargateprotocol.gitbook.io/stargate/ — Stargate docs
2. https://github.com/stargate-protocol/stargate — source repo (not cloned; verified source used instead)
3. Verified source of `StargatePoolUSDC` and the owner `OneSig`, from `eth.blockscout.com`, 2026-10-04
4. eth_call on Ethereum, Arbitrum and Base, 2026-10-04: `owner`, `getAddressConfig`, `status`, OneSig `threshold` / `getSigners`, endpoint `delegates`, `getReceiveLibrary`, `getConfig(…, 2)`
