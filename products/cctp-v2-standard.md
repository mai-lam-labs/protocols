---
slug: cctp-v2-standard
name: Circle CCTP V2 Standard Transfer
scope: CCTP V2 burn-and-mint of USDC between EVM domains at the finalized threshold (minFinalityThreshold 2000); MessageTransmitterV2, TokenMessengerV2, TokenMinterV2, the USDC token they mint and burn, and Circle's Iris attestation API. Fast Transfer (threshold 1000) is in cctp-v2-fast; TokenMessengerWithFees (upfront fees), CrossChainTokenService (non-USDC assets) and non-EVM domains are not covered
kind: bridge
class: C                                 # no return path once the burn lands; the mint needs Circle's attestation
cross_chain: true
chains: [Ethereum, Avalanche, OP Mainnet, Arbitrum, Solana, Base, Polygon PoS, Aptos, Unichain, Linea, Codex, Sonic, World Chain, Monad, Sei, XDC, HyperEVM, Ink, Plume, Starknet, Arc, Stellar, EDGE, Injective, Morph, Pharos, Cronos, Plasma, X Layer]   # Circle's supported-domains list; only Ethereum (and spot checks on Base and Arbitrum) were read on-chain
source_public: true                      # contracts (Apache-2.0); the Iris attestation service is not public
inherits: []
updated: 2026-09-29

verification:
  service: spec-only                     # Iris is closed; API behaviour from Circle docs and three live unauthenticated calls
  exit: source-verified
  actors: partial                        # attester keys matched to Circle's published keys; who holds them inside Circle is not public
  admin: source-verified                 # every role read on Ethereum; deployed bytecode not compared byte-for-byte with source
  data: source-verified
  judgment: partial                      # contract denylist read; whether Iris screens is not published
  incidents: partial

exit:
  custody: in_flight_message             # USDC is burned on the source chain; the user holds a message that only an attestation can turn into a mint
  execution: permissionless              # anyone can submit message + attestation to receiveMessage unless the depositor set destinationCaller; producing the attestation is Circle's alone (see overrides)
  overrides:
    - who: Circle, as operator of the Iris attestation service
      needs: one organisation; it holds both enabled attester keys (threshold 2 of 2)
      how: never attest the burn, or attest it and decline to re-attest after its expirationBlock (about 24 h) passes. Nothing on the source chain returns burned USDC
      reach: one
      bounded: false
      cost: none on-chain; reputational and legal only
    - who: Circle attester keys, 2 of 2 (0x725b06f7..., 0x52ed4cbf...), both Circle's published Iris keys
      needs: both keys; both held by Circle
      how: sign a message other than the burn (a different mintRecipient or amount, any unused nonce). receiveMessage checks only the signatures, the destination domain, the caller, the version and nonce reuse (MessageTransmitterV2.sol:271-321), not that a matching burn exists
      reach: one
      bounded: false
      cost: none on-chain
    - who: USDC blacklister on the destination chain (Ethereum 0x0a06be16275b95a7d2567fbdae118b36c7da78f9, an EOA)
      needs: one key
      how: blacklist the mintRecipient; FiatToken.mint reverts on notBlacklisted(_to), so receiveMessage reverts and the message stays unreceived (the user's own address; the same power applies to any USDC holder)
      reach: one
      bounded: false
      cost: none on-chain
    - who: Proxy admin of MessageTransmitterV2 (Ethereum 0xb7569e9e..., EOA) or TokenMessengerV2 (Ethereum 0xa820a620..., EOA)
      needs: one key; no timelock
      how: upgradeTo code that rejects a chosen message or nonce
      reach: one
      bounded: false
      cost: none on-chain
  refund_trigger: none                   # no refund, cancel or timeout anywhere in the V2 contracts; expirationBlock only makes the attestation stale
  exit_bound_seconds: [1, 115200]        # Circle's published average attestation times at finalized: ~0.5 s (Aptos, Arc) to 6-32 h (Linea); Ethereum and OP-stack/Arbitrum sources 900-1140 s. Averages, not enforced by anything; plus one destination transaction
  exit_bound_chosen_by: source chain finality and Circle   # the depositor picks the source chain and threshold; Iris decides when it has seen finality
  standing_approval: upgradeable_target  # depositForBurn pulls USDC with transferFrom from msg.sender into TokenMinterV2, on an approval to the TokenMessengerV2 proxy; an exact approval leaves nothing standing

actors:
  - role: Iris attestation service; observes DepositForBurn, waits for finality, fills in nonce, finalityThresholdExecuted, feeExecuted and expirationBlock, and signs the message
    entity: Circle Internet Group, Inc.
    jurisdiction: [US]
    set: single                          # 2 of 2 enabled attester keys on MessageTransmitterV2, both published by Circle at /v2/publicKeys
    independence: single_org
  - role: Receiver; calls MessageTransmitterV2.receiveMessage(message, attestation) on the destination chain
    entity: anyone, or the destinationCaller the depositor named; Circle when the burn carries a cctp-forward hook
    jurisdiction: pseudonymous
    set: permissionless                  # destinationCaller == bytes32(0) lets anyone call (MessageTransmitterV2.sol:300-306); a non-zero destinationCaller makes it that single address
    independence: independent

admin:
  upgradeable: true                      # MessageTransmitterV2 and TokenMessengerV2 are AdminUpgradableProxy; TokenMinterV2 is not a proxy; USDC is a proxy
  authority: eoa                         # every role holder read on Ethereum has no code and no EIP-7702 delegation; internal key custody (HSM, MPC) is not visible
  timelock_seconds: none
  immediate_functions:
    - function: AdminUpgradableProxy.upgradeTo / upgradeToAndCall on MessageTransmitterV2 and TokenMessengerV2
      caller: proxy admins (Ethereum 0xb7569e9eb64eaed5c4166e510b4f6ff54ef42258 and 0xa820a620f638114f3eb45df87382383322ddbc49)
      effect: replaces the code that verifies attestations and mints
    - function: MessageTransmitterV2.pause
      caller: pauser (Ethereum 0x383048265851aa10035bb32b2055632ec4fbb6eb)
      effect: receiveMessage and sendMessage revert; every in-flight mint on that chain waits
    - function: MessageTransmitterV2.enableAttester, disableAttester, setSignatureThreshold
      caller: attesterManager (Ethereum 0xc16b03f84563c1467017c9f7216f8ad6098dc95a)
      effect: changes which signatures mint; attestations already issued stop verifying if their keys are removed or the threshold changes; new keys can sign anything
    - function: MessageTransmitterV2.updateAttesterManager, updatePauser, updateRescuer, setMaxMessageBodySize, transferOwnership
      caller: owner (Ethereum 0xb43aa882f497c0ecb395a5a54f8fa29d12289f65)
      effect: appoints the roles above
    - function: TokenMessengerV2.removeRemoteTokenMessenger, removeLocalMinter
      caller: owner (Ethereum 0x2329baf15f86023e5b0f5592e230d02a51116cd5)
      effect: mints from a source domain (or all) revert with "Remote TokenMessenger unsupported" / "Local minter is not set"
    - function: TokenMinterV2.pause
      caller: pauser (Ethereum 0x4e898cee7c5809a63de0ef745177a9bb82feac69)
      effect: mint and burn revert on that chain
    - function: TokenMinterV2.unlinkTokenPair
      caller: tokenController (Ethereum 0x740f494cd63f87547fec1591646720e5cc285846)
      effect: mints of a source domain's USDC revert with "Mint token not supported"
    - function: TokenMinterV2.removeLocalTokenMessenger, setTokenController, updatePauser
      caller: owner (Ethereum 0x7d1565698cddf4c8f90d6b8574729fef565cae0e)
      effect: stops all mints, or appoints the roles above
    - function: USDC pause, blacklist, configureMinter/removeMinter (via MasterMinter), proxy upgrade
      caller: USDC pauser 0x4914f61d..., blacklister 0x0a06be16..., MasterMinter 0xe982615d... (contract, owner EOA 0xc1d9fe41...), proxy admin 0x807a9628... (Ethereum)
      effect: the mint is FiatToken.mint called by TokenMinterV2; pause or removing TokenMinterV2 as a minter stops every mint; blacklisting a recipient stops one
  grandfathered: none                    # the mint runs under the attester set, pause state, remote messengers, token links and code at the time it is received
  outside_exit_path:
    - what: TokenMessengerV2 denylist (denylist / unDenylist by denylister, Ethereum 0xbed4b046f7d185d730e9930b2bcddc86eb3cfbc9)
      effect: depositForBurn reverts for a listed msg.sender or tx.origin; blocks starting a transfer, not receiving one
      caller: denylister
    - what: TokenMinterV2.setMaxBurnAmountPerMessage, TokenMessengerV2.addRemoteTokenMessenger, setFeeRecipient, MessageTransmitterV2 maxMessageBodySize
      effect: burn-side limits and configuration
      caller: tokenController, owners
    - what: rescueERC20 on all three contracts
      effect: moves tokens held by the contract; in-flight USDC is burned, not held
      caller: rescuers (Ethereum MT 0x53d81df7..., TM 0x070b2a0c..., TMin 0xe206be23...)

data_gates:
  - kind: source finality
    where: Iris, before signing (minFinalityThreshold 2000)
    trigger: burn not yet final on the source chain by Circle's rule (~65 Ethereum blocks for Ethereum and L2s settling to it)
    blocks_exit: true
    reset: bounded                       # clears when the source finalizes; a source-chain finality halt holds it (Linea, September 2026, about 2.3 days)
  - kind: attestation expiry
    where: TokenMessengerV2._validatedReceivedMessage (TokenMessengerV2.sol:460-465)
    trigger: block.number >= expirationBlock, set by Iris about 24 h after attestation (on Arbitrum-stack destinations, an L1 block number)
    blocks_exit: true
    reset: unbounded                     # reopens only when Circle re-attests on POST /v2/reattest/{nonce}; Circle's docs say there is no deadline for that
  - kind: minter allowance
    where: FiatToken.mint (minterAllowed[TokenMinterV2]) on the destination
    trigger: remaining allowance below the amount (Ethereum 330,877,915.09 USDC at read time)
    blocks_exit: true
    reset: unknown                       # topped up by Circle's minter controller; schedule not published
  - kind: per-message burn limit
    where: TokenController.onlyWithinBurnLimit on TokenMinterV2.burn
    trigger: amount > burnLimitsPerMessage[USDC] (Ethereum 10,000,000 USDC)
    blocks_exit: false                   # the burn reverts and the user keeps the USDC
  - kind: message body size
    where: MessageTransmitterV2.sendMessage
    trigger: messageBody longer than maxMessageBodySize (Ethereum 8192 bytes)
    blocks_exit: false

judgment:
  screening:
    - what: TokenMessengerV2 denylist on msg.sender and tx.origin
      where: depositForBurn, depositForBurnWithHook (Denylistable.notDenylistedCallers)
      status: active                     # deployed and a denylister is set on Ethereum, Base and Arbitrum; which addresses are listed was not read (needs an event scan)
      on_exit: false                     # the mint side has no denylist check
    - what: Iris attestation policy
      where: Circle's attestation service
      status: unknown                    # Circle publishes no rule for declining to attest
  freeze_assets: [USDC]
  freeze_pooled: false                   # USDC is burned, not pooled; blacklisting TokenMinterV2 (the minter) or removing it as a minter would stop every burn and mint on that chain

service:
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: true
    note: "Iris needs no key; 40 requests/s, over that a 5-minute block"
  operators:
    - role: Iris attestation service and API (iris-api.circle.com); signs every message and serves attestations, fees, allowance and re-attestation
      entity: Circle Internet Group, Inc.
      single_operator: true
      source_public: false
      deployment_config_public: false
    - role: Circle Forwarding Service (optional); submits receiveMessage on the destination for burns carrying a cctp-forward hook, for a fee
      entity: Circle Internet Group, Inc.
      single_operator: true
      source_public: false
      deployment_config_public: false
  screening:
    - kind: denylist
      where: TokenMessengerV2.depositForBurn
      in_source: true
      enabled_in_production: true        # denylister set; contents unknown
    - kind: attestation refusal
      where: Iris
      in_source: false
      enabled_in_production: unknown
  bypass: false                          # no mint without signatures from the enabled attesters, both Circle's; the API can be bypassed only by receiving an attestation some other way from Circle

integration:
  calls:
    - "USDC.approve(TokenMessengerV2, amount) on the source chain"
    - "TokenMessengerV2.depositForBurn(amount, destinationDomain, mintRecipient, burnToken, destinationCaller, maxFee, minFinalityThreshold=2000), or depositForBurnWithHook(..., hookData)"
    - "GET https://iris-api.circle.com/v2/messages/{sourceDomain}?transactionHash=... until status is complete; returns message and attestation"
    - "MessageTransmitterV2.receiveMessage(message, attestation) on the destination chain"
    - "if expirationBlock passed before receipt: POST /v2/reattest/{nonce}, poll again, receive"
  signatures:
    - ERC-20 approve (on-chain transaction) by the depositor to the TokenMessengerV2 proxy; depositForBurn takes no permit, so USDC's EIP-2612 and EIP-3009 can't be used without a wrapper
    - Circle's attestation, 2 ECDSA signatures of 65 bytes over the message, ordered by attester address
  offchain_required:
    - role: Iris API, attestation retrieval
      api_key: false                     # no security scheme in Circle's OpenAPI; unauthenticated calls succeeded on 2026-09-29
      rate_limited: true                 # 40 requests/s per the technical guide (35 on another Circle page); over it, all requests blocked for 5 minutes with HTTP 429
  finisher: anyone                       # the integrator or any relayer; the protocol (Circle) only if the Forwarding Service hook is used. If nobody calls receiveMessage, nothing is minted; after ~24 h the attestation expires and needs re-attesting
  gasless_start: none                   # depositForBurn burns msg.sender's USDC, so the depositor sends a transaction with native gas; only a smart account or wrapper can hide that. The destination side is gasless with the Forwarding Service
  monitoring:
    - DepositForBurn and MessageSent in the source receipt
    - "GET /v2/messages: status pending_confirmations or complete; delayReason; forwardState and forwardTxHash when forwarded"
    - MessageReceived and MintAndWithdraw on the destination, or usedNonces(nonce) on MessageTransmitterV2
    - expirationBlock in the attested message against the destination (or, on Arbitrum-stack chains, Ethereum) block number
  deployment_data: https://developers.circle.com/cctp/references/contract-addresses (same CREATE2 addresses on EVM chains) and /cctp/concepts/supported-chains-and-domains
  sdk:
    - "@circle-fin/bridge-kit, with @circle-fin/provider-cctp-v2 and @circle-fin/adapter-viem-v2; TypeScript; Apache-2.0"
    - circlefin/evm-cctp-contracts (Solidity, Apache-2.0) for interfaces
  testnet: true                          # every supported mainnet's official testnet; iris-api-sandbox.circle.com
  steps: 4                               # approve, burn, poll attestation, receive; 3 with the Forwarding Service (approve, burn with hook, poll)

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

incidents:
  - date: 2026-06-25
    duration: "over 3 weeks at report (2026-07-10); no resolution posted"
    user_funds_lost: unknown
    exits_blocked: true
    cause: "8 Base-to-Arc V2 burns (900 USDC) never attested; the reattest endpoint answered 'Message is already finalized'. Reported in circlefin/arc-node issue 200; Circle's status page showed a same-day Pharos incident"
  - date: 2026-09-02
    duration: "about 2.3 days (outbound attestations paused 2026-09-02 18:21 UTC to 2026-09-05 02:27 UTC)"
    user_funds_lost: false
    exits_blocked: true
    cause: "Linea stopped finalizing; Circle paused outbound CCTP attestations from Linea until finality resumed"
  - date: 2026-09-28
    duration: "about 13 h"
    user_funds_lost: false
    exits_blocked: true
    cause: "Circle paused attestations for burns on Noble (CCTP V1) for maintenance; shows Circle pausing attestation for a whole domain"

open_questions:
  - "Whether Iris applies any screening or policy to decide not to attest a burn, and whether it ever has; Circle publishes no rule"
  - "Whether burns that Iris never attested (circlefin/arc-node issue 200) were ever minted or made good, and how"
  - "How the attester keys, proxy admins and role EOAs are held inside Circle (HSM, MPC, approval process); on-chain they are single EOAs"
  - "Which addresses are on the TokenMessengerV2 denylist on each chain (needs a Denylisted event scan)"
  - "How and how often the USDC minter allowance for TokenMinterV2 is replenished, and whether it has ever run out"
  - "Whether deployed bytecode matches circlefin/evm-cctp-contracts at the commit Circle names for each chain"
  - "Role holders and thresholds on chains other than Ethereum, Base and Arbitrum, and on non-EVM domains"
  - "Whether Circle will re-attest a burn whose attestation expired unclaimed, in every case; the docs say yes, with no deadline"
  - "TokenMessengerWithFees (upfront fees) has its own DenylistedCaller check; its source and role holders were not read"
sources:                                 # repositories read, at the commit read; clones live in source/<repo>
  - repo: evm-cctp-contracts
    url: https://github.com/circlefin/evm-cctp-contracts
    commit: a92a2b4e7e6ef99bf0b05dca71780f5ec190e729
    commit_date: 2026-06-18
    note: "Circle's fees page names commit 7d703109a2cfcb3f76375fef5f1a97f03c447b94 (PR #57) as the TokenMessengerV2 source on Ethereum, Base, Arbitrum and eight other chains; src/v2/TokenMessengerV2.sol and BaseTokenMessenger.sol at that commit were fetched from raw.githubusercontent.com on 2026-09-29 and differ from the pinned commit only by the minFee switch; MessageTransmitterV2, TokenMinterV2, TokenController, Attestable and Denylistable are identical"
  - repo: stablecoin-evm
    url: https://github.com/circlefin/stablecoin-evm
    commit: fc85788bc7c23cefe3df1a757133048bfddadeaa
    commit_date: 2026-08-12
---

# Circle CCTP V2 Standard Transfer

**Primitive (one line):** The depositor calls `TokenMessengerV2.depositForBurn`, which pulls USDC into `TokenMinterV2` and burns it; Circle's Iris service waits for source finality, fills in the nonce, fee and expiry, and signs the message with its two attester keys; anyone (or the named `destinationCaller`) submits message and attestation to `MessageTransmitterV2.receiveMessage` on the destination, which mints to `mintRecipient`. Fast Transfer differs only in when Iris signs and what it charges; see `cctp-v2-fast.md`.

References are to `source/evm-cctp-contracts` `src/` and `source/stablecoin-evm` `contracts/` unless stated.

## Category 1 — Actor-gated edges

**No return path.** Nothing in the V2 contracts returns burned USDC. `_depositForBurn` transfers from `msg.sender` to the minter and burns in the same call (`v2/TokenMessengerV2.sol:332-395`, `v2/BaseTokenMessenger.sol:307-319`, `TokenMinter.sol` `burn`). The only way the value reappears is a mint on the destination through `receiveMessage`. There is no refund, cancel or timeout function in `MessageTransmitterV2`, `TokenMessengerV2` or `TokenMinterV2`.

**What the source emits vs what is signed.** `MessageV2._formatMessageForRelay` writes an empty nonce (`bytes32(0)`) and `finalityThresholdExecuted` 0 (`messages/v2/MessageV2.sol:63-98`); `BurnMessageV2` leaves `feeExecuted` and `expirationBlock` empty. Iris fills in all four and signs the result. The zero nonce is pre-claimed at initialisation (`MessageTransmitterV2.sol:129-130`), so the unsigned source message can never be received. Nonces are assigned off-chain by Circle (technical guide).

**Receiving.** `receiveMessage` (`MessageTransmitterV2.sol:206-257`) verifies the attestation (`roles/Attestable.sol` `_verifyAttestationSignatures`: exactly `signatureThreshold` signatures of 65 bytes, from enabled attesters, in increasing address order), then the format, destination domain, `destinationCaller` if non-zero, version and unused nonce (`:271-321`). It marks the nonce used and calls `handleReceiveFinalizedMessage` on `TokenMessengerV2` for thresholds of 2000 and above. That checks the caller is the local transmitter and the sender the registered remote TokenMessenger for the source domain, rejects a message past its `expirationBlock` ("Message expired and must be re-signed", `TokenMessengerV2.sol:460-465`), checks `feeExecuted <= maxFee`, and mints through `TokenMinterV2`, which calls `FiatToken.mint`. If anything reverts, the whole transaction reverts and the nonce stays unused, so the message can be retried until it expires.

**Attesters, read on-chain.** On Ethereum `MessageTransmitterV2` (proxy `0x81D40F21F12A8F0E3252Bccb954D722d4c464B64`) has `signatureThreshold` 2 and 2 enabled attesters, `0x725b06f73ff761ef5390e39315e2bfbf60d33f96` and `0x52ed4cbff8dce6a19748043f3240ec03c834bcef`. Base and Arbitrum show the same two and the same threshold. Deriving addresses from the two `cctpVersion: 2` keys that `GET /v2/publicKeys` returns gives exactly these two addresses. So the set is 2 of 2, and both keys are Circle's. The `attesterManager` (`0xc16b03f8...`, an EOA) adds and removes attesters and sets the threshold (`Attestable.sol:83-163`); the owner appoints the manager.

**Can one transfer be singled out?**
- **Circle, by not attesting.** Iris alone decides whether and when to sign. The attestation also carries an `expirationBlock` about 24 h ahead; after it, only a re-attestation (`POST /v2/reattest/{nonce}`) revives the message. Circle's docs say re-attestation has no deadline, but it is Circle's to grant.
- **Circle's attester keys, by signing something else.** The contract doesn't check an attested message against any source-chain burn; both keys together can sign any message. This is how every mint is authorised, not a special path.
- **USDC blacklister.** `FiatTokenV1.mint` carries `notBlacklisted(_to)` (`v1/FiatTokenV1.sol:121-145`); a blacklisted `mintRecipient` makes `receiveMessage` revert. `mintRecipient` is fixed in the burn, so nobody can redirect it. This is a freeze of the user's own address.
- **Proxy admins.** Each proxy has one EOA admin that can `upgradeTo` at once (`proxy/AdminUpgradableProxy.sol`).
- **Not an exit override: the denylist.** `Denylistable.notDenylistedCallers` checks `msg.sender` and `tx.origin` on `depositForBurn` and `depositForBurnWithHook` only (`roles/v2/Denylistable.sol:67-76`, `TokenMessengerV2.sol:174, 219`). A listed caller can't burn, so keeps the USDC. Nothing on the receive or mint side checks it, and it doesn't look at `mintRecipient`.
- **`destinationCaller`.** Chosen by the depositor. If it is non-zero, only that address can call `receiveMessage` (`MessageTransmitterV2.sol:300-306`). If that address never acts, the message can't be received by anyone else, even after re-attestation, because `destinationCaller` is part of the signed message.

**Who calls `receiveMessage`.** Circle doesn't mint automatically: "Consumers must query the attestation and submit it" (technical guide). The exception is the Forwarding Service. A burn whose hook data begins with `cctp-forward` is minted by Circle on the destination, for a service fee taken from `maxFee` ($0.05 on most routes). If nobody submits the message, nothing happens on-chain; once `expirationBlock` passes it needs re-attesting.

**Compellability profile:** every transfer depends on one US company's signature, with no on-chain alternative and no refund. Circle is also the USDC issuer, so the same organisation can freeze the recipient.

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** `MessageTransmitterV2` and `TokenMessengerV2` are `AdminUpgradableProxy` instances (`upgradeTo`, `upgradeToAndCall`, `changeAdmin`, no delay). `TokenMinterV2` is deployed directly and isn't upgradeable, but its owner can detach it (`removeLocalTokenMessenger`), and the TokenMessenger owner can detach the minter (`removeLocalMinter`).

**Role holders on Ethereum (read 2026-09-29, block ~26,077,458):**

| Contract | Role | Address | Code |
|---|---|---|---|
| MessageTransmitterV2 | proxy admin | 0xb7569e9eb64eaed5c4166e510b4f6ff54ef42258 | none |
| | owner | 0xb43aa882f497c0ecb395a5a54f8fa29d12289f65 | none |
| | pauser | 0x383048265851aa10035bb32b2055632ec4fbb6eb | none |
| | rescuer | 0x53d81df780baed54fdca7020618ad6e1c4ac1d84 | none |
| | attesterManager | 0xc16b03f84563c1467017c9f7216f8ad6098dc95a | none |
| TokenMessengerV2 | proxy admin | 0xa820a620f638114f3eb45df87382383322ddbc49 | none |
| | owner | 0x2329baf15f86023e5b0f5592e230d02a51116cd5 | none |
| | rescuer | 0x070b2a0c255c148ae7b98b4bb9560ff147c36f2a | none |
| | denylister | 0xbed4b046f7d185d730e9930b2bcddc86eb3cfbc9 | none |
| | feeRecipient | 0x6efa3205a385420cf1cfd6b725b48f96117a7bee | none |
| TokenMinterV2 | owner | 0x7d1565698cddf4c8f90d6b8574729fef565cae0e | none |
| | pauser | 0x4e898cee7c5809a63de0ef745177a9bb82feac69 | none |
| | rescuer | 0xe206be2331d6aaa4495887755babe892aece704a | none |
| | tokenController | 0x740f494cd63f87547fec1591646720e5cc285846 | none |
| USDC (FiatToken) | blacklister | 0x0a06be16275b95a7d2567fbdae118b36c7da78f9 | none |
| | pauser | 0x4914f61d25e5c567143774b76edbf4d5109a8566 | none |
| | masterMinter | 0xe982615d461dd5cd06575bbea87624fda4e3de17 | MasterMinter contract, owner 0xc1d9fe41d19dd52cb3ae5d1d3b0030b5d498c704 (no code) |
| | proxy admin | 0x807a96288a1a408dbc13de2b1d087d10356395d2 | none |

None is a multisig on-chain: each is an address with no code (and so no EIP-7702 delegation either). `pendingOwner` is zero on all three CCTP contracts. Many of these addresses have never sent a transaction (nonce 0). How Circle holds them internally isn't visible. Base and Arbitrum use different addresses for every owner, admin and denylister, so each chain has its own keys.

**Immediate-effect functions on transfers in flight:** listed in the header. The ones that stop every mint on a chain: `MessageTransmitterV2.pause`, `TokenMinterV2.pause`, `removeLocalMinter`, `removeLocalTokenMessenger`, the USDC pause and removal of `TokenMinterV2` as a USDC minter. The ones that stop one source domain: `removeRemoteTokenMessenger`, `unlinkTokenPair`. The ones that reach one transfer: the proxy upgrades, attester changes and the USDC blacklist. None has a timelock.

**Grandfathering:** none. A message is minted under whatever attester set, links and code exist when it is received; changing attesters invalidates attestations already issued until Iris re-signs.

## Category 3 — Data-oracle-gated edges

No price oracle. On the exit:
- **Finality.** Iris signs a Standard message once the burn is final by Circle's rule. Published averages: Ethereum ~65 blocks, 15-19 minutes; OP-stack chains, Arbitrum and others that settle to Ethereum 15-19 minutes (Ink ~30, Morph 20-30); Starknet 2-4 h; Linea 6-32 h; fast-finality chains 0.5-10 s. A source chain that stops finalizing stops attestations: Circle paused outbound attestations from Linea for about 2.3 days in September 2026.
- **Expiry.** `expirationBlock`, about 24 h after attestation, checked in `TokenMessengerV2._validatedReceivedMessage`. Reopened only by Circle re-attesting.
- **USDC minter allowance.** `TokenMinterV2` mints under `minterAllowed`, 330,877,915.09 USDC on Ethereum at read time. A mint larger than what is left reverts until Circle's controller raises it.

Off the exit: the per-message burn limit (10,000,000 USDC on Ethereum, `TokenController.onlyWithinBurnLimit`) and `maxMessageBodySize` (8192 bytes) make the burn revert, so funds stay with the user.

**Source vs documentation.** Circle's fees page says that if the actual fee exceeds `maxFee`, "the transaction will revert on the source blockchain, and no USDC will be burned". In source, the only on-chain fee check at burn time is `minFee` (`TokenMessengerV2.sol:346-354`), and the Ethereum, Base and Arbitrum implementations don't have it: `minFee()` reverts, and Circle's own table lists these chains as deployed from the commit without the fee switch. The fee is chosen by Iris as `feeExecuted <= maxFee` and checked at mint. A too-low `maxFee` doesn't revert the burn; for Fast it makes Iris fall back to Standard (the fee page's own warning, and `delayReason: insufficient_fee`).

## Category 4 — Judgment-oracle-gated edges

**In the contracts:** the `TokenMessengerV2` denylist on burn callers (`msg.sender` and `tx.origin`), managed by one EOA denylister per chain. It is on the entry, not the exit. The mint side has no screening in CCTP's own code.

**Iris:** Circle publishes no attestation policy. Nothing public says whether Iris screens senders or recipients before signing.

**Issuer freeze:** the recipient's USDC blacklist status decides the mint (`notBlacklisted(_to)`). Burning checks the depositor via `transferFrom` (`notBlacklisted(from)`). USDC isn't pooled: `TokenMinterV2` holds it only within the burn transaction. Circle's record on freezes is mixed. In March 2026 it froze 16 business wallets over a sealed civil case. In April 2026 about $232M of USDC stolen from Drift crossed CCTP from Solana to Ethereum over about six hours without a freeze, and a class action followed. Neither is a CCTP-specific refusal to attest.

## Service

Circle runs Iris (`iris-api.circle.com`, sandbox `iris-api-sandbox.circle.com`). The API needs no key: Circle's OpenAPI has no security scheme, and unauthenticated calls to `/v2/fastBurn/USDC/allowance`, `/v2/publicKeys` and `/v2/burn/USDC/fees/0/3` succeeded on 2026-09-29. The limit is 40 requests per second (technical guide; another Circle page is quoted at 35), and exceeding it blocks all requests for five minutes with HTTP 429. The attestation service is not public source. There is no bypass. The contract accepts only the enabled attesters' signatures, and both keys are Circle's, so a transfer can't complete without Circle signing it. Getting the attestation from somewhere other than the Iris API wouldn't change who signed it.

## Integration

1. `approve` USDC to `TokenMessengerV2` on the source chain (a separate transaction; `depositForBurn` takes no permit).
2. `depositForBurn` with `minFinalityThreshold` 2000 (values above 1000 are treated as 2000), `maxFee` 0 on routes whose Standard fee is 0, and `destinationCaller` zero unless a specific contract must receive. `depositForBurnWithHook` carries hook data; CCTP doesn't execute hooks, except the `cctp-forward` hook that Circle's Forwarding Service acts on.
3. Poll `GET /v2/messages/{sourceDomain}?transactionHash=` until `status: complete`; watch `delayReason`.
4. Call `MessageTransmitterV2.receiveMessage(message, attestation)` on the destination before `expirationBlock`. With forwarding, Circle does this and `forwardState` and `forwardTxHash` show it.

The depositor needs native gas on the source chain. Destination gas is needed unless forwarding is used. Addresses are the same CREATE2 addresses on every EVM chain (`TokenMessengerV2` `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d`, `MessageTransmitterV2` `0x81D40F21F12A8F0E3252Bccb954D722d4c464B64`, `TokenMinterV2` `0xfd78EE919681417d192449715b2594ab58f5D002`). The SDK is Bridge Kit (TypeScript, Apache-2.0). Every supported mainnet has its testnet. There are no bespoke proofs: the attestation is plain concatenated ECDSA signatures.

## Historical incidents

- 2026-06-25: eight Base-to-Arc V2 burns (900 USDC) were never attested. Iris reported them `pending_confirmations` while `reattest` answered "Message is already finalized". The report (circlefin/arc-node issue 200, 2026-07-10) shows no Circle reply or resolution. It shows that a burn can sit unattested with no recourse outside Circle.
- 2026-09-02 to 2026-09-05: Linea stopped finalizing, and Circle paused outbound CCTP attestations from Linea until it resumed (status.circle.com).
- 2026-08-22 to 2026-09-18: several short "CCTP attestations delayed" incidents on Ink, HyperEVM, Injective, Cronos and Arc (status.circle.com RSS; hours each).
- 2026-09-28: Circle paused attestations for Noble burns (CCTP V1) for maintenance, about 13 h. Noble V1 support ends from 2026-10-13.
- Only the last ~25 status entries and a web search were reviewed.

## Composite

**Stuck-leg failure modes:**
1. Iris doesn't attest (outage, finality halt, policy, bug): USDC burned, nothing minted, no refund.
2. The attestation expires unclaimed: it needs Circle to re-attest.
3. The recipient is blacklisted: the mint reverts until it is unblacklisted.
4. A pause, unlink, remote-messenger removal or removal of the minter on the destination: every mint on that chain, or from that source, waits.
5. The minter allowance is exhausted: mints larger than what remains wait for Circle to raise it.
6. `destinationCaller` set to an address that never acts: that transfer can't be received.

**Time-to-recovery per mode:**
| Mode | Recovery bound | Basis |
|---|---|---|
| Normal (Ethereum source) | ~15-19 min + one destination tx | Circle's published attestation times |
| Iris doesn't attest | unbounded | no on-chain alternative (`Attestable.sol`) |
| Attestation expired | when Circle re-attests | `TokenMessengerV2.sol:460-465`; reattest API |
| Recipient blacklisted | unbounded | `FiatTokenV1.sol:121-145` |
| Pause or config removal | unbounded | no timelock on any role |
| Source finality halt | until the chain finalizes | Linea, September 2026 |

**Cross-protocol correlation:** everything minting USDC through CCTP (Across, Skip Go Fast and others that settle in CCTP) shares Iris, the two attester keys and Circle's issuer controls.

## Sources

- `source/evm-cctp-contracts` (https://github.com/circlefin/evm-cctp-contracts): `src/v2/MessageTransmitterV2.sol`, `BaseMessageTransmitter.sol`, `TokenMessengerV2.sol`, `BaseTokenMessenger.sol`, `TokenMinterV2.sol`, `FinalityThresholds.sol`; `src/TokenMinter.sol`; `src/roles/Attestable.sol`, `roles/v2/AttestableV2.sol`, `roles/v2/Denylistable.sol`, `roles/TokenController.sol`, `Pausable.sol`, `Rescuable.sol`, `Ownable2Step.sol`; `src/proxy/AdminUpgradableProxy.sol`; `src/messages/v2/MessageV2.sol`, `BurnMessageV2.sol`; `scripts/v2/DeployProxiesV2.s.sol`; `README.md`. Read 2026-09-29.
- The same repository at the commit Circle names for the Ethereum, Base and Arbitrum TokenMessenger (see the note in the header's `sources`): `TokenMessengerV2.sol` and `BaseTokenMessenger.sol` fetched from raw.githubusercontent.com and diffed. They differ only by the `minFee` switch; the other V2 files are identical. Retrieved 2026-09-29.
- `source/stablecoin-evm` (https://github.com/circlefin/stablecoin-evm): `contracts/v1/FiatTokenV1.sol` (`mint`, `burn`, `transferFrom`, `configureMinter`, `removeMinter`), `v1/Blacklistable.sol`, `v1/Pausable.sol`. Read 2026-09-29.
- On-chain reads, Ethereum mainnet, 2026-09-29, block ~26,077,458, via ethereum-rpc.publicnode.com. On all three CCTP contracts: EIP-1967 admin and implementation slots, `owner`, `pendingOwner`, `pauser`, `rescuer`. On MessageTransmitterV2: `attesterManager`, `signatureThreshold`, `getNumEnabledAttesters`, `getEnabledAttester`, `paused`, `localDomain`, `version`, `maxMessageBodySize`. On TokenMessengerV2: `denylister`, `feeRecipient`, `minFeeController` and `minFee` (both revert), `localMinter`, `remoteTokenMessengers(0..31)`. On TokenMinterV2: `tokenController`, `localTokenMessenger`, `burnLimitsPerMessage(USDC)`. On USDC: `minterAllowance(TokenMinterV2)`, `isMinter`, `masterMinter`, `blacklister`, `pauser`, `owner`, `paused`, `isBlacklisted` for the CCTP contracts, and the proxy admin slot. `eth_getCode` and `eth_getTransactionCount` on every role holder, and selector presence in the deployed implementations. Spot checks on Base and Arbitrum (publicnode): threshold, attesters, owners, admins, denylister.
- https://iris-api.circle.com/v2/publicKeys, `/v2/fastBurn/USDC/allowance`, `/v2/burn/USDC/fees/0/3`, called without a key. Retrieved 2026-09-29.
- https://developers.circle.com/llms.txt and the markdown of `/cctp`, `/cctp/references/technical-guide`, `/cctp/concepts/fees`, `/cctp/concepts/fast-transfer-allowance`, `/cctp/concepts/finality-and-block-confirmations`, `/cctp/concepts/supported-chains-and-domains`, `/cctp/concepts/forwarding-service`, `/cctp/concepts/upfront-fees`, `/cctp/concepts/how-upfront-fees-work`, `/cctp/concepts/upfront-fee-quotes`, `/cctp/references/contract-interfaces`, `/cctp/references/contract-addresses`, `/cctp/migration-from-v1-to-v2`, `/cctp/quickstarts/transfer-usdc-ethereum-to-arc`, `/cctp/howtos/transfer-usdc-with-forwarding-service`, and `/openapi/cctp.yaml`. Retrieved 2026-09-29.
- https://developers.circle.com/cctp/technical-guide (WebFetch summary). Retrieved 2026-09-29.
- https://developers.circle.com/cctp/references/cctp-apis, https://developers.circle.com/cctp/cctp-finality-and-fees and https://developers.circle.com/cctp/limits returned 404. The "35 requests per second" figure comes from a search snippet of the limits page. Retrieved 2026-09-29.
- https://registry.npmjs.org/@circle-fin/bridge-kit (tarball LICENSE: Apache-2.0), `@circle-fin/provider-cctp-v2`, `@circle-fin/adapter-viem-v2`. Retrieved 2026-09-29.
- https://github.com/circlefin/arc-node/issues/200 (unattested Base-to-Arc burns) and https://github.com/circlefin/arc-node/issues/428 (Arc finalized attestations taking hours; search summary only). Retrieved 2026-09-29.
- https://status.circle.com/history.rss, the last 25 incidents. https://status.circle.com/history returned only the page shell. Retrieved 2026-09-29.
- https://www.theblock.co/post/396183/drift-280m-exploit-zachxbt-circle, https://www.coindesk.com/business/2026/04/03/circle-under-fire-after-usd285-million-drift-hack-over-inaction-to-freeze-stolen-usdc and https://thepaypers.com/fraud-and-fincrime/news/circle-faces-class-action-lawsuit-over-failure-to-freeze-funds-in-drift-protocol-exploit, on the Drift flows over CCTP and the class action. Search summaries. Retrieved 2026-09-29.
- Cited by the earlier version and not re-read: https://www.circle.com/blog/cctp-v2-the-future-of-cross-chain, https://l2beat.com/interop/protocols/cctpv2, https://finance.yahoo.com/markets/crypto/articles/circle-first-froze-16-usdc-085427724.html (March 2026 freeze of 16 wallets), https://www.ccn.com/education/crypto/circle-zama-freeze-stablecoin-censorship-resistance/ (May 2026 Zama cUSDC freeze) and https://www.theblock.co/post/396296/blockchain-sleuth-zachxbt-accuses-circle-slow-usdc-freezes-420-million-illicit-funds. All retrieved 2026-09-16.

## Notes / follow-ups

- Corrections to the earlier entry. It had Iris as one attester; on-chain it is 2 of 2 keys, both Circle's. It said "recovery would require Circle to mint replacement USDC, which is an off-chain process". That is not in any source read; the documented path is re-attestation. Its admin surface was unknown; it is now read. The earlier entry didn't mention `expirationBlock`, the burn-side denylist, the minter allowance or the Forwarding Service.
- The earlier entry listed "source chain reorg after attestation" as a Standard failure mode. That risk falls on Circle, not the user, and matters for Fast, not Standard.
- Remaining open questions are in the header.
