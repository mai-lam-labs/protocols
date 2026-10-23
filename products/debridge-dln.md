---
slug: debridge-dln
name: deBridge DLN
scope: DLN (DlnSource, DlnDestination) on EVM chains and the deBridge messaging layer it uses for unlocks and cancels (DeBridgeGate, SignatureVerifier); the DLN API in front. Solana DLN isn't covered
kind: bridge
class: C
cross_chain: true
chains: unknown                          # DlnSource/DlnDestination share addresses across many EVM chains; read on Ethereum, Arbitrum, Base, BSC
source_public: true                      # contracts; the validator node software and the API aren't reviewed
inherits: []
updated: 2026-10-04

verification:
  service: spec-only
  exit: source-verified                  # sendEvmOrderCancel, claimCancel, SignatureVerifier.submit read
  actors: partial                        # 12 validator addresses read on Ethereum; operators not identified
  admin: source-verified                 # proxy admins, owners and admin roles read on Ethereum; DlnSource admin on Arbitrum, Base, BSC
  data: partial
  judgment: partial
  incidents: partial                     # web search 2026-09-16

exit:
  custody: escrow                        # DlnSource 0xeF4fB24aD0916217251F553c0596F8Edc630EB66 holds the give amount of every open order
  execution: self                        # the order's orderAuthorityAddressDst calls sendEvmOrderCancel on the destination; it is self only if the user set it to an address they control there
  overrides:
    - who: deBridge validators on the source chain's SignatureVerifier (12 on Ethereum)
      needs: 5 of 12 decline to sign one cancel message (8 of 12 required); 8 of 12 to sign a forged unlock instead
      parties: quorum
      independent: unknown
      how: withhold signatures for one claimCancel submission, or sign a claimUnlock for an order that was never filled
      reach: one
      bounded: false
      cost: none on-chain; no slashing found in the contracts
    - who: DEFAULT_ADMIN of DeBridgeGate, a 5-of-8 Safe (0x6bec1faf33183e1bc316984202ecc09d46ac92d5 on Ethereum)
      needs: 5 of 8 Safe signers; who they are isn't published
      parties: unknown
      how: blockSubmission([submissionId], true) stops one cancel message from being claimed on the source; or upgrade DlnSource through its ProxyAdmin
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: timeout_proof          # no expiry: cancel any time the order is unfilled on the destination, proven to the source by a deBridge message
  exit_bound_seconds: unknown            # validator signing plus claim; not measured
  exit_bound_chosen_by: none
  standing_approval: upgradeable_target  # createOrder pulls by transferFrom (or permit) into the DlnSource proxy

actors:
  - role: deBridge validators; sign the claimCancel submission from the destination
    entity: unknown                      # 12 addresses on Ethereum's SignatureVerifier; deBridge names operators in its docs, not matched to addresses here
    jurisdiction: unknown
    set: m_of_n                          # 8 of 12 (minConfirmations 8; excessConfirmations 3 is below it, so 8 always)
    independence: unknown
  - role: Claimer; submits the signatures to DeBridgeGate.claim on the source
    entity: anyone
    jurisdiction: pseudonymous
    set: permissionless                  # claim has no caller check; the executionFee pays whoever does it
    independence: independent

admin:
  upgradeable: true                      # DlnSource, DlnDestination, DeBridgeGate and SignatureVerifier are transparent proxies
  authority: multisig                    # ProxyAdmins owned by a 5-of-8 Safe on every chain checked (different Safe addresses per chain); the same Safe holds DEFAULT_ADMIN on the gate, DlnSource and the verifier on Ethereum
  timelock_seconds: none
  immediate_functions:
    - function: ProxyAdmin.upgrade on DlnSource, DlnDestination, DeBridgeGate, SignatureVerifier
      caller: 5-of-8 Safe
      effect: replaces the code holding escrow or deciding which messages count
    - function: pause on DlnSource, DlnDestination and DeBridgeGate
      caller: GOVMONITORING_ROLE (holders not enumerable on-chain)
      effect: claimCancel, sendEvmOrderCancel and claim are whenNotPaused; unpause needs the admin
    - function: DeBridgeGate.blockSubmission
      caller: admin (the Safe)
      effect: blocks chosen submissions, including one user's cancel
    - function: OraclesManager addOracles / updateOracle, updateMinConfirmations
      caller: admin
      effect: who signs and how many must
    - function: DlnSource.setDlnDestinationAddress, DlnDestination.setDlnSourceAddress
      caller: admin
      effect: which remote contract's messages are trusted for unlocks and cancels
  grandfathered: none
  outside_exit_path:
    - what: updateGlobalFee and fee settings
      effect: fees on new orders

data_gates:
  - kind: validator confirmation
    where: deBridge validators before signing a submission
    trigger: source-chain finality as each validator applies it
    blocks_exit: true
    reset: bounded                       # assumed to clear once the source block is final; validator software not read

judgment:
  screening: []                          # none in the contracts; whether validators or the API screen isn't known
  freeze_assets: unknown
  freeze_pooled: true                    # every open order's give amount sits at the one DlnSource per chain

service:
  integrator_access:
    api_key: false                       # dln.debridge.finance/v1.0/dln/order/create-tx built an order with no key, for exact input and exact output (2026-10-07)
    identity: unknown
    revocable: unknown
    rate_limited: unknown
  operators:
    - role: DLN API (quotes, builds createOrder transactions)
      entity: deBridge
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: Takers; fill orders on the destination
      entity: unknown
      single_operator: unknown
      source_public: unknown
      deployment_config_public: false
  screening: unknown
  bypass: true                           # createOrder and fulfillOrder are open contract calls

integration:
  calls: ["DLN API create-tx, or DlnSource.createOrder with approval or permit", "taker fulfills on the destination", "to cancel: orderAuthorityAddressDst calls DlnDestination.sendEvmOrderCancel (paying the deBridge fee), then the claim is executed on the source"]
  signatures: ["optional ERC-2612 permit in createOrder"]
  offchain_required:
    - role: DLN API for quotes
      api_key: unknown
      rate_limited: unknown
  finisher: anyone
  gasless_start: none                   # createOrder is sent by the user and pays the deBridge fixed fee in native gas
  monitoring: "DLN API order status, or CreatedOrder / FulfilledOrder / SentOrderCancel / ClaimedOrderCancel events"
  sdk: unknown
  testnet: unknown
  steps: 3

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: anyone                         # any taker, unless allowedTakerDst names one
  strike: signed
  expiry: none                           # no expiry: the order stands until filled or cancelled
  early_close: gas_other_chain
  premium: none
  terms_fixed_by: signature
  price_set_by: user_bound
  discipline: unknown
  surplus_to: holder
  extraction: []
  sides: [exact_in, exact_out]           # create-tx takes a fixed input with dstChainTokenOutAmount=auto, or a fixed output with srcChainTokenInAmount=auto (both live 2026-10-07)
  rate: firm                             # giveAmount and takeAmount are both in the order; patchOrderGive and patchOrderTake re-price it later
  quote_validity: unknown
  partial_fill: none                     # fulfilOrder pays the full takeAmount, less any patch the user signed
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: "createOrder, paying the deBridge fixed fee in native gas"
  - action: cancel
    performer: user
    paid: none
    gas_on: other_chain
    note: "orderAuthorityAddressDst calls sendEvmOrderCancel on the destination, paying the deBridge fee there"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: createOrder
    form: calldata
    bounds: bounded
    verifiable_locally: true
    api_optional: true
    note: "DlnSource.createOrder can be called directly"

incidents: []                            # none found (web search 2026-09-16)

open_questions:
  - "Trade: discipline (CRITERIA.md, Trade)"
  - "Quote: quote_validity (CRITERIA.md, Trade); these decide which quote modes (exact, atleast, upto) the venue can serve, and who decides a partial fill"
  - Who the 12 validators on each chain are (entities, jurisdictions), and whether any are deBridge itself
  - Who holds GOVMONITORING_ROLE (the contracts don't enumerate role members; needs RoleGranted logs)
  - Who signs the 5-of-8 Safes, and whether they are the same people on every chain
  - DLN chain list, and admin and validator configuration on chains other than those read
  - Time from sendEvmOrderCancel to claimCancel in practice
  - Whether the DLN API screens users (it needs no key)
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: debridge-dln
    url: https://github.com/debridge-finance/debridge-contracts-v1
    commit: 2e9f9c73438738310b5293cec4cffe25741e9b1f
    commit_date: 2024-10-23
  - repo: debridge-dln-contracts
    url: https://github.com/debridge-finance/dln-contracts
    commit: d54e94f2b5102bff89a4df506404bb77f3edc148
    commit_date: 2024-06-04
---

# deBridge DLN

**Primitive (one line):** 0-TVL intent protocol; user deposits into DlnSource escrow on source chain; taker fulfills on destination chain; cross-chain unlock message (8/12 validator attestation via DeBridgeGate) releases escrowed funds to taker; cancel requires `orderAuthorityAddressDst` to initiate cross-chain cancel via same validator attestation.
**Product scope of this entry:** DLN (Debridge Liquidity Network) EVM contracts

## Category 1 — Actor-gated edges

**Actors on exit path (cancel/refund):**

User CANNOT self-refund on the source chain. Cancel requires two things:

- Actor: `orderAuthorityAddressDst` (set by user at order creation)
  - Role: ONLY address that can call `sendEvmOrderCancel()` on DlnDestination. If this address is wrong, inaccessible, or lost, funds are stuck **permanently**. Docs explicitly warn: "Ensure that the address specified as the dstChainOrderAuthorityAddress parameter is accessible by the user. Otherwise, there is a risk of an order (and funds) being stuck forever."
  - Source: [3] `DlnDestination.sol:538`

- Actor: deBridge validator set (12 validators, 8/12 threshold)
  - Role: must attest the cross-chain cancel message for it to reach DlnSource. Without attestation, cancel cannot complete.
  - Legal entity: governance-elected validators (Stakin confirmed; others governance-managed)
  - Set size: 12 validators, 8/12 quorum. (Corrected 2026-10-04: the earlier "10/12 for large amounts" doesn't hold. `submit` needs max(excessConfirmations, minConfirmations), and on Ethereum excessConfirmations is 3, so 8 always.)
  - Independence: permissioned, governance-managed via `OraclesManager.addOracles()`
  - Source: [3] `SignatureVerifier.sol:58-114`, `OraclesManager.sol:80-143`

**Cancellation mechanism:** `orderAuthorityAddressDst` calls `sendEvmOrderCancel()` on destination → cross-chain message via DeBridgeGate → 8/12 validator attestation → `claimCancel()` on DlnSource → full refund to user. Source: [3] `DlnDestination.sol:530-561`, `DlnSource.sol:378-385,684-695`

**Expiry/timeout:** **NONE.** The Order struct has no deadline or expiry field. Orders persist indefinitely. Source: [3] DlnOrderLib

**Compellability profile:** validators are governance-elected, identifiable. `orderAuthorityAddressDst` is user-set.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** fully upgradeable via OpenZeppelin `TransparentUpgradeableProxy`. Proxy admin can call `upgradeTo()`. This is the only theoretical escape hatch for stuck funds. Source: [3] deployment architecture

**Immediate-effect admin functions:**
- `pause()` by `GOVMONITORING_ROLE` — **pauses ALL operations including cancel/refund**. Source: [3] `DlnBase.sol:103`
- `unpause()` by admin. Source: [3] `DlnBase.sol:108`
- `setDlnDestinationAddress()` — changes trusted destination contract per chain. Source: [3] `DlnSource.sol:478`
- `updateGlobalFee()` — changes fee parameters. Source: [3] `DlnSource.sol:513`
- `blockSubmission()` on DeBridgeGate — can block specific cross-chain messages. Source: [3] DeBridgeGate

**Grandfathering:** existing orders are affected by pause (all operations blocked) and by admin changes to trusted destination addresses.

## Category 3 — Data-oracle-gated edges

**Oracles:** the 12-validator attestation IS the oracle system. Validators monitor blockchain events and sign attestations. No external price oracles (no Chainlink). Validator signatures stored on Arweave for DA. Source: [3] `SignatureVerifier.sol`

## Category 4 — Judgment-oracle-gated edges

**Risk-scoring integrations:** none identified in contracts. Validators may apply their own compliance filters when signing attestations — this would be opaque to users.

**Stablecoin freeze exposure:** DlnSource holds escrowed tokens. If DlnSource address (0xeF4fB24aD0916217251F553c0596F8Edc630EB66) is frozen by stablecoin issuer, all escrowed funds in that asset are stuck.

## Historical incidents

No exploits, hacks, or stuck-fund incidents found (web search 2026-09-16). Zero downtime reported since 2022 mainnet launch. Per deBridge docs: "User funds are never held on a third-party address... if an order is not fulfilled, users can always cancel and reclaim their tokens in full, including all fees." **Note:** this marketing claim understates the dependency — cancel requires `orderAuthorityAddressDst` action + 8/12 validator attestation, and there is no timeout/expiry mechanism. "Always cancel" is only true if the dst authority address is accessible and validators are online. Multiple Halborn audits (most recent December 2024). Bug bounty on Immunefi (Critical $200K). Source: [1]

**Note on compliance:** no documented cases of deBridge validators refusing to attest for compliance reasons, but the 12-validator set is governance-managed and could theoretically be directed to refuse specific attestations.

## Composite

**Stuck-leg failure modes:**
1. `orderAuthorityAddressDst` inaccessible — funds stuck **permanently** (no on-chain recovery path). **Critical.**
2. Validator set offline — cancel messages cannot be delivered. Funds stuck until validators recover. **Unbounded.**
3. Admin pause — all operations including cancel blocked. **Unbounded** until unpause.
4. Order never fulfilled and never cancelled — funds sit in escrow indefinitely (no expiry). **Unbounded.**
5. Stablecoin issuer freezes DlnSource — all escrowed funds in that asset stuck. **Unbounded.**

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Wrong orderAuthorityAddressDst | **permanent lock** (no recovery at contract level) | [3] docs warning |
| Validator offline | unbounded (no fallback) | [3] |
| Admin pause | unbounded (admin controls unpause) | [3] |
| No expiry (unfulfilled order) | unbounded (orders never expire) | [3] |
| Stablecoin freeze | unbounded | issuer-dependent |
| Admin-initiated upgrade rescue | depends on admin action | proxy architecture |

## On-chain state (2026-10-04)

Read on Ethereum unless noted:

- **Proxies:**
  - `DlnSource` (`0xeF4f…EB66`) and `DlnDestination` (`0xE735…dd7f`) are transparent proxies under ProxyAdmin `0xa7b8…f46b`.
  - `DeBridgeGate` (`0x43dE…98aA`) and its `SignatureVerifier` (`0x949b…8a8c`) are under ProxyAdmin `0xe442…94fe`.
  - Both ProxyAdmins are owned by Safe `0x6bec…92d5`, 5 of 8. There is no timelock.
  - The same Safe holds `DEFAULT_ADMIN_ROLE` on the gate, `DlnSource` and the verifier.
- **Other chains:** on Arbitrum, Base and BSC, `DlnSource`'s ProxyAdmin is owned by a 5-of-8 Safe at a different address on each chain (`0xa528…b265` on Arbitrum and BSC, `0xf0a9…a29e` on Base).
- **Validators:** the verifier has 12 oracles, all valid, with `minConfirmations` 8 and `requiredOraclesCount` 0. The gate's `excessConfirmations` is 3. Since `submit` takes the larger of the two, every submission needs 8 of 12.
- **Paused:** no, on any contract checked.
- **`blockSubmission`:** gives the gate admin a per-message veto. One user's cancel can be blocked without pausing anyone else.

## Sources

1. https://docs.debridge.com/ — deBridge documentation
2. https://docs.dln.trade/ — DLN-specific documentation
3. Source repos:
   - https://github.com/debridge-finance/debridge-contracts-v1 — base messaging layer (`SignatureVerifier.sol`, `OraclesManager.sol`, `DeBridgeGate.sol`)
   - DLN contracts repo — `DlnSource.sol` (createOrder lines 182-274, claimCancel lines 378-385), `DlnDestination.sol` (fulfillOrder lines 147-257, sendEvmOrderCancel lines 530-561), `DlnBase.sol` (pause lines 103-108)
   — cloned and read 2026-09-16

## Notes / follow-ups

- **The combination of no order expiry + cancel requires validator attestation + wrong dst authority = permanent lock makes DLN one of the highest-risk Class C protocols.** The routing engine should verify `orderAuthorityAddressDst` is correct before committing.
- Verify whether the proxy admin has a timelock or is a direct multisig
- Verify the current validator set and their identities/jurisdictions
- The admin upgrade path is the ONLY theoretical recovery for stuck funds — this means trusting the admin is a necessary condition for DLN usage
