# Method

How an entry in `products/` is researched and written. It applies to people and
to agents alike; an agent asked to analyse a protocol should follow this file.

- `CONSTRAINT.md` and `DESIGN_IMPLICATIONS.md`: why exits are analysed this way.
- `CRITERIA.md`: the facets an entry records, and the current model built on them.

The model will change; the facts shouldn't have to. Record what is true, what it
takes to break it, and what isn't known yet. If a finding doesn't fit a facet,
record it anyway and say so.

## One entry per product

Each file in `products/` covers one product, or one mode of a product when the
modes have different exits (Hashflow same-chain and X-Chain; CCTP Standard and
Fast). A standard or framework that many parties deploy (x402, OIF,
NTT, OFT, Hyperlane Warp) gets `framework: true`. Rate only what the standard
fixes, leave what deployments choose as `unknown`, and give each deployment
that matters its own entry. Never fill a framework's facts from its most
favourable deployment, such as a self-hosted reference service. Facts the modes share aren't copied: point at the entry that holds them
with `inherits` and `service: {same_as: <slug>}`.

## Steps

### 1. Find the sources

- The project's own documentation, not aggregator summaries.
- The contract source: GitHub or GitLab, or verified source on a block explorer
  at the deployed address, which is definitive.
- Off-chain components that decide things: order books, auction servers,
  attestation or relayer services, solver or keeper code.
- Audits, post-mortems, forum threads and news for incidents.

Clone repositories with `git clone --depth 1 <url> source/<name>` and add each to
the entry's `sources` list with its URL, commit and commit date. `source/` isn't
committed.

If a source is hard to find: check the docs' developer section, the org's pinned
repositories on GitHub, verified source at the deployed address, and L2BEAT or
DefiLlama. If a URL has moved, follow it and record where it went.

### 2. Read the exit path in source

Start from how a user gets funds back when things go wrong, and trace it in code:
who calls what, when, under whose authority, and what can stop it. Documentation
describes intent; source describes behaviour, and they diverge. Where they
disagree, say so in the entry. That is some of the most useful data here.

Then read everything that can reach the exit: owners, admin and upgrade paths,
pausers, role managers, messaging and attestation layers, automatic halts, and
any screening.

### 3. Read live configuration on-chain

Who holds each role, thresholds, timelocks and delays are set at deployment, not
in the repository. Read them with targeted calls (`eth_call`, `eth_getStorageAt`,
`eth_getCode`) against a public RPC, and record what was read, on which chains,
and when. Check whether an owner is a multisig and what its threshold is.

Don't install packages (`pip`, `npm -g`) or write anywhere outside this
repository; function selectors can be looked up or hard-coded.

Don't run broad event-log scans over public RPCs; they are slow and often hang.
If an answer needs one (every pool ever created, every dispute), make it an open
question.

### 4. Answer the questions

For each section of `CRITERIA.md`: exit path, actors, admin, data gates,
judgment, censorship resistance (the `service` facts) and incidents. Also answer
the integration questions below.

Record normal operation and what it takes to break it, separately. For each way
of breaking it, say who, what it takes (one key, or m of n, as numbers), whether
it reaches one user or everyone, whether anything bounds it, and what it costs
the party. Don't label these with the adversary names in `CRITERIA.md`; those
are worked out from the facts.

### Censorship resistance: test it live

Documentation describes intent here too, and it's often vaguer than for
contracts. Establish the `service` facts by asking the operator's own API.

- **API key.** Call the quote and order endpoints with no key and record the
  status code and error text. Docs that say "all requests require a key" and an
  API that answers without one are both worth recording; the live response
  decides the fact. Note the per-key or global rate limits.
- **Identity.** How a key is obtained: self-serve dashboard, email, support
  ticket, partnership form, KYC. Record whether keyless use is possible at all.
- **Screening.** Request a quote, and an order where creating one needs no
  signature, from an address that is currently sanctioned and from a fresh
  unflagged one, and compare. Confirm the flagged address is still sanctioned
  first, for example with `isSanctioned` on the Chainalysis oracle
  (`0x40C57923924B5c5c5455c48D93317139ADDaC8fb` on most EVM chains); delisted
  addresses (Tornado Cash) prove nothing. Test on a chain without the oracle as
  well: a refusal there shows a second list. Note geo-blocking from the docs or
  terms.
- **Orders without funds.** Create orders the API builds for you to sign, but
  never sign or send them. Decode the returned transaction to find the
  contracts users actually call. If a well-known address is refused, generate a
  fresh random one rather than reusing a real user's.
- **Bypass.** On-chain permissionlessness isn't enough. Show that orders
  created outside the operator are filled in practice (fills of orders the API
  never saw, or a documented independent filler), or record `unknown`.

Record each request (endpoint, chain, address used, status, error text) and the
date in the entry's sources, so a later reader can repeat it.

### 5. Integration

What an integrator has to build and run to use the protocol. Recorded, not
rated.

- **Calls and signatures.** Which contract calls, and what the user or
  integrator signs (EIP-712 orders, permits, Permit2, EIP-3009, approvals).
- **Off-chain services required.** Quote, order, attestation or status APIs;
  whether they need an API key; whether they are rate-limited.
- **Who finishes the job.** Does the integrator have to relay, claim, mint,
  finalise or trigger a refund, or does someone else? What happens if nobody
  does?
- **Gas.** Who pays, on which chains, and whether a transfer can start from an
  account holding no native gas. Record which token standards that works for
  (`gasless_start`).
- **Paid steps.** List every step the flow can need in `actions`: start,
  cancel, refund, claim, and any proof or finalisation. For each, record who may
  perform it, and whether they're paid for it in the same transaction from the
  assets in the step (CRITERIA.md, Paid execution). Read this from the
  contracts: a refund function with no fee or bounty to its caller pays no one,
  whatever the docs say about "anyone can call it".
- **Monitoring.** What has to be polled or watched to know the outcome, and
  what the failure states look like.
- **Deployment data.** Where contract addresses and supported chains and tokens
  are published.
- **Tooling.** SDKs, their language and licence; testnet availability.
- **Effort.** The number of distinct steps from start to finished, and anything
  unusual (cross-chain proofs, a separate VM, bespoke encodings).

### 6. Write the entry

The file opens with a YAML header between `---` lines, then the analysis text.
The header format is not final. Until it is reconciled, follow the shape of the
most recently written entries (`skip-go-fast.md`, `hashflow-xchain.md`), with
these rules:

- Anything not established is `unknown`, with an item in `open_questions` saying
  what would settle it. Don't leave fields out; don't guess.
- Thresholds, delays and bounds go in fields as numbers. A fact never lives only
  in a YAML comment.
- Quote any string containing `: ` so it stays a string. Check that the header
  parses and that `open_questions` are all strings.
- Set `updated` to the date of the research.

The text below the header explains the findings, citing files by name, with line
numbers where they help narrow things down (`HubPool.sol:797`). List every URL
consulted with the date retrieved, including ones that returned nothing useful,
so later work knows what was checked. Commit hashes go only in the header's
`sources` list, not in the text.

### 7. Verification levels

Per facet group in the header:

- `spec-only`: from documentation only.
- `partial`: some of it read in source or on-chain.
- `source-verified`: read in source, and live configuration checked on-chain.

Incident history is `reviewed`, `partial` or `not-reviewed`.

## Quality

- Prefer source over documentation, and on-chain state over source defaults.
- Don't summarise code in ways that could be wrong. Name the function and say
  what it does.
- Incident history comes from post-mortems, forum posts, audits and news, not
  marketing pages claiming no downtime.
- Don't extrapolate from similar protocols; each one made its own choices.
- If exit behaviour is genuinely unspecified in public, say so and note that it
  needs the team to confirm.

## Reporting back

An agent finishing an entry reports: the key findings with file citations;
the live API tests behind the censorship facts;
anything the previous version of the entry got wrong; which facts decide each
part of the rating under the current `CRITERIA.md`; the open questions; and any
repositories cloned, with URL and commit.
