# Maya Protocol

**Verification tier:** `spec-only` (incident reports; source at gitlab.com/mayachain/mayanode not yet read)
**Last updated:** 2026-09-16
**Class:** D
**Primitive (one line):** THORChain fork with same TSS-vault architecture; validators co-sign threshold signatures on external chains (BTC, ETH, ARB); native token CACAO; settles cross-chain swaps via validator consensus.
**Product scope of this entry:** Maya Protocol (MAYAChain) cross-chain swap

## Category 1 — Actor-gated edges

**Actors on exit path:**
- Actor: Maya validator set
  - Role: same as THORChain — observe, consensus, TSS co-sign on external chains
  - Set size: smaller validator set than THORChain (exact count unknown — verify)
  - Source: [1]

**User self-refund:** **NO.** Same TSS-vault custody model as THORChain. User has no self-service exit.

## Category 2 — Modification-gated edges

**Pause mechanism:** network was fully halted after Aug 2026 exploit. Validators can halt.
**Upgrade authority:** validator-controlled.

## Historical incidents (CRITICAL)

- **2026-08-18 (~17:30 UTC):** Sophisticated exploit chaining 6 separate software bugs in MAYAChain's trade account and outbound handling. Single transaction containing 23 messages. Results:
  - $1.36-1.7M extracted (20.83 BTC sent to single address across ~10 blocks)
  - Attacker minted ~48.87 million CACAO (nearly half of 100M supply)
  - CACAO crashed 88% from $0.115 to $0.013
  - Network fully halted
  - Source: [2][3][4]

- **Key implication:** as a THORChain fork, Maya inherits THORChain's architectural risks but with a smaller validator set and less security review. The 6-bug chain exploit demonstrates that forked codebases can accumulate unique vulnerabilities that diverge from the upstream.

**Note:** "Mayan Finance" (Swift/MCTP cross-chain swap) is an UNRELATED project despite the similar name. Mayan Finance has no known exploits. Source: Wormhole/Mayan agent research.

## Composite

**Stuck-leg failure modes:**
1. Network halt after exploit — all operations frozen. **Happened Aug 2026.**
2. CACAO token collapse — 88% crash means validator bonds denominated in CACAO lose value, potentially creating undercollateralization spiral.
3. Same TSS custody risks as THORChain — rogue validator, key compromise, validator compulsion.

## Route flags for decision engine

- `class`: D
- `custody_model`: tss_vault (THORChain fork architecture)
- `requires_actor_liveness`: [maya_validator_set]
- `user_can_self_refund`: **no**
- `has_immediate_admin_pause`: yes (validator halt)
- `known_incident_count_12mo`: 1 (Aug 2026, $1.7M, 6-bug chain)
- `native_token_crash`: yes (CACAO -88% during exploit)
- `is_fork_of`: thorchain

## Sources

1. https://docs.mayaprotocol.com/ — Maya Protocol documentation
2. https://en.cryptonomist.ch/2026/08/19/maya-protocol-exploit-theft/ — exploit overview
3. https://defimon.xyz/blog/maya-protocol-hack-august-2026 — 6-bug technical analysis
4. https://beincrypto.com/maya-protocol-exploit-halts-btc-swaps/ — network halt and CACAO crash
5. https://gitlab.com/mayachain/mayanode — source repo (not yet read)

## Notes / follow-ups

- The 6-chained-bug exploit is one of the most sophisticated attacks in the audit — demonstrates risks of forked codebases
- Smaller validator set than THORChain means lower security budget and potentially easier to attack
- Verify current network status — may still be halted or in recovery post-exploit
- Consider whether Maya should be flagged as high-risk or excluded from routing given recent exploit + token crash
