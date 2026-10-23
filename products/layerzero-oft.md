---
slug: layerzero-oft
name: LayerZero OFT
framework: true                          # a framework: each OApp owner picks its DVNs, executor and peers; Stargate is one deployment
scope: The OFT and OFT Adapter standard on LayerZero V2 as each token issuer deploys it; DVNs, executors, peers and owners are per deployment and none is read here. Stargate's configuration is in stargate
kind: bridge
class: E
cross_chain: true
chains: unknown                          # per deployment
source_public: true
inherits: []
updated: 2026-10-04

verification:
  service: spec-only
  exit: spec-only
  actors: spec-only
  admin: spec-only
  data: spec-only
  judgment: spec-only
  incidents: partial

exit:
  custody: in_flight_message             # burned (OFT) or locked in the adapter (OFT Adapter) until delivered
  execution: automatic                   # DVNs verify, an executor delivers; lzReceive is permissionless once verified
  overrides:
    - who: the deployment's required DVNs
      needs: unknown                     # per deployment; LayerZero's quickstart default was 1 of 1, and any required DVN can withhold
      parties: unknown
      how: withhold verification of one message, or verify a fabricated one (the KelpDAO case)
      reach: one
      bounded: false
      cost: none on-chain
    - who: the OApp owner and its endpoint delegate
      needs: unknown                     # per deployment
      parties: unknown
      how: change DVNs, libraries or peers; skip, nilify or burn a message
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: none
  exit_bound_seconds: unknown
  exit_bound_chosen_by: none
  standing_approval: unknown             # OFT burns from the holder; an adapter needs approval, and whether it is upgradeable depends on the deployment

actors:
  - role: DVNs; verify the message
    entity: unknown                      # per deployment
    jurisdiction: unknown
    set: unknown
    independence: unknown
  - role: Executor; delivers the verified message
    entity: anyone
    jurisdiction: pseudonymous
    set: permissionless
    independence: independent

admin:
  upgradeable: unknown
  authority: unknown
  timelock_seconds: unknown
  immediate_functions: unknown           # setPeer, setDelegate, setEnforcedOptions (owner); setConfig, set libraries, skip / nilify / burn / clear (delegate)
  grandfathered: none
  outside_exit_path: []

data_gates: unknown

judgment:
  screening: unknown
  freeze_assets: unknown
  freeze_pooled: unknown

service:
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: false
  operators: []
  screening: unknown
  bypass: true

integration:
  calls: ["quoteSend", "send on the OFT or adapter", "track by guid on LayerZero Scan"]
  signatures: ["approval for an OFT Adapter"]
  offchain_required: []
  finisher: anyone
  gasless_start: none
  monitoring: "LayerZero Scan by guid, or OFTSent / OFTReceived events"
  sdk: "@layerzerolabs/oft-evm (TypeScript, Solidity)"
  testnet: true
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
    note: "send on the OFT, paying the LayerZero fee in native gas"
  - action: deliver
    performer: designated
    paid: deferred
    note: "the executor delivers, paid in advance from the sender's fee"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: send
    form: self_built

incidents:
  - date: "2026-04-18"
    duration: unknown
    user_funds_lost: true
    exits_blocked: unknown
    cause: "KelpDAO rsETH, $292M: the single DVN in a 1-of-1 configuration attested a fabricated message after its RPC nodes were compromised"

open_questions:
  - DVN, owner and delegate configuration of the specific OFT deployments that routes use
---

# LayerZero OFT

**Primitive (one line):** Omnichain Fungible Token standard on LayerZero messaging; burn/mint (new tokens) or lock/unlock via OFT Adapter (existing tokens); cross-chain messages verified by configurable DVN (Decentralized Verifier Network) set before destination endpoint processes them.
**Product scope of this entry:** LayerZero OFT standard and OFT Adapter

## Category 1 — Actor-gated edges

**Actors on exit path:**
- Actor: DVN (Decentralized Verifier Network)
  - Role: verify cross-chain messages. Configuration is per-OApp — the OApp owner chooses which DVNs verify each pathway.
  - **CRITICAL: LayerZero's default/quickstart is 1-of-1 DVN (single verifier).** 40% of protocols were using this at the time of the KelpDAO exploit.
  - Source: [1]
- Actor: OApp owner / delegate
  - Role: owner controls DVN config, peer settings, enforced options. Delegate controls library config and message management (skip, nilify, burn, clear).
  - Source: [1]

**User self-refund:** **NO.** No timeout or automatic refund. Failed messages can be retried but only by the delegate/owner. The skip/nilify/burn/clear functions are admin-only. End users have no self-service recovery.

## Category 2 — Modification-gated edges

**Admin surface (significant):**
- OApp owner: `setPeer()`, `setEnforcedOptions()`, `setDelegate()`
- Delegate: `setConfig()` (DVNs, executor, confirmations), `setSendLibrary()`, `setReceiveLibrary()`, message management
- DVN contracts: multisig capabilities, upgradeability, pausing, fee management
- **Once owner sets DVN config, only owner can change it** — but owner CAN change it at any time

## Historical incidents (CRITICAL)

- **2026-04-18: KelpDAO rsETH exploit — $292M stolen.** Lazarus Group compromised the RPC nodes that KelpDAO's single LayerZero DVN relied on via social engineering of a LayerZero Labs developer (gaining session keys from March 6, 2026). Manipulated RPC responses to make the DVN attest to a fabricated cross-chain message claiming 116,500 rsETH was locked when it wasn't. **No smart contract was exploited — every contract behaved as designed.** Root cause: 1-of-1 DVN configuration (LayerZero's own default). 40% of protocols using same setup at the time. Secondary damage: 89,567 rsETH deposited on Aave as collateral to borrow $190M WETH against now-worthless backing. LayerZero subsequently tightened security requirements. Source: [2]

**Implication:** the OFT standard's security is entirely dependent on DVN configuration, which is per-OApp and controlled by the OApp owner. A misconfiguration (or the default 1-of-1 setup) is catastrophic and non-recoverable by users. **This is not a bug — it's the designed trust model working as intended, with catastrophic consequences when misconfigured.**

## Sources

1. https://docs.layerzero.network/v2/concepts/applications/oft-standard — OFT standard docs
2. Multiple sources on KelpDAO exploit: social engineering of LZ developer, 1-of-1 DVN, $292M stolen, Lazarus Group attribution
3. https://github.com/LayerZero-Labs/LayerZero-v2 — source repo
