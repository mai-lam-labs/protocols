---
slug: zetachain
name: ZetaChain
scope: ZetaChain cross-chain calls and transfers through GatewayEVM and ERC20Custody on connected EVM chains, with native assets held at the TSS address; observers and signers on ZetaChain decide outbound transfers and reverts. Read on Ethereum
kind: bridge
class: D
cross_chain: true
chains: unknown                          # ZetaChain plus connected chains (Ethereum, BSC, Polygon, Base, Arbitrum, Bitcoin, Solana, ...)
source_public: true                      # zeta-chain/protocol-contracts and node; not cloned
inherits: []
updated: 2026-10-04

verification:
  service: spec-only
  exit: spec-only
  actors: spec-only
  admin: partial                         # proxies and TSS address read on Ethereum; role holders not found
  data: spec-only
  judgment: spec-only
  incidents: not-reviewed

exit:
  custody: mpc_vault                     # ERC-20s in ERC20Custody (proxy), ETH at the TSS address 0x70e967ac...FD83; both released only by TSS signature
  execution: automatic                   # observers vote on ZetaChain; signers produce the outbound or revert with the TSS key
  overrides:
    - who: ZetaChain TSS signers
      needs: unknown                     # signer set and threshold not read
      parties: unknown
      how: decline to sign one outbound or revert, or sign one that wasn't voted
      reach: one
      bounded: false
      cost: stake at risk only if slashed
    - who: admin of GatewayEVM and ERC20Custody (UUPS)
      needs: unknown                     # role holders not found
      parties: unknown
      how: upgrade the custody contract, or change its TSS address
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: on_failure             # a failed cross-chain call reverts to the revert address through a TSS-signed outbound
  exit_bound_seconds: unknown
  exit_bound_chosen_by: none
  standing_approval: upgradeable_target  # approve GatewayEVM, a UUPS proxy

actors:
  - role: Observers and TSS signers on ZetaChain
    entity: ZetaChain validator set
    jurisdiction: unknown
    set: staked
    independence: unknown

admin:
  upgradeable: true                      # GatewayEVM 0x48B9AACC... and ERC20Custody 0x0Bad40D9... are UUPS proxies on Ethereum
  authority: unknown
  timelock_seconds: unknown
  immediate_functions: unknown           # pause, upgrade and TSS updates exist as roles; holders not enumerable on-chain
  grandfathered: none
  outside_exit_path: []

data_gates: unknown

judgment:
  screening: unknown
  freeze_assets: [USDC, USDT]
  freeze_pooled: true                    # ERC20Custody holds every bridged ERC-20

service:
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: false
    note: "gateway calls are direct"
  operators: []
  screening: unknown
  bypass: true

integration:
  calls: ["GatewayEVM.deposit / depositAndCall on the source", "a universal contract on ZetaChain handles it", "withdraw back out through the ZetaChain gateway"]
  signatures: ["ERC-20 approval to GatewayEVM"]
  offchain_required: []
  finisher: protocol
  gasless_start: none
  monitoring: "ZetaChain CCTX status by inbound hash"
  sdk: "@zetachain/toolkit (TypeScript)"
  testnet: true
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: delivery
  holder: none
  strike: unknown
  expiry: none
  early_close: none
  premium: none
  terms_fixed_by: calldata
  price_set_by: unknown
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
    note: GatewayEVM.deposit from the user's account
  - action: revert
    performer: none
    paid: none
    note: a failed call reverts through a TSS-signed outbound; the user does nothing

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: gateway deposit
    form: self_built

incidents: []

open_questions:
  - "Trade: strike, price_set_by, discipline, surplus_to (CRITERIA.md, Trade)"
  - Who holds DEFAULT_ADMIN, PAUSER and TSS-update roles on GatewayEVM and ERC20Custody (needs RoleGranted logs; public RPC refused the query)
  - TSS signer set size and threshold, and how a TSS migration moves funds
  - Incident history
---

# ZetaChain

**Primitive (one line):** L1 blockchain with PoS observer validator set; validators observe events on connected chains and reach consensus; TSS-controlled addresses on external chains hold custodied assets; universal smart contracts execute cross-chain logic natively.
**Product scope of this entry:** ZetaChain cross-chain infrastructure

## Category 1 — Actor-gated edges

**Actors on exit path:**
- Actor: ZetaChain validator set (observers + signers)
  - Role: observe cross-chain events, reach consensus, sign TSS transactions on external chains. Required for all cross-chain operations including refunds.
  - Set size: permissioned validator set (PoS with staking)
  - Source: [1]

**User self-refund:** no — requires validator consensus and TSS signing.

**TSS custody:** external chain assets are held in TSS-controlled addresses. This is effectively committee custody (Class D characteristic), though the protocol routes intents (Class C characteristic). Hybrid C/D classification.

## Category 2 — Modification-gated edges

**Upgrade authority:** chain governance (validator set controls upgrades).
**Pause mechanism:** unknown — requires source verification.

## Historical incidents

No major exploits found in web search for ZetaChain specifically. The TSS architecture is similar to THORChain's (which has had multiple incidents).

## On-chain state, Ethereum (2026-10-04)

Addresses are from `zeta-chain/protocol-contracts` `data/addresses.mainnet.json`.

- **TSS address:** `0x70e9…FD83`, an address with no code.
- **Gateway and custody:** `GatewayEVM` `0x48B9…30ed` and `ERC20Custody` `0x0Bad…23B5` are UUPS proxies. Both have `tssAddress()` set to the TSS address, and neither is paused.
- **Roles not found:** the roles aren't enumerable. The RPC refused an `eth_getLogs` for `RoleGranted`, and the first pages of Blockscout logs held no grants.

## Sources

1. https://www.zetachain.com/docs/ — ZetaChain documentation
2. https://github.com/zeta-chain/protocol-contracts — source repo

## Notes / follow-ups

- Verify current validator set size and composition
- TSS key rotation mechanism should be evaluated
