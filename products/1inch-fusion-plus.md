---
slug: 1inch-fusion-plus
name: 1inch Fusion+
scope: 1inch Fusion+ cross-chain swap (EscrowSrc, EscrowDst, EscrowFactory, BaseEscrow, TimelocksLib; v1.0 and v1.1), plus the Limit Order Protocol it fills through and the resolver/relayer service in front of it
kind: swap
class: C                                 # the maker has no self-service exit; every path back to a taker-only or access-token-gated third party
cross_chain: true
chains: [Ethereum, Arbitrum, Avalanche, Base, BNB Chain, Gnosis, Linea, Optimism, Polygon, Unichain, Sonic, zkSync Era, Monad, Cronos, HyperEVM, Robinhood]
source_public: true
inherits: []
updated: 2026-10-10
depth: basics                            # scouting pass; see open_questions

verification:
  exit: source-verified                  # EscrowSrc/EscrowDst/BaseEscrow/TimelocksLib/BaseEscrowFactory read; timelock bound confirmed as order-supplied, not protocol-fixed
  actors: partial                        # resolver whitelist mechanism and KYC vendor named from docs, not read on-chain; RES token holder set not confirmed
  admin: source-verified                 # EscrowFactory and Limit Order Protocol owners read on Ethereum mainnet
  data: source-verified                  # no oracle or data gate found in the escrow/factory contracts
  judgment: partial                      # no screening in the escrow contracts; resolver-side compliance is off-chain and unauditable
  incidents: partial                     # two web searches; not a full review

exit:
  custody: escrow                        # EscrowSrc/EscrowDst are deterministic EIP-1167 clones holding the maker's (src) and resolver's (dst) tokens
  execution: discretionary               # withdraw/cancel are onlyCaller(taker) until the public-stage timelock opens; the maker never has a self-service call
  overrides:
    - who: taker (the resolver that filled the order)
      needs: one party
      how: "EscrowSrc.cancel() (onlyCaller(taker), after SrcCancellation) returns the maker's tokens; before that, only the taker can withdraw() on either escrow. If the taker never acts, the maker's funds sit until the public-cancellation stage."
      reach: one
      bounded: true                      # bounded by the SrcPublicCancellation timelock, after which access-token holders can act instead
      cost: forfeits its own safety deposit on that escrow to whoever eventually cancels or withdraws
    - who: holders of the Resolver Access Token (RES, "0xacce550000159e70908c0499a1119d04e7039c28" on Ethereum)
      needs: one holder
      how: EscrowSrc.publicCancel() / EscrowDst.publicWithdraw() after the public-stage timelock; still pay the maker/taker per the immutables, caller collects the safety deposit
      reach: one
      bounded: false                     # nothing on-chain compels any RES holder to act; SECURITY.md documents this as an accepted, unbounded risk
      cost: none on-chain
    - who: taker, via rescueFunds
      needs: one party
      how: "BaseEscrow.rescueFunds() transfers any amount of any token in the escrow to the taker, after RESCUE_DELAY (691200 s / 8 days) from deployment. It doesn't exclude the escrowed funds: if nobody has cancelled by then, the taker can take the maker's tokens. SECURITY.md describes it as recovery of tokens sent by mistake"
      reach: one
      bounded: false                     # the loss is permanent once swept
      cost: none on-chain; the resolver's whitelist slot and reputation
  refund_trigger: timeout
  exit_bound_seconds: unknown            # a number of seconds per stage, packed into the order's Timelocks; no protocol-wide constant found on-chain or in source
  exit_bound_chosen_by: order            # extraDataArgs.timelocks, part of the extension attached when the order is built; the maker signs the order as a whole but SECURITY.md assigns responsibility for the stage values to "whoever builds the order," not the maker independently
  standing_approval: unknown             # maker approval to the Limit Order Protocol could be a standing approve() or a one-shot permit/Permit2 signature; which one wasn't confirmed

actors:
  - role: 1inch's API (relayer); the only channel for the signed order, the only judge (in the SDK flow) of when both escrows are ready, and the only channel for the secret to reach resolvers. Completion needs it; if it stops, the swap can only unwind through the cancellation stages
    entity: 1inch (business.1inch.com); legal entity not confirmed
    jurisdiction: unknown
    set: single
    independence: single_org
  - role: Taker (resolver); only party that can withdraw or cancel during the private stages, and the only party that can rescueFunds
    entity: whitelisted professional resolvers, KYC/KYB-screened by Synaps and wallet/account-screened by TRM Labs per 1inch's resolver onboarding process
    jurisdiction: unknown
    set: whitelist                       # WhitelistRegistry; capped at 10 slots, gated by holding >=5% of total staked-1INCH "Unicorn Power"
    independence: independent            # distinct organisations, admitted under one whitelist/KYC process
  - role: Resolver Access Token (RES) holder; can publicCancel/publicWithdraw once the public-stage timelock opens
    entity: unknown; RES's totalSupply() call reverted on a direct read, so its holder set wasn't confirmed, but the token is purpose-built ("Resolver Access Token") and presumed to sit mostly with resolvers
    jurisdiction: unknown
    set: whitelist                       # gated by holding RES, not open to the general public
    independence: unknown

admin:
  upgradeable: false                     # EscrowSrc/EscrowDst are fixed-implementation EIP-1167 clones with immutable args; EscrowFactory is not behind a proxy (SECURITY.md, "Nothing is upgradeable")
  authority: eoa                         # EscrowFactory owner on Ethereum mainnet ("0x03a25b3215a0e5c15cf23ac4d2e5cf86c0ff7efa"), read on-chain: owner() = "0x0bd61d605c64a857c3d94779aef7ca295702b3a2", eth_getCode on that address returned "0x" (EOA)
  timelock_seconds: none
  immediate_functions:
    - function: EscrowFactory owner's rescueFunds (inherited via SimpleSettlement/FeeTaker)
      caller: factory owner (EOA "0x0bd61d605c64a857c3d94779aef7ca295702b3a2")
      effect: withdraws tokens sent to the EscrowFactory contract itself by mistake; SECURITY.md states it "confers nothing over escrow clones or user funds"
  grandfathered: full                    # each escrow's Immutables, including its Timelocks, are fixed at CREATE2 deployment and unaffected by any later factory change
  outside_exit_path:
    - what: Limit Order Protocol / Aggregation Router V6 ("0x111111125421ca6dc452d289314280a0f8842a65" on Ethereum and most other chains), which EscrowFactory's postInteraction relies on to fill the order that creates EscrowSrc
      effect: its owner() on Ethereum is "0x9f8102b1bb05785bad2874f2c7b1aaea4c6d976a", a Gnosis Safe (v1.3.0) with a 3-of-5 threshold, read on-chain (getThreshold, getOwners); its powers over order filling and fees weren't read in this pass, and its address is not on any escrow's exit path once EscrowSrc/EscrowDst are deployed
      caller: 3 of 5 Safe signers, identities not established

data_gates: []                           # no oracle, price feed, cap or circuit breaker found in EscrowSrc, EscrowDst, BaseEscrow or BaseEscrowFactory

judgment:
  screening: []                          # no blocklist, geo-block or KYC check in the escrow or factory contracts themselves
  freeze_assets: unknown                 # each escrow clone can hold any ERC-20 named in the order, stablecoins included; not enumerated for this pass
  freeze_pooled: false                   # each swap gets its own deterministic escrow address; a freeze would hit one order, not the protocol

service:
  integrator_access:
    api_key: true
    identity: kyc
    revocable: true
    rate_limited: true
    note: "API returned 401 without a key (2026-09-29); keys issued after KYC/KYB on business.1inch.com; Dev tier limits"
  operators:
    - role: "Quoter; supplies every escrow term the maker signs: escrow factory, timelocks, safety deposits, resolver whitelist, auction curve and minimum (auctionEndAmount), fees (quote/receive)"
      entity: 1inch
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: Relayer; receives the signed order (relayer/submit) and runs the Dutch auction among whitelisted resolvers
      entity: 1inch (business.1inch.com); the specific legal entity operating the relayer wasn't confirmed
      single_operator: true
      source_public: false               # no relayer/auction server repository found; only a resolver-side reference contract (1inch/fusion-resolver-example) is public
      deployment_config_public: false
    - role: "Readiness oracle and secret relay; tells the maker which fills are ready for their secret (order/ready-to-accept-secret-fills), takes the secret (relayer/submit/secret), and hands it to resolvers (order/secrets, websocket secret_shared)"
      entity: 1inch
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: Resolver; fills the order on-chain, funds EscrowDst, and later withdraws or cancels both escrows
      entity: whitelisted resolvers (up to 10 slots)
      single_operator: false
      source_public: true                # 1inch/fusion-resolver-example is a public MIT-licensed reference; production resolver implementations are each operator's own
  screening:
    - kind: resolver KYC/KYB (Synaps) and wallet/account screening (TRM Labs), plus a staked-1INCH "Unicorn Power" threshold
      where: off-chain, at admission to the resolver whitelist (WhitelistRegistry)
      in_source: false                   # not in this contracts repo; from 1inch's resolver-onboarding documentation
      enabled_in_production: true
    - kind: "secret release: in the SDK flow, the maker reveals only for fills 1inch's API reports ready, and only to 1inch"
      where: 1inch API (order/ready-to-accept-secret-fills, relayer/submit/secret)
      in_source: false
      enabled_in_production: true        # the API can stall any order by never reporting it ready; the maker then waits for the cancellation stages
  bypass: false                          # the SDK has one channel for the order (relayer/submit) and one for the secret (relayer/submit/secret), both 1inch's, both keyed; no documented way to reach a resolver directly

integration:                             # @1inch/cross-chain-sdk at b2b72a1; see Integration flow
  calls: ["GET quoter/v1.2/quote/receive", "sign the Limit Order Protocol v4 Order (escrow extension hashed into salt)", "POST relayer/v1.2/submit", "poll orders/v1.2/order/ready-to-accept-secret-fills/{orderHash}", "POST relayer/v1.2/submit/secret per ready fill", "GET orders/v1.2/order/status/{orderHash}"]
  signatures: ["EIP-712 Order(uint256 salt,address maker,address receiver,address makerAsset,address takerAsset,uint256 makingAmount,uint256 takingAmount,uint256 makerTraits) on the Limit Order Protocol domain; takerAsset is a TRUE_ERC20 placeholder and the destination terms are in the extension", "optional EIP-2612 permit carried in the extension"]
  offchain_required:
    - role: 1inch Fusion+ API (quoter, relayer, orders) for terms, order submission, readiness and secret relay
      api_key: true
      rate_limited: true
  finisher: user                         # the maker must stay online and reveal each secret through the API; resolvers then withdraw
  gasless_start: [eip2612, permit2_approved, prior_approval]  # makerPermit in the extension (EIP-2612), makerTraits Permit2 flag, or an approval to the Limit Order Protocol (README: "wallet has enough allowance")
  monitoring: "orders/v1.2/order/status (fills[].escrowEvents with tx hashes), websocket"
  sdk: "@1inch/cross-chain-sdk (TypeScript)"
  testnet: unknown
  steps: 5                               # approve or permit, quote, sign and submit, reveal per fill, poll

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: allowlist                      # resolvers holding the Resolver Access Token
  strike: decaying
  expiry: api_chosen
  early_close: none                      # the maker has no self-service call before the public stage
  premium: none
  terms_fixed_by: signature
  price_set_by: decaying_auction
  discipline: allowlist_competition
  surplus_to: holder
  extraction: []
  sides: [exact_in]                      # the quote takes the source amount
  rate: decaying                         # the Dutch auction curve in the extension, down to auctionEndAmount
  quote_validity: unknown
  partial_fill: user_signed              # multiple fills only if the order allows them, with N+1 secrets in a Merkle tree (docs/protocol.md)
  partial_remainder: unknown

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: designated
    paid: unknown
    fee: signed
    note: a resolver fills the signed order and deploys the source escrow; paid by the auction spread the maker signed; whether the maker must first approve the Limit Order Protocol by transaction wasn't confirmed
  - action: release
    performer: user
    paid: none
    score: 0.2
    score_reason: "the maker must stay online, poll 1inch's API and reveal a secret per fill, unpaid; only 1inch's API carries it to resolvers"
    note: "off-chain, no gas; if the maker never reveals, the swap unwinds through cancellation"
  - action: withdraw
    performer: designated
    paid: atomic
    fee: signed
    note: "the taker withdraws EscrowDst (to the maker) and EscrowSrc (to itself) with the secret; in the public stages RES holders may, for the safety deposit"
  - action: cancel
    performer: designated
    paid: atomic
    fee: signed
    note: "publicCancel after the public-stage timelock, by Resolver Access Token holders; the caller collects the resolver's safety deposit"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: Fusion+ order
    form: typed_data
    bounds: bounded
    verifiable_locally: true
    api_optional: false
    score: 0.8
    score_reason: "the wallet shows a placeholder takerAsset and a salt; the destination chain, token, escrow factory, timelocks, deposits and resolver whitelist are in the extension, bound by its hash in the salt. All come from 1inch's quote, and the SDK checks none of them, but a client can decode the extension and check them"
    note: "EIP-712 Limit Order Protocol v4 order signed by the maker"
  - path: secret release
    form: api_signal
    bounds: arbitrary
    verifiable_locally: true
    api_optional: false
    score: 0.2
    score_reason: "the SDK reveals the secret when 1inch's API lists the fill as ready, without reading either escrow. createDstEscrow accepts whatever immutables the resolver passes, so a wrong signal loses the maker's funds. A client can check the escrow tx hashes the API returns on both chains before revealing, but the SDK doesn't, and the secret still goes only to 1inch"

incidents:
  - date: 2025-03-05
    duration: unknown
    funds_lost: true
    exits_blocked: false
    cause: "calldata-corruption vulnerability in the deprecated Fusion v1 _settleOrder Yul code let an attacker impersonate resolvers and drain ~$5M in resolver/market-maker funds, not end-user funds; ~$4.55M returned after negotiation, attacker kept ~$450K as a bounty. In Fusion v1, not the current Fusion+ / cross-chain-swap codebase."
  - date: 2026-05
    duration: unknown
    funds_lost: true
    exits_blocked: false
    cause: "TrustedVolumes, a market maker/resolver used by 1inch Fusion among others, was drained for ~$6.7M in an exploit of its own infrastructure on Ethereum, not of the escrow protocol; Blockaid linked it to the same operator as the March 2025 incident."

open_questions:
  - "Quote: sides, rate, quote_validity, partial_fill, partial_remainder (CRITERIA.md, Trade); these decide which quote modes (exact, atleast, upto) the venue can serve, and who decides a partial fill"
  - "Paid execution, start step: whether the maker must approve the Limit Order Protocol by transaction first, or a permit in the order suffices; if the latter, the resolver is paid atomically from the auction spread"
  - "Whether the Resolver Access Token (RES, 0xacce550000159e70908c0499a1119d04e7039c28) is held only by whitelisted resolvers or more broadly; totalSupply() reverted on a direct read, so its holder set isn't confirmed."
  - "Who the 3 of 5 Gnosis Safe signers behind the Limit Order Protocol owner (0x9f8102b1bb05785bad2874f2c7b1aaea4c6d976a) are, and their jurisdictions."
  - "Whether the Limit Order Protocol / Aggregation Router V6 has a pause or admin function that can affect an order mid-fill; its SimpleSettlement/FeeTaker base (in the limit-order-settlement dependency) isn't vendored in this clone and wasn't read."
  - "Whether the maker's approval to the Limit Order Protocol is a standing ERC-20 approve() or a one-shot Permit2/EIP-2612 signature, which decides the standing_approval fact."
  - "Whether 1inch's API itself checks the destination escrow's immutables and balance before reporting a fill ready, and against what; the relayer's source isn't public."
  - "The current, named list of active resolvers, their jurisdictions, and whether TRM Labs screening is enforced on every fill or only at whitelist admission."
  - "Whether zkSync's separate escrow implementation (EscrowFactoryZkSync.sol, delegatecall-based) changes the exit path; out of scope for this pass."
  - "Rescue delay and factory-owner facts were read on Ethereum mainnet only; other chains' factory owners and RES holders weren't checked."
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: 1inch-fusion-plus
    url: https://github.com/1inch/cross-chain-swap
    commit: 8b806e28ac00d3749886cb05fad7b2826c7fe743
    commit_date: 2026-09-14
  - repo: 1inch-cross-chain-sdk
    url: https://github.com/1inch/cross-chain-sdk
    commit: b2b72a173de7922004cc3171b94a56a8eed30aa9
    commit_date: 2026-09-11
  - repo: 1inch-limit-order-protocol    # the cross-chain-swap submodule commit
    url: https://github.com/1inch/limit-order-protocol
    commit: b655e74665559450ebf3500c2149b805db8ee229
    commit_date: 2025-07-04
  - repo: 1inch-limit-order-settlement  # the cross-chain-swap submodule commit
    url: https://github.com/1inch/limit-order-settlement
    commit: 78a5a68f4814361332e347071513b3d191a630e1
    commit_date: 2025-07-08
---

# 1inch Fusion+

Research for this pass: `contracts/EscrowSrc.sol`, `EscrowDst.sol`, `BaseEscrow.sol`, `BaseEscrowFactory.sol`, `EscrowFactory.sol`, `libraries/TimelocksLib.sol`, `SECURITY.md`, `docs/protocol.md`, `deployments.md` and `deployments/provenance.md` in `source/1inch-fusion-plus`; targeted `eth_call`/`eth_getCode` reads on Ethereum mainnet; and web sources listed below.

## How centralised it is

Fusion+ is described as an atomic swap: two hashlocked escrows, so neither
side can take the other's funds. On-chain that's only half true. The escrows
check one thing, `keccak256(secret) == hashlock` (`SECURITY.md`, "The secret is
distributed off-chain"). Everything that makes the swap fair is decided
off-chain, and in the SDK's flow 1inch's API decides all of it:

1. **The terms.** The quote (`GET quoter/v1.2/quote/receive`) supplies the
   escrow factory, the seven timelocks, both safety deposits, the resolver
   whitelist, the auction curve and its floor (`auctionEndAmount`, the
   minimum the maker gets) and the fees. `Quote.createEvmOrder` copies them
   into the order unchecked. The maker generates only the secrets.
2. **What the wallet shows.** The signed `Order` has `takerAsset` set to a
   placeholder (`TRUE_ERC20`) and a `salt`. The destination chain, token,
   amount curve and every escrow term live in the order's extension, bound
   only by its hash in the low 160 bits of `salt`
   (`OrderLib.isValidExtension`). A wallet prompt shows none of them.
3. **The auction.** The order goes only to 1inch's relayer
   (`POST relayer/v1.2/submit`), which runs the Dutch auction among at most
   10 KYC'd resolvers. Calling it needs a KYC'd API key.
4. **Whether the destination escrow is right.** On the destination chain,
   `createDstEscrow` deploys an escrow from whatever immutables the resolver
   passes: amount, token, maker, hashlock and timelocks. It checks only that
   the native value matches and that the destination cancellation is no later
   than a source-cancellation timestamp the resolver also passes
   (`BaseEscrowFactory.sol:165-185`). Nothing on-chain links it to the order.
   So the only protection is the check the maker makes before revealing.
5. **When to reveal.** The SDK's documented loop (`README.md`, "Secret
   submission") polls `orders/v1.2/order/ready-to-accept-secret-fills/{orderHash}`.
   That returns `{ idx, srcEscrowDeployTxHash, dstEscrowDeployTxHash }` per
   fill, and the loop submits `secrets[idx]` at once. It reads neither escrow.
   **The SDK trusts 1inch's API to say the destination escrow holds the right
   amount for the right recipient.** If the API is wrong, compromised or
   colluding, the maker reveals. The resolver withdraws the source escrow (the
   maker's tokens) and the maker gets whatever the destination escrow holds.
6. **Who gets the secret.** The maker posts it to 1inch
   (`POST relayer/v1.2/submit/secret`). 1inch passes it to resolvers
   (`GET orders/v1.2/order/secrets/{orderHash}`, websocket `secret_shared`).
   There is no documented way to hand it to the resolver directly.
7. **What happens if 1inch stops.** The maker has no on-chain function to
   finish the swap or recover funds. Completion needs the API to carry the
   secret, and recovery needs the taker or an RES holder to cancel (Category 1,
   below).

**A careful client can check step 5 itself,** and should:
- take the two tx hashes;
- on the destination chain, read the `DstEscrowCreated(escrow, hashlock, taker)`
  event and recompute the escrow address from the expected immutables
  (`EscrowFactory.addressOfEscrowDst`, or the SDK's `getDstEscrowAddress`);
- check that the escrow holds at least the fill's amount of the right token,
  for the right maker;
- check that its withdrawal window outlasts the time needed to use it, and
  check the source escrow the same way from `SrcEscrowCreated`, which carries
  the full immutables.

Steps 1 and 2 can be checked by decoding the extension. But the secret still
reaches resolvers only through 1inch, and the order only through 1inch's keyed
API. So Fusion+ is an HTLC whose safety, liveness and access all run through
one operator. The contracts stop a resolver stealing once a correct secret
release has happened; they don't stop a wrong one.

## Category 1 — Actor-gated edges

**Actors on exit path (source-chain refund, the maker's funds):**

The maker has **no on-chain function of their own** to recover escrowed tokens. Every path runs through a third party:

- Taker (the resolver that filled the order): the only address `onlyCaller(immutables.taker.get())` can call `cancel()` on `EscrowSrc` during the private cancellation stage, and the only address that can call `rescueFunds()` after the 8-day `RESCUE_DELAY`. `EscrowSrc.sol` (`cancel`, `withdraw`, `withdrawTo`), `BaseEscrow.sol` (`rescueFunds`, `onlyCaller`).
- Resolver Access Token (RES) holders: any holder of the ERC-20 configured as `_ACCESS_TOKEN` at deployment can call `publicCancel()` on `EscrowSrc` (and `publicWithdraw()` on `EscrowDst`) once the public-stage timelock opens. The caller collects the resolver's safety deposit as an incentive. `EscrowSrc.sol` (`publicCancel`), `BaseEscrow.sol` (`onlyAccessTokenHolder`). On Ethereum this token is deployed at `0xacce550000159e70908c0499a1119d04e7039c28`, named "Resolver Access Token" (symbol RES) on-chain; its `totalSupply()` reverts on a direct call, so how widely it's held wasn't confirmed in this pass.

**Tiered timelock stages**, `TimelocksLib.sol`:

```
SrcWithdrawal -> SrcPublicWithdrawal -> SrcCancellation -> SrcPublicCancellation   (source chain)
DstWithdrawal -> DstPublicWithdrawal -> DstCancellation                            (destination chain)
```

Each stage is a `uint32` number of seconds added to the escrow's deployment timestamp. **The durations are supplied by the order, not fixed by the protocol.** `BaseEscrowFactory._postInteraction` reads them straight out of `extraDataArgs.timelocks` in the order's extension data and stamps on `block.timestamp` at deployment; nothing on-chain checks that the stages are ordered sensibly or that the source and destination schedules line up. `SECURITY.md` calls this out directly: "Those relationships are the responsibility of whoever builds the order" — in practice the order (and its extension) is built when a Fusion+ quote is generated and the maker signs it as a whole, rather than choosing the timelock values independently.

**Worst case:** if the taker never acts and no RES holder calls `publicCancel()`/`publicWithdraw()`, the maker's funds sit in the escrow clone indefinitely. `SECURITY.md`: "Stuck funds are recoverable only by the taker, and only after the rescue delay". `rescueFunds()` (`BaseEscrow.sol`) sends any amount of any token to the taker and doesn't exclude the escrowed funds, so it recovers stuck funds *for the taker*, not the maker: if the escrow is still funded 8 days after deployment, the taker can sweep the maker's tokens. The maker's recovery therefore depends on the taker or an RES holder cancelling within those 8 days.

**Compellability profile:** the taker is a whitelisted, KYC'd resolver (see Service, below) — an identifiable, plausibly compellable party. RES holders are presumed to be resolvers as well, not the general public.

## Category 2 — Modification-gated edges (in-window effect)

**Upgradeability:** none. `EscrowSrc`/`EscrowDst` clones are EIP-1167 minimal proxies over fixed implementations with immutable constructor args; `EscrowFactory` is not behind a proxy. `SECURITY.md`: "There is no way to patch a deployed escrow."

**EscrowFactory owner, read on Ethereum mainnet:** `owner()` on the v1.1 factory (`0x03a25b3215a0e5c15cf23ac4d2e5cf86c0ff7efa`) returns `0x0bd61d605c64a857c3d94779aef7ca295702b3a2`. `eth_getCode` on that address returns `0x` — **it is an externally-owned account, not a multisig.** Its only exposed power, per `SECURITY.md`, is `rescueFunds` on the factory contract itself (tokens sent there by mistake), which has no reach into deployed escrow clones or user funds.

**Limit Order Protocol, outside the escrow exit path but load-bearing for the fill:** `EscrowFactory` fills orders through the Limit Order Protocol / Aggregation Router V6 at `0x111111125421ca6dc452d289314280a0f8842a65` (same address on Ethereum and most other deployed chains, per `deployments/provenance.md`). Its `owner()` on Ethereum returns `0x9f8102b1bb05785bad2874f2c7b1aaea4c6d976a`; `eth_getCode` there is a Gnosis Safe proxy, and `getThreshold()`/`getOwners()` confirm a **3-of-5 Safe** (5 owner addresses returned, `VERSION() = "1.3.0"`). What that Safe can actually change (fees, order-filling logic) wasn't read in this pass; it doesn't sit on an escrow's own exit path once `EscrowSrc`/`EscrowDst` exist.

**Pause mechanism:** none found in `EscrowSrc.sol`, `EscrowDst.sol`, `BaseEscrow.sol` or the factory contracts. A `paused()` call against the Limit Order Protocol returned a zero word, but that contract's dispatcher fallback makes a bare `eth_call` inconclusive without its source (not vendored in this clone); left as an open question rather than asserted.

**Grandfathering:** each escrow's `Immutables` (including its `Timelocks`) are fixed at CREATE2 deployment; nothing about the factory or Limit Order Protocol can change an escrow already deployed.

## Category 3 — Data-oracle-gated edges

None. No Chainlink or other price oracle, no external data dependency, in `EscrowSrc.sol`, `EscrowDst.sol`, `BaseEscrow.sol` or `BaseEscrowFactory.sol`. Pricing is off-chain via the Dutch auction.

## Category 4 — Judgment-oracle-gated edges

No blocklist or screening logic inside the escrow or factory contracts. Since the maker can't self-refund, the practical judgment layer is the taker's (and RES holders') willingness to act, and that is gated off-chain: resolvers go through KYC/KYB with Synaps and wallet/account screening with TRM Labs before they can join the whitelist (1inch resolver-onboarding documentation, not read in source). That compliance posture is opaque from the user's side.

**Stablecoin freeze exposure:** each escrow clone is a distinct deterministic address holding whatever ERC-20 the order names; a stablecoin issuer freeze would hit one order's clone, not the protocol as a whole.

## Service

1inch runs one API with three parts, all behind a KYC'd key: the quoter (all
escrow terms), the relayer (order intake and the Dutch auction) and the orders
service (readiness and secret relay). Their source isn't public; only a
resolver-side reference contract, `1inch/fusion-resolver-example`, is.
Becoming a resolver requires a WhitelistRegistry slot (capped at 10), a stake
of 5% of total "Unicorn Power" (staked 1INCH), and Synaps KYC/KYB plus TRM Labs
wallet screening, all off-chain gates to the whitelist and, implicitly, the
RES access token. The Limit Order Protocol's fill call has no on-chain tie to
the relayer. But the relayer is the only channel for orders, and the orders
service the only channel for secrets, so a maker has no bypass.

## Integration flow

From `@1inch/cross-chain-sdk` (`source/1inch-cross-chain-sdk`, `README.md` and
`src/api/*`). Base URL `https://api.1inch.com/fusion-plus`, every call with an
`authKey` (401 without one, 2026-09-29).

1. **Authorise the token.** Approve the Limit Order Protocol
   (`0x111111125421ca6dc452d289314280a0f8842a65`) on the source chain (the
   README requires an allowance). Alternatively, put an EIP-2612 permit into
   the order (`permit`, carried in the extension as `makerPermit`), or set the
   Permit2 flag if Permit2 is already approved. Only the permit starts with
   no native gas.
2. **Quote:** `GET quoter/v1.2/quote/receive?srcChain&dstChain&srcTokenAddress&dstTokenAddress&amount&walletAddress&enableEstimate`.
   The response carries `presets` (`fast`, `medium`, `slow`; each with its
   auction curve, `auctionEndAmount` and `secretsCount`), `srcEscrowFactory`,
   `timeLocks`, `srcSafetyDeposit`, `dstSafetyDeposit`, the whitelist and
   `quoteId`.
3. **Secrets:** generate `secretsCount` random 32-byte secrets locally. The
   hashlock is `keccak256(secret)` for one fill, or a Merkle root over
   `keccak256(idx, keccak256(secret))` for multiple fills (N parts, N+1
   secrets, `docs/protocol.md`).
4. **Order:** `sdk.createOrder(quote, { walletAddress, hashLock, preset, secretHashes })`
   builds a Limit Order Protocol v4 order with the escrow extension. The maker
   signs
   `Order(uint256 salt,address maker,address receiver,address makerAsset,address takerAsset,uint256 makingAmount,uint256 takingAmount,uint256 makerTraits)`,
   with `takerAsset` the `TRUE_ERC20` placeholder and the extension's hash in
   `salt`.
5. **Submit:** `POST relayer/v1.2/submit` with the order, signature,
   `quoteId`, `srcChainId`, extension and `secretHashes`.
6. **Reveal, per fill:** poll
   `GET orders/v1.2/order/ready-to-accept-secret-fills/{orderHash}`, which
   returns `{ fills: [{ idx, srcEscrowDeployTxHash, dstEscrowDeployTxHash }] }`.
   Verify both escrows (above), then `POST relayer/v1.2/submit/secret` with
   `{ orderHash, secret }`. The maker must stay online for this until the order
   ends.
7. **Status:** `GET orders/v1.2/order/status/{orderHash}` returns `status`
   (ending in `executed`, `expired` or `refunded`), the auction points,
   `approximateTakingAmount`, `positiveSurplus`, and `fills[]`, each with
   `txHash`, filled amounts and `escrowEvents[]` (`transactionHash`,
   `escrow`, `side`, `action`, `blockTimestamp`).

Resolvers then withdraw `EscrowDst` (paying the maker) and `EscrowSrc`
(paying themselves). The first withdrawal publishes the secret on-chain
(`EscrowWithdrawal(secret)`), after which anyone can read it.

## Historical incidents

- 2025-03-05: a calldata-corruption vulnerability in the deprecated Fusion v1 `_settleOrder` Yul code let an attacker impersonate resolvers, draining ~$5M in resolver/market-maker funds. No end-user funds lost; ~$4.55M returned after negotiation, attacker kept ~$450K as a white-hat bounty. This was Fusion v1, not the current Fusion+ / `cross-chain-swap` codebase this entry covers.
- 2026-05: TrustedVolumes, a market maker/resolver used by 1inch Fusion among other protocols, was drained for ~$6.7M in an exploit of its own infrastructure on Ethereum — not of the escrow protocol. Blockaid linked it to the same operator as the March 2025 incident.
- No user-fund losses were found for the current Fusion+ escrow contracts themselves.

## Composite

**Stuck-leg failure modes:**
1. Taker offline or unwilling during the private cancellation stage — bounded by the wait until the public-cancellation stage opens.
2. No RES holder calls `publicCancel()`/`publicWithdraw()` during the public stage — **unbounded**, per `SECURITY.md`'s own accepted-risk framing.
3. Neither side's secret is ever revealed — both escrows' cancellation timelocks eventually open; still gated by who is willing to call `cancel()`.
4. Stablecoin issuer freezes one escrow clone — that order's funds are stuck; unbounded, and doesn't touch other orders.

**Time-to-recovery per mode:**

| Mode | Recovery bound | Basis |
|---|---|---|
| Taker cancels | order-chosen `SrcCancellation` stage duration | `TimelocksLib.sol`, `BaseEscrowFactory._postInteraction` |
| RES holder public-cancels | order-chosen `SrcPublicCancellation` stage duration | `TimelocksLib.sol` |
| No third party acts | unbounded | `SECURITY.md` |
| `rescueFunds` by taker | 691200 s (8 days) after escrow deployment | `BaseEscrow.sol`, `deploy/DeployEscrowFactory.s.sol` |

**Cross-protocol correlation:** a taker's unavailability affects every in-flight order it is resolving simultaneously; a RES-holder shortfall affects every order waiting on the public stage.

## Sources

- `source/1inch-cross-chain-sdk` (pinned in `sources`): `README.md`, `src/sdk/sdk.ts`, `src/api/quoter/quote/quote.ts`, `src/api/relayer/relayer.api.ts`, `src/api/orders/orders.api.ts` and `types.ts`, `src/cross-chain-order/evm/evm-cross-chain-order.ts`, `src/ws-api/types.ts`. Read 2026-10-10.
- `source/1inch-limit-order-protocol` at the cross-chain-swap submodule commit: `contracts/OrderLib.sol` (`isValidExtension`, the order typehash). Read 2026-10-10.
- `source/1inch-fusion-plus` (https://github.com/1inch/cross-chain-swap, pinned in the header's `sources`): `BaseEscrowFactory.createDstEscrow` and `IEscrowFactory` events, read 2026-10-10; `contracts/EscrowSrc.sol`, `contracts/EscrowDst.sol`, `contracts/BaseEscrow.sol`, `contracts/EscrowFactory.sol`, `contracts/BaseEscrowFactory.sol`, `contracts/libraries/TimelocksLib.sol`, `SECURITY.md`, `docs/protocol.md`, `docs/README.md`, `deploy/DeployEscrowFactory.s.sol`, `deployments.md`, `deployments/provenance.md`, `examples/README.md`. Read 2026-09-29.
- Ethereum mainnet, `eth_call`/`eth_getCode` via a public RPC (ethereum-rpc.publicnode.com), 2026-09-29: `EscrowFactory` (`0x03a25b3215a0e5c15cf23ac4d2e5cf86c0ff7efa`) `owner()`; that owner's `eth_getCode`; Limit Order Protocol (`0x111111125421ca6dc452d289314280a0f8842a65`) `owner()`; that owner's `eth_getCode`, `getThreshold()`, `getOwners()`, `VERSION()`; RES token (`0xacce550000159e70908c0499a1119d04e7039c28`) `name()`, `symbol()`, `totalSupply()` (reverted).
- https://help.1inch.com/en/articles/6796085-what-is-1inch-fusion-and-how-does-it-work (2026-09-29) — swap flow, no native gas needed for the maker
- https://help.1inch.com/en/articles/6800254-1inch-fusion-faq (2026-09-29)
- https://business.1inch.com/portal/documentation/resolvers/introduction (2026-09-29) — resolver onboarding: KYC/KYB via Synaps, wallet screening via TRM Labs, Unicorn Power threshold, WhitelistRegistry, 10-slot cap
- https://gov.1inch.io/discussion/12048-1ip33-implement-dynamic-fusion-mode-resolver-whitelist-based-on-unicorn-power-threshold (2026-09-29)
- https://business.1inch.com/portal/documentation (2026-09-29) — API key required, Dev tier limits
- https://github.com/1inch/fusion-resolver-example (2026-09-29) — public reference resolver contract, MIT licensed; not the relayer itself
- https://www.halborn.com/blog/post/explained-the-1inch-hack-march-2025 (2026-09-29)
- https://thedefiant.io/news/defi/1inch-resolver-trustedvolumes-drained-for-usd6-7m-on-ethereum (2026-09-29)

## Notes / follow-ups

- The defining fact is unchanged from the prior pass: the maker has zero direct on-chain recourse, ever. What this pass adds is that the fallback (RES-holder public cancel) is gated to a named, purpose-built access token, not "anyone," and that the factory owner is a plain EOA while the Limit Order Protocol it fills through is owned by a separate 3-of-5 multisig — neither of which reaches a deployed escrow's funds directly, but both are worth tracking if either sits closer to the exit path than this pass found.
- `EscrowFactoryZkSync.sol` uses `delegatecall`-based escrows and wasn't examined; it may warrant a separate entry if zkSync's exit mechanics differ.
