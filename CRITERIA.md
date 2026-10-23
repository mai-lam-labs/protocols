# Evaluation criteria

Each protocol is rated on seven axes, drawn as the seven petals of a rosette. Five
axes come from one test (see `CONSTRAINT.md`): a commitment is safe when its exit
is

> self-executing, time-bounded, non-discretionary, exercisable **by the depositor
> alone**, against **contract state inspectable at commit time**, without requiring
> action from **any actor compellable within the exit window**.

| Petal | Clause of the test | Question |
|---|---|---|
| **Exit path** | self-executing, time-bounded, by the depositor alone | Who can get my funds back, and by when? |
| **Actors** | no actor compellable in the window | Who else has to act, and can they be stopped? |
| **Admin** | state inspectable at commit time | Can the rules change while my funds are in flight? |
| **Data gates** | time-bounded | Can an automatic condition hold my exit shut? |
| **Judgment** | non-discretionary | Can someone refuse me for their own reasons? |
| **Censorship resistance** | (entry, not exit) | Can they decline to serve me at all? |
| **Paid execution** | (every action, start to exit) | Can every step run without me holding gas, because whoever performs it is paid from the assets in it? |

The first five petals rate the **exit path**: how funds come back when things go
wrong. The sixth rates **getting served at all**: whether an operator can refuse
to take a user's order in the first place. A protocol can have a perfect exit
and still let one operator decide whose orders get filled. The seventh rates
**whether each step pays its own way**: whoever starts, cancels, refunds or
claims is paid for doing it in the same transaction, from the assets in that
step. When that holds, anyone can perform the step and the user needs nothing
they don't already hold. How fast the happy path settles is described, not
rated.

**Ranking.** The overview ranks entries in groups:
1. protocols;
2. aggregators;
3. frameworks;
4. deprecated products;
5. entries not yet rated.

An aggregator's own petals (Admin, Censorship resistance, Paid execution) rate
the layer it controls. Its Exit path, Actors, Data gates and Judgment belong to
whichever route it picks. So aggregators are compared only with each other,
and those inherited petals count neither for nor against them. That keeps an
aggregator with two clean petals from outranking a fully rated protocol, and
keeps a well-built aggregator from looking unresearched.

Within a group, complete entries come first (fewest grey petals), then the
mean score of the petals the entry is rated on, so a verified quorum ranks
above one organisation, and that above one key. Which routes an aggregator can
use is listed on its page; the combined risk depends on the routes the
integrator allows.

These ratings describe; they don't exclude. A red petal is information for the
person choosing a route, not a verdict that the protocol is unusable.

## Scores and colours

Every fact gets a **score** from 0 to 1. The score asks one question on every
petal: who, or what, stands between the user and the outcome?

| Score | Anchor | Colour |
|---|---|---|
| 1.0 | no one but you | green |
| 0.8 | someone has to act, but anyone will do; or a delay with a known limit | yellow |
| 0.6 | a quorum of parties shown to be independent | orange |
| 0.4 | a quorum whose independence isn't shown | orange |
| 0.2 | one organisation, even acting through its own multisig | red |
| 0.0 | one key, or unbounded in normal operation | red |
| none | not known | grey |
| inherited | belongs to something the product doesn't control (the route an aggregator picks, the issuer of an asset it holds) | dotted, not scored |

The bands are: green from 0.9, yellow from 0.7, orange from 0.3, red below.
The rosette draws each petal at its score's length, so two oranges can still
be told apart: a verified quorum draws longer than an unverified one.

A petal's score is the **lowest** of its facts' scores. Unknowns count as
follows: a known red stands whatever else is unknown, but any unknown keeps a
petal from showing orange, yellow or green that it hasn't earned.

A quorum earns credit for needing many parties, and loses part of it when
their independence can't be shown. That is the difference between 0.6 and
0.4. One organisation's own multisig is 0.2: several keys, one decision.

The anchors are the defaults. Where an argument is too nuanced for the table,
an entry can score a fact by hand with `score` (0 to 1) and `score_reason`
on that fact. The site shows hand scores as such, with the reason. Use this
sparingly, and prefer adding a row to the table when the same argument
recurs.

For Censorship resistance, which is about being served rather than exiting,
the anchors read: 1.0, no one can refuse you; 0.8, someone can, but only
weakly or in a way you can route around; 0.2, one organisation can refuse you
with no way around; 0.0, a KYC account or nothing at all.

Scores and colours are never written into an entry, except a `score` set by
hand on one fact. Entries record facts with citations; scores are computed
from those facts by the rules below and in `site/scoring.py`. To dispute a
score, dispute the fact or the rule. When the rules change, every entry
re-scores on the next build.

### Who it takes: `parties`

Overrides, admin `immediate_functions` and `data_gates` record who it takes
to act, in the same vocabulary:

| `parties` | Meaning | Score |
|---|---|---|
| `key` | one key | 0.0 |
| `organisation` | one organisation, however many keys | 0.2 |
| `quorum` | several parties must act together; add `independent: true` · `false` · `unknown` | 0.6 if `true`, 0.4 if `unknown`, 0.2 if `false` |
| `unknown` | not known | grey |

Older entries use `one` (one key or one organisation: the text decides,
"one key" or "EOA" scoring 0.0 and anything else 0.2) and `threshold` (read
as `quorum`). Where an entry has no `parties`, the site reads the free text
(`needs`, `caller`) and marks the score as inferred.

## Facts first, model later

The petals, colours and rules on this page are the current model, and they will
change. Entries don't depend on them: an entry records what is true of the
protocol, what it takes to break it, and what isn't known yet. When a discovery
doesn't fit a facet, record it anyway, and adjust the model afterwards.

One lens the model is heading towards separates normal operation from
adversarial conditions, using three adversaries:

- **Chaos monkey**: things break without anyone meaning them to. Operators go
  offline, bots crash, messengers stall.
- **Angry gorilla**: someone with power stops everything. Pauses, halts,
  global freezes.
- **Evil octopus**: someone reaches for particular funds, or coordinates to.
  Colluding quorums, dispute games, targeted overrides, screening.

Which adversary a fact belongs to is worked out from the fact (did someone
mean it; does it reach one user or all; what does it take), not recorded as a
label. A protocol that holds up in normal operation but can be broken by a
colluding quorum doesn't get full marks.

## Exit path

| Facet | Values |
|---|---|
| `custody` | `user_wallet` · `escrow` · `mpc_vault` · `in_flight_message` · `pooled` |
| `execution` | `self` (the depositor acts) · `permissionless` (anyone can trigger it) · `automatic` (protocol rules carry it out; operators run the machine but don't choose per exit) · `discretionary` (a party decides per exit) |
| `overrides` | every known way to hold back one exit without stopping every exit; each with `who`, `needs` (what it takes: one key, one organisation, m of n, a missed dispute), `parties` and `independent` (see Scores and colours), `how`, `reach` (`one` · `all`), `bounded`, `cost`, and optionally `score` / `score_reason`. An empty list means none known |
| `refund_trigger` | `expiry_or_nonce` · `timeout` · `timeout_proof` · `on_failure` (the protocol refunds when the operation fails) · `none` |
| `exit_bound_seconds` | in normal operation: a number, a `[min, max]` range, or `unbounded` |
| `exit_bound_chosen_by` | who picks the bound within the range, if anyone |
| `standing_approval` | `none` · `immutable_target` · `upgradeable_target` |

The question is automation versus discretion. A process that can only be
stopped as a whole is close to neutral: a halt is visible and costly, and
blocking one user means blocking everyone. A party that can single out one exit
is a choke point for each user, and whoever can compel that party can compel
it against that user.

Halts that stop every exit are not rated here. A halt someone decides on is
rated under Admin; one that triggers by itself, under Data gates.

Scores:

| Fact | Score |
|---|---|
| `execution: self` | 1.0 |
| `execution: permissionless` or `automatic` | 0.8 |
| `execution: discretionary` | 0.2 |
| exit bound finite | 1.0 |
| exit bound `unbounded` | 0.0 |
| standing approval none or to an immutable contract | 1.0 |
| standing approval to an upgradeable contract | 0.8 |
| no known overrides | 1.0 |
| each override | by its `parties` (above) |

## Actors

Every actor whose action the exit needs, each rated separately. The petal is
the worst actor; no actors is green.

| Facet | Values |
|---|---|
| `role` | what they do on the exit path |
| `entity` | legal entity, or `pseudonymous` |
| `jurisdiction` | countries, or `pseudonymous` |
| `set` | `single` · `whitelist` · `m_of_n` · `staked` (anyone with a bond or stake) · `permissionless` |
| `independence` | `single_org` · `affiliated` · `independent` |

Scores, per actor; the petal is the lowest:

| Fact | Score |
|---|---|
| no actors | 1.0 |
| `set: permissionless` | 0.8 |
| `staked`, `m_of_n` or `whitelist`, `independence: independent` | 0.6 |
| the same, `independence` unknown | 0.4 |
| `single`, or members `single_org` / `affiliated` | 0.2 |

Record `independence: independent` only when it's shown. "By docs" or "by
name" is `unknown`.

Jurisdictions don't change the colour; they are recorded so users can filter
on them.

## Admin

What an admin, governance or upgrade authority can do to contracts **on the
exit path**. Admin power elsewhere (for example over who may fill orders) goes
in `outside_exit_path`: shown, not rated.

| Facet | Values |
|---|---|
| `upgradeable` | `true` · `false` |
| `authority` | `none` · `eoa` · `multisig` · `dao` · `validators` |
| `timelock_seconds` | a number, or `none` |
| `immediate_functions` | `function`, `caller`, `effect`, and `parties` / `independent`, for each function that affects funds already in flight without a timelock |
| `grandfathered` | do commitments keep their terms across changes? `full` · `partial` · `none` |
| `outside_exit_path` | admin power that can't touch the exit |

Scores:

| Fact | Score |
|---|---|
| not upgradeable | 1.0 |
| upgradeable behind a timelock at least as long as the longest exit bound | 0.8 |
| upgradeable with no timelock, or a shorter one | by `authority`: `eoa` 0.0, `multisig` 0.4, `dao` 0.6, `validators` 0.4, `none` 1.0 |
| each immediate function | by its `parties`; failing that, its `caller` text; failing that, `authority` |

An instant power held only by a quorum that already controls the funds (NEAR
Chain Signatures' participants, say) scores as that quorum, not as one party.

## Data gates

Automatic conditions: rate limits, caps, circuit breakers, finality or
confirmation gating, price feeds, solvency checks. Each gate is recorded
separately.

| Facet | Values |
|---|---|
| `kind` | what sort of gate |
| `where` | the function or decision point |
| `trigger` | the condition that closes it |
| `blocks_exit` | `true` if it gates the exit, `false` if only the happy path |
| `reset` | `bounded` (clears on a known schedule) · `unbounded` |
| `parties` / `independent` | for an unbounded gate, who has to act, or fail together, to hold it shut |

Scores, per gate that blocks the exit:

| Fact | Score |
|---|---|
| no gate blocks the exit | 1.0 |
| `reset: bounded` | 0.8 |
| `reset: unbounded` | by `parties` (who has to act, or fail together, to hold it shut); 0.0 when not recorded |

## Judgment

| Facet | Values |
|---|---|
| `screening` | address screening, blocklists, geo-blocks or KYC on the exit, each with `status: active` or `proposed` |
| `freeze_assets` | issuer-freezable assets that pass through |
| `freeze_pooled` | `true` if those assets are pooled at a shared protocol address |

Whether anyone *can* single out an exit is rated under Exit path. Judgment rates
whether there are rules for doing so: screening is how an override gets used.

Scores:

| Fact | Score |
|---|---|
| no active screening, nothing pooled | 1.0 |
| active screening on the exit | 0.2 |
| freezable assets pooled at a shared address | inherited |

Issuer freezes are the asset's risk, not the protocol's. A freeze of the
user's own wallet comes with holding the asset; a freeze of a shared contract
holding many users' funds is a long-tail event no operator can avoid while
supporting the asset. Both are shown, so the user can weigh the underlying, but
neither is scored against the protocol. The token's own entry (USDC, WBTC,
cbBTC) is where an issuer's freeze power is rated.

`proposed` screening is shown but doesn't change the colour. It is worth
watching: screening that lets operators act on individual addresses turns an
automatic exit into one with an individual override.

A party with an override may already screen in infrastructure no one can
inspect (see `DESIGN_IMPLICATIONS.md`). That is why an override one party can
use is red under Exit path, whether or not any screening is known.

## Censorship resistance

Can they decline to serve me? Everything above asks the custody question: can
I get my funds back? This asks the other one. It reads the `service` facts: who
runs the API or auction an order goes through, whether its source is public,
whether it screens users, what an integrator needs to use it, and whether an
order can be filled without it.

| Facet | Values |
|---|---|
| `operators` | each with `role`, `entity`, `single_operator`, `source_public`, `deployment_config_public` |
| `screening` | each with `kind`, `where`, `in_source`, `enabled_in_production` |
| `bypass` | can an order be filled without the operator? |
| `integrator_access` | what an integrator needs to use the off-chain service, with `api_key` (`true` · `false` · `optional`: works without one, with lower limits), `identity` (`none` · `signup` · `kyc`), `revocable` (can the provider cut off one integrator), `rate_limited` |

Screening refuses a user. Integrator access is the level above: a provider
that issues revocable keys can cut off every user of an integration at once,
and links all of its traffic to one account, without giving a reason. A service
with no key and no account can only throttle or refuse individual requests.

Scores:

| Fact | Score |
|---|---|
| no operator in the path, or a working bypass | 1.0 |
| one operator in the path, no bypass | 0.8 |
| no API key needed | 1.0 |
| API key optional, or required but not revocable | 0.8 |
| revocable API key required | 0.2, or 0.8 with a bypass |
| active screening on the way in | 0.2, or 0.8 with a bypass |
| KYC account required | 0.0, or 0.8 with a bypass |
| any of `api_key`, `identity`, `screening`, `bypass` not established | grey |

**Instruction trust.** The same petal rates how far the user must trust what
the operator's API hands them to sign or send: a misleading instruction is the
other way a service can fail a user. An entry records it as a top-level
`instructions` list, one item per path (`path`, `form`, `bounds`,
`verifiable_locally`, `api_optional`, `target_admin`, `note`):

| Fact | Score |
|---|---|
| `api_optional: true`, or `form: self_built` (built from public contracts and SDK without the API) | 1.0 |
| `form: typed_data`: the user signs readable terms the contract enforces | 1.0 |
| `form: typed_data`, `verifiable_locally: false`: the user signs hashes whose preimages the API doesn't return | 0.4 |
| `form: calldata`, `bounds: bounded` or `exact`, `verifiable_locally: true` | 0.8 |
| the same, not checkable locally | 0.4 |
| `form: calldata`, `bounds: arbitrary`: it can make any call with the user's approval | 0.2 |
| the same, through a contract one key can change (`target_admin: key`) | 0.0 |
| form or bounds not known | grey |

`form: api_signal` records an instruction that isn't a payload but a signal to act, such as an API telling the maker when to release a secret. It has no default score: the entry scores it by hand (`score`, `score_reason`) by what a wrong signal costs and whether the client can check it.

An entry with an operator in its path and no `instructions` recorded is grey.

`bypass` is what turns red into yellow. It has to be real in practice, not
only on-chain: an order a filler will never see isn't served. Values: `true`
(shown to work, for example orders created outside the operator do get
filled), `false`, `unknown`. Anything short of `true`, such as `partial`, counts
as no bypass.

Finer points of the rule:

- A required key that the provider can't revoke scores 0.8. The censorship
  risk in a key is the power to switch it off.
- Screening counts only when `enabled_in_production` is `true`. `proposed` or
  disabled screening doesn't change the score; `unknown` makes it grey.
- With no operator in the path (`operators: []`), there is no service to
  screen, so unknown service screening doesn't make the petal grey.
- Screening on the exit itself (a refund held for review) belongs under
  Judgment; screening on the way in belongs here. A protocol can be red on
  both.

A KYC requirement scores lowest (0.0): it refuses anyone who won't identify.
A revocable key and an active deny-list score 0.2: one lets the provider cut
off a whole integration for any reason, the other refuses a known set of
addresses. The facts keep them apart, so the table can separate them further
without new research.

## Paid execution

Every step of a flow needs someone to perform it: start the order, cancel it,
trigger a refund, claim on the destination. The question is from the
performer's side. Is whoever performs the step guaranteed payment for it,
atomically, in the same transaction, from the assets in the step?

When it is, the performer takes no credit risk and the user prepays nothing.
Performers become interchangeable, because anyone who performs is paid, and the
step happens even when the user holds no native gas. When it isn't, the user
must perform the step themselves with gas they may not have, often on a chain
where their funds aren't.

This is the protocol's own gasless path: a step that pays its performer can
run from an account holding no native gas, without trusting a sponsor. Gas
sponsored by a relayer, a subsidy or an API key is deferred payment and scores
accordingly.

| Facet | Values |
|---|---|
| `actions` | every step the flow can need, each with the fields below; the petal is the worst step |
| `action` | `start` · `cancel` · `refund` · `claim` · `withdraw` · `finalise` · `release`, or another verb |
| `performer` | who may perform it: `anyone` · `designated` (one operator or a permissioned set) · `user` · `none` (nothing needs to be done; it happens on its own) |
| `paid` | how the performer is compensated: `atomic` (in the same transaction, from the assets in the step) · `deferred` (later: a reimbursement, rebate, subsidy, or business relationship) · `none` |
| `fee` | for `atomic`: `signed` if the user's signature pins it (a limit price, a fee field, a cap), `unsigned` otherwise |
| `gas_on` | for `paid: none`: `funds_chain` (the user needs native gas where their funds are) or `other_chain` (gas or a messaging fee somewhere their funds aren't) |
| `inherited` | `true` when the route an aggregator picks decides this step; shown, not scored |
| `note` | what the step is, in the protocol's terms |

| A step… | Score |
|---|---|
| needs no one to do anything | 1.0 |
| pays whoever performs it, atomically, anyone may perform it, and the fee is pinned by the user's signature | 1.0 |
| pays atomically, but only a designated performer may do it, or the fee isn't pinned | 0.8 |
| compensates the performer, but not in the same transaction | 0.4 |
| pays no one, and the user needs native gas where their funds are | 0.2 |
| pays no one, and only a designated party may perform it | 0.2 |
| pays no one, and the user needs gas or fees on a chain where their funds aren't | 0.0 |

**Rate the protocol, not the account.** An EIP-7702 account with a relayer can
pay for almost any step, but that is the account's ability, not the protocol's.
Account-level options are recorded in `GASLESS.md` and the relayer entries.

**Which token the start is rated for.** A protocol's start often depends on the
token: CoW can carry an EIP-2612 permit in a pre-hook, but a token without one
needs an approval transaction first. Rate the `start` step for the best path the
protocol itself offers to a token with both EIP-2612 and EIP-3009, such as
USDC, and record the per-standard detail in `integration.gasless_start`. A protocol that only works after an
approval transaction to its own spender or to Permit2 has a `start` the user
pays for (`paid: none`).

**A step that has to happen for the exit counts,** even if it's rare: a cancel
after expiry, a refund claim, a proof submission. A step that only an operator
performs as part of its own business, like a solver's fill, counts with the
performer and payment it actually has.

## Trade

The petals rate what stands between the user and their funds. They don't say
what trade the user has entered. Almost every commitment here is an options
position. A signed order writes the filler an option: the right, not the
obligation, to fill at the signed price until the deadline, usually for no
premium. A firm quote writes the user one instead. A deposit address hands an
operator an option whose terms only its API knows. The petals are impediments
on managing that position, and the `trade` block records the position itself.
It is described, not rated, until the facts show where a rating belongs
(Facts first, model later).

The block also separates a **market price** from a **bad price**. When a fill is
worse than the user hoped, either the market moved (the risk the user agreed to
when they set the strike and expiry) or the fill was worse than the market at
that moment and someone kept the difference. The second is extraction. The
structure decides how large it can be: who holds the option, who sets the
price, what forces it toward the market, and who keeps the surplus between the
user's bound and the market.

| Facet | Values |
|---|---|
| `structure` | `spot` (atomic, no option) · `user_writes` (the user grants the right to fill) · `counterparty_writes` (a firm quote the user may take) · `mutual` (both sides hold one, as in an HTLC) · `delivery` (same asset across chains: no price risk, only settlement and time) · `authorisation` (the right to pull up to an amount) · `short_vol` (a liquidity provider, short volatility to traders) · `claim` (a wrapped token: a redemption claim on its issuer) · `service` (no trade, a service such as signing) · `inherited` (the route's) |
| `holder` | who holds the option: `anyone` · `allowlist` · `exclusive` (one party, for all or part of the window) · `operator` · `designated` (a party named in the order) · `user` · `none` |
| `strike` | `signed` · `decaying` (moves over the window, as in a Dutch auction) · `quoted` (set by the writer) · `off_chain` (only the API knows it) · `curve` · `par` (one for one) · `none` |
| `expiry` | `user_chosen` · `api_chosen` (set by the API, signed by the user) · `counterparty_chosen` · `contract` (a fixed protocol constant) · `none` |
| `early_close` | can the user close before expiry: `free` · `free_offchain` (an API cancel, trusting the API) · `gas_same_chain` · `gas_other_chain` · `none` |
| `premium` | what the holder pays for the right: `none`, or what it is |
| `terms_fixed_by` | what binds the terms: `signature` · `contract` · `calldata` (whatever an API-built transaction does) · `api` (only the API's word) · `issuer` · `none` |
| `price_set_by` | `user_bound` · `auction` · `decaying_auction` · `quote` · `oracle` · `curve` · `operator` · `par` · `none` |
| `discipline` | what pulls the price toward the market: `open_competition` · `allowlist_competition` · `single_holder` · `oracle_check` · `arbitrage` · `none` |
| `surplus_to` | who keeps the gap between the user's bound and the market: `user` · `holder` · `operator` · `split` · `none` |
| `extraction` | known routes to a bad price: `public_bound` (a slippage bound anyone can sandwich) · `exclusive_window` · `operator_quote` · `last_look` · `unpinned_fee` · `stale_reference` · `arbitrage` (a liquidity provider's loss to arbitrage) |

**The quote.** These decide which quote modes a venue can serve:

| Facet | Values |
|---|---|
| `sides` | which amount the user can fix: `exact_in` (the input, with a floor on the output) · `exact_out` (the output, with a cap on the input) |
| `rate` | `firm` (both amounts fixed when the user signs) · `floating_above_bound` (at or better than the signed bound; who gets the better part is `surplus_to`) · `decaying` (moves along a signed curve) · `curve` (an AMM's) · `par` · `none` |
| `quote_validity` | how long a quote holds before the user must sign: seconds, `api_chosen`, `counterparty_chosen`, `user_chosen` or `none` |
| `partial_fill` | who decides a partial fill: `none` (whole or nothing) · `user_signed` (only if the user's signed order allows it) · `user_chooses` (the user sets the size in their own transaction) · `submitter_chooses` (whoever submits sets the size, and the user's signature doesn't cover it) · `counterparty_chooses` (the payee or filler sets it, within a signed cap) |
| `partial_remainder` | where the unfilled part goes: `in_wallet` (it never left) · `stays_open` (the order can fill further until expiry) · `refunded` · `none` |

| Quote mode | Needs |
|---|---|
| **exact**: both amounts fixed at approval | `rate: firm` |
| **atleast**: input fixed, output floored | `exact_in` in `sides`, with any rate that honours a signed bound |
| **upto**: output fixed, input capped | `exact_out` in `sides` |

Where a layer underneath or on top decides the amounts (a resource lock, an
aggregator's bridge), record `inherited`. **Partial fills decided by someone other than the user** (`submitter_chooses`,
`counterparty_chooses`) break every mode's promise. The user signed for one
outcome and may get a fraction of it, with the rest left to route again. The derived modes carry a `partial by others` flag for these. The build
derives the modes each venue can serve from these facts and shows
them as a filter. A quote that expires before the user can approve it serves
no mode in practice, so `quote_validity` sits beside them.

The free option itself, filling only when the market has moved toward the
holder, comes with every `user_writes` structure. It grows with the expiry and
the asset's volatility, so it isn't listed under `extraction`. A short expiry
and open competition are what shrink it.

## Integration

Recorded, not rated: what an integrator has to build and run. The questions are
in `METHOD.md`.

| Facet | Values |
|---|---|
| `calls` | contract calls, in order |
| `signatures` | what is signed, and by whom (EIP-712 order, permit, Permit2, EIP-3009, approval) |
| `offchain_required` | each service needed, with `role`, `api_key`, `rate_limited` |
| `finisher` | who has to relay, claim, mint or finalise: `protocol` · `integrator` · `anyone` · `user` |
| `gasless_start` | the token standards for which a transfer can start from an account holding no native gas: a list of `eip2612` · `dai_permit` · `eip3009` (a signature alone authorises the pull) · `permit2_approved` (only once the token is approved to Permit2, which takes a transaction) · `prior_approval` (only once approved to the protocol's own spender) · `fee_from_asset` (the source asset pays its own fee, as with BTC); or `none` · `unknown` |
| `monitoring` | what must be watched to learn the outcome |
| `sdk` | SDKs, language, licence |
| `testnet` | whether a testnet deployment exists |
| `steps` | number of distinct steps from start to finished |

## Tokens

A wrapped or pegged token (WBTC, cbBTC, tBTC) is a standing commitment: the
holder's exit is redemption, burning the token for the asset it stands for. The
same petals apply, read for a holder:

- **Exit path**: redemption. Who may redeem (any holder, account holders,
  approved merchants), who carries it out, and the bound on it. A holder who
  can't redeem can only sell, and that goes in `redemption.eligible`, not as
  an exit.
- **Actors**: whoever holds the backing and releases it.
- **Admin**: the token contract: who can mint, upgrade, pause or change roles,
  on each chain it is issued on.
- **Data gates**: redemption minimums, caps, batching windows, timeouts.
- **Judgment**: KYC on minting or redeeming, and the token's blacklist. A
  freeze of the holder's own wallet counts here: it is the asset's own risk,
  recorded once on the token's entry and not repeated on every protocol entry
  the token passes through.

Additional facets, recorded under the token's own headings:

| Facet | Values |
|---|---|
| `backing` | `custodian` · `signer_set` · `escrow`; who holds it, where, and whether the reserve can be checked (on-chain addresses, proof of reserves, attestations) |
| `issuance` | each chain: contract, issued natively or bridged (and by which bridge), mint authority, freeze authority |
| `redemption` | `eligible` (who may redeem), `kyc`, `minimum`, `fee`, `bound_seconds`, `steps` |

A token bridged from another chain (WBTC on Arbitrum, through Arbitrum's
gateway) inherits the token's entry and the bridge's.

## Outside the rosette

**Verification**, per petal: `spec-only` (documentation), `partial` (some of the
exit path read in source), `source-verified` (the exit path read in source and
cited by file and line). Drawn as how solid the petal looks, separately from
the score, which is drawn as its length. Censorship
resistance takes its level from `verification.service`; for it, `partial` means
some facts were tested live against the operator's API, and `source-verified`
means every recorded fact was tested or read in source. Incident history is
`reviewed`, `partial` or `not-reviewed`.

**Incidents**: date, duration, whether user funds were lost, whether exits were
blocked, cause. Shown as a timeline; counts and the longest stuck
duration are computed from it.

**Description**: `kind` (`swap` · `bridge` · `settlement` · `aggregator` ·
`payment`), cross-chain or not, chains, whether source is public, what it
and what it inherits from.

**Aggregators** are rated on what they control: Admin (their router and
approval target) and Censorship resistance (their API's access, screening and
the instructions it hands out). Exit path, Actors, Data gates and Judgment
belong to the route they pick, so those petals are **inherited**: drawn dotted,
not scored, and not counted as missing. Aggregators rank in their own group
(see Ranking). Their pages link to the routes' own
entries.

**Frameworks and standards** (`framework: true`: x402, the OIF settlers,
Wormhole NTT, LayerZero OFT, Hyperlane Warp Routes) describe what every
deployment shares, not what a user meets. An entry for one rates only what the
standard and its reference contracts fix. Anything a deployment chooses
(facilitator, scheme, oracle, owner, DVNs, ISM, order server) is recorded as
unknown, so it shows grey. Frameworks rank after every deployment. A
deployment people actually use (LI.FI Intent on OIF, Stargate on LayerZero, a
named x402 facilitator) gets its own entry, with `inherits` naming the
framework.

**Deprecated products** (`status: deprecated`) are still rated on what is left
on-chain, since funds can still sit there, but they rank after every live
deployment and every framework. Record what was found live in the entry (pool
balances, whether it is paused) so a reader can tell a drained venue from an
abandoned one still holding funds.

## Entry format

Each file in `products/` opens with a YAML header holding the facets above, then
the analysis. Anything not established is `unknown`, with an item in
`open_questions` saying what would settle it.

A protocol whose modes have different exits (a same-chain and a cross-chain
trade, say) gets one entry per mode, so each has one rosette. Facts the modes
share aren't copied: `service: {same_as: <slug>}` points at the entry that
holds them, and `inherits` names it.

References stay loose so they don't break. The header's `sources` list records
which repositories were read and at which commit, at the time of analysis: each
item has `repo` (the clone's directory name), `url`, `commit`, `commit_date` and
an optional `note`. A repository read for two entries is listed in both. Clones
live in `source/<repo>` (not committed). Entries name the repository and file,
adding line numbers only where they help narrow things down. Web sources are
listed by URL with the date they were retrieved.

An entry still in the earlier prose format has a header holding only `sources`.
