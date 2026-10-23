---
slug: everclear
name: Everclear
scope: Everclear (formerly Connext) intents created on EverclearSpoke 0xa05A3380889115bf313f1Db9d5f335157Be4D816 through the FeeAdapter, netted on the Everclear hub chain and settled back to spokes over Hyperlane; read on Ethereum, Arbitrum, Base
kind: settlement
class: C
cross_chain: true
chains: [Ethereum, Optimism, BSC, Unichain, Polygon, zkSync Era, Ronin, Base, ApeChain, Mode, Arbitrum, Avalanche, Zircuit, Linea, Blast, Scroll, Taiko, Berachain, Gnosis, Mantle, Sonic, Ink, TAC, Tron, Solana]   # spokes per docs; hub on Everclear (25327)
source_public: true
inherits: [hyperlane-warp]               # Hyperlane carries hub and spoke messages
updated: 2026-10-04

verification:
  service: spec-only
  exit: partial                          # spoke source read; hub settlement logic from docs
  actors: partial
  admin: source-verified                 # spoke and gateway owners, lighthouse, watchtower, ISM read on three spokes
  data: spec-only
  judgment: spec-only
  incidents: partial

exit:
  custody: in_flight_message             # the input sits in the origin spoke until the hub settles the intent to a destination
  execution: automatic                   # Everclear's agents dispatch the queues; anyone can dispatch them by paying the Hyperlane fee
  overrides:
    - who: spoke and gateway owner, a 2-of-6 Safe (0xa02a88f0... on Ethereum, 0xf20d5277... on Arbitrum and Base)
      needs: 2 of 6 Safe signers; who they are isn't read
      parties: unknown
      how: upgrade the UUPS spoke, or updateGateway / updateMessageReceiver / updateSecurityModule so a forged settlement pays elsewhere or a real one is refused
      reach: one
      bounded: false
      cost: none on-chain
    - who: whoever controls the Everclear hub chain and its contracts
      needs: unknown                     # hub admin not read
      parties: unknown
      how: never settle one intent, or settle it to someone else
      reach: one
      bounded: false
      cost: unknown
  refund_trigger: none                   # an unfilled intent isn't returned; after its TTL it is netted and settled on the hub instead
  exit_bound_seconds: unknown
  exit_bound_chosen_by: none
  standing_approval: upgradeable_target  # approve the FeeAdapter, which forwards to the upgradeable spoke

actors:
  - role: Hyperlane validators securing hub and spoke messages (ISM per spoke; Arbitrum uses the mailbox default)
    entity: unknown
    jurisdiction: unknown
    set: unknown
    independence: unknown
  - role: Queue dispatchers (processIntentQueue / processFillQueue / settlement queue)
    entity: anyone                       # Everclear's agents by default; solvers can call them with the Hyperlane fee
    jurisdiction: pseudonymous
    set: permissionless
    independence: independent

admin:
  upgradeable: true                      # EverclearSpoke and SpokeGateway are UUPS proxies (ERC-1967 implementation, no admin slot)
  authority: multisig                    # 2-of-6 Safes per chain
  timelock_seconds: none
  immediate_functions:
    - function: upgradeToAndCall on EverclearSpoke and SpokeGateway
      caller: owner Safe (2 of 6)
      effect: replaces the code holding deposits and receiving settlements
    - function: updateGateway, updateMessageReceiver, updateSecurityModule, updateFillSigner
      caller: owner Safe
      effect: which messages count as settlements, and how they're verified
    - function: pause / unpause
      caller: lighthouse (0x38f18895...) or watchtower (0x6281ea30...), each an EOA acting alone (hasPauseAccess, SpokeStorageV6.sol:178); the owner can't pause
      effect: new intents, fills and queue processing stop
  grandfathered: none
  outside_exit_path:
    - what: setStrategyForAsset, setModuleForStrategy, updateFeeAdapter, updateMessageGasLimit
      effect: asset strategies (xERC20 modules) and fees

data_gates:
  - kind: queue dispatch thresholds
    where: Everclear's off-chain agents (queue size, oldest item age)
    trigger: thresholds not reached
    blocks_exit: false                   # anyone can dispatch a queue themselves
  - kind: settlement liquidity
    where: hub settlement to a destination spoke
    trigger: insufficient liquidity on the intent's destinations
    blocks_exit: true
    reset: unbounded                     # the docs describe settling to another domain for solvers; for users it waits on liquidity

judgment:
  screening: unknown
  freeze_assets: unknown
  freeze_pooled: true                    # spokes hold every unsettled intent's input and solver balances

service:
  integrator_access:
    api_key: unknown
    identity: unknown
    revocable: unknown
    rate_limited: unknown
  operators:
    - role: Everclear API and queue agents (lighthouse)
      entity: Everclear
      single_operator: true
      source_public: true                # monorepo includes agents
      deployment_config_public: false
  screening: unknown
  bypass: true                           # newIntent and queue processing are open contract calls

integration:
  calls: ["FeeAdapter.newIntent on the origin spoke (approve first)", "agents or the caller dispatch queues to the hub", "settlement arrives at the destination spoke"]
  signatures: ["ERC-20 approval or Permit2"]
  offchain_required: []
  finisher: protocol
  gasless_start: none
  monitoring: "Everclear API intent status, or IntentAdded / Settled events and the subgraph"
  sdk: unknown
  testnet: true
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: delivery
  holder: unknown
  strike: signed                         # the intent's max fee
  expiry: unknown
  early_close: none
  premium: none
  terms_fixed_by: signature
  price_set_by: user_bound
  discipline: unknown
  surplus_to: unknown
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
    note: "approve, then FeeAdapter.newIntent on the origin spoke"
  - action: dispatch
    performer: designated
    paid: deferred
    note: "Everclear's agents dispatch the queues; anyone else can, paying the Hyperlane fee themselves"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: newIntent
    form: calldata
    bounds: bounded
    verifiable_locally: true
    api_optional: true
    note: "FeeAdapter.newIntent can be called directly"

incidents: []

open_questions:
  - "Trade: holder, expiry, discipline, surplus_to (CRITERIA.md, Trade)"
  - The hub's admin, upgradeability and timelock on the Everclear chain
  - Hyperlane ISM configuration on each spoke and on the hub (Ethereum's spoke gateway names its own ISM; Arbitrum's uses the mailbox default)
  - What a user receives, and when, if no solver fills and settlement liquidity on the destination is short
sources:
  - repo: everclear-monorepo
    url: https://github.com/everclearorg/monorepo
    commit: a935ca2e93e9cfbadc50a66bb0f2e3ae39c5be1b
    commit_date: 2026-03-31
    note: "sparse clone of packages/contracts/src"
---

# Everclear

**Primitive (one line):** Decentralized clearing layer for cross-chain solver rebalancing; operates as Ethereum L2 performing settlement netting — matching opposing cross-chain flows to reduce solver rebalancing costs; hub-and-spoke model with intent contracts on spoke chains and Everclear L2 as hub.
**Product scope of this entry:** Everclear (fka Connext) clearing layer

## Custody model

Everclear's intent contracts on spoke chains handle intent deposits, and the hub chain processes netting and settlement. The protocol **does temporarily hold funds during clearing/settlement.** Primarily solver/filler infrastructure — users can declare intents on spoke chains but the product is designed for solver rebalancing.

## User-facing vs. solver infrastructure

Primarily **solver infrastructure.** "Socialize the costs of rebalancing by netting off settlements against other fillers and users in the network." Over 80% of cross-chain transfers in a 24-hour period are "nettable."

## Admin surface

Emphasizes "permissionless expansion to new chains and rollups." Modular architecture. Specific admin controls not well-documented. As former Connext, likely retains some multisig governance.

## Historical incidents

No major exploits found. 2022 Connext "fees frontrunning" issue described as "by design."

## Source and on-chain state (2026-10-04)

Source is `everclearorg/monorepo`, `packages/contracts/src` (`EverclearSpokeV6.sol`, `SpokeStorageV6.sol`). There is no cancel or refund for an intent. Its lifecycle is intent → fill → netting on the hub → settlement.

Read on Ethereum, Arbitrum and Base:
- **Spoke:** `EverclearSpoke` `0xa05A…D816` is a UUPS proxy with a different implementation per chain.
- **Owners:** a 2-of-6 Safe owns the spoke and `SpokeGateway` `0x9ADA…99A7`. It is `0xa02a…74d6` on Ethereum and `0xf20d…dff9` on Arbitrum and Base.
- **Other roles:** `lighthouse` is `0x38f1…a2c6` and `watchtower` is `0x6281…c4fd`, both EOAs, the same on all three chains.
- **Hyperlane ISM:** Ethereum's gateway names its own ISM (`0x6185…0108`); Arbitrum's is unset, so it uses the mailbox default; Base's is `0xf0b4…792c`.
- **Paused:** no.
- **Pause access:** `hasPauseAccess` admits only `lighthouse` and `watchtower` (`SpokeStorageV6.sol:178`). Either EOA alone can pause the spoke.

## Sources

1. https://docs.everclear.org/ — Everclear documentation
2. https://github.com/everclearorg/monorepo — sparse clone of `packages/contracts/src`, 2026-10-04
3. https://docs.everclear.org/resources/contracts/mainnet.md and /concepts/how-it-works/intents.md, retrieved 2026-10-04
4. Spoke and gateway proxy slots, `owner`, `paused`, `lighthouse`, `watchtower`, `interchainSecurityModule` on Ethereum, Arbitrum, Base, 2026-10-04
