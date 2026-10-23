---
slug: bob-gateway-offramp
name: BOB Gateway (X to BTC)
scope: BOB Gateway swaps from tokens to native BTC; USDT is escrowed in GatewayOfframpRegistryV7 0xca79896bcec80aa7628d67c6fac85bdf6ae63b1c on Ethereum (through GatewayRouter and 0x's AllowanceHolder), the solver pays BTC and claims the escrow with an SPV proof against tBTC's LightRelay. Users on other chains reach it through Gateway composer contracts
kind: swap
class: C
cross_chain: true
chains: [Bitcoin, Ethereum, Base, Arbitrum, BSC, Avalanche, Unichain, Robinhood, HyperEVM]   # sources from /v4/get-routes, 2026-10-06
source_public: partial                   # registry, router and relay verified on Blockscout; solver and API not public
inherits: [bob-gateway-onramp]
updated: 2026-10-06

verification:
  service: partial
  exit: source-verified                  # createOrder, refundOrder, finalizeOfframpOrder read from verified source
  actors: source-verified                # owner, solverRecipient, submitters read on-chain
  admin: source-verified
  data: source-verified
  judgment: partial
  incidents: not-reviewed

exit:
  custody: escrow                        # GatewayOfframpRegistryV7 holds the order's USDT (0.2 USDT at read time; 598 orders created)
  execution: discretionary               # the user can neither refund nor submit a proof; refundOrder is onlyOwner
  overrides:
    - who: registry owner EOA 0x1bf42bbf47411d47a6e3368e3b938c09968e4859, which is also the solverRecipient, the protocol-fee recipient and the only authorised proof submitter
      needs: one key
      parties: key
      how: refundOrder(orderId, receiver) sends an active order's whole escrow to any receiver once refundDelay (86400 s) has passed; or never pay the BTC and never refund
      reach: one
      bounded: false
      cost: none on-chain
    - who: anyone able to produce txProofDifficultyFactor blocks of Bitcoin proof-of-work at the current epoch difficulty (factor is 1 today), acting with the authorised submitter
      needs: one party with roughly one block reward of hashpower, plus the owner's submitter key
      parties: organisation
      how: a header chain carrying a payout that never confirmed on Bitcoin's main chain passes LightRelay's work check; finalizeOfframpOrder then pays the escrow to the solver
      reach: one
      bounded: false
      cost: about one Bitcoin block's work per forged proof
  refund_trigger: timeout                # refundOrder after refundDelay, but only the owner can call it
  exit_bound_seconds: unbounded          # no path the user can take; in normal operation the payout lands in minutes and a refund needs the owner after 1 day
  exit_bound_chosen_by: none
  standing_approval: immutable_target    # the user approves 0x's AllowanceHolder (ownerless, allowances transient); GatewayRouter has no owner and leaves no allowance

actors:
  - role: Solver and owner; pays BTC, submits the proof, or refunds
    entity: BOB
    jurisdiction: unknown
    set: single
    independence: single_org

admin:
  upgradeable: false                     # registry, router and relay are not proxies; relay is immutable in the registry
  authority: eoa                         # owner 0x1bf42bbf...4859
  timelock_seconds: none
  immediate_functions:
    - function: refundOrder(orderId, receiver)
      caller: owner EOA
      effect: pays an active order's escrow to any address after refundDelay
    - function: setTxProofDifficultyFactor (1 to 144), setRefundDelay (12 h to 7 days)
      caller: owner EOA
      effect: how much proof-of-work a payout proof needs, and when refunds open
    - function: authorize / deauthorize, setSolver, setOrderSigner
      caller: owner EOA
      effect: who can submit proofs, who is paid, whose signature creates orders
  grandfathered: none
  outside_exit_path:
    - what: pause / unpause
      effect: blocks createOrder only
    - what: setProtocolFee (up to 100% of the escrow, applied at finalise)
      effect: reduces the solver's payout after the user's BTC has been paid
    - what: LightRelay owner (Safe 6 of 9, Threshold / tBTC) and its authorised retargeters
      effect: if the relay stops being updated, proofs fail and orders wait for an owner refund

data_gates:
  - kind: proof-of-work check
    where: LightRelay.validateProof with txProofDifficultyFactor
    trigger: relay not updated to the epoch the payout is in
    blocks_exit: false                   # blocks the solver's claim, not a user path (there is none)
  - kind: refund delay
    where: refundOrder
    trigger: before order.timestamp + refundDelay
    blocks_exit: true
    reset: bounded                       # 86400 s now; settable 12 h to 7 days

judgment:
  screening:
    - kind: TRM Labs screening (3 hops) of the payout address and source
      status: active
    - kind: geo-IP blocking (33 countries including US and UK)
      status: active
  freeze_assets: [USDT]
  freeze_pooled: true                    # every open order's USDT sits in the registry

service:
  same_as: bob-gateway-onramp

integration:
  calls: ["GET /v4/get-quote", "POST /v4/create-order: returns an EVM transaction to AllowanceHolder.exec → GatewayRouter.execute → GatewayOfframpRegistryV7.createOrder", "approve AllowanceHolder and send it", "GET /v4/get-order/{id}"]
  signatures: ["ERC-20 approval to 0x AllowanceHolder; the solver's EIP-712 order signature comes from the API"]
  offchain_required:
    - role: Gateway API (order signature) and solver (payout and proof)
      api_key: optional
      rate_limited: true
  finisher: protocol
  gasless_start: none                   # the user sends the createOrder transaction on the source chain
  monitoring: "GET /v4/get-order/{id}, or OrderCreated / OrderProcessed / OrderRefunded events"
  sdk: "@gobob/bob-sdk (TypeScript); Gateway CLI"
  testnet: unknown
  steps: 3

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: user_writes
  holder: designated                     # the Gateway solver, which is also the registry owner
  strike: signed
  expiry: none                           # refund only after refundDelay, at the owner's call
  early_close: none
  premium: none
  terms_fixed_by: calldata
  price_set_by: quote
  discipline: single_holder
  surplus_to: operator
  extraction: [operator_quote]
  sides: [exact_in]                      # get-quote fixes the token input (live 2026-10-07)
  rate: floating_above_bound             # the order carries satOutputMinimum, signed by BOB's order signer; 100 bps slippage in the quote
  quote_validity: api_chosen             # creationDeadline in the signed order data
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: funds_chain
    note: approve AllowanceHolder and send createOrder
  - action: refund
    performer: designated
    paid: none
    note: refundOrder is onlyOwner and pays its caller nothing; the user can't trigger it

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: createOrder
    form: calldata
    bounds: exact
    verifiable_locally: true
    api_optional: false
    note: "AllowanceHolder.exec → GatewayRouter.execute → registry.createOrder; decodable from public ABIs; router pulls exactly the amount and leaves no allowance; needs the API order signature"

incidents: []                            # not reviewed

open_questions:
  - Who controls owner EOA 0x1bf42bbf...4859; whether BOB intends to move refundOrder to the user or fix the receiver, as the docs describe
  - Why txProofDifficultyFactor is 1 when tBTC's Bridge uses 6 on the same relay, and what order sizes Gateway accepts
  - Whether the composer contracts for other source chains add custody or admin of their own
  - Incident history
sources:
  - repo: bob
    url: https://github.com/bob-collective/bob
    commit: 82fb406a1b8c62a88f1db121b2889655a5b8a59b
    commit_date: 2026-10-01
    note: "SDK (gateway API client), gateway-docs and the Bitcoin relay; the V7/V8 Gateway contracts aren't in it and were read as verified source on Blockscout"
---

# BOB Gateway (X to BTC)

**Primitive (one line):** The user escrows USDT in `GatewayOfframpRegistryV7`, with an EIP-712 order signed by Gateway's order signer. The solver pays BTC to the user's script with an `OP_RETURN` committing to the order, proves it with SPV against tBTC's LightRelay, and is paid the escrow. Otherwise the owner refunds after `refundDelay`.

## The refund path: docs versus contract

The Refunds page says: "The escrow has only two possible destinations, and the contract fixes both: the user, or a solver that has proven on-chain that it already paid the user… the registry owner controls the timing of a refund, not its destination." The Deep Dive says the same.

The deployed contract disagrees. In `GatewayOfframpRegistryV7` (verified source, `src/GatewayOfframpRegistryV7.sol:180-193`):

```solidity
function refundOrder(uint256 orderId, address receiver) external override onlyOwner {
    ...
    require(order.timestamp + refundDelay < block.timestamp, "Funds are still locked");
    ...
    IERC20(order.token).safeTransfer(receiver, amountToUnlock);
```

The owner passes `receiver`. The interface's own NatSpec calls it "a trusted mechanism that allows the contract owner to withdraw and manually refund an order to a user". So the owner, an EOA, can send any active order's escrow anywhere once `refundDelay` (86,400 s at read time) has passed.

The SPV guarantee only binds the solver against itself. The owner is also `solverRecipient`, the protocol-fee recipient and the only authorised proof submitter (`isAuthorized(0x1bf4…) = true`). The same key that is supposed to need a Bitcoin proof can also use `refundOrder` after a day.

## Proof-of-work threshold

`txProofDifficultyFactor` is **1** (allowed range 1 to 144, owner-settable). `LightRelay.validateProof` checks that the headers carry that many blocks' worth of work at the relay's epoch difficulty. It doesn't check that they're on the main chain. A forged payout therefore costs about one block's work, and it also needs the authorised submitter, which is the owner. tBTC's own Bridge (`0x5e48…8e7B`) uses the same relay with `txProofDifficultyFactor() = 6`, read on-chain on 2026-10-06.

## Approvals

The order transaction calls 0x's `AllowanceHolder.exec` (`0x0000…2734`), which calls `GatewayRouter` (`0x559b…b624`, verified, no owner). The router pulls the exact amount, approves the registry for exactly that, and reverts if any allowance or balance is left over. The user's standing approval is to AllowanceHolder, which has no owner and grants allowances only within the user's own transaction.

## On-chain state (Ethereum, 2026-10-06)

- **Registry `0xca79…3b1c`:** not a proxy, not paused.
  - `owner()` = `solverRecipient` = protocol-fee recipient = `0x1bf42bbf…4859`, an EOA. It is the authorised submitter; `0xa932…60db` is not.
  - `orderSigner()` is `0xf118…4fd3`, an EOA.
  - `refundDelay` is 86,400 s and `txProofDifficultyFactor` is 1.
  - `nextOrderId` is 598, and it holds 0.2 USDT.
- **Relay:** `LightRelay` `0x836c…896e` (tBTC's). Its owner is Safe `0x9f6e…2f5f`, 6 of 9, with `authorizationRequired` true and current epoch 481.

## Sources

1. https://docs.gobob.xyz/gateway/technical, /gateway/refunds, /gateway/faq, /gateway/onboarding — retrieved 2026-10-06
2. Verified source from `eth.blockscout.com`: `GatewayOfframpRegistryV7` (`0xca79…`), `GatewayRouter` (`0x559b…`), `LightRelay` (`0x836c…`), 2026-10-06
3. Live API: `/v4/get-quote` and `/v4/create-order` (USDT on Ethereum → BTC; not signed or sent), decoded to find the router and registry; one refused with `NON_COMPLIANT_ADDRESSES`, 2026-10-06
4. eth_call on the registry and relay (`owner`, `orderSigner`, `refundDelay`, `txProofDifficultyFactor`, `relay`, `paused`, `nextOrderId`, `solverRecipient`, `protocolFeeDetails`, `isAuthorized`), 2026-10-06
