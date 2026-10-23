# Design implications

## For bonded-execution systems

A protocol that has replaced permissioning with bilateral bonded penalties has a specific exposure that permissioned systems don't face. The bond fires on non-delivery regardless of cause — that's the property that makes the penalty credible and the market functional. It also means an unbounded edge anywhere in the execution path becomes a direct financial loss to the executing party, even when their own execution was correct.

A TEE-attested execution can prove *what happened inside the enclave*. It cannot prove *what happened at the network edge* — an RPC that dropped the tx, an attestation service that refused to sign, a stablecoin issuer that declined to mint. The attestation is truthful and the enclave did its job; the transaction still didn't land, and the bond still fires.

For a bonded system, every edge in the execution path — not just the exit path — must be evaluated at commit time. Any edge whose duration is not bounded by the protocol must either be routed around or explicitly priced into the bond spread.

## Self-insurance trap

Absorbing failure into fees and warehousing reserves against correlated events is the classical insurance model. It is viable but pushes the protocol into de facto custody of user losses, which reintroduces the fiduciary and regulatory posture the underlying design was meant to avoid. Support costs compound this: every stuck-leg incident requires investigation, documentation, and often manual intervention, meaning humans making judgment calls about user funds. This is a regulated financial service in substance regardless of registration status.

The alternative is per-route exposure analysis made visible to the user. Each route's exposure is shown, and the user chooses the criteria a route must meet. Criteria the user chooses can exclude routes whose exposure exceeds what they accept, but the ratings themselves describe and never exclude (CRITERIA.md). The failure modes stay off the operator's balance sheet by construction, because the operator never decides on the user's behalf which risk to take.

## Structural passes worth studying

Two families pass Category 1 by architectural construction:

**IBC and IBC-based protocols.** Every IBC packet carries `timeout_height` and `timeout_timestamp`. Any party can submit a timeout proof after expiry to unwind the packet. Permissionless — no validator, no committee, no operator. Composable MANTIS, Osmosis IBC Hooks, and Union all inherit this property. IBC Eureka extends the same guarantee to Ethereum.

**Signature-only / pull-based flows.** Everything Class A. Funds never leave the user's wallet until the counterparty pulls at fill time. User retains custody by construction; any revocation is trivial.

Both families still require Category 2, 3, and 4 evaluation for the specific implementation.

## Compliance posture inherits from exit-path controller

For Class A and B protocols where the user can self-exit (cancel, timeout refund, nonce invalidation), on-chain compliance gates are the relevant Category 4 surface — if the contracts don't check, there's no gate.

For Class C and D protocols where the user **cannot** self-refund, the compliance posture of whoever controls the exit path IS the compliance posture of the exit itself, regardless of what's in the escrow contracts. A resolver, validator set, or MPC committee that operates closed-source infrastructure is a compliance black box — the user must assume they have screening capability and may refuse to process refunds for compliance reasons. The absence of on-chain compliance logic provides no assurance when the exit requires a third party whose internal processes are opaque and unauditable.

This means Category 4 evaluation for Class C/D protocols should treat the exit-path controller's potential compliance posture as a dependency even when no compliance code is visible in the contracts. The question is not "does the contract check OFAC?" but "can the entity I depend on for my refund refuse to act, for any reason including compliance, with no on-chain override?"

## x402 as a category distinction

x402 is a payment protocol, not an intent-settlement protocol. The payment leg (EIP-3009 signed authorization) passes Category 1 cleanly. But x402 provides no on-chain enforcement on the service side — pay-and-hope for delivery. Different failure surface than intents; the framework applies but only to the payment leg. Multi-chain x402 extensions (Cross402) start to look like intent flows because a facilitator orchestrates settlement across chains; when they do, they inherit the intent-protocol revocability question in full.
