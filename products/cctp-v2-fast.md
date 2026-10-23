---
slug: cctp-v2-fast
name: Circle CCTP V2 Fast Transfer
scope: CCTP V2 burns with minFinalityThreshold 1000 or lower, attested at the confirmed level and minted through handleReceiveUnfinalizedMessage, backed by Circle's off-chain Fast Transfer allowance. Contracts, roles, admin, screening and Iris are the same as cctp-v2-standard; this entry records what differs
kind: bridge
class: C
cross_chain: true
chains: [Ethereum, Arbitrum, Base, Codex, EDGE, Ink, Linea, Morph, OP Mainnet, Plume, Solana, Starknet, Unichain, World Chain, X Layer]   # Fast is offered only from these sources; every CCTP domain is a destination
source_public: true
inherits: [cctp-v2-standard]
updated: 2026-09-29

verification:
  service: spec-only
  exit: source-verified
  actors: partial
  admin: source-verified
  data: partial                          # the unfinalized-message path read in source; the allowance and fee logic are off-chain in Iris
  judgment: partial
  incidents: partial

exit:
  custody: in_flight_message
  execution: permissionless              # as Standard: anyone calls receiveMessage unless destinationCaller is set
  overrides:
    - who: every override in cctp-v2-standard (Circle not attesting or not re-attesting, the 2-of-2 Circle attester keys, the USDC blacklister on mintRecipient, the proxy admins)
      needs: as in cctp-v2-standard
      how: as in cctp-v2-standard
      reach: one
      bounded: false
      cost: none on-chain
    - who: Circle, as operator of Iris
      needs: one organisation
      how: withhold the fast attestation so the burn waits for finality (delayReason insufficient_fee, amount_above_max or insufficient_allowance_available); this degrades one transfer to Standard timing rather than stopping it
      reach: one
      bounded: true                      # to Standard finality, if Circle then attests at 2000
      cost: none on-chain
  refund_trigger: none
  exit_bound_seconds: [8, 20]            # Circle's published average fast attestation times (8 s on most sources, 20 s from Ethereum and Starknet), plus one destination tx; when the allowance, fee or amount rule isn't met, Standard timing applies ([1, 115200] in cctp-v2-standard)
  exit_bound_chosen_by: Circle           # the depositor asks for Fast with minFinalityThreshold <= 1000 and a maxFee; Iris decides whether the allowance and fee allow it
  standing_approval: upgradeable_target  # as Standard

actors:
  - role: Iris attestation service; attests at the confirmed level (finalityThresholdExecuted 1000), sets feeExecuted up to maxFee, and debits Circle's Fast Transfer allowance
    entity: Circle Internet Group, Inc.
    jurisdiction: [US]
    set: single                          # the same 2-of-2 Circle keys as Standard
    independence: single_org
  - role: Receiver; calls MessageTransmitterV2.receiveMessage on the destination
    entity: anyone, the named destinationCaller, or Circle's Forwarding Service
    jurisdiction: pseudonymous
    set: permissionless
    independence: independent

admin:
  same_as: cctp-v2-standard              # same proxies, roles and holders; one addition below
  immediate_functions_additional:
    - function: TokenMessengerV2.setFeeRecipient
      caller: owner (Ethereum 0x2329baf15f86023e5b0f5592e230d02a51116cd5)
      effect: a Fast mint makes two FiatToken.mint calls, one to feeRecipient (Ethereum 0x6efa3205a385420cf1cfd6b725b48f96117a7bee, an EOA); if that address can't receive USDC (blacklisted), every Fast mint with a non-zero fee reverts

data_gates:
  - kind: Fast Transfer allowance (off-chain)
    where: Iris, before a fast attestation
    trigger: burn amount above the remaining global allowance (53,939,249.82 USDC at 2026-09-28T17:35:38Z per /v2/fastBurn/USDC/allowance), or above a per-transfer maximum (delayReason amount_above_max; value not published)
    blocks_exit: false                   # the transfer falls back to Standard timing; the allowance is credited back as burns reach finality
  - kind: fee
    where: Iris, against maxFee in the burn
    trigger: maxFee below Circle's current Fast fee (0-13 bps by source chain; 1 bps from Ethereum)
    blocks_exit: false                   # falls back to Standard; the burn doesn't revert on-chain (see cctp-v2-standard, Source vs documentation)
  - kind: unfinalized threshold floor
    where: TokenMessengerV2.handleReceiveUnfinalizedMessage (TokenMessengerV2.sol:274-292)
    trigger: finalityThresholdExecuted below 500
    blocks_exit: false                   # Iris only signs 1000 or 2000
  - kind: every gate in cctp-v2-standard (finality for the fallback, expirationBlock, USDC minter allowance)
    where: as in cctp-v2-standard
    trigger: as in cctp-v2-standard
    blocks_exit: true
    reset: unbounded                     # the worst of them, expiry, reopens only when Circle re-attests

judgment:
  same_as: cctp-v2-standard

service:
  same_as: cctp-v2-standard

integration:
  calls:
    - "GET /v2/burn/USDC/fees/{sourceDomain}/{destDomain} for the current Fast fee (bps); optionally GET /v2/fastBurn/USDC/allowance"
    - "USDC.approve(TokenMessengerV2, amount)"
    - "TokenMessengerV2.depositForBurn(..., maxFee >= amount x fee, minFinalityThreshold=1000)"
    - "GET /v2/messages/{sourceDomain}?transactionHash=... until complete; check finalityThresholdExecuted and delayReason"
    - "MessageTransmitterV2.receiveMessage(message, attestation) on the destination, before expirationBlock"
  signatures:
    - as cctp-v2-standard; the upfront-fee path (TokenMessengerWithFees.depositForBurnWithFees) adds a Circle-signed quote passed through by the user, not covered here
  offchain_required:
    - role: Iris API, attestation retrieval (as Standard)
      api_key: false
      rate_limited: true
    - role: Iris fee API, to set maxFee; fees change without notice and Circle says not to hardcode them
      api_key: false
      rate_limited: true
  finisher: anyone                       # as Standard
  gasless_start: none                   # as Standard
  monitoring:
    - as cctp-v2-standard
    - "finalityThresholdExecuted in the attested message (1000 = fast, 2000 = fell back); delayReason while pending"
    - MintAndWithdraw.feeCollected on the destination for the fee actually taken
  deployment_data: as cctp-v2-standard; Fast source chains on /cctp/concepts/supported-chains-and-domains
  sdk: as cctp-v2-standard
  testnet: true
  steps: 5                               # fee lookup, approve, burn, poll, receive

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: delivery
  holder: none
  strike: par
  expiry: none
  early_close: none
  premium: "none; the Fast fee is a maxFee the user signs"
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
    note: "approve, then depositForBurn burns msg.sender's USDC, so the depositor sends it"
  - action: claim
    performer: designated
    paid: atomic
    note: "receiveMessage on the destination by Circle's Forwarding Service, for a fee taken from the transfer; anyone else may call it unpaid"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: burn
    form: self_built
    note: "depositForBurn on TokenMessengerV2"

incidents: []                            # none found specific to Fast; incidents that stop Iris affect both modes (see cctp-v2-standard)

open_questions:
  - "The per-transfer maximum behind delayReason amount_above_max, and how Iris orders transfers competing for the allowance"
  - "Whether a Fast transfer that fell back to Standard is still charged the Fast fee; the reattest API description says the fee is still paid 'since allowance was reserved'"
  - "What Circle does if a source chain reorgs a burn it has already fast-attested; the docs say the allowance mitigates reorg risk, and the mint on the destination stands"
  - "Whether the Fast allowance size (the docs' example is 10 million; 53.9 million at read time) is set by any published rule"
  - "All open questions in cctp-v2-standard apply"
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: evm-cctp-contracts
    url: https://github.com/circlefin/evm-cctp-contracts
    commit: a92a2b4e7e6ef99bf0b05dca71780f5ec190e729
    commit_date: 2026-06-18
    note: "Circle's fees page names commit 7d703109a2cfcb3f76375fef5f1a97f03c447b94 (PR #57) as the TokenMessengerV2 source on Ethereum, Base, Arbitrum and eight other chains; src/v2/TokenMessengerV2.sol and BaseTokenMessenger.sol at that commit were fetched from raw.githubusercontent.com on 2026-09-29 and differ from the pinned commit only by the minFee switch; MessageTransmitterV2, TokenMinterV2, TokenController, Attestable and Denylistable are identical"
---

# Circle CCTP V2 Fast Transfer

**Primitive (one line):** The same burn and mint as `cctp-v2-standard.md`, requested with `minFinalityThreshold` 1000 or lower. Iris signs after soft finality (1-4 blocks) instead of hard finality, takes a fee of up to `maxFee` out of the minted amount, and backs the pre-finality risk with its own global Fast Transfer allowance.

Everything in `cctp-v2-standard.md` applies: no return path once burned, the 2-of-2 Circle attester set, the EOA role holders, the `expirationBlock` and re-attestation, the USDC blacklist on the recipient, the Iris API and its limits. This entry covers what differs.

## Category 1 — Actor-gated edges

**Receive path.** Iris sets `finalityThresholdExecuted` to 1000. `receiveMessage` sends anything below 2000 to `handleReceiveUnfinalizedMessage` (`MessageTransmitterV2.sol:224-233`). That requires at least 500 (`TOKEN_MESSENGER_MIN_FINALITY_THRESHOLD`, `v2/FinalityThresholds.sol`; `TokenMessengerV2.sol:274-292`), then follows the same `_handleReceiveMessage` as Standard. It mints `amount - feeExecuted` to `mintRecipient` and `feeExecuted` to `feeRecipient` in two `FiatToken.mint` calls (`BaseTokenMessenger.sol:330-359`, `TokenMinterV2.sol` `mint`). Both mints must succeed, so a blacklisted `feeRecipient` would stop every Fast mint with a non-zero fee on that chain. That address is Circle's (Ethereum `0x6efa3205...`, an EOA).

**Fee.** Iris chooses `feeExecuted`; the contract only checks `feeExecuted <= maxFee` and `< amount` (`TokenMessengerV2.sol:467-471`). The published Fast fees run from 0 to 13 bps by source chain (1 bps from Ethereum; `/v2/burn/USDC/fees/0/3` returned `minimumFee` 1 for threshold 1000 and 0 for 2000 on 2026-09-29). Circle says excess over the actual fee is "refunded during minting". In source, that just means `feeExecuted` is set below `maxFee`.

**What decides Fast vs Standard.** Iris, off-chain. It attests fast only if `maxFee` covers the fee, the amount is within its per-transfer maximum and the global allowance has room. Otherwise the message waits for hard finality, and `GET /v2/messages` shows `delayReason` `insufficient_fee`, `amount_above_max` or `insufficient_allowance_available` (Circle OpenAPI `DelayReason`). With the Forwarding Service, a `maxFee` too small for both fees makes Circle favour forwarding and run the transfer as Standard (forwarding-service page). So a Fast request is bounded by Standard timing, not stuck, as long as Circle attests at all.

**Can one transfer be singled out?** Everything in the Standard entry. In addition, Circle can hold one transfer to Standard timing by not fast-attesting it. That is bounded by source finality.

## Category 2 — Modification-gated edges (in-window effect)

Same contracts, proxies, role holders and absence of timelocks as `cctp-v2-standard.md`. The one Fast-specific role is `feeRecipient`, set by the TokenMessengerV2 owner with `setFeeRecipient`, with immediate effect.

## Category 3 — Data-oracle-gated edges

- **Fast Transfer allowance.** A single global pool across all chains, debited when a fast burn is attested and credited back when that burn reaches hard finality (fast-transfer-allowance page). It stood at 53,939,249.82 USDC at 2026-09-28T17:35:38Z. It is off-chain Iris state and can't be inspected on-chain. When it is short, transfers fall back to Standard; it doesn't block the exit.
- **Fee.** Same fallback.
- **Soft finality.** Fast attestation waits for 1 block on most sources, 2 on Ethereum, 2-3 on Solana and 4 on Starknet (~8-20 s).
- **Everything in Standard** still applies: `expirationBlock` (a fast attestation also expires about 24 h later, and an expired one can be re-attested), the USDC minter allowance on the destination, and source finality for any fallback.

**Reorg risk.** If the source chain reorgs a burn after a fast attestation, the destination mint has already happened; Circle's allowance is what absorbs the loss. This is Circle's exposure, not the user's.

## Category 4 — Judgment-oracle-gated edges

Same as `cctp-v2-standard.md`: a denylist on burn callers, no screening on the mint in source, an unpublished Iris policy and the USDC blacklist on the recipient. The allowance and fee decisions are made per transfer by Iris without published rules beyond the documented delay reasons.

## Service

Same operator, API and limits as `cctp-v2-standard.md`. Fast also needs the fee endpoint to set `maxFee`. Circle's docs say to re-read fees at least weekly and add a 10-20% buffer.

## Integration

Five steps: read the fee, approve, `depositForBurn` with `minFinalityThreshold` 1000 and a buffered `maxFee`, poll `/v2/messages`, and `receiveMessage`. Check `finalityThresholdExecuted` in the attested message to see whether it went fast. The upfront-fee path (`TokenMessengerWithFees`, a Circle-signed quote, the fee paid on the source in native gas or USDC) lets the recipient get the full amount; it wasn't read in source for this entry.

## Historical incidents

None found specific to Fast. The Standard entry's Iris incidents apply to both modes.

## Composite

**Stuck-leg failure modes:** those of `cctp-v2-standard.md`, plus fallback to Standard timing when the allowance, fee or amount rules aren't met (bounded by source finality), plus a blacklisted `feeRecipient` stopping every fee-bearing Fast mint on a chain.

| Mode | Recovery bound | Basis |
|---|---|---|
| Normal | ~8-20 s + one destination tx | Circle's published fast attestation times |
| Allowance short, fee too low, amount above max | Standard timing | `delayReason`; allowance docs |
| Anything in Standard | as in `cctp-v2-standard.md` | |

## Sources

- `source/evm-cctp-contracts`: `src/v2/TokenMessengerV2.sol` (`handleReceiveUnfinalizedMessage`, `_validatedReceivedMessage`), `src/v2/BaseTokenMessenger.sol` (`_mintAndWithdraw`), `src/v2/TokenMinterV2.sol`, `src/v2/FinalityThresholds.sol`, `src/v2/MessageTransmitterV2.sol`. Read 2026-09-29.
- On-chain, Ethereum, 2026-09-29: TokenMessengerV2 `feeRecipient` and its `eth_getCode`; `minFee()` reverts (no fee switch).
- https://iris-api.circle.com/v2/fastBurn/USDC/allowance and `/v2/burn/USDC/fees/0/3`. Retrieved 2026-09-29.
- https://developers.circle.com markdown of `/cctp/concepts/fast-transfer-allowance`, `/cctp/concepts/fees`, `/cctp/concepts/finality-and-block-confirmations`, `/cctp/concepts/supported-chains-and-domains`, `/cctp/concepts/forwarding-service`, `/cctp/concepts/upfront-fees`, `/cctp/concepts/how-upfront-fees-work`, `/cctp/references/technical-guide`, `/cctp/references/contract-interfaces`, and `/openapi/cctp.yaml` (`DelayReason`, `reattestMessage`). Retrieved 2026-09-29.
- Cited by the earlier version and not re-read: https://6778953.fs1.hubspotusercontent-na1.net/hubfs/6778953/PDFs/Whitepapers/CCTPV2_White_Paper.pdf (CCTP V2 whitepaper). Retrieved 2026-09-16.
- All other sources are listed in `cctp-v2-standard.md`.

## Notes / follow-ups

- Corrections to the earlier entry. It described an "over-collateralization pool"; Circle's docs describe a global allowance that caps unfinalized mints and is credited back at finality, and say nothing of collateral. It said a reorg "could theoretically create inconsistent state" for the user; the mint has already happened, so the exposure is Circle's. It said Fast has "a small on-chain fee". The fee is chosen off-chain by Iris and only capped on-chain by `maxFee`.
- The header uses `same_as` for `admin` and `judgment` as well as `service`, and `immediate_functions_additional` for the one extra role, so shared facts aren't copied. This goes beyond the current header shape and may need reconciling.
- Remaining open questions are in the header.
