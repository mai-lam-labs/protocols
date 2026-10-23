---
slug: near-chain-signatures
name: NEAR Chain Signatures
scope: The v1.signer MPC contract on NEAR mainnet (v3.16.0) and its participant network, which signs for NEAR-derived addresses on other chains (secp256k1, Ed25519, and foreign-transaction domains). Products that hold funds at derived addresses (Relay's Allocator, NEAR Intents' bridges) inherit this
kind: settlement
class: D
cross_chain: true
chains: [NEAR, Bitcoin, Ethereum, Solana, Cosmos, Dogecoin, XRP]   # any chain whose signature schemes it supports
source_public: true                      # github.com/near/mpc
inherits: []
updated: 2026-10-06

verification:
  service: source-verified               # sign() access read in source; no deny-list in contract or node
  exit: source-verified                  # sign / respond / yield timeout read; live state and block time read
  actors: source-verified                # participants, threshold and TEE attestations read on-chain
  admin: source-verified                 # update and governance votes read in source; no access keys on-chain
  data: source-verified                  # accept_requests gate read in source
  judgment: partial                      # no screening in public source; operators' own behaviour can't be inspected beyond the TEE pinning
  incidents: not-reviewed

exit:
  custody: mpc_vault                     # assets at derived addresses are controlled by the participants' threshold key
  execution: automatic                   # any NEAR account calls sign(); participants respond; nobody decides per request in the contract
  overrides:
    - who: MPC participants
      needs: 7 of 17 decline (11 of 17 needed to sign); 11 of 17 to sign anything for any derived address
      parties: quorum
      independent: unknown               # 17 named operators; independence not otherwise established
      how: withhold a signature for one request, or produce one nobody requested; 11 can also reshare the key among themselves and drop the rest
      reach: one
      bounded: false
      cost: none on-chain; no stake or slashing in the contract
  refund_trigger: none                   # a signing service, not a transfer; a timed-out request can simply be sent again
  exit_bound_seconds: [1, 118]           # each request is answered or fails at NEAR's yield timeout, 200 blocks at the measured 0.59 s per block
  exit_bound_chosen_by: none
  standing_approval: none

actors:
  - role: MPC participants; hold key shares in TEEs and sign
    entity: 17 operators (blacksandtech, mpc-lgns, Aurora, Staking4All, nodemonster, n1-multichain, Everstake, Stakin, mpch, svrn, greenfield, natsai, HashKey, astrostakers, Klever, Nansen, Bitwise)
    jurisdiction: unknown
    set: m_of_n                          # 11 of 17, reconstruction_threshold 11 on every domain
    independence: unknown                # distinct operators by name; not otherwise established

admin:
  upgradeable: true                      # submit_contract_update deploys new code once threshold participants have voted for its hash
  authority: validators                  # the participants themselves; v1.signer has no access keys
  timelock_seconds: none                 # an approved update applies as soon as a participant submits it
  immediate_functions:
    - function: vote_contract_update / submit_contract_update
      caller: 11 of 17 participants
      parties: quorum
      independent: unknown
      effect: replaces the contract code at once; adds no power over signing that the same 11 don't already have
    - function: vote_new_parameters (resharing)
      caller: every member of the proposed set, with newcomers admitted after 11 current participants vote
      parties: quorum
      independent: unknown
      effect: changes who holds shares and the threshold
  grandfathered: none
  outside_exit_path:
    - what: vote_add_domains, TEE measurement and launcher votes, foreign-chain RPC whitelist votes
      effect: which signature schemes exist and which node images and RPC providers are accepted

data_gates:
  - kind: TEE attestation coverage
    where: verify_tee sets accept_requests = false when removing participants with invalid attestations would leave too few; respond() then refuses
    trigger: too many participants without a valid attestation within tee_upgrade_deadline (604800 s)
    blocks_exit: true
    reset: unbounded                     # "requires manual intervention"
    parties: quorum                      # fires only if 7 or more of 17 participants lose attestation; reopening is by participant votes
    independent: unknown
  - kind: request timeout
    where: NEAR yield/resume on sign()
    trigger: no response within 200 blocks
    blocks_exit: false                   # the request fails and can be resubmitted

judgment:
  screening: []                          # no deny-list or caller filter in sign() (contract) or in the node software; nodes run a pinned image in TEEs
  freeze_assets: []
  freeze_pooled: false

service:
  integrator_access:
    api_key: false
    identity: none
    revocable: false
    rate_limited: false
    note: "any NEAR account can call sign() with the 1-yoctoNEAR deposit (which forces a full-access key) and enough gas"
  operators: []
  screening: []                          # none in sign() or in node source
  bypass: true                           # there is no operator in front; the contract is called directly

integration:
  calls: ["v1.signer.sign(request) from a NEAR account with the derivation path, a deposit and at least the configured gas", "broadcast the signed transaction on the target chain"]
  signatures: ["MPC signature over the target-chain payload"]
  offchain_required: []
  finisher: user
  gasless_start: none
  monitoring: "the sign call's return value on NEAR, or its timeout error"
  sdk: "chainsig.js (TypeScript)"
  testnet: true
  steps: 2

trade:                                   # the position the user enters, described, not rated (CRITERIA.md, Trade)
  structure: service
  holder: none
  strike: none
  expiry: none
  early_close: none
  premium: none
  terms_fixed_by: contract
  price_set_by: none
  discipline: none
  surplus_to: none
  extraction: []
  sides: none
  rate: none
  quote_validity: none
  partial_fill: none
  partial_remainder: none

actions:                                 # every step, and whether its performer is paid for it in the same transaction (CRITERIA.md, Paid execution)
  - action: start
    performer: user
    paid: none
    gas_on: other_chain
    note: "sign() from a NEAR account, with a deposit and NEAR gas"

instructions:                            # what the user signs or sends, and how far it must be trusted (CRITERIA.md, Censorship resistance)
  - path: sign
    form: self_built

incidents: []

open_questions:
  - Legal entities and jurisdictions of the 17 participants
  - Whether the deployed v3.16.0 matches the repository at the tag it was built from (the head read here is newer)
  - What "manual intervention" means if accept_requests goes false, and who would perform it
sources:
  - repo: near-mpc
    url: https://github.com/near/mpc
    commit: 5c8946e124d93a7e5e7c0a90d818860dd4f6b92f
    commit_date: 2026-10-06
    note: "head is newer than the deployed v3.16.0; the functions read exist in both"
---

# NEAR Chain Signatures

**Primitive (one line):** `v1.signer` on NEAR accepts `sign()` requests from any NEAR account. A network of 17 MPC participants, running a pinned image in TEEs, produces a threshold signature (11 of 17) for the requester's derived address on another chain. The request is answered through NEAR yield/resume, or fails after 200 blocks.

## Signing

`sign(request)` (`crates/contract/src/api/sign.rs:29`) runs `check_request_preconditions` (`api/common.rs:25`). That checks the domain exists and is for signing, that enough gas is attached, and that a minimum deposit is attached. The deposit exists so that only a full-access key can request a signature, which stops a malicious frontend holding a function-call key. Nothing checks who the caller is.

The request is parked with `promise_yield_create` and answered by a participant's `respond()`. Unanswered, it fails at NEAR's yield timeout: 200 blocks in the live protocol config, about 118 s at the measured 0.59 s per block. A failed request can be sent again.

## Who can refuse or forge

The participants. 7 of 17 declining stops a signature, and 11 of 17 can sign anything, for any derived address. The contract holds no stake and has no slashing.

There is no deny-list in the contract; its only whitelist is of foreign-chain RPC providers. The node software (`crates/node`) has no screening either. Nodes must attest to an approved Docker image hash inside a TEE, which makes it hard for an operator to quietly run a modified, screening node, short of the 11-of-17 votes needed to approve a new image.

## Governance

- **Code updates.** `vote_contract_update` and `submit_contract_update` (`api/update.rs`) need a threshold of participants (11) to vote for an update's hash. A participant then submits it, and it deploys at once. There is no delay, and `v1.signer` has no access keys.
- **Participant changes** (`vote_new_parameters`, `state/running.rs`). Every member of the proposed set must vote. A newcomer can vote only after a threshold of current participants has. So the same 11 who can sign anything can also reshare the key to drop the other six.
- **TEE enforcement** (`verify_tee`, `api/attestation.rs`). Participants without a valid attestation are removed by resharing. If removing them would leave fewer than the threshold, the contract sets `accept_requests = false`, and `respond()` refuses every request until "manual intervention".

## On-chain state (2026-10-06)

Read through `rpc.mainnet.fastnear.com`:

- **Contract:** v3.16.0, Running.
- **Participants:** 17, threshold 11, `reconstruction_threshold` 11 on all four domains.
- **TEE:** all 17 participants have TEE attestations (`get_tee_accounts` lists 20).
- **Access keys:** none.
- **Config:** `tee_upgrade_deadline_duration_seconds` is 604,800 and `key_event_timeout_blocks` is 30.
- **Protocol:** `yield_timeout_length_in_blocks` is 200, and the measured block time over 2,000 blocks is 0.59 s.

## Corrections to the earlier entry

- **Size and threshold.** The earlier entry listed 8 proof-of-authority nodes and called the threshold undisclosed. The contract holds 17 participants with threshold 11, readable by anyone.
- **"Permanently locked."** It said assets would be "permanently locked" if the committee went offline. That holds only if fewer than 11 participants come back. Shares persist across restarts, and resharing can move them.

## Historical incidents

None found for 2024–2026 (search 2026-09-16). Not reviewed since.

## Sources

1. https://docs.near.org/build/chain-abstraction/chain-signatures/getting-started — NEAR Chain Signatures docs (2026-09-16)
2. https://github.com/near/mpc — `crates/contract/src/api/{sign,common,update,governance,attestation}.rs`, `state/running.rs`, `crates/node` (searched for screening), 2026-10-06
3. `v1.signer` views (`state`, `version`, `config`, `get_tee_accounts`), access-key list, `EXPERIMENTAL_protocol_config` and block headers through `rpc.mainnet.fastnear.com`, 2026-10-04 and 2026-10-06
4. https://cryptorank.io — operator list at mainnet launch (out of date)
