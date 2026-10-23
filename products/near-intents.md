---
slug: near-intents
name: NEAR Intents
scope: The intents.near verifier contract (Defuse) on NEAR mainnet, its internal ledger and role-based admin, and the 1Click / solver-relay services in front. Cross-chain assets enter and leave through the PoA bridge and Chain Signatures, which are separate
kind: settlement
class: B
cross_chain: true
chains: [NEAR]                           # the ledger lives on NEAR; other chains are reached through bridges
source_public: true                      # contract; the 1Click API, solver relay and compliance tooling aren't
inherits: [near-chain-signatures]
updated: 2026-10-07

verification:
  service: spec-only
  exit: source-verified                  # ft_withdraw, ft_force_withdraw, account lock read; roles read on-chain
  actors: source-verified
  admin: source-verified                 # ACL grantees, DAO policy and contract keys read 2026-10-04
  data: source-verified
  judgment: partial                      # screening from docs and an incident report; not in the contract
  incidents: partial

exit:
  custody: escrow                        # tokens held by intents.near against per-account ledger balances
  execution: self                        # ft_withdraw / mt_withdraw / native_withdraw by the account holder at any time
  overrides:
    - who: UnrestrictedAccountLocker, one key (implicit account ac39364a...), also a DAO council member
      needs: one key; no timelock
      parties: key
      how: force_lock_account(user); withdrawals from a locked account fail with AccountLocked. No one holds UnrestrictedAccountUnlocker, so unlocking needs the DAO
      reach: one
      bounded: false
      cost: none on-chain
    - who: DAO, intents.sputnik-dao.near, council of five keys
      needs: 4 of 5 council keys (79% threshold); members not identified
      parties: unknown
      how: ft_force_withdraw / mt_force_withdraw a user's balance to any receiver, force-change their keys, or upgrade the contract
      reach: one
      bounded: false
      cost: none on-chain
    - who: Intents Technology, operator of 1Click and the PoA bridge
      needs: one organisation's decision; no on-chain step
      parties: organisation
      how: "on the 1Click path, decline or delay crediting a deposit sent to its deposit address, or decline a refund: NEAR.com terms make refunds subject to 'compliance review and freezing and/or blocking' and guarantee none; 1Click terms 12.4: no obligation to refund or recover"
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: none                   # nothing to refund on the ledger: the balance is withdrawable. 1Click swaps refund unspent input to a refund address off-chain
  exit_bound_seconds: 0
  exit_bound_chosen_by: none
  standing_approval: none                # deposits are ft_transfer_call; no allowance

actors: []                               # a withdrawal needs only the account holder

admin:
  upgradeable: true
  authority: multisig                    # Sputnik DAO council, 4 of 5, and ctl-intents.near (Aurora controller, administered by the DAO)
  timelock_seconds: none                 # Sputnik proposals execute once the threshold is reached
  immediate_functions:
    - function: upgrade
      caller: Upgrader ctl-intents.near, or the DAO
      effect: arbitrary new code on intents.near
    - function: pause (pa_pause_feature), including ft_withdraw and the other withdraw methods, which carry #[pause]
      caller: any one of six PauseManager keys (five are the DAO council members)
      effect: stops withdrawals for everyone; no one holds UnpauseManager, so unpausing needs the DAO
    - function: force_lock_account
      caller: UnrestrictedAccountLocker (one key) or DAO
      effect: stops one account's withdrawals
    - function: ft_force_withdraw, nft_force_withdraw, mt_force_withdraw
      caller: DAO (no one holds UnrestrictedWithdrawer)
      effect: moves any account's balance to any receiver
    - function: force_add_public_key / force_remove_public_key
      caller: DAO (no one holds UnrestrictedAccountManager)
      effect: takes over an account's signing keys
  grandfathered: none
  outside_exit_path:
    - what: fees, relayer keys (relay-key-manager.near), salts
      effect: happy-path settings

data_gates: []

judgment:
  screening:
    - kind: "address screening of quote requests against NEAR Intents' own AML portal, Binance AML, AMLBot and PureFi, plus TRM Labs on non-dry quotes"
      where: 1Click quote flows (Risk & Compliance page, 2026-10-07); coverage "can vary by flow and integration path"
      status: active
    - kind: "SHIELD policy layer: quote-time allow or delay decisions from incidents, a security mode (normal, paranoid, under_attack) and a rule-based anomaly engine; scoped pauses by chain, token or destination"
      where: 1Click swaps live; bridge paths rolling out; targeting by sender, recipient and deposit address modelled (SHIELD page, 2026-10-07)
      status: active
    - kind: "compliance review, freezing or blocking of refunds and recovery requests"
      where: NEAR.com terms of service (read 2026-10-07)
      status: active                     # a $589K hold reported in 2026 lasted 50+ days; see incidents
  freeze_assets: unknown
  freeze_pooled: true                    # NEAR-side tokens for every account sit at intents.near

service:
  integrator_access:
    api_key: false                       # ORIGIN_CHAIN quotes (with deposit address) and /v0/status answer with no key (2026-10-07), at an extra 25 bps; INTENTS deposits (generate-intent, submit-intent) and the solver relay need partner auth (X-API-Key or JWT)
    identity: none                       # for the keyless path; keys come from the Partner Portal
    revocable: unknown
    rate_limited: unknown
  operators:
    - role: 1Click API and solver relay; quotes, routes deposits, refunds
      entity: NEAR Intents (Defuse Labs)
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: PoA bridge; moves assets between other chains and the ledger
      entity: unknown
      single_operator: true
      source_public: unknown
      deployment_config_public: false
  screening:
    - kind: AML screening (AMLBot, Binance AML, PureFi, TRM Labs)
      where: 1Click quotes, swaps, refunds
      in_source: false
      enabled_in_production: true
  bypass: true                           # signed intents can be submitted to execute_intents directly; cross-chain entry and exit still go through the PoA bridge

integration:
  calls: ["deposit: ft_transfer_call to intents.near, or a 1Click deposit address", "sign a token_diff intent; a solver bundles it into execute_intents", "withdraw: ft_withdraw / mt_withdraw, or a withdraw intent to the PoA bridge"]
  signatures: ["NEP-413 or other supported signed intent payloads"]
  offchain_required:
    - role: 1Click API or solver relay for quotes
      api_key: unknown
      rate_limited: unknown
  finisher: protocol
  gasless_start: [eip3009]               # 1Click deposit addresses: a relayer can deliver an EIP-3009 transfer to the address; other tokens need a transfer with gas
  monitoring: "1Click status endpoint, or intents.near events"
  sdk: unknown
  testnet: unknown
  steps: 3

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: allowlist                      # solvers on the Message Bus, which registers them through the Partner Portal; 1Click picks the quote
  strike: signed
  expiry: user_chosen                    # the deadline in the signed payload
  early_close: none                      # a 1Click deposit can't be withdrawn early; unspent input refunds after the deadline
  premium: none
  terms_fixed_by: signature              # the token_diff intent on the ledger; 1Click deposit addresses rest on the API's quote
  price_set_by: quote
  discipline: allowlist_competition      # the Message Bus forwards each quote request to all connected solvers and waits up to 3000 ms
  surplus_to: split                      # 1Click: a fill better than the quote, within about 30 minutes of issue, is split 50/50 between user and protocol (fees page); on the bare ledger the solver keeps it
  extraction: []
  sides: [exact_in, exact_out]           # 1Click swapType EXACT_INPUT, or EXACT_OUTPUT with the input capped by amountIn (both live 2026-10-07)
  rate: firm                             # token_diff signs exact deltas; fees come from the negative side
  quote_validity: user_chosen            # refunds begin at the deadline in the request; the deposit address itself goes inactive about 3 days later and funds sent after that may be lost
  partial_fill: none                     # a token_diff applies whole
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: deliver
    performer: designated
    paid: atomic
    note: 1Click withdraws the output to the recipient on the destination chain through its bridge, taking withdrawFee from the output
  - action: refund
    performer: designated
    paid: atomic
    note: 1Click refunds unspent input to refundTo on the origin chain after the deadline, taking refundFee (0.30 USDC in a live USDC quote) from the refund; the refund itself is discretionary and subject to compliance freezing (NEAR.com terms), so this rates who pays, not whether it happens
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: "ft_transfer_call to intents.near, or a transfer to a 1Click deposit address"
  - action: withdraw
    performer: user
    paid: none
    gas_on: funds_chain
    note: ft_withdraw from the account needs NEAR gas; whether a solver will carry a signed withdraw intent for a fee wasn't read

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: intent
    form: typed_data
    note: "signed token_diff intent, readable"

incidents:
  - date: "2026-07-20"
    duration: "50+ days (ongoing at 2026-09-11)"
    user_funds_lost: unknown
    exits_blocked: true
    cause: "single-user report (Zcash forum, 2026-09-08; Crypto Times, 2026-09-11, not independently verified): ~$589K USDT sent to a NEAR Intents-generated Ethereum deposit address confirmed on-chain but was never credited; support applied a 'temporary withdrawal restriction', wrote on 2026-07-23 that the review was concluded and funds released, did not execute the refund, and on 2026-08-26 said it was 'paused subject to ongoing standard regulatory compliance reviews' with no date"
  - date: "2026-04-16"
    duration: unknown
    user_funds_lost: false
    exits_blocked: true
    cause: "NEAR Intents and near.com activity paused platform-wide after the ~$7.6M Rhea Finance exploit, 'in accordance with Intents' compliance and transaction monitoring procedures'; the status page said swaps were paused 'to prevent laundering the funds' while a blacklist was awaited (operator post on X, as reported by Crypto Times)"

open_questions:
  - "Who holds DEFAULT_ADMIN_ROLE and PAUSABLE_ADMIN_ROLE on Omni Bridge's EVM contracts, and whether upgrades are timelocked"
  - "Whether Message Bus access (the Partner Portal key) involves screening or KYB, and whether solvers fill intents from accounts funded through Omni rather than 1Click"
  - "Whether any public relayer submits execute_intents for a fee paid from the intent, which would make withdrawals gasless without the operator"
  - "Who holds the keys of 1Click's ORIGIN_CHAIN deposit addresses (a fresh EOA on Ethereum, 0x0E89…81d9, nonce 0): the PoA bridge operator, Chain Signatures, or 1Click itself"
  - "Whether a deposit sent by a contract (for example CoW's settlement contract, as an order's receiver) is credited like any other, and whether refunds still go to refundTo"
  - "Whether keyless quotes are rate-limited, and how hard"
  - "Trade: holder, early_close, discipline (CRITERIA.md, Trade)"
  - Who the five DAO council keys and the sixth PauseManager key belong to
  - What ctl-intents.near (Aurora controller 0.3.3) lets its admins do, and whether it adds a delay
  - Whether the July 2026 hold used force_lock_account or happened off-chain in 1Click / the PoA bridge
  - The PoA bridge's operator, custody and admin
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: near-intents
    url: https://github.com/near/intents
    commit: 72c66887562629d1abc3c1285366b42135d5e501
    commit_date: 2026-09-24
    note: "cloned 2026-09-28; the entry was read on 2026-09-16 at an unrecorded commit, so its line citations need re-checking against this one"
  - repo: omni-bridge                    # sparse: evm/src (OmniBridge.sol initTransfer, roles, pause)
    url: https://github.com/Near-One/omni-bridge
    commit: 3124f85f7b02c45ad4517b059525963d53a7aab9
    commit_date: 2026-09-18
---

# NEAR Intents

**Primitive (one line):** Users deposit tokens into `intents.near` verifier contract (internal ledger); sign token_diff intents declaring desired balance changes; solvers bundle intents into atomic net-zero batches; users withdraw from ledger at any time.
**Product scope of this entry:** NEAR Intents (fka Defuse) on NEAR mainnet (same-chain and cross-chain via Chain Signatures)

## Using 1Click from a gasless account (2026-10-07)

Everything here was checked live against `1click.chaindefuser.com`, read in its
OpenAPI spec (`/docs/v0/openapi.yaml`), or read on docs.near-intents.org
(Fees; Signed Intent Execution; Message Bus API; Token Bridges).

**What needs no key.** `POST /v0/quote` with `depositType: ORIGIN_CHAIN`
returned a real quote and a deposit address, and `GET /v0/status` answered. The
quote is signed by the service, and the docs say to keep it for disputes.
Unauthenticated quotes carry an extra 0.25% fee. With a Partner Portal key the
fee is 0.20%, or 0.01% on stablecoin and same-asset routes. Two things need
partner auth (`X-API-Key` or JWT): signing from a balance already on the ledger
(`depositType: INTENTS`, then `generate-intent` and `submit-intent`), and the
solver relay (Message Bus).

**An EVM key is a ledger account by itself.** The verifier accepts ERC-191
signatures, and the signer's account is its `0x…` address
(`to_implicit_account_id`). `execute_intents` has no caller check beyond the
pause flag, so anyone can submit a signed intent, though the submitter pays
NEAR gas. Withdrawals (`FtWithdraw` and the others) are intents too.

**What the user does, and what pays for itself.**

1. **Start.** The deposit address on the origin chain is a fresh EOA (`0x0E89…81d9`,
   nonce 0). Funds sent there are in the operator's hands until the swap or
   refund. Getting tokens to it is a plain transfer. 1Click doesn't pay for
   that, but anything that can deliver tokens to an address can do it:
   - a relayed EIP-3009 transfer, for USDC;
   - a CoW order with the deposit address as `receiver`;
   - a batch through an EIP-7702 relayer.
2. **Deliver.** 1Click withdraws the output to the recipient through the Omni,
   PoA or HOT bridge, chosen by destination. It takes `withdrawFee` from the
   output, so the user needs nothing on the destination chain.
3. **Refund.** If the swap hasn't happened by the request's deadline, 1Click
   refunds to `refundTo` and takes `refundFee` from the refund. Both are paid in
   kind. Neither is in the user's signature: the quote, which the service
   signs, states them.

**Swap types and quote modes.**
- `EXACT_INPUT` (atleast): a short deposit is refunded, and any excess is
  refunded after the swap.
- `EXACT_OUTPUT` (upto): the output is fixed, `minAmountIn` is the least
  accepted, and unused input is refunded.
- `FLEX_INPUT`: any deposit above `minAmountIn` is swapped, provided
  `minAmountOut` holds. This suits an upstream leg whose output varies, such
  as a CoW order whose surplus isn't known in advance.

Nothing is partly filled: an order swaps whole or refunds.

**Timing.** Refunds begin at the deadline the request sets. The deposit address
goes inactive about three days later, and the docs warn that funds sent after
that "may be lost".

**Price.** Quotes come from solvers on the Message Bus, which forwards each
request to every connected solver for up to 3 seconds. If the fill beats the
quote within about 30 minutes, the improvement is split 50/50 between user and
protocol.

**Who can hold it up.** The AML screening and the $589K, 50-day hold
(Judgment) apply to this path, and the deposit address isn't the user's. The
bridges are separate trust domains, recorded in their own entries where they
exist.

## Paths that avoid 1Click (2026-10-07)

The contract doesn't screen. 1Click, the PoA bridge and the Message Bus do,
and all three are Intents Technology's. Below is each piece a flow needs, and
whether it has a route that avoids that operator.

| Piece | Operator's route | Other route | Who controls the other route |
|---|---|---|---|
| **Onto the ledger** (EVM) | 1Click or PoA deposit address: an EOA the operator holds | Omni Bridge (Ethereum, Base, Arbitrum, BNB, Solana, Bitcoin) | Near One. Deposits are proven by a light client or Wormhole, and anyone can submit the proof. The EVM contract is UUPS-upgradeable and pausable by its admin, with no screening in `OmniBridge.sol` |
| **A counterparty** | Message Bus (`solver-relay-v2`), keyed through the Partner Portal | none in practice | The contract settles any matching signed intents, but quotes and solvers are reached through the Message Bus |
| **Submitting signed intents** | 1Click `submit-intent` or Message Bus `publish_intent` (keyed) | `execute_intents` directly | anyone with a NEAR account and NEAR gas; solvers submit their own bundles |
| **Off the ledger** | PoA bridge withdrawal | Omni Bridge withdrawal | MPC Network signs the release (see near-chain-signatures) |
| **The ledger's own powers** | — | — | on every path: one key can lock an account, the DAO (4 of 5, no delay) can force-withdraw, upgrade or unpause, and six keys can pause |

**What the Omni route needs from a gasless account.**
- **Deposit:** `OmniBridge.initTransfer(token, amount, fee, nativeFee, recipient, message)` takes the tokens from `msg.sender`, after an approval, so the account sends it itself. A relayed EIP-7702 batch can do that; a CoW receiver or EIP-3009 can't. The `fee` is paid in the bridged token to whoever finalises on NEAR, so that leg pays for itself. The deposit names `intents.near` as recipient, with the account's `0x…` id as `receiver_id` in the message.
- **Trading:** this still means reaching solvers through the keyed Message Bus, or knowing a counterparty directly.
- **Withdrawing:** this is an intent someone has to submit. That's either the operator's keyed relay or a NEAR account paying gas.

So the operator's deposit-address custody, where the reported hold happened,
can be avoided. Its say over liquidity and submission can't, short of direct
counterparties and NEAR gas. Neither can the ledger's own admin powers.

## Category 1 — Actor-gated edges

**Actors on exit path (withdrawal from ledger):**
- None required for withdrawal. Users can withdraw from their unlocked ledger balance at any time via direct function call. No timeout, no delay.
- **BUT:** DAO/PauseManager can pause `execute_intents`, and DAO can force-lock accounts — see Category 2.

**Cancellation:** API-based at `/v0/orders/{orderId}/cancel`. Unspent input refunded to refund address. Not an on-chain timeout mechanism.

**Actors in happy path:**
- Solvers: bundle intents into atomic net-zero batches, submit via `execute_intents()`
- NEAR Chain Signatures: threshold signature scheme for cross-chain settlement
- PoA Bridge: cross-chain token transfers (BTC, ETH, SOL to NEAR)

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** DAO or Upgrader role can call `upgrade()` to deploy **arbitrary code** to the contract account. This is the most powerful admin function — it can change all contract logic. Source: [3] `contracts/defuse/src/contract/upgrade.rs:11-29`

**Immediate-effect admin functions:**
- `pause`/`unpause`: PauseManager or DAO can pause `execute_intents` and `simulate_intents`. Source: [3] `contracts/defuse/src/contract/intents/mod.rs:26-27`
- `force_lock_account()`: UnrestrictedAccountLocker or DAO can force-lock any user account, preventing intent execution. Source: [3] `contracts/defuse/src/contract/accounts/force.rs:16-33`
- `force_add_public_key`/`force_remove_public_key`: UnrestrictedAccountManager or DAO can modify any account's keys. Source: [3] `contracts/defuse/src/contract/accounts/force.rs`
- Full access key management: DAO can add/delete full access keys on the contract account itself. Source: [3] `contracts/defuse/src/contract/admin.rs`

**AML/Compliance screening:** Automated compliance via AMLBot, Binance AML, PureFi, TRM Labs on quote flows. This is off-chain enforcement on the fill side.

## Category 3 — Data-oracle-gated edges

**Oracles:** NEAR Chain Signatures (threshold signature by NEAR validators) for cross-chain settlement.

## Category 4 — Judgment-oracle-gated edges (CRITICAL)

### Screening, holds and refunds, from primary sources (2026-10-07)

**Screening runs at quote time and checks addresses.** The Risk & Compliance
page names five sources: NEAR Intents' own AML portal, Binance AML, AMLBot,
PureFi, and TRM Labs (for non-dry quotes). It checks "overlap between addresses
in the request and addresses flagged in external databases", and says coverage
"can vary by flow and integration path".

**SHIELD sits on top, and can target one user.** It is a policy service fed by
incidents from internal operators, partner integrations and an anomaly engine.
- **What's live:** quote-time decisions to allow or delay 1Click swaps, and
  three platform modes: normal; paranoid, which adds delays; and under attack,
  which pauses.
- **Who can trigger it:** producers with the right permission, partners
  included, can pause a single chain, token or destination.
- **What's coming:** controls scoped to a sender, recipient or deposit address
  are modelled and rolling out.

So a hold can come from a sanctions match, an anomaly score, an incident a
partner files, or a platform-wide mode change.

**Refunds aren't promised.** NEAR.com's terms say that when execution fails,
"the Services may attempt to return eligible assets … subject to … compliance
review and freezing and/or blocking", and that Intents Technology "does not
guarantee that any refund will be available, complete, timely, economically
rational, or successful". Recovery help is "voluntary, best-efforts only, may be
refused". It isn't offered at all for user errors under $300, and "generally"
takes 14 days once approved. The 1Click API terms add three things:
- **12.4:** no obligation to "reverse, retry, refund, or recover"; end users
  bear "partial execution, asset loss, or permanent lock-up".
- **7.7(a):** bridged assets "may be held, locked, or controlled" by the PoA
  bridge's validators or authorities.
- **4.2(g):** end users have no rights against Intents Technology.

**Where it bites: the deposit address, not the ledger.** In the reported $589K
case, the funds never reached the ledger. A deposit to an Ethereum deposit
address NEAR Intents had generated confirmed on-chain but was never credited.
The hold then sat in the off-chain service, where the contract's self-withdrawal
doesn't reach. The ledger's own locks (a one-key `force_lock_account`, the
DAO's force-withdraw) are separate and on-chain.

**Two incidents.**
- **The $589K hold, from July 2026.** It's a single user's report that the
  press hasn't verified: cleared in writing, then re-held with no date.
- **The April 2026 platform-wide pause.** It's operator-confirmed. It followed
  an unrelated exploit, "to prevent laundering the funds".

The earlier summary below is kept for history. Its quote about refunds being
frozen comes from the NEAR.com terms, not the 1Click terms.

### Earlier summary (2026-09-16)

**Compliance screening gate — CONFIRMED WITH REAL-WORLD STUCK FUNDS:**
NEAR Intents runs real-time AML screening on quote flows using multiple providers:
- AMLBot
- Binance AML
- PureFi
- TRM Labs

**Screening can block fund flows at the quote stage**, preventing users from executing swaps. More critically, the $589K stuck funds incident (July 2026) demonstrates that compliance holds can be applied AFTER a swap is initiated, with no defined timeline for resolution, and can be re-applied even after initial clearance.

Per NEAR Intents docs ([5]): screening "matches can block quotes." Per terms of service: "refunds and recoveries can be subject to compliance review, freezing, or blocking."

This is a textbook Category 4 judgment-oracle-gated edge — opaque criteria, multiple third-party providers with different rulesets, no on-chain appeal mechanism, and confirmed indefinite holds on user funds.

## Composite

**Stuck-leg failure modes:**
1. DAO upgrades contract with malicious code — all funds at risk. Unbounded.
2. PauseManager pauses operations — **withdrawals stop too:** `ft_withdraw`, `mt_withdraw` and the other withdraw methods carry `#[pause]`. Any one of six keys can pause; only the DAO can unpause. Source: [3] `contract/tokens/nep141/withdraw.rs:25`
3. Account force-locked — **the account can't withdraw:** the withdraw path returns `AccountLocked`. The locker role is one key. Source: [3] `contract/intents/state.rs:181`, `contract/accounts/force.rs:22`
4. PoA bridge failure — cross-chain deposits stuck. Depends on bridge.

## On-chain state (2026-10-04)

Read through `rpc.mainnet.fastnear.com`.

- **Super admins of `intents.near`:** `intents.sputnik-dao.near` and `intents.near` itself.
- **`intents.near` keys:** function-call keys only, nine of them. There is no full-access key.
- **Roles:**
  - DAO: `intents.sputnik-dao.near`.
  - Upgrader: `ctl-intents.near`, an Aurora controller-factory contract (v0.3.3) whose super admins are itself and the DAO.
  - PauseManager: six implicit accounts.
  - UnrestrictedAccountLocker: one implicit account, `ac39364a…`.
  - RelayerKeysManager: `relay-key-manager.near`.
  - Empty: UnpauseManager, UnrestrictedAccountUnlocker, UnrestrictedWithdrawer and UnrestrictedAccountManager hold no one.
- **DAO policy:** the council has five implicit accounts, and every action needs 79% of role weight, which is 4 of 5. The proposal period is 7 days, but a proposal executes as soon as it reaches the threshold, so there is no delay. Five of the six pause managers are council members, and so is the account locker. The sixth pause manager, `c98fb45f…`, isn't.
- **Pause state:** nothing paused.

## Sources

1. https://docs.near-intents.org/near-intents — NEAR Intents docs
2. https://github.com/near/intents — source repo
3. Contract source at `contracts/defuse/src/` — roles (mod.rs:50-70), upgrade (upgrade.rs:11-29), force-lock (accounts/force.rs:16-33), pause (intents/mod.rs:26-27), admin (admin.rs)
4. https://www.cryptotimes.io/2026/09/11/zcash-holder-says-589k-usdt-stuck-on-near-intents-50-days-after-zodl-swap/ — $589K USDT stuck 50+ days after compliance hold
5. https://docs.near-intents.org/security-compliance/risk-and-compliance — NEAR Intents risk & compliance page (AMLBot, Binance AML, PureFi, TRM Labs screening)

## Incident search (2026-09-16)

No **exploits or hacks** found. However, a significant **compliance-related stuck funds incident** was identified:

- **2026-07-20 (ongoing as of 2026-09-11):** A Zcash holder reported $589K USDT frozen after swapping via Zodl and routing through NEAR Intents infrastructure. On July 23, support notified the user that the compliance check had cleared and authorized release — but the payout was never executed. After weeks without resolution, NEAR Intents stated on August 26 that the transaction "remained paused pending a renewed regulatory assessment with no defined deadline." As of September 11, 2026 (50+ days), funds remain stuck. Source: [4][5]
- **Implication:** this confirms that NEAR Intents' AML screening (AMLBot, Binance AML, PureFi, TRM Labs) can indefinitely block user fund flows — even after an initial compliance clearance. The terms of service explicitly state "refunds and recoveries can be subject to compliance review, freezing, or blocking." This is a live Category 4 judgment-oracle-gated edge with confirmed real-world impact.
- Protocol has processed >$10B cumulative volume. Audited by Hacken (Dec 2024). Three active bug bounty programs on HackenProof.

## Notes / follow-ups

- Verify whether withdrawal from unlocked balance is affected by pause or account lock
- The DAO upgrade capability is the dominant risk — equivalent to full custody by DAO keyholders
- >$10B cumulative volume as of 2025
