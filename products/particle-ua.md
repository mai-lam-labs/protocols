# Particle Universal Accounts

**Verification tier:** `spec-only`
**Last updated:** 2026-09-16
**Class:** different (smart account infrastructure, not intent/bridge protocol)
**Primitive (one line):** Chain abstraction via smart account infrastructure; Universal Accounts aggregate token balances across all chains (EVM + Solana) by automatically routing atomic cross-chain transactions; uses EIP-7702 to let existing EOAs act as Universal Accounts; Master Keystore Hub as central state; Bundler Network executes operations.
**Product scope of this entry:** Particle Network Universal Accounts

## Custody model

**User-controlled.** Accounts are "extensions of the user's existing wallet." Users sign with existing wallet (MetaMask, etc.) or social login (MPC-TSS key shares). Particle does not hold custody. However:
- Bundler Network and Relayer nodes that execute cross-chain operations are infrastructure dependencies
- Master Keystore Hub is "a central source of truth" for account state — an infrastructure dependency
- Social login uses MPC-TSS (threshold signatures) meaning key shares are distributed

## Revocability

User controls the smart account and signs all transactions. "Revocation" is native — simply don't sign. The infrastructure dependency is Bundler/Relayer availability, not fund custody.

## Route flags for decision engine

- `class`: different (smart account, not intent protocol)
- `custody_model`: user_controlled
- `infrastructure_dependencies`: [bundler_network, relayer_nodes, master_keystore_hub]
- `key_management`: wallet_native or mpc_tss (social login)

## Sources

1. https://developers.particle.network/ — Particle documentation
2. https://github.com/Particle-Network — source repos

## Notes / follow-ups

- Not an intent protocol — included for completeness since it was in the original index
- The Master Keystore Hub as "central source of truth" is a potential single point of failure — verify redundancy
- UniversalX trading interface has done $440M+ volume
