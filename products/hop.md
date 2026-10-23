---
slug: hop
name: Hop Protocol (V1)
scope: Hop V1 bonder-fronted bridge between Ethereum and its rollups; L1 bridges on Ethereum, L2 bridges, hTokens and AMMs
kind: bridge
cross_chain: true
chains: [Ethereum, Optimism, Arbitrum, Polygon, Base, Gnosis, Linea]   # DefiLlama lists 7 chains; the last two not confirmed
source_public: true
inherits: []                              # the fallback exit is each rollup's canonical bridge
updated: 2026-09-29
depth: basics
status: dormant                           # contracts live, no sunset announced; see Status below

verification:
  exit: spec-only
  actors: spec-only
  admin: partial                          # governance read on-chain for the USDC and ETH L1 bridges
  data: partial
  judgment: unknown
  incidents: partial

exit:
  custody: pooled                         # L1 bridge escrow, hToken AMMs on L2
  execution: permissionless               # without a bonder, a transfer settles through the rollup's canonical message; anyone can relay it
  overrides: unknown
  refund_trigger: none                    # a user can't cancel; the transfer completes by the slow path instead
  exit_bound_seconds: unknown             # the rollup's exit time without a bonder: about 7 days for optimistic rollups
  standing_approval: unknown

actors:
  - role: bonder; fronts liquidity on the destination chain
    entity: unknown
    jurisdiction: unknown
    set: whitelist                        # getIsBonder on the L1 bridge; governance adds and removes bonders
    independence: unknown

admin:
  upgradeable: false                      # no EIP-1967 implementation on the USDC L1 bridge
  authority: multisig
  roles:
    l1_bridge_governance: "Timelock 0x22e3f828b3f47dacfacd875d20bd5cc0879c96e7 (86400 s), for the USDC (0x3666f603cc164936c1b87e207f36beba4ac5f18a) and ETH (0xb8901acb165ed027e32754e0ffe830802919727f) L1 bridges"
    timelock_admin: "0x1ec078551A5ac8F0f51fAc57Ffc48Ea7d9A86E9d, a Safe, 2 of 3 (Etherscan label: Hop Protocol: Future Team Tokens)"
  timelock_seconds: 86400
  immediate_functions: unknown            # functions governance can call, and any pause, not read in source
  grandfathered: unknown
  outside_exit_path: []

data_gates:
  - kind: transfer root challenge period
    where: L1_Bridge challengePeriod
    trigger: every transfer root; 86400 s when read
    blocks_exit: true                     # on the slow path
    reset: bounded

judgment:
  screening: unknown
  freeze_assets: [USDC, USDT]             # among the bridged assets
  freeze_pooled: true                     # held at the L1 bridge address

service:
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: unknown
    note: "contracts can be called directly; the explorer API is down"
  operators:
    - role: bonders and the front end
      entity: unknown
      single_operator: unknown
      source_public: true
  bypass: true                            # the canonical-bridge slow path needs no bonder

integration:
  calls: unknown
  signatures: unknown
  offchain_required: []
  finisher: unknown
  gasless_start: unknown
  monitoring: unknown
  sdk: "@hop-protocol/sdk"
  testnet: unknown
  steps: unknown

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
    paid: unknown
    note: not researched
  - action: settle
    performer: anyone
    paid: unknown
    note: "without a bonder, the canonical message settles it; whether its relayer is paid wasn't read"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: send
    form: self_built

incidents: []                             # none found (2023-2026 searches)

open_questions:
  - "Paid execution, settle step: who may perform it and whether they are paid for it in the same transaction, from the assets in it"
  - "Which functions can governance call on the L1 and L2 bridges, and is there a pause?"
  - "Who are the active bonders, and how many?"
  - "Who are the three signers on the timelock admin Safe?"
  - "Who governs the L2 bridges and AMMs on each rollup?"
  - "How long does the slow path take per rollup, and does anyone have to relay the final message?"
  - "Etherscan's page summary gave governance as 0xf56e3050…, but the on-chain read gave the timelock 0x22e3…; confirm"
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: hop-contracts
    url: https://github.com/hop-protocol/contracts
    commit: 0726ffa0e14745134116e552178fd7e0edcfa8e6
    commit_date: 2025-02-26
    note: "cloned; not yet read"
---

# Hop

A scouting pass that stopped early; this records what it read. The
`hop-contracts` clone was not yet read. On-chain reads on Ethereum on
2026-09-29.

## How it works

A bonder fronts the transfer on the destination chain from its own capital.
User deposits are bundled into transfer roots that settle through the L1
canonical bridges, which restores the bonder's credit. If no bonder acts, the
transfer settles through the canonical bridge after the rollup's exit time
(about 7 days for optimistic rollups). The user can't cancel.

Transfer roots can be challenged within the challenge period (86,400 s when
read on the USDC L1 bridge).

## Governance

The USDC and ETH L1 bridges share one governance address: a timelock with a
24-hour delay, whose admin is a 2-of-3 Safe. The USDC L1 bridge isn't behind
a proxy.

## Status

Checked 2026-09-29. No sunset has been announced, but the protocol looks
dormant:

- TVL (DefiLlama): $3.9M, down from $149M at its peak (2022-04-04), $59M in
  2023-09, $45M in 2024-09 and $9M in 2025-09. Flat at about $3.7M since
  2026-04. $2.85M of it sits on Ethereum.
- On-chain: no events at all from the USDC or ETH L1 bridges in the last
  7,200 blocks (about a day): no transfers to L2 and no transfer roots settled.
- The explorer API returns Cloudflare errors (1016, 530), explorer.hop.exchange
  returns 404 and app.hop.exchange 400; hop.exchange and the docs are up.
- The last commit to the `hop-protocol/hop` monorepo was 2025-10-29.

Bridge volume couldn't be read: DefiLlama's bridge API now needs a paid plan,
and the event history beyond a day needs an archive node.

## Sources

- https://blog.li.fi/hop-protocol-a-deep-dive-5075eddc4dd (2026-09-16)
- https://etherscan.io/address/0x3666f603cc164936c1b87e207f36beba4ac5f18a (2026-09-29)
- https://etherscan.io/address/0x22e3f828b3f47dacfacd875d20bd5cc0879c96e7 (2026-09-29)
- DefiLlama TVL, via web search (2026-09-29)
- https://docs.hop.exchange/ (not yet retrieved)
