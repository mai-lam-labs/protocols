# ICP Chain Fusion

**Verification tier:** `spec-only` (docs, forum posts, and incident reports read; canister source not inspected)
**Last updated:** 2026-09-16
**Class:** D
**Primitive (one line):** Internet Computer subnet threshold cryptography (tECDSA, tSchnorr, Ed25519) produces signatures for derived addresses on external chains; ckBTC/ckETH/ckERC20 are 1:1 backed chain-key tokens minted by protocol canisters on the fiduciary subnet (28-34 nodes); NNS governance controls all infrastructure.
**Product scope of this entry:** ICP Chain Fusion — ckBTC, ckETH, ckERC20, ckSOL chain-key tokens

## Category 1 — Actor-gated edges

**Actors on exit path (redemption of ckBTC → BTC, ckETH → ETH):**
- Actor: Fiduciary subnet (pzp6e)
  - Role: hosts threshold signing keys. Minter canister signs external chain transactions to release underlying assets on redemption.
  - Set size: 28-34 nodes (high-replication subnet for financial operations)
  - Threshold: tolerates up to 1/3 Byzantine failures (~9 of 28 malicious nodes tolerated). Uses Groth-Shoup protocol with "guaranteed output delivery."
  - Selection: NNS governance proposals add/remove nodes
  - Source: [1][2]
- Actor: NNS governance (ICP stakers)
  - Role: ultimate authority over all chain-key infrastructure. Can upgrade, freeze, or modify minter canisters via proposals.
  - Source: [1]

**User self-refund:** **NO.** Redemption requires the minter canister to sign origin-chain transactions via subnet threshold cryptography. No escape hatch, no pre-signed recovery, no user key share. The key derivation is deterministic (anyone can compute the address) but only the subnet can produce signatures.

**If subnet goes offline:** no chain-key signatures can be produced. No ckBTC/ckETH can be minted or redeemed. External chain assets become inaccessible. NNS governance can theoretically restore the subnet with new nodes via proposal. Source: [1]

## Category 2 — Modification-gated edges (in-window effect)

**Upgrade authority:** NNS proposals can upgrade all system canisters (Bitcoin canister, ckBTC minter, EVM RPC canister). Proposals that pass execute automatically. Source: [1]

**Freeze capability:** DFINITY has confirmed ability to freeze the ckBTC ledger if needed. This was mentioned in the context of the October 2023 security patch. Source: [3]

**Key resharing:** DKG protocol supports subnet membership changes without key reconstruction. Removed nodes' shares become useless. Source: [1]

## Category 3 — Data-oracle-gated edges

**Oracles:** Bitcoin canister and EVM RPC canister provide chain state to the IC. These are protocol-level system canisters, not external oracles.

## Category 4 — Judgment-oracle-gated edges

**KYT (Know-Your-Transaction) compliance canister — CRITICAL FINDING:**
The ckBTC minter integrates a mandatory KYT check on BOTH minting and withdrawals via the Bitcoin Checker canister (`oltsj-fqaaa-aaaar-qal5q-cai`):

- **Minting:** before minting ckBTC, the minter sends each incoming UTXO to the Bitcoin Checker canister, which checks Bitcoin addresses against the OFAC Specially Designated Nationals (SDN) list. UTXOs that fail are **quarantined indefinitely** — ckBTC is NOT minted, and the deposited BTC sits in the minter's custody with no documented release mechanism. Source: [5][6]
- **Withdrawal:** before executing a BTC withdrawal, the minter checks the destination Bitcoin address against the SDN list. Flagged addresses are rejected. Source: [5]
- **Fee:** 100 satoshi KYT fee per UTXO on deposit. Source: [5]
- **No documented appeal process** for quarantined UTXOs. "Tainted UTXOs are quarantined indefinitely." Source: [6]
- **External dependency:** the checker canister uses HTTPS outcalls to query external KYT service providers. The specific providers and their criteria are controlled by the canister configuration (NNS-governed). Source: [5]

**Implication for revocability:** a user who deposits BTC that is later flagged (even retroactively) by the OFAC SDN list or the KYT provider has their BTC quarantined with no on-chain exit path. This is a judgment-oracle-gated edge with **unbounded duration and no appeal mechanism at the protocol level.**

**NNS governance as judgment oracle:** ICP stakers (NNS neuron holders) can vote on proposals that affect ckBTC/ckETH infrastructure. This is both a safety mechanism (can freeze/upgrade to fix vulnerabilities) and a centralization risk (governance can modify rules affecting user funds). DFINITY Foundation holds significant NNS voting power.

## Historical incidents

- **2023-10-05:** ckBTC ledger `icrc2_approve` bug — upgrade proposal 124868 deployed code that inserted duplicate approval entries instead of updating existing ones. Discovered Oct 6, patched same day via proposal 125000 (executed in 4 min 22 sec). **No funds lost.** DFINITY assessed exploitation risk as low ("several millions of entries...practically impossible"). A debug assertion designed to catch the issue had failed due to "configuration error." Source: [3]
- **2023-11:** Trail of Bits audit assessed ckBTC for double-spend, DoS, and invalid minting risks. Results not fully public. Source: [3]
- **2026 (recent):** Reports of attacks targeting ckBTC Bitcoin minting canisters. Details not available from text search. Source: [4]

## Composite

**Stuck-leg failure modes:**
1. Fiduciary subnet offline — all ckBTC/ckETH redemptions halted. NNS governance can restore with new nodes. **Bounded by NNS governance response time.**
2. NNS governance freezes minter — redemptions blocked by governance vote. **Unbounded (governance-controlled).**
3. NNS governance upgrades minter with malicious code — user funds at risk. **Irreversible.**
4. Pre-signature exhaustion under high load — signing requests time out. **Bounded (retry).**

## Route flags for decision engine

- `class`: D
- `custody_model`: subnet_threshold_signed_addresses
- `requires_actor_liveness`: [icp_fiduciary_subnet_28_nodes]
- `user_can_self_refund`: **no**
- `escape_hatch`: **none**
- `committee_model`: NNS governance (ICP stakers)
- `threshold`: 2/3 honest (tolerates 1/3 Byzantine)
- `has_freeze_capability`: yes (DFINITY confirmed)
- `has_kyt_compliance_gate`: **yes (OFAC SDN check on mint AND withdrawal, quarantine indefinite)**
- `judgment_oracle_dependencies`: [bitcoin_checker_canister (OFAC SDN), external_kyt_providers_via_https]
- `governance_can_upgrade`: yes (NNS proposals)
- `known_incident_count_12mo`: 1+ (2026 minting canister attacks, details unclear)
- `audit_history`: Trail of Bits (Nov 2023)

## Sources

1. https://internetcomputer.org/docs/current/developer-docs/multi-chain/overview — ICP Chain Fusion overview
2. https://forum.dfinity.org/t/number-of-parties-in-threshold-ecdsa/29674 — fiduciary subnet node count
3. https://forum.dfinity.org/t/context-around-the-security-patch-proposal-125000-for-the-ckbtc-ledger/23549 — October 2023 ckBTC bug and patch
4. Search results referencing 2026 attacks on ckBTC minting canisters
5. https://docs.internetcomputer.org/concepts/chain-fusion/bitcoin/ — Bitcoin integration docs, KYT checker integration
6. https://forum.dfinity.org/t/ckbtc-and-kyt-compliance/18754 — ckBTC KYT compliance forum discussion (490+ posts)
7. https://internetcomputer.org/whitepapers/A%20Decentralized%20Mechanism%20for%20Know-Your-Transaction%20Compliance.pdf — KYT whitepaper
- https://github.com/dfinity/ic — listed in the original protocol index; not yet retrieved

## Notes / follow-ups

- ICP is more transparent than NEAR Chain Signatures (disclosed threshold, larger committee, on-chain governance) but shares the fundamental Class D property: no user unilateral exit
- DFINITY Foundation's NNS voting power concentration should be quantified — if DFINITY can unilaterally pass proposals, the decentralization claim is weaker
- The 2026 minting canister attacks need investigation once details are public
- Verify whether the 4-confirmation requirement for ckBTC minting creates any edge cases where BTC is sent but ckBTC is not minted
