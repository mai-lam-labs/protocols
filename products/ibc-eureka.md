---
slug: ibc-eureka
name: IBC / IBC Eureka
scope: IBC Eureka's Ethereum side (ICS26Router, ICS20Transfer, Escrow, SP1 Tendermint light clients) for transfers between Ethereum and Cosmos Hub; the rating is for a transfer out of Ethereum. IBC Classic between Cosmos chains is described in the text, not rated
kind: bridge
class: B
cross_chain: true
chains: [Ethereum, Cosmos Hub]
source_public: true
inherits: []
updated: 2026-10-04

verification:
  service: spec-only
  exit: source-verified                  # timeoutPacket, onTimeoutPacket, _refundTokens, Escrow.send read; roles read on-chain
  actors: source-verified                # relayer role and its four holders read from the AccessManager
  admin: source-verified                 # timelock delay, council thresholds and role holders read 2026-10-04
  data: source-verified
  judgment: partial
  incidents: partial

exit:
  custody: escrow                        # the ICS20 Escrow for the client holds tokens sent from Ethereum
  execution: automatic                   # after timeoutTimestamp, a timeout proof refunds the sender; only whitelisted relayers can submit it
  overrides:
    - who: the four whitelisted relayer EOAs (RELAYER_ROLE on the AccessManager); operator not published
      needs: all four decline to submit one timeout
      parties: unknown
      how: never call timeoutPacket for one packet; no one else can, since timeoutPacket is restricted to role 1
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: timeout_proof          # timeoutPacket with a proof of non-receipt on the Hub, then _refundTokens
  exit_bound_seconds: unknown            # timeoutTimestamp is at most 86400 s ahead (MAX_TIMEOUT_DURATION), plus a relayer's light-client update and timeout submission
  exit_bound_chosen_by: sender           # within the 1-day cap
  standing_approval: upgradeable_target  # ICS20Transfer is a UUPS proxy; Permit2 is also supported

actors:
  - role: Relayer; updates the light client and submits timeoutPacket
    entity: unknown                      # four EOAs with RELAYER_ROLE; IBC Eureka is operated by Interchain Labs / Skip
    jurisdiction: unknown
    set: whitelist
    independence: unknown

admin:
  upgradeable: true                      # ICS26Router and ICS20Transfer are UUPS; Escrow and IBCERC20 are beacons
  authority: multisig                    # Security Council Safe 0x7B96CD54..., 4 of 7, through a TimelockController
  timelock_seconds: 259200               # TimelockController 0xb3999B2D... minDelay; it alone holds ADMIN_ROLE
  immediate_functions:
    - function: ICS20Transfer.pause
      caller: any one of five pauser EOAs (PAUSER_ROLE)
      effect: onTimeoutPacket is whenNotPaused, so every timeout refund stops; unpause needs the Security Council (UNPAUSER_ROLE)
    - function: setRateLimit on the Escrow
      caller: Eureka Ops Council Safe 0x4b46ea82..., 2 of 5 (RATE_LIMITER_ROLE)
      effect: refunds pay out through Escrow.send, which enforces the daily limit; a limit of zero stops refunds of that token
  grandfathered: none
  outside_exit_path:
    - what: upgrades, light client migration, application and client registration
      effect: through the 3-day timelock
      caller: Security Council (4 of 7)
      timelock_seconds: 259200

data_gates:
  - kind: withdrawal rate limit
    where: Escrow.send (_assertAndUpdateRateLimit), on refunds as well as inbound transfers
    trigger: the token's daily limit is used up
    blocks_exit: true
    reset: bounded                       # daily, unless the rate limiter changes it
  - kind: light client frozen
    where: SP1ICS07Tendermint, after submitMisbehaviour (permissionless)
    trigger: misbehaviour proven, or the trusting period lapses without updates
    blocks_exit: true
    reset: unbounded                     # needs a client migration by the Security Council through the 3-day timelock

judgment:
  screening: []                          # none in the contracts; relayers' policies unknown
  freeze_assets: unknown
  freeze_pooled: true                    # escrow per client holds every token sent from Ethereum

service:
  integrator_access:
    api_key: unknown
    identity: unknown
    revocable: unknown
    rate_limited: unknown
    note: "transfers can be sent directly to ICS20Transfer; Skip Go routes them"
  operators:
    - role: Relayers for the Ethereum side
      entity: unknown                    # four EOAs; the docs point to Interchain Labs' operations
      single_operator: unknown
      source_public: true                # relayer in the solidity-ibc-eureka repo
      deployment_config_public: false
  screening: unknown
  bypass: false                          # recvPacket and timeoutPacket are restricted to the whitelisted relayers

integration:
  calls: ["ICS20Transfer.sendTransfer on Ethereum (approve or Permit2)", "relayer delivers to the Hub", "on timeout, a relayer calls ICS26Router.timeoutPacket"]
  signatures: ["ERC-20 approval or Permit2"]
  offchain_required:
    - role: whitelisted relayer
      api_key: false
      rate_limited: false
  finisher: protocol
  gasless_start: none
  monitoring: "SendPacket / WriteAcknowledgement / TimeoutPacket events, or Skip Go status"
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
    note: ICS20Transfer.sendTransfer after approve or Permit2
  - action: refund
    performer: designated
    paid: unknown
    note: timeoutPacket by a whitelisted relayer; whether it is paid wasn't read

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: sendTransfer
    form: self_built

incidents: []                            # none found for Eureka; IBC Classic incidents are in the text

open_questions:
  - "Paid execution, refund step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - Who operates the four relayer EOAs, and whether they are run by one organisation
  - Who the five pauser EOAs belong to (the docs say a subset of the Security Council)
  - Whether any rate limit is set on the escrows today, and at what level
  - The Security Council is 4 of 7 on-chain but documented as 5 of 7; which is intended
  - Whether the Hub-side (Cosmos governance) can refuse or halt a packet to or from Ethereum
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: solidity-ibc-eureka
    url: https://github.com/cosmos/solidity-ibc-eureka
    commit: f6a4899607a9df595a3c16b5c473cbc562de8332
    commit_date: 2026-09-15
---

# IBC / IBC Eureka

**Primitive (one line):** Every IBC packet carries timeout fields; on expiry, any party submits a cryptographic proof of non-receipt on the destination chain; source chain automatically refunds escrowed tokens to sender. IBC Eureka extends this to Ethereum via Solidity contracts with ZK-verified light clients.
**Product scope of this entry:** IBC Classic (ibc-go) and IBC Eureka (solidity-ibc-eureka) for EVM chains

## Category 1 — Actor-gated edges

**IBC Classic (Cosmos):**
- **Timeout proof submission: PERMISSIONLESS.** Any account can submit a timeout proof transaction. The IBC core has no access control on `TimeoutPacket`. Source: [3] ibc-go `modules/core/04-channel/keeper/timeout.go`
- **Refund is automatic** on timeout: `OnTimeoutPacket` callback calls `refundPacketTokens` which returns escrowed/re-mints tokens to sender. Source: [3] ibc-go `modules/apps/transfer/keeper/relay.go`

**IBC Eureka (Solidity):**
- **Timeout proof submission: PERMISSIONED.** `timeoutPacket()` on ICS26Router has `restricted` modifier requiring `RELAYER_ROLE` (role ID 1). Only addresses granted this role by the AccessManager can submit timeout proofs. Source: [4] `ICS26Router.sol:254`, `IBCRolesLib.sol:22-23,44-51`
- **Refund is automatic** once timeout is processed: `onTimeoutPacket` on ICS20Transfer calls `_refundTokens`. Source: [4] `ICS20Transfer.sol:384-439`
- **MAX_TIMEOUT_DURATION: 1 day** (86,400 seconds) enforced by ICS26Router. Source: [4] `ICS26Router.sol:48,105-111`

**Expiry fields:**
- IBC Classic: `timeoutHeight` (consensus height) and `timeoutTimestamp` (Unix nanoseconds). At least one must be non-zero. Either triggers timeout independently.
- IBC Eureka: `timeoutTimestamp` only (Unix seconds). No height-based timeout.

## Category 2 — Modification-gated edges (in-window effect)

**IBC Classic:** no built-in admin surface at the IBC core layer. Individual chains can implement governance-controlled changes.

**IBC Eureka (Solidity) — significant admin surface:**
- **UUPS upgrade:** ADMIN_ROLE can call `upgradeToAndCall` on ICS26Router and ICS20Transfer. Can change all logic. Source: [4] `ICS26Router.sol:311`, `ICS20Transfer.sol:571`
- **Beacon upgrades:** ADMIN_ROLE can upgrade Escrow and IBCERC20 beacons. Source: [4] `ICS20Transfer.sol:574-581`
- **Client migration:** ADMIN_ROLE can replace light client contracts entirely. Source: [4] `ICS02ClientUpgradeable.sol:148-157`
- **Pause:** PAUSER_ROLE can pause ICS20Transfer. **When paused, `onTimeoutPacket` is blocked** — timeout refunds cannot be processed even with valid proofs. Source: [4] `ICS20Transfer.sol:389` (whenNotPaused)
- **Rate limiting:** RATE_LIMITER_ROLE can set daily withdrawal limits per token on Escrow contracts. Aggressive limits could prevent refunds. Source: [4] `RateLimitUpgradeable.sol:39-41`

**Admin roles (IBCRolesLib.sol):**
| Role | ID | Power |
|---|---|---|
| ADMIN_ROLE | 0 | Upgrades, migrations, full authority |
| RELAYER_ROLE | 1 | Submit recv/ack/timeout packets, update clients |
| PAUSER_ROLE | 2 | Pause ICS20Transfer (blocks ALL ops including timeout refunds) |
| UNPAUSER_ROLE | 3 | Unpause |
| RATE_LIMITER_ROLE | 5 | Set withdrawal rate limits |

**Light client freeze:** `submitMisbehaviour()` is permissionless. Freezes a light client, blocking ALL packet operations. Security Council can unfreeze via client migration. Source: [4] `SP1ICS07Tendermint.sol:220-222,569-573`

## Category 3 — Data-oracle-gated edges

**No price oracles.** IBC verification is entirely cryptographic — light client verification of counterparty chain consensus + Merkle proofs of packet commitments/receipts.

**IBC Eureka ZK dependency:** SP1 light client uses ZK proofs to verify Tendermint consensus. Dependency on SP1 verifier contract correctness.

## Category 4 — Judgment-oracle-gated edges

**None.** IBC has no risk-scoring, compliance, or judgment-oracle dependencies.

**Stablecoin freeze exposure:** ICS20Transfer Escrow contracts hold escrowed tokens during cross-chain transfers. If an Escrow address is frozen, all in-flight transfers for that asset are stuck.

## Historical incidents

- **IBC stuck transfers on expired channels (pre-2023):** In earlier periods, IBC transfers made to expired light clients never properly failed and user funds were not returned. Keplr wallet defaulted to channel-0 when no channel was entered, which became an expired channel to the Cosmos Hub. Transactions reported as successful but never arrived at the destination. Source: [5] Akash Network discussion #433 on stuck IBC transactions
- **SEI IBC shutdown (2025-2026):** SEI Network's v6.4 upgrade enabled IBC transfer shutdown, requiring holders of USDC, USDT, ATOM, WBTC on SEI to bridge assets out before Cosmos support was killed — or risk losing access permanently. This demonstrates a chain-level governance risk where a connected chain can unilaterally shut down IBC, stranding assets. Source: [6] Blockchain.News report
- **General IBC reliability:** IBC has processed billions in transfers across the Cosmos ecosystem since 2021. The timeout mechanism has generally worked as designed on active channels with live relayers. The primary failure mode is relayer liveness — if no relayer submits timeout proofs, funds sit in escrow indefinitely (though proofs can be submitted later).

## Composite

**Stuck-leg failure modes (IBC Eureka Solidity):**
1. PAUSER_ROLE pauses ICS20Transfer — **timeout refunds blocked**. Unbounded (until unpause).
2. RELAYER_ROLE not granted to any active relayer — timeout proofs cannot be submitted. Unbounded.
3. Light client frozen via misbehaviour — all packet operations blocked. Bounded by Security Council response.
4. ADMIN_ROLE upgrades contracts maliciously — all logic changeable. Unbounded.
5. Rate limits block refund transfer — bounded by rate limit reset.
6. Stablecoin issuer freezes Escrow — all escrowed funds in that asset stuck. Unbounded.

**Stuck-leg failure modes (IBC Classic):**
1. No relayer submits timeout proof — funds sit in escrow. Bounded (proof can be submitted later).
2. Light client trusting period expires without updates — can no longer verify proofs. May require governance intervention.
3. Stablecoin freeze on escrow module — all escrowed funds stuck. Unbounded.

## On-chain state, Ethereum (2026-10-04)

Addresses are from the Cosmos docs' contract-address page, which points to `cosmos/eureka-ops` `deployments/mainnet/1.json`. Roles were read from the AccessManager `0x3fa3…77ec` with `hasRole` and `getTargetFunctionRole`.

- **Timeouts:** `ICS26Router.timeoutPacket` (selector `0xb98c330a` in the deployed implementation `0x17fa…b7b5`) needs role 1 (RELAYER). Its four holders are all EOAs. There is no public role on it.
- **Admin:** `ADMIN_ROLE` is held only by TimelockController `0xb399…b614`, which has a 259,200 s (3-day) `minDelay`.
- **Security Council:** Safe `0x7B96…559a` is **4 of 7**, where the docs say 5 of 7. It holds UNPAUSER.
- **Ops Council:** Safe `0x4b46…9A46` is 2 of 5. It holds RATE_LIMITER and is the token operator and client-ID customiser.
- **Pausers:** five EOAs hold PAUSER. Any one of them can pause `ICS20Transfer`, which blocks `onTimeoutPacket`. That means one key can stop every timeout refund, and only the Security Council can resume them.
- **Rate limit:** refunds go through `Escrow.send`, which runs `_assertAndUpdateRateLimit`. A rate limit therefore throttles refunds as well as inbound transfers (`Escrow.sol:45-46`).
- **`ICS20Transfer`:** not paused.

## Sources

1. https://ibc.cosmos.network/ — IBC overview
2. https://github.com/cosmos/ibc-go — IBC Go implementation
3. ibc-go source: `modules/core/04-channel/keeper/timeout.go`, `modules/apps/transfer/keeper/relay.go`
4. https://github.com/cosmos/solidity-ibc-eureka — Solidity implementation:
   - `ibc-solidity/contracts/ICS26Router.sol` — packet routing, timeout (line 254), MAX_TIMEOUT_DURATION (line 48)
   - `ibc-solidity/contracts/ICS20Transfer.sol` — token transfer, onTimeoutPacket (384-394), _refundTokens (396-439), pause
   - `ibc-solidity/contracts/utils/IBCRolesLib.sol` — role definitions (lines 22-23, 44-51)
   - `ibc-solidity/contracts/light-clients/sp1-ics07/SP1ICS07Tendermint.sol` — ZK light client, freeze (569-573)
   - `ibc-solidity/contracts/utils/RateLimitUpgradeable.sol` — rate limiting
   — cloned and read 2026-09-16

5. https://github.com/orgs/akash-network/discussions/433 — Investigation of stuck IBC transactions (expired channels) — retrieved 2026-09-16
6. https://blockchain.news/news/sei-ibc-assets-bridge-deadline-cosmos-shutdown — SEI IBC shutdown deadline — retrieved 2026-09-16

## Notes / follow-ups

- **IBC Eureka's permissioned relayers and pausable timeout refunds are the critical departure from IBC Classic.** For routing decisions, IBC Classic provides stronger revocability guarantees than IBC Eureka.
- Verify whether the IBC Eureka deployment on Ethereum has relayer role granted to any public/permissionless set
- The Security Council model (timelock claims are self-enforced, not contract-enforced) needs verification
- IBC-inheriting protocols (Composable MANTIS, Osmosis IBC Hooks, Union) inherit IBC Classic timeout by default — they should be evaluated separately if they deploy on IBC Eureka
