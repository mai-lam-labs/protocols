---
slug: skip-go-fast
name: Skip Go Fast
scope: Go Fast FastTransferGateway on six EVM source chains, the CosmWasm fast-transfer gateway on Osmosis that every live route fills on, the Hyperlane path between them, and the Skip Go API in front
kind: bridge
class: C
cross_chain: true
chains: [Ethereum, Arbitrum, Optimism, Base, Polygon, Avalanche, Osmosis]   # EVM gateways are sources only; each has one remote domain, Osmosis (875)
source_public: true                      # contracts and reference solver; the Skip Go API server isn't
inherits: [Hyperlane]
updated: 2026-09-28

verification:
  service: partial                       # client, widget and reference solver read; API server not public
  exit: source-verified
  actors: partial                        # mechanism in source; validator operators named only by their announced storage locations
  admin: source-verified                 # owners, admins, ISMs and hooks read on-chain; deployed bytecode not compared with source
  data: source-verified
  judgment: partial                      # contracts read; API-side screening unknown
  incidents: partial

exit:
  custody: escrow                        # USDC held by the source-chain FastTransferGateway proxy
  execution: permissionless              # anyone calls initiate_timeout on Osmosis and anyone relays the message; no local refund on the source chain
  overrides:
    - who: EVM gateway owner, one EOA per chain (0x24a9267CE9e0a8F4467B584FDDa12BAf1Df772B5 on Ethereum, Optimism, Base, Polygon, Avalanche; 0x56Ca414d41CD3C1188A4939b0D56417dA7Bb6DA2 on Arbitrum)
      needs: one key; no timelock
      how: upgradeToAndCall, or setRemoteDomain / setInterchainSecurityModule / setMailbox so that a SETTLE_ORDERS naming the pending order is accepted and pays the escrow out, or so that its REFUND_ORDERS is rejected
      reach: one
      bounded: false
      cost: none on-chain
    - who: Osmosis gateway owner and wasm admin, one secp256k1 key (osmo1zhqrfu9w3sugwykef3rq8t0vlxkz72vwd63q67)
      needs: one key; no timelock
      how: migrate the Osmosis gateway to code that refuses initiate_timeout for chosen orders, or that dispatches SETTLE_ORDERS for a pending order; every EVM gateway accepts any message from that address as settlement
      reach: one                         # across all six source chains
      bounded: false
      cost: none on-chain
    - who: Owner of the Osmosis Hyperlane mailbox, the same key as above
      needs: one key; no timelock
      how: set_required_hook to a hook that reverts for chosen messages, so that order's timeout can't be dispatched
      reach: one
      bounded: false
      cost: none on-chain
    - who: Hyperlane validators in the source gateways' ISM, 3 of 5
      needs: 3 of 5 to sign a forged message, or 3 of 5 to withhold
      how: sign a SETTLE_ORDERS that was never dispatched, paying the escrow to themselves; or never sign the checkpoint for one REFUND_ORDERS message (message-id multisig needs signatures over that message), again for each re-initiation
      reach: one
      bounded: false
      cost: none on-chain; static multisig ISM, no bond or slashing
  refund_trigger: timeout_proof          # timeoutTimestamp passes on Osmosis unfilled, then an attested Hyperlane message back to the source
  exit_bound_seconds: unknown            # timeoutTimestamp (orders sampled on Arbitrum: ~300-600 s after submission) + Osmosis tx + 3-of-5 signing + relay; after the timeout the contracts impose no deadline and signing latency wasn't measured
  exit_bound_chosen_by: order creator    # timeoutTimestamp is set at submitOrder with no upper limit; in practice the Skip Go API builds it
  standing_approval: upgradeable_target  # submitOrder pulls with transferFrom into the UUPS gateway proxy; the Permit2 path is a one-shot signature

actors:
  - role: Timeout initiator; calls initiate_timeout on the Osmosis gateway after the timeout
    entity: anyone
    jurisdiction: pseudonymous
    set: permissionless                  # no caller check; the reference solver does it only with --refund-orders (off by default)
    independence: independent
  - role: Hyperlane validators; sign the Osmosis merkle-hook checkpoint carrying the REFUND_ORDERS message
    entity: five operators, named by their announced storage locations as Polkachu, Cosmostation, Hyperlane, Imperator and Lavender.Five
    jurisdiction: unknown
    set: m_of_n                          # 3 of 5, the same static ISM configuration on all six source gateways; chosen by the gateway owner, who can replace it at once
    independence: unknown                # distinct organisations by name; not otherwise established
  - role: Relayer; submits the message and signatures to the source-chain Mailbox.process
    entity: anyone
    jurisdiction: pseudonymous
    set: permissionless                  # Mailbox.process has no caller check; signatures are public in S3
    independence: independent
  - role: Osmosis chain validators; include the initiate_timeout transaction
    entity: pseudonymous
    jurisdiction: pseudonymous
    set: staked
    independence: independent

admin:
  upgradeable: true                      # EVM gateways are UUPS proxies; the Osmosis gateway has a wasm admin that can migrate it
  authority: eoa                         # every gateway owner and the Osmosis wasm admin is a single key; the Base owner EOA carries an EIP-7702 delegation, which leaves the key in control
  timelock_seconds: none
  immediate_functions:
    - function: FastTransferGateway.upgradeToAndCall
      caller: EVM gateway owner
      effect: replaces the contract holding the escrow
    - function: FastTransferGateway.setInterchainSecurityModule, setMailbox, setRemoteDomain
      caller: EVM gateway owner
      effect: decides which messages count as settlement or refund; can release or strand any pending order
    - function: MsgMigrateContract on the Osmosis gateway
      caller: Osmosis wasm admin (osmo1zhqrfu9w...)
      effect: arbitrary new code at the address every EVM gateway trusts
    - function: Osmosis gateway update_config, add_remote_domain
      caller: Osmosis gateway owner (same key)
      effect: points timeouts at another mailbox or hook, or drops a source domain, so its timeouts can't be initiated
    - function: Osmosis mailbox set_required_hook, set_default_hook, set_default_ism
      caller: Osmosis mailbox owner (same key)
      effect: the required hook runs on every dispatch; one that reverts stops timeouts, for everyone or for chosen messages
    - function: pause on the Osmosis mailbox's required pausable hook
      caller: hook owner osmo14n3a65fnqz9jve85l23al6m3pjugf0atvrfqh5, which created the Osmosis Hyperlane contracts
      effect: every dispatch from Osmosis reverts; no timeout or settlement can be sent
  grandfathered: none                    # timeoutTimestamp is fixed in the order ID, but the ISM, remote domain, mailbox and code that decide the refund are live state
  outside_exit_path:
    - what: EVM Hyperlane Mailbox upgrade (on the exit path, but not immediate)
      effect: the source Mailbox runs process; on Arbitrum it is a transparent proxy whose ProxyAdmin is owned by a TimelockController with a 604800 s delay
      caller: Hyperlane
      timelock_seconds: 604800           # Arbitrum only; other chains not checked
    - what: EVM Mailbox owner (a 6-of-10 Safe on Arbitrum)
      effect: default ISM and hooks; not used for the refund, since the gateway names its own ISM and nothing is dispatched from the source
      caller: Hyperlane

data_gates:
  - kind: timeout
    where: Osmosis gateway initiate_timeout (assert_order_is_expired, assert_order_not_filled)
    trigger: block time before timeoutTimestamp, or the order was filled
    blocks_exit: true
    reset: bounded                       # opens at timeoutTimestamp; fill and timeout are mutually exclusive on Osmosis
  - kind: validator confirmation
    where: Hyperlane validators before signing an Osmosis checkpoint
    trigger: reorg period
    blocks_exit: true
    reset: bounded                       # 1 block per hyperlane-registry osmosis metadata
  - kind: transfer limits
    where: Skip Go API routing ($10-$25,000; $20 minimum from Ethereum)
    trigger: order size
    blocks_exit: false

judgment:
  screening: []                          # none in the gateways, the Hyperlane contracts or the reference solver
  freeze_assets: [USDC]                  # native Circle USDC on each source chain
  freeze_pooled: true                    # each source gateway holds every pending order's USDC (21,842.80 on Ethereum at read time)

service:
  integrator_access:
    api_key: optional
    identity: none                       # most of the API works without a key at a shared global rate limit; a key is requested by Discord support ticket
    revocable: true
    rate_limited: true
    note: "works without a key at a limit; unlimited use needs a key from the team"
  operators:
    - role: Skip Go API (api.skip.build); quotes Go Fast routes and builds the submitOrder transaction, including timeoutTimestamp and amountOut
      entity: Interchain Inc. (formerly Skip Protocol), a subsidiary of the Interchain Foundation
      single_operator: true
      source_public: false               # no API server repository in github.com/skip-mev; the client, widget and go.skip.build app are public
      deployment_config_public: false
    - role: Solvers; fill orders on Osmosis from their own USDC and settle over Hyperlane
      entity: unknown                    # permissionless by contract and docs; who fills in production isn't established
      single_operator: unknown
      source_public: true                # skip-mev/skip-go-fast-solver, Apache-2.0
      deployment_config_public: false
  screening: []                          # none in the public client, widget or reference solver; the API server can't be inspected; unlimited use needs an API key from the team
  bypass: true                           # submitOrder is open to anyone and the reference solver finds orders from OrderSubmitted events, not the API; whether production solvers fill orders made outside the API isn't established. Refunds need no API at all

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
  structure: user_writes
  holder: unknown
  strike: signed
  expiry: unknown
  early_close: none
  premium: none
  terms_fixed_by: signature
  price_set_by: user_bound
  discipline: unknown
  surplus_to: holder                     # both amounts are fixed, so the solver keeps whatever the market gives beyond them
  extraction: []
  sides: unknown
  rate: firm                             # amountIn and amountOut are both in the FastTransferOrder
  quote_validity: unknown
  partial_fill: none                     # fillOrder pays the full amountOut
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: unknown
    note: not researched
  - action: refund
    performer: anyone
    paid: unknown
    note: initiate_timeout on Osmosis and the relay back; whether either is paid wasn't read

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: submitOrder
    form: calldata
    bounds: bounded
    verifiable_locally: true
    api_optional: true
    note: "FastTransferGateway.submitOrder is open to anyone"

incidents: []                            # none found

open_questions:
  - "Trade: holder, expiry, discipline (CRITERIA.md, Trade)"
  - "Quote: sides, quote_validity (CRITERIA.md, Trade); these decide which quote modes (exact, atleast, upto) the venue can serve, and who decides a partial fill"
  - "Paid execution, refund step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - "The integration facts (calls, signatures, finisher, gasless_start by token standard), from FastTransferGateway submitOrder and its signature path"
  - Who holds the EVM owner keys 0x24a9267C... and 0x56Ca414d... and the Osmosis key osmo1zhqrfu9w...; the Arbitrum owner is the `owner` constant in the repo's Deploy.s.sol, and the Osmosis key created the gateway, which points at Skip, but it isn't confirmed
  - Who controls osmo14n3a65fnqz9jve85l23al6m3pjugf0atvrfqh5, owner of the pausable required hook; hyperlane-registry names Mitosis as deployer of the Osmosis Hyperlane contracts
  - Why the Osmosis mailbox (created by osmo14n3a65...) is now owned by the Go Fast gateway key, and whether that owner has ever changed the hooks or ISM
  - Whether Skip or anyone runs timeouts and relays for every expired order in production; no OrderRefunded on the Arbitrum gateway in the last ~20M blocks, and full history wasn't queried
  - Latency from timeout to refund in practice (validator signing, relay), which sets exit_bound_seconds
  - Validator operators' legal entities and jurisdictions, beyond names in their S3 storage locations
  - Whether the Skip Go API screens addresses or regions for Go Fast, and what timeoutTimestamp it sets by rule
  - Whether production solvers fill orders submitted without the API
  - Whether deployed bytecode on each chain (EVM implementations, Osmosis code_id 1874) matches the pinned source
  - The solver's shipped config names a different Osmosis mailbox and merkle hook (osmo1r6u37..., osmo1e765..., 70 messages) from the gateway's (osmo1jjf788..., osmo13ysw...); which one validators watch for Go Fast
  - EVM Mailbox proxy admin and timelock on chains other than Arbitrum
  - Whether GoFastERC7683 is deployed anywhere
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: go-fast-contracts
    url: https://github.com/skip-mev/go-fast-contracts
    commit: 65f061c978c0c2ae876470f4abd1d76fb3149fe3
    commit_date: 2025-12-18
  - repo: skip-go-fast-solver
    url: https://github.com/skip-mev/skip-go-fast-solver
    commit: 0051d3583c8ebdb201154a3410f788dcf4232ca1
    commit_date: 2026-07-27
  - repo: cw-hyperlane
    url: https://github.com/many-things/cw-hyperlane
    commit: 7573576c97fe9ee9a91c3e4557ff5a32bfbcee40
    commit_date: 2025-01-03
  - repo: hyperlane-monorepo
    url: https://github.com/hyperlane-xyz/hyperlane-monorepo
    commit: 274b3cbb5bd9bb3f4269456bdadd044461abeac6
    commit_date: 2026-09-28
    note: "sparse clone, solidity/contracts only"
  - repo: skip-go
    url: https://github.com/skip-mev/skip-go
    commit: 386438e4f0b5db0b2e0e160084e1d65c2a11d8c7
    commit_date: 2026-09-11
---

# Skip Go Fast

**Primitive (one line):** Solver-fronted intent bridge from EVM chains to Cosmos. The user calls `submitOrder` on a `FastTransferGateway` on the source chain, which pulls USDC into escrow; a solver fills on Osmosis from its own USDC; settlement or refund goes back to the source over Hyperlane, verified by a 3-of-5 multisig ISM.

## Topology

Every live route runs from one of six EVM source chains to Osmosis. Each EVM gateway has exactly one remote domain, Osmosis (875), set to the Osmosis gateway `osmo1vy34lpt5...`; `remoteDomains` is empty for every other domain on the Ethereum gateway, and the Osmosis gateway lists the six EVM gateways (on-chain reads, 2026-09-28). The addresses match those in `source/skip-go-fast-solver` `README.md` and `config/local/config.yml`. So fills, and timeouts, happen on Osmosis in the CosmWasm contract (`source/go-fast-contracts` `cosmwasm/contracts/fast-transfer-gateway/src/execute.rs`), not in `FastTransferGateway.sol`. The EVM contract's `fillOrder` and `initiateTimeout` would only matter for EVM-destination routes, and none are configured.

## Category 1 — Actor-gated edges

**Refund path, end to end:**
1. The user's USDC sits in the source `FastTransferGateway`; `submitOrder` records `settlementDetails[orderID]` with the refund address `sender`, which the caller chooses (`solidity/src/FastTransferGateway.sol:160-191`). The source contract has no local refund: nothing on the source chain can release escrow except `handle`, callable only by the mailbox (`:377-399`).
2. After `timeoutTimestamp`, anyone calls `initiate_timeout` on the Osmosis gateway with the full order structs. It checks the order is expired, not filled, and addressed to Osmosis, and dispatches `TimeoutOrders` through the Osmosis Hyperlane mailbox to the source gateway (`execute.rs:266-315`, `helpers.rs:30-57`). There is no caller check, and no record that a timeout was sent, so it can be repeated.
3. The Osmosis mailbox runs the required hook (a pausable hook) and the gateway's configured hook (the merkle tree hook) (`source/cw-hyperlane` `contracts/core/mailbox/src/execute.rs:95-155`). Neither charges a fee (`quote_dispatch` returns no fees).
4. Hyperlane validators sign a checkpoint for that merkle index and message ID and publish it to S3. Each source gateway names its own ISM through the public `interchainSecurityModule` variable, which `Mailbox.recipientIsm` uses (`source/hyperlane-monorepo` `solidity/contracts/Mailbox.sol:410-431`). On all six chains that ISM is a static message-ID multisig (`moduleType` 5) needing 3 of 5 validators, the same five on every chain.
5. Anyone relays: `Mailbox.process` has no caller check (`Mailbox.sol:201-247`). The reference solver's relayer fetches the signatures from the validators' announced storage locations and calls `process` (`source/skip-go-fast-solver` `hyperlane/relayer.go`). A user can do the same with its CLI (`initiate-timeout`, then `relay`).
6. The source gateway's `handle` checks that the origin is 875 and the sender is the registered Osmosis gateway, then `_refundOrder` sends `amount` to `sender` and marks the order `REFUNDED`, skipping any order already `FILLED` or `REFUNDED` (`FastTransferGateway.sol:433-463`).

A refund needs an attested message from Osmosis; the user can't reclaim funds on the source chain alone. The attestation comes from 3 of 5 validators, and every step is permissionless except theirs.

**Fill vs timeout:** on Osmosis a fill needs the block time before `timeout_timestamp` and a timeout needs it at or after, and a fill blocks a timeout, so the two can't both happen (`helpers.rs:30-57`). A fill has to pay exactly `amount_out` of the configured denom to the recipient in the same transaction (`execute.rs:160-202`, `assert_correct_funds`). A solver can't mark an order filled without paying the user. `initiate_settlement` only settles fills recorded to the caller (`execute.rs:204-264`).

**Actors on exit path:**
- Timeout initiator: permissionless. The reference solver only initiates timeouts when started with `--refund-orders`, which is off by default (`cmd/solver/main.go:49`, `orderfulfiller/orderfulfiller.go:62-145`).
- Hyperlane validators: 3 of 5. Signers are 0x3f869c36..., 0x754be770..., 0xa98a3ab7..., 0xb4d0604b..., 0xf5498213... (`validatorsAndThreshold` on each gateway's ISM). Their announced storage on the Osmosis ValidatorAnnounce (`osmo147r8mfds...`) names buckets for Polkachu, Cosmostation, Hyperlane, Imperator and Lavender.Five. Hyperlane describes Skip as running "their own custom validator set with Hyperlane ISMs", and Osmosis has no entry in Hyperlane's default multisig config. The ISMs are EIP-1167 clones with no owner, but the gateway owner can point the gateway at a different ISM at any time.
- Relayer: permissionless.
- Osmosis validators: they must include the `initiate_timeout` transaction, so an Osmosis halt stops refunds.

**Can one refund be singled out?** A solver can't: filling means paying the user. A relayer can't, since anyone relays. What remains:
- EVM gateway owner, one EOA per chain: by upgrade, `setRemoteDomain`, `setInterchainSecurityModule` or `setMailbox`, it can accept a forged `SETTLE_ORDERS` for one pending order, which pays its escrow to a chosen address, or reject that order's refund.
- Osmosis gateway owner and wasm admin, one key: a migration can make the trusted Osmosis address refuse one order's timeout, or dispatch a `SETTLE_ORDERS` for it. Validators sign every dispatched message, so this needs no collusion and reaches all six source chains.
- Osmosis mailbox owner (the same key): can install a required hook that reverts only for chosen messages.
- 3 of 5 validators: can sign a forged settlement, or withhold signatures from one refund message each time it is re-initiated. The ISM is static, with no bond.

**Uptime / SLA:** none published. Orders sampled on the Arbitrum gateway set `timeoutTimestamp` about 300–600 s after submission, all to Osmosis. No `OrderRefunded` events appeared on the Arbitrum gateway in the last ~20M blocks, a sample, not the full history.

**Compellability profile:** in normal operation the exit depends on someone initiating and relaying (anyone can) and on 3 of 5 named Cosmos validator operators signing. Two single keys, one on the EVM side and one on Osmosis, can each redirect or withhold any one order immediately. The Osmosis key also owns the Osmosis Hyperlane mailbox.

## Category 2 — Modification-gated edges (in-window effect)

**EVM gateways:** UUPS proxies (`FastTransferGateway.sol:78`, `_authorizeUpgrade` `:518`, `onlyOwner`, no timelock). Owners read on-chain: `0x24a9267C...` on Ethereum, Optimism, Base, Polygon and Avalanche, and `0x56Ca414d...` on Arbitrum (the `owner` constant in `solidity/script/Deploy.s.sol`). Both are EOAs with no code, except that on Base `0x24a9267C...` carries an EIP-7702 delegation. The key still controls it; `getThreshold` reverts. Owner functions: `setRemoteDomain` (`:148`), `setMailbox` (`:331`), `setInterchainSecurityModule` (`:337`), upgrade, and ownership transfer. **No pause**, and nothing on the gateway stops `handle`.

**Osmosis gateway:** the contract's `migrate` entry point is a no-op, but wasm admin `osmo1zhqrfu9w...` can migrate to any code (`contract.rs:25-29`, on-chain `contract_info`). The same key is the `cw_ownable` owner, and `update_config` (mailbox, hook, token denom) and `add_remote_domain` take effect at once (`execute.rs:139-158`). It is a plain secp256k1 account, not a multisig. `pending_owner` is null.

**Osmosis Hyperlane mailbox (`osmo1jjf788...`, the one in hyperlane-registry):** its owner is the same key, `osmo1zhqrfu9w...`, and it has no wasm admin. The owner can reset the default ISM, the default hook and the required hook (`source/cw-hyperlane` `contracts/core/mailbox/src/execute.rs:26-93`). The required hook today is a pausable hook, `osmo1tql3ltzv...`, owned by `osmo14n3a65...`, the account that created the Osmosis Hyperlane contracts. While it is paused, `post_dispatch` reverts (`contracts/hooks/pausable/src/lib.rs:62-80`), so every dispatch from Osmosis, timeouts included, fails. It is unpaused at read time. This pause stops all exits at once, not one.

**EVM Hyperlane mailboxes:** on the exit path because they run `process`. On Arbitrum the mailbox is a transparent proxy whose ProxyAdmin is owned by a TimelockController with a 604800 s minimum delay. The mailbox owner is a 6-of-10 Safe; its powers (default ISM, hooks) don't reach this route, because the gateway names its own ISM and the refund doesn't dispatch from the source. Other chains weren't checked.

**Grandfathering:** none in practice. `timeoutTimestamp` and the refund address are fixed in the order ID, but whether a refund message is accepted, and whether a settlement for the order is, depends on the ISM, remote domain, mailbox and code at the time it arrives.

## Category 3 — Data-oracle-gated edges

No price oracles. The gates on the exit are the timeout itself (opens at `timeoutTimestamp`) and the validators' reorg wait (1 block for Osmosis in hyperlane-registry). Both are bounded. Transfer limits ($10–$25,000; $20 minimum from Ethereum) are applied by the Skip Go API when routing and don't touch refunds. `submitOrder` doesn't cap `timeoutTimestamp`, so an order built with a far-off timeout stays locked until then.

## Category 4 — Judgment-oracle-gated edges

**Contracts:** no blocklist or screening in either gateway, the Hyperlane contracts or the reference solver. The reference solver filters only on fee, size, balance and confirmations (`orderfulfiller/order_fulfillment_handler/order_fulfillment_handler.go`).

**Stablecoin freeze exposure:** each source gateway holds all pending USDC at one address (21,842.80 USDC on the Ethereum gateway at read time). A Circle freeze of a gateway stops every refund and settlement on that chain. If the refund `sender` is blacklisted, `handle` reverts; the message stays undelivered and can be relayed again later (`Mailbox.sol:215-246`), which counts as a freeze of the user's own wallet.

## Service

The Skip Go API (Interchain Inc., formerly Skip Protocol, acquired by the Interchain Foundation in December 2024) quotes Go Fast routes and builds the `submitOrder` call, including `amountOut` and `timeoutTimestamp`. Unlimited use needs an API key from the team (Skip Go FAQ). There is no API server repository in the `skip-mev` GitHub organisation. The client and widget (`source/skip-go`) and the go.skip.build app are public, and no address screening was found in the client or widget. Whether the API screens is not known.

Bypass is possible on-chain. `submitOrder` is open, and the reference solver discovers orders from `OrderSubmitted` events (`transfermonitor/transfermonitor.go:294-296`), not from the API. Docs say anyone can run a solver. Refunds don't touch the API at all. Who fills in production, and whether they fill orders made outside the API, is not established.

## Historical incidents

None found in a web search on 2026-09-28. Full event history wasn't reviewed.

## Composite

**Stuck-leg failure modes:**
1. No one initiates or relays the timeout: anyone can, the user included, with OSMO for gas on Osmosis and gas on the source chain.
2. 3 of 5 validators offline or withholding: every refund, or a chosen one, waits.
3. EVM owner key or Osmosis key used (or compelled) against one order: that order's escrow is redirected or stranded.
4. Pausable required hook paused, or a reverting required hook set: no dispatch from Osmosis, so all refunds stop.
5. Osmosis halt: no `initiate_timeout`.
6. Circle freezes a source gateway: every order on that chain.

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| No initiator or relayer | as soon as anyone acts | permissionless (`execute.rs:266-315`, `Mailbox.sol:201`) |
| Validators withhold | unbounded | static 3-of-5 ISM |
| Owner key action | unbounded, per order | no timelock on either side |
| Required hook paused or replaced | unbounded, all orders | `hooks/pausable/src/lib.rs` |
| Osmosis halt | until the chain resumes | chain liveness |
| Issuer freeze of a gateway | unbounded | USDC |

**Cross-protocol correlation:** anything that dispatches through the Osmosis Hyperlane mailbox shares the pausable hook and the mailbox owner. Anything using the same five validators shares their liveness.

## Sources

- `source/go-fast-contracts` (https://github.com/skip-mev/go-fast-contracts): `solidity/src/FastTransferGateway.sol`, `GoFastERC7683.sol`, `GoFastCaller.sol`, `libraries/OrderEncoder.sol`, `script/Deploy.s.sol`, `script/Upgrade.s.sol`; `cosmwasm/contracts/fast-transfer-gateway/src/{contract,execute,helpers,state,fills}.rs`; `cosmwasm/scripts/*.ts`. Read 2026-09-28.
- `source/skip-go-fast-solver` (https://github.com/skip-mev/skip-go-fast-solver): `README.md`, `config/local/config.yml`, `hyperlane/relayer.go`, `orderfulfiller/`, `transfermonitor/transfermonitor.go`, `cmd/solver/main.go`. Read 2026-09-28.
- `source/cw-hyperlane` (https://github.com/many-things/cw-hyperlane): `contracts/core/mailbox/src/execute.rs`, `contracts/hooks/pausable/src/lib.rs`. Read 2026-09-28.
- `source/hyperlane-monorepo` (https://github.com/hyperlane-xyz/hyperlane-monorepo, sparse `solidity/contracts`): `Mailbox.sol`, `isms/multisig/AbstractMessageIdMultisigIsm.sol`. Read 2026-09-28.
- `source/skip-go` (https://github.com/skip-mev/skip-go): client and widget, searched for screening. Read 2026-09-28.
- On-chain reads, 2026-09-28, latest block. On the six EVM gateways: `owner`, `interchainSecurityModule`, `mailbox`, `token`, `localDomain`, `remoteDomains`, `nonce` and the ERC-1967 implementation slot. On each ISM: `moduleType` and `validatorsAndThreshold`. Owner `eth_getCode` and Safe calls. On the Arbitrum Mailbox: ProxyAdmin, its owner's `getMinDelay`, and the mailbox owner's Safe threshold. On the Arbitrum gateway: `OrderSubmitted` and `OrderRefunded` logs. On Osmosis (LCD): gateway `contract_info`, `config`, `remote_domains` and the raw `ownership` key; mailbox, hook and ISM `contract_info`, owners, hooks and pause state; ValidatorAnnounce storage locations; account types.
- https://raw.githubusercontent.com/hyperlane-xyz/hyperlane-registry/main/chains/osmosis/addresses.yaml and `metadata.yaml`, the Osmosis mailbox and deployer. Retrieved 2026-09-28.
- https://raw.githubusercontent.com/hyperlane-xyz/hyperlane-monorepo/main/typescript/sdk/src/consts/multisigIsm.ts, which has no Osmosis entry. Retrieved 2026-09-28.
- https://docs.skip.build/go/advanced-transfer/go-fast, the Go Fast overview, limits and fees. Retrieved 2026-09-28.
- https://docs.cosmos.network/skip-go/advanced-transfer/go-fast, which says solvers are permissionless. Retrieved 2026-09-28.
- https://docs.cosmos.network/skip-go/general/faq, on API keys and open source. Retrieved 2026-09-28.
- https://www.hyperlane.xyz/post/skip-go-fast-intents-powered-by-hyperlane, on the custom validator set. Retrieved 2026-09-28.
- https://www.theblock.co/post/330189/in-latest-shakeup-interchain-foundation-acquires-skip-to-refocus-cosmos-hub-at-ecosystems-core and https://www.coindesk.com/press-release/2024/12/10/interchain-foundation-acquires-blockchain-solutions-provider-skip-to-reignite-cosmos-the-interchain, on Skip becoming Interchain Inc. Retrieved 2026-09-28.
- https://docs.skip.build/go/fast-transfer/fast-transfer-overview, cited by the earlier version of this entry, now returns 404.

## Notes / follow-ups

- The earlier entry treated `FastTransferGateway.initiateTimeout` as the exit. On every live route the timeout runs on the Osmosis CosmWasm gateway; the EVM gateways are sources only.
- The earlier entry said there was no pause. That holds for the gateways, but the Osmosis mailbox's required hook is pausable, and the mailbox owner can swap that hook.
- The earlier entry gave the relayer as a required actor. Relaying is permissionless. The validators aren't: 3 of 5 of them must sign.
- The earlier entry didn't say that every owner is a single key. Remaining open questions are in the header.
