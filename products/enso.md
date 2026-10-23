---
slug: enso
name: Enso Shortcuts (same-chain)
scope: Enso's route and bundle API and the EnsoRouter / EnsoShortcuts contracts it targets, for actions on one chain. Cross-chain shortcuts are in enso-xchain
kind: aggregator
cross_chain: false
chains: unknown                           # the router is at the same address on Ethereum, Arbitrum, Base and others
source_public: true                       # contracts; the API and route builder are closed
inherits: []                              # the protocols a shortcut calls
updated: 2026-09-29
depth: basics

verification:
  exit: source-verified                   # EnsoRouter.sol, EnsoShortcuts.sol
  actors: source-verified
  admin: source-verified                  # router has no owner; code present at the deployed address on Ethereum
  data: source-verified
  judgment: partial
  incidents: not-reviewed

exit:
  custody: user_wallet                    # tokens leave the wallet only inside the user's own transaction
  execution: self                         # the user submits the transaction; it succeeds or reverts as a whole
  overrides: []
  refund_trigger: on_failure              # a revert leaves funds in the wallet
  exit_bound_seconds: 0                   # atomic
  standing_approval: immutable_target     # approvals go to EnsoRouter, which has no owner and no proxy

actors: []

admin:
  upgradeable: false
  authority: none
  timelock_seconds: none
  immediate_functions: []
  grandfathered: full
  outside_exit_path:
    - what: the calldata Enso's API returns
      effect: the user signs whatever shortcut the API builds; safeRouteSingle/safeRouteMulti check a minimum amount out at the receiver, routeSingle/routeMulti don't

data_gates: []

judgment:
  screening: []                           # none on-chain; API-side screening unknown
  freeze_assets: none
  freeze_pooled: false

service:
  integrator_access:
    api_key: true
    identity: signup
    revocable: true
    rate_limited: unknown
    note: "API returned 403 without a key (2026-09-29); keys from developers.enso.build; whether that involves KYC is unknown"
  operators:
    - role: route API (builds the shortcut calldata)
      entity: Enso
      single_operator: true
      source_public: false
  screening:
    - kind: API key
      where: api.enso.finance
      in_source: false
      enabled_in_production: true         # an unauthenticated request returns 403
  bypass: true                            # anyone can build weiroll calldata and call the router directly; Enso's API is how a shortcut is normally built

integration:
  calls: [approve, "EnsoRouter.safeRouteSingle or safeRouteMulti"]
  signatures: [approval]
  offchain_required:
    - role: route API
      api_key: true
      rate_limited: unknown
  finisher: user
  gasless_start: none                    # the user sends the transaction
  monitoring: the transaction receipt
  sdk: "@ensofinance/sdk (TypeScript)"
  testnet: unknown
  steps: 3                                # request the route; approve; send

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: spot
  holder: none
  strike: none
  expiry: none
  early_close: none
  premium: none
  terms_fixed_by: calldata
  price_set_by: quote
  discipline: unknown
  surplus_to: user                       # everything the route produces above the minimum reaches the receiver
  extraction: [public_bound]             # the user sends the shortcut with its slippage bound
  sides: [exact_in]                      # tokenIn.amount is pulled; tokenOut.amount is a minimum checked on the receiver's balance (EnsoRouter.safeRouteSingle)
  rate: floating_above_bound
  quote_validity: unknown
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: "approve, then EnsoRouter.safeRouteSingle from the user's account"
  - action: exit
    performer: none
    paid: none
    inherited: true
    note: the route's

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: shortcut
    form: calldata
    bounds: arbitrary
    verifiable_locally: false
    api_optional: false
    target_admin: none
    note: "the API returns weiroll-style shortcut commands that EnsoRouter executes with the user's tokens"

incidents: []

open_questions:
  - "Trade: discipline (CRITERIA.md, Trade)"
  - "Quote: quote_validity (CRITERIA.md, Trade); these decide which quote modes (exact, atleast, upto) the venue can serve, and who decides a partial fill"
  - "Does the API screen addresses or regions?"
  - "Which routes does the API build with routeSingle (no minimum-out check) rather than safeRouteSingle?"
  - "What are the API's rate limits and pricing?"
  - "Incident history not reviewed"
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: enso-shortcuts
    url: https://github.com/EnsoBuild/shortcuts-client-contracts
    commit: 044b3c97eb4af56437eae135b35b4907c0e8e060
    commit_date: 2026-09-28
---

# Enso Shortcuts (same-chain)

Enso's API builds a "shortcut": a weiroll script that calls a series of
protocols. The user sends it through the `EnsoRouter`. Source: the
`enso-shortcuts` clone (`src/router/EnsoRouter.sol`, `src/EnsoShortcuts.sol`),
and on-chain reads on Ethereum on 2026-09-29.

## Exit

The router pulls the user's tokens into `EnsoShortcuts` and runs the script
in the same transaction; if any step reverts, everything reverts and the
tokens never left. `safeRouteSingle` and `safeRouteMulti` also check that the
receiver's balance of the output token rose by at least a minimum.
`EnsoShortcuts.executeShortcut` can only be called by the router.

`EnsoRouter` has no owner, no proxy and no admin functions; it creates its
`EnsoShortcuts` in its constructor. It's deployed at
`0xF75584eF6673aD213a685a1B58Cc0330B8eA22Cf` on Ethereum, Arbitrum and Base.

So on one chain Enso itself holds nothing. The risks are in what the shortcut
calls, and in trusting the API's calldata, which the user signs.

## Service

The route API needs an API key: a request without one returns 403, "API
requests require an API key". The API isn't open source. A shortcut can be
built without it, since the router accepts any weiroll script, but in practice
the API is the route builder.

## Sources

- https://docs.enso.build/ (2026-09-16)
- https://api.enso.finance/api/v1/shortcuts/route, unauthenticated (2026-09-29, 403)
