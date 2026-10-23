---
slug: jumper
name: Jumper (LI.FI)
scope: The LI.FI aggregation API and the LI.FI Diamond 0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE (EIP-2535) that users approve; Jumper Exchange is the front end. Each route's risk is the bridge or DEX it uses. LI.FI Intent is a separate entry
kind: aggregator
class: unknown                           # inherits the class of the chosen route
cross_chain: true
chains: unknown                          # 60+ per docs; Diamond read on Ethereum, Arbitrum, Base
source_public: true                      # lifinance/contracts
inherits: []
updated: 2026-10-04

verification:
  service: spec-only
  exit: spec-only
  actors: spec-only
  admin: partial                         # Diamond owner and its timelock read on three chains; facets not reviewed
  data: spec-only
  judgment: spec-only
  incidents: partial

exit:
  custody: user_wallet                   # the Diamond passes funds to the chosen bridge or DEX in the same transaction
  execution: unknown                     # the route's
  overrides: unknown                     # the route's, plus the Diamond's owner (below)
  refund_trigger: unknown
  exit_bound_seconds: unknown
  exit_bound_chosen_by: none
  standing_approval: upgradeable_target  # users approve the Diamond; facets can be added or replaced with diamondCut

actors: unknown

admin:
  upgradeable: true                      # EIP-2535 diamondCut
  authority: multisig                    # owner is a TimelockController; its proposers weren't read
  timelock_seconds: 10800                # TimelockController minDelay on Ethereum (0x55117ecc...), Arbitrum and Base (0x5604a94a...)
  immediate_functions: unknown           # LI.FI documents an emergency pause facet that can remove facets; not read
  grandfathered: none
  outside_exit_path: []

data_gates: unknown

judgment:
  screening: unknown
  freeze_assets: []
  freeze_pooled: false

service:
  integrator_access:
    api_key: false                       # li.quest /v1/quote and /v1/quote/toAmount answered with no key (2026-10-07); whether a key raises limits wasn't read
    identity: unknown
    revocable: unknown
    rate_limited: unknown
  operators:
    - role: LI.FI API (routes and transaction building)
      entity: LI.FI
      single_operator: true
      source_public: false
      deployment_config_public: false
  screening: unknown
  bypass: true

integration:
  calls: ["GET li.quest/v1/quote", "approve the Diamond and send the built transaction", "GET /status"]
  signatures: ["ERC-20 approval (or Permit2) to the Diamond"]
  offchain_required:
    - role: LI.FI API
      api_key: unknown
      rate_limited: unknown
  finisher: unknown
  gasless_start: none
  monitoring: "LI.FI /status by transaction hash"
  sdk: "@lifi/sdk (TypeScript)"
  testnet: unknown
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: inherited
  holder: unknown
  strike: unknown
  expiry: unknown
  early_close: unknown
  premium: none
  terms_fixed_by: calldata
  price_set_by: quote
  discipline: unknown
  surplus_to: user                       # same-chain routes settle atomically to the receiver
  extraction: [public_bound]             # the user sends the built transaction with its slippage bound
  sides: [exact_in, exact_out]           # /v1/quote fixes the input; /v1/quote/toAmount computes the input for a target output, with the floor set just above it (both live 2026-10-07)
  rate: floating_above_bound             # toAmountMin about 0.5% below toAmount by default
  quote_validity: unknown
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: approve the Diamond and send the built transaction
  - action: exit
    performer: none
    paid: none
    inherited: true
    note: the route's

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: LI.FI route
    form: calldata
    bounds: arbitrary
    verifiable_locally: false
    api_optional: false
    target_admin: quorum
    note: "calldata to the LI.FI Diamond, whose facets change through a 3-hour timelock"

incidents:
  - date: "2024-07-16"
    duration: unknown
    user_funds_lost: true
    exits_blocked: false
    cause: "$11.6M drained from 153 wallets with infinite approvals to the Diamond, through call injection in a newly added facet"
  - date: "2022"
    duration: unknown
    user_funds_lost: true
    exits_blocked: false
    cause: "earlier call-injection exploit through a facet"

open_questions:
  - "Trade: holder, strike, expiry, early_close, discipline (CRITERIA.md, Trade)"
  - "Quote: quote_validity (CRITERIA.md, Trade); these decide which quote modes (exact, atleast, upto) the venue can serve, and who decides a partial fill"
  - Who holds PROPOSER and EXECUTOR on the Diamond's timelocks, and whether a CANCELLER exists
  - What the emergency pause facet can do without the timelock
  - Whether the 3-hour delay is long enough for users with standing approvals to revoke
---

# Jumper (LI.FI)

**Primitive (one line):** Bridge and DEX aggregation protocol connecting 20+ bridges and 20+ DEX aggregators across 60+ chains; diamond pattern (EIP-2535) contract allows individual bridge "facets" to be added/updated/disabled; Jumper Exchange is the consumer-facing interface.
**Product scope of this entry:** Jumper Exchange / LI.FI aggregation layer (distinct from LI.FI Intent which is the OIF-based product)

## Custody model

Jumper/LI.FI takes **no custody** — assets move between user wallet and bridge/DEX contracts. The LI.FI diamond proxy contract is the shared approval target. The EIP-2535 diamond pattern allows facets to be upgraded by the owner, which is a significant admin/attack surface.

## Admin surface

Diamond pattern (EIP-2535) allows owner to add, update, or disable facets. This means the owner can introduce new code paths that interact with user approvals. Both exploits (2022 and 2024) were caused by newly added facets.

## Historical incidents

- **2024-07-16: $11.6M exploit.** Shortly after deploying a new facet, attackers executed a "call injection" attack to drain funds from 153 wallets with infinite approvals. USDC, USDT, DAI drained on Ethereum and Arbitrum. LI.FI attributed to "individual human error in overseeing the deployment process." Source: [1]
- **2022: First LI.FI exploit.** Similar call injection pattern through a facet. Exact amount varies by source.
- **Pattern:** both exploits followed the same vector — new facet deployed → call injection → drain approved wallets. The EIP-2535 upgrade capability is the root cause enabling this pattern.

## On-chain state (2026-10-04)

**LI.FI Diamond** `0x1231…4EaE`:
- **Owner:** a TimelockController with `minDelay` 10,800 s (3 hours). It is `0x5511…faee` on Ethereum and `0x5604…4e29` on Arbitrum and Base.
- **Facets:** 41 on Ethereum, 33 on Arbitrum and 34 on Base.

So adding or replacing the code that user approvals point at now waits 3 hours in the timelock. The 2024 exploit came through a newly added facet. Whether that delay existed then wasn't checked.

## Sources

1. Various sources on LI.FI July 2024 exploit ($11.6M, call injection via new facet)
2. https://docs.li.fi/ — LI.FI documentation
- https://github.com/lifinance/contracts — listed in the original protocol index; not yet retrieved

## Notes / follow-ups

- Jumper/LI.FI aggregation is a SEPARATE product from LI.FI Intent (OIF-based). The aggregation layer routes through other bridges; the Intent product uses OIF escrow + The Compact. Different custody models, different risk profiles.
- The diamond proxy upgrade pattern has enabled TWO separate exploits — consider whether infinite approval to this contract is acceptable
