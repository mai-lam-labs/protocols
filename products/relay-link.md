---
slug: relay-link
name: Relay.link
scope: Relay's crosschain orders on EVM origin chains through the protocol-v2 RelayDepository 0x4cd00e387622c35bddb9b4c962c136462338bc31 (what /quote/v2 returned for Ethereum to Base, 2026-10-04), settled through Relay Chain (Hub, Oracle) and the Allocator on Aurora; the Relay API in front
kind: bridge
class: C
cross_chain: true
chains: unknown                          # /chains lists 60; depository read on Ethereum, Base, Arbitrum, Optimism, Polygon, BSC
source_public: true                      # relay-depository, relay-settlement, relay-protocol-oracle; the API and solver aren't
inherits: [near-chain-signatures]        # the Allocator signs through NEAR MPC
updated: 2026-10-04

verification:
  service: spec-only
  exit: partial                          # RelayDepository read in full; refund and withdrawal flows from docs
  actors: spec-only
  admin: source-verified                 # owner and allocator read on six chains; no proxy
  data: spec-only
  judgment: spec-only                    # screening from docs
  incidents: partial

exit:
  custody: escrow                        # RelayDepository holds deposits until the Allocator signs a CallRequest
  execution: discretionary               # the user can't withdraw from the depository; refunds are sent by a solver or Relay, and a user-triggered withdrawal needs Relay's Oracle to attest the deposit and the Allocator to sign
  overrides:
    - who: RelayDepository owner, EOA 0xf61a305199fa1135d76ffab3752d42f55cbd775a, the same on all six chains read
      needs: one key; no timelock
      parties: key
      how: setAllocator to an address it controls, then execute any CallRequest, which can send any deposit anywhere; the docs' "no admin withdrawal" holds only while the owner leaves the allocator alone
      reach: one
      bounded: false
      cost: none on-chain
    - who: Relay's Oracle signer on Relay Chain
      needs: unknown                     # an authorised signer, or a RelayOracleMultisig threshold; not read
      parties: unknown
      how: decline to attest one deposit, so it never becomes the user's Hub balance and can't be refunded or withdrawn
      reach: one
      bounded: false
      cost: none on-chain
    - who: Relay platform screening
      needs: one party
      parties: organisation
      how: a fill-time screening failure "does not trigger an automatic refund"; the user is told to contact support
      reach: one
      bounded: false
      cost: none
  refund_trigger: on_failure             # solver or Relay refunds on the origin chain to refundTo, if set and the amount covers gas
  exit_bound_seconds: unknown
  exit_bound_chosen_by: none
  standing_approval: immutable_target    # approve to RelayDepository, which isn't upgradeable; but its allocator can be replaced (above)

actors:
  - role: Relay Oracle; attests deposits and fills on Relay Chain
    entity: Relay
    jurisdiction: unknown
    set: single                          # authorised signer; threshold if a multisig signer is used isn't read
    independence: single_org
  - role: Allocator (NEAR MPC via Aurora); signs the withdrawal CallRequest
    entity: NEAR MPC network
    jurisdiction: unknown
    set: m_of_n
    independence: unknown
  - role: Solver; sends the refund or withdraws on the user's behalf
    entity: Relay's solver (0xf70da978... in the quotes sampled)
    jurisdiction: unknown
    set: whitelist
    independence: single_org

admin:
  upgradeable: false                     # RelayDepository is not a proxy
  authority: eoa                         # owner 0xf61a3051...775a
  timelock_seconds: none
  immediate_functions:
    - function: RelayDepository.setAllocator
      caller: owner EOA
      effect: replaces the only key that can move deposits
    - function: suspend an approved withdrawer (RelayAllocatorSpender)
      caller: any single Security Council member
      effect: halts all withdrawal proof generation, including user withdrawals
  grandfathered: none
  outside_exit_path:
    - what: replace the Allocator, change Security Council membership
      effect: structural changes on Aurora
      caller: Security Council supermajority

data_gates: []                           # none known; not read on Relay Chain

judgment:
  screening:
    - kind: address screening with Chainalysis, HackBounty and an internal blocklist, at quote and fill
      status: active
  freeze_assets: unknown
  freeze_pooled: true                    # every deposit on a chain sits in one RelayDepository

service:
  integrator_access:
    api_key: true                        # docs: "Starting October 2, 2026, every quote/v2 request will require a valid API key" (api-keys page, modified 2026-10-05); not yet enforced: keyless quote/v2 calls for exact input and exact output both answered on 2026-10-07
    identity: signup                     # self-serve keys from the Relay Dashboard, after signing in
    revocable: unknown                   # the dashboard lets an integrator revoke its own keys; whether Relay can revoke one wasn't found
    rate_limited: true                   # 50 /quote requests per minute per key by default; more on request
  operators:
    - role: Relay API (quotes, execution, refunds, user withdrawals)
      entity: Relay (Reservoir Protocol)
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: Relay Oracle
      entity: Relay
      single_operator: true
      source_public: true                # relay-protocol-oracle
      deployment_config_public: false
  screening:
    - kind: Chainalysis, HackBounty, internal blocklist
      where: quote and fill
      in_source: false
      enabled_in_production: true
  bypass: false                          # depositing directly is possible, but only Relay's Oracle and Allocator can release funds

integration:
  calls: ["POST api.relay.link/quote/v2", "approve (ERC-20) and call RelayDepository.depositErc20 / depositNative with the order id", "poll /intents/status"]
  signatures: ["none for the deposit; an owner signature for a user-triggered withdrawal via /withdrawals/request"]
  offchain_required:
    - role: Relay API
      api_key: unknown
      rate_limited: unknown
  finisher: protocol
  gasless_start: [eip3009]               # deposit addresses accept a plain transfer, which a relayer can deliver for EIP-3009 tokens; other tokens need a transfer with gas
  monitoring: "/intents/status by request id"
  sdk: "@relayprotocol/relay-sdk (TypeScript)"
  testnet: true                          # api.testnets.relay.link
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: operator
  strike: off_chain
  expiry: api_chosen                     # the v2 order data's deadline was 168 h out on 2026-10-07
  early_close: none
  premium: none
  terms_fixed_by: api
  price_set_by: quote
  discipline: unknown
  surplus_to: operator
  extraction: [operator_quote]
  sides: [exact_in, exact_out]           # tradeType EXACT_INPUT and EXACT_OUTPUT, both answered live 2026-10-07
  rate: floating_above_bound             # exact input: a 2% minimumAmount below the quote; exact output: input and output fixed at the quote; neither is signed on-chain
  quote_validity: unknown
  partial_fill: unknown
  partial_remainder: unknown

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: "approve and depositErc20, or a transfer to a deposit address"
  - action: refund
    performer: designated
    paid: atomic
    note: "a solver or Relay refunds on the origin, deducting its gas from the amount"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: deposit
    form: calldata
    bounds: bounded
    verifiable_locally: true
    api_optional: false
    note: "depositErc20 / depositNative with the order id; funds land in the depository either way"

incidents: []                            # none found (2026-09-16)

open_questions:
  - "Whether Relay enforces the documented API-key requirement on quote/v2 (keyless calls still answered on 2026-10-07), and whether Relay can revoke an integrator's key"
  - "Trade: discipline (CRITERIA.md, Trade)"
  - "Quote: quote_validity, partial_fill, partial_remainder (CRITERIA.md, Trade); these decide which quote modes (exact, atleast, upto) the venue can serve, and who decides a partial fill"
  - Who holds the depository owner key 0xf61a3051...775a, and whether Relay considers setAllocator an admin withdrawal path
  - Whether allocator 0x63c1d3e9...1b56 is a NEAR MPC-derived key, and which derivation path
  - The Oracle's signer configuration on Relay Chain (single signer or RelayOracleMultisig, and threshold)
  - Security Council membership and thresholds
  - Whether every route uses the v2 depository, or some still send to the solver directly
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: relay-depository
    url: https://github.com/relayprotocol/relay-depository
    commit: 458a64c310a3504aaf37e112af9a8707c9eb11ad
    commit_date: 2026-08-13
  - repo: relay-settlement
    url: https://github.com/relayprotocol/relay-settlement
    commit: b2f3e0e5fba9381293f030ef340ffb4872687fcf
    commit_date: 2026-09-11
    note: "cloned; only the docs' description of Hub, Oracle and Allocator was used, not the contracts"
---

# Relay.link

**Primitive (one line):** User deposits into Depository contract on origin chain; solver fronts liquidity on destination chain; settlement via NEAR MPC-signed cryptographic proofs (EIP-712 for EVM, Ed25519 for Solana) through Allocator on Aurora/NEAR; solver claims escrowed deposit after attestation.
**Product scope of this entry:** Relay cross-chain bridge (85+ chains)

## Category 1 — Actor-gated edges

**Actors on exit path (refund):**
- Actor: Solver
  - Role: initiates fast refund if order cannot be filled. "Instead of filling, the solver sends funds directly to the user on the origin chain." Refund still requires settlement attestation.
  - Source: [1]
- Actor: NEAR MPC / Allocator
  - Role: generates MPC-signed proofs for withdrawal verification. Required for both fill settlement and refund settlement.
  - Source: [1]

**User self-refund:** docs state "the user can reclaim their deposit" if solver fails to fill, but the reclaim mechanism, timeframe, and conditions are not specified. No explicit timeout or expiry mechanism documented. Source: [1]

**Compellability profile:** NEAR MPC is a threshold signature scheme operated by NEAR validators.

## Category 2 — Modification-gated edges

**Upgrade authority:** unknown — requires source verification.
**Pause mechanism:** unknown.
**Admin functions:** unknown.

## Category 3 — Data-oracle-gated edges

**Oracles:** NEAR MPC attestation is the oracle/settlement layer. MPC-signed proofs verify fills and refunds.

## Historical incidents

No exploits or stuck-fund incidents found in web search. Claims 99.9% uptime, most transactions < 2 seconds.

## Depository source and on-chain state (2026-10-04)

`RelayDepository.sol` (relay-depository, `packages/ethereum-vm/src`, 281 lines) is Solady `Ownable` plus EIP-712. It holds deposits (`depositNative`, `depositErc20`) and releases them only through `execute(CallRequest, signature)`. That function checks `expiration`, checks that `allocator` signed it (ERC-1271 or ECDSA) and checks nonce uniqueness, then runs an arbitrary list of calls. The owner can change `allocator` with `setAllocator`, at once. There is no deposit-specific refund, timeout or user withdrawal in the contract.

On Ethereum, Base, Arbitrum, Optimism, Polygon and BSC, the depository is at `0x4cd0…bc31`:

- Code is 8,628 bytes, and there is no proxy.
- `owner()` is `0xf61a305199fa1135d76ffab3752d42f55cbd775a`, an EOA.
- `allocator()` is `0x63c1d3e9c646184529c5694630a01c00df171b56`, also an address with no code. The docs say the Allocator signs with NEAR MPC, so this may be an MPC-derived key; that isn't verified here.

A `/quote/v2` request for 1 ETH Ethereum → Base, and one for 100 USDC Ethereum → Base, both deposit into this contract, with the solver `0xf70da978…dbef` named in the order.

**Docs versus contract.** The security page says the Depository has "no admin withdrawal" and that "only the registered Allocator can authorize withdrawals". Both are true as written, but the owner chooses the Allocator, with one key and no delay.

**User exits.** Refunds go to `refundTo` on the origin chain when a solver or Relay sends them, and only if `refundTo` is set and the amount covers gas. A user-triggered withdrawal through `/withdrawals/request` needs the Oracle to attest the deposit and the Allocator to sign. A fill-time screening failure doesn't refund automatically.

## Sources

1. https://docs.relay.link/references/protocol/how-it-works — protocol architecture, refund flow
2. https://github.com/relayprotocol — `relay-depository` and `relay-settlement` cloned 2026-10-04
3. https://docs.relay.link/references/protocol/security.md, /references/api/api_core_concepts/refunds.md, /security/compliance.md, /references/api/request-withdrawal.md, /references/protocol/how-it-works.md — retrieved 2026-10-04
4. `api.relay.link/chains` and `/quote/v2` (ETH and USDC, Ethereum → Base), 2026-10-04
5. `owner()`, `allocator()`, code and the ERC-1967 slot on six chains through publicnode, 2026-10-04

## Notes / follow-ups

- NEAR MPC dependency means NEAR validator set liveness is required for settlement
- Very high chain coverage (85+) — verify whether all chains use same security model
