# Gasless starts

How a token can be moved from an account that holds no native gas, when
someone else may pay the gas only if they are repaid in the same transaction
from the job's own tokens. This page records each token's own gasless path.
Relayers, paymasters, bundlers and EIP-7702 delegates
get entries of their own.

Everything below was read on-chain on 2026-10-06 unless a line says otherwise.

## Each token's own path

The functions were found by their selectors in the deployed bytecode, following
EIP-1967 and beacon proxies to the implementation. Domains were checked by
recomputing `DOMAIN_SEPARATOR` (or `getDomainSeperator`, as Polygon's PoS tokens
spell it).

| Chain | Token | Address | EIP-2612 | DAI permit | EIP-3009 | Meta-tx | EIP-712 domain |
|---|---|---|---|---|---|---|---|
| Ethereum | WETH | `0xC02a…6Cc2` | – | – | – | – | none |
| Ethereum | WBTC | `0x2260…C599` | – | – | – | – | none |
| Ethereum | USDC | `0xA0b8…eB48` | yes, and `bytes` signature | – | yes, and `bytes` signature | – | standard, version 2 |
| Ethereum | USDT | `0xdAC1…1ec7` | – | – | – | – | none |
| Ethereum | DAI | `0x6B17…1d0F` | – | yes | – | – | standard, version 1 |
| Polygon | WPOL | `0x0d50…1270` | – | – | – | – | none |
| Polygon | WETH | `0x7ceB…f619` | – | – | – | yes | salted, version 1 |
| Polygon | WBTC | `0x1BFD…BfD6` | – | – | – | yes | salted, version 1 |
| Polygon | USDC | `0x3c49…3359` | yes, and `bytes` signature | – | yes, and `bytes` signature | – | standard, version 2 |
| Polygon | USDC.e | `0x2791…4174` | yes | – | yes | yes | salted, version 1 |
| Polygon | USDT0 | `0xc213…8e8F` | yes | – | – | yes | salted, version 1 |
| Polygon | DAI | `0x8f3C…A063` | – | yes | – | yes | salted, version 1 |
| BNB Chain | ETH (Binance-Peg) | `0x2170…33F8` | – | – | – | – | none |
| BNB Chain | BTCB (Binance-Peg) | `0x7130…ad9c` | – | – | – | – | none |
| BNB Chain | WBNB | `0xbb4C…095c` | – | – | – | – | none |
| BNB Chain | USDC (Binance-Peg) | `0x8AC7…580d` | – | – | – | – | none |
| BNB Chain | USDT (Binance-Peg) | `0x55d3…7955` | – | – | – | – | none |
| Base | WETH | `0x4200…0006` | – | – | – | – | none |
| Base | USDC | `0x8335…2913` | yes, and `bytes` signature | – | yes, and `bytes` signature | – | standard, version 2 |
| Base | cbBTC | `0xcbB7…33Bf` | yes | – | yes | – | standard, version 2 |
| Arbitrum | WETH | `0x82aF…Bab1` | yes | – | – | – | standard, version 1 |
| Arbitrum | WBTC | `0x2f2a…5B0f` | yes | – | – | – | standard, version 1 |
| Arbitrum | USDC | `0xaf88…5831` | yes, and `bytes` signature | – | yes, and `bytes` signature | – | standard, version 2 |
| Arbitrum | USDT0 | `0xFd08…bb9` | yes, and `bytes` signature | – | yes, and `bytes` signature | – | standard, version 1 |
| Arbitrum | DAI | `0xDA10…0da1` | yes | – | – | – | standard, version 2 |

"Standard" means `EIP712Domain(name, version, chainId, verifyingContract)`.
"Salted" means `EIP712Domain(name, version, verifyingContract, bytes32 salt)`
with the chain id as the salt. A signer must use the token's own form, so x402's
`exact` scheme, which names a standard domain, can't sign for USDC.e on
Polygon. The `bytes` signature variants of USDC and USDT0 accept an ERC-1271
signature from a contract account as well as an ECDSA one.

## What this changes

- **Arbitrum: confirmed.** The gateway's bridged WETH and WBTC (a beacon proxy,
  implementation `0x3f77…ad46`) carry EIP-2612, so every token on the list can
  start gasless there.
- **Arbitrum DAI uses standard EIP-2612,** not DAI's own permit. The permit
  encoding differs from DAI's on Ethereum and Polygon.
- **Polygon WETH and WBTC can start gasless through `executeMetaTransaction`.**
  - **What the user signs:** `MetaTransaction(nonce, from, functionSignature)`,
    where `functionSignature` is one exact call to the token itself, for
    example `approve(spender, amount)`.
  - **Who sends it:** anyone. The token then runs that call with the signer as
    the caller.
  - **What it can and can't do:** the signature binds that call and a
    sequential nonce, so a submitter can't change the spender or the amount.
    It can only send the call or withhold it.
  - **No expiry:** the signature stays valid until the account uses that nonce.
  - **Delegated accounts:** it works for an account delegated by EIP-7702,
    since it is checked against the account's key.
  - **CoW:** it can therefore carry an `approve` of CoW's VaultRelayer in a
    pre-hook, as a permit is carried today. The solver pays the gas and is
    repaid from the order.

  Source: `pos-portal` `contracts/common/NativeMetaTransaction.sol`. Its type
  string is present in the deployed bytecode of Polygon WETH, WBTC, DAI and
  USDT0, and `getNonce` answers. That WBTC, DAI and USDT0 also have it adds a
  second route alongside their permits.
- **Still blocked, with no path of their own:**
  - the wrapped native tokens (Ethereum WETH, Base WETH, Polygon WPOL,
    BNB Chain WBNB);
  - Ethereum WBTC;
  - the Binance-Peg ETH and BTCB on BNB Chain.

  These need an EIP-7702 batch, paid for in the same transaction by someone
  who takes that token or what the batch turns it into. Ethereum USDT and the
  Binance-Peg USDC and USDT have no path of their own either, but 1Shot takes
  USDC and USDT as its fee, so a batch can pay with the token it moves.
- **Wrapped native tokens have one advantage.** A batch can call `withdraw` and
  pay the submitter in native gas within the same transaction. So any relayer
  or searcher willing to take native gas as its fee will do; it doesn't need
  to accept the wrapped token.
- **The other blocked tokens can be swapped inside the batch first.** A slice
  can be swapped to a token the relayer takes, on an on-chain pool, before
  paying it. Whether 1Shot accepts a fee that only exists partway through the
  batch decides whether this works today; see Open questions.

## Venues that start without gas

Read from each venue's contracts, 2026-10-07. "Paid in the call" means the
submitter is repaid from the user's tokens in the same transaction, by an amount
the user signed. Details and sources are in each entry.

| Venue | Entry point | Tokens | Who submits | How they're repaid |
|---|---|---|---|---|
| **Across** | `SpokePoolPeriphery` `depositWithPermit`, `depositWithPermit2`, `depositWithAuthorization` (`0x97CCDBea4632140639aD5eA9b944aa034eb15fD4` current, six chains checked, immutable; testnet `0x10D8b8DaA26d307489803e10477De69C0492B610`) | EIP-2612, EIP-3009, Permit2-approved | anyone | paid in the call: `submissionFees`, signed; a zero recipient pays the submitter |
| **Mayan Swift** | `createOrderWithSig` | EIP-2612, or already approved | anyone | credited in the call: `submissionFee`, signed, credited to the submitter in Mayan's FeeManager |
| **DZap** (Core and Fuse) | `GasLessFacetV2` `execute*` on DZapDiamond; `DZapZapCore.executeZap` | EIP-2612 (Permit2 and allowances need a prior approval) | anyone, **but only with DZap's co-signature** (a fee-validator or zap-verifier EOA) | paid in the call: the executor fee, signed |
| **CoW** | a permit in the order's pre-hook (or a Polygon meta-transaction, above) | EIP-2612, DAI permit | allowlisted solvers | from the order, within the signed limit price |
| **LI.FI Intent, OIF** | `openFor` | EIP-3009, Permit2-approved | anyone, or the order server | not in the call; the solver is paid when the order is finalised |
| **x402** | facilitator settles `transferWithAuthorization` | EIP-3009 | the facilitator | by the payee, not from the payment |
| **NEAR Intents (1Click)** | any transfer that lands in the deposit address, such as a CoW order's `receiver` | anything that can be delivered | whoever delivers | not by 1Click |

**Further steps that pay for themselves:**
- **Mayan Swift:** the refund submitter is credited `refundFee` in the same
  call. The canceller is credited `cancelFee` only later, on the source chain,
  having fronted destination gas and the Wormhole fee.
  An order can also deliver native gas on the destination (`gasDrop`), which
  can unlock destination tokens with no permit.
- **1Click:** delivery and refunds take their fees from the assets.
- **CCTP:** destination minting through Circle's Forwarding Service is paid
  from the transfer.

**Read, and not gasless:**
- **Skip Go Fast:** `submitOrderWithPermit` pulls Permit2 tokens from
  `msg.sender`, so the user sends it.
- **Garden:** `initiateWithSignature` can be sent by anyone, but it pays them
  nothing and needs a prior approval.
- **deBridge:** `createOrder` takes a native fixed fee.
- **Omni Bridge:** `initTransfer` takes tokens from `msg.sender`.
- **UniswapX and The Compact:** they need a Permit2 approval by transaction
  first.

## Open questions

- Whether 1Shot accepts a fee produced inside the batch, for example
  `[approve, swap a slice of WBTC to USDC, pay the fee, …]`. If so, every
  blocked token with an on-chain pool to USDC or USDT can start gasless
  through 1Shot today.
- Which relayers take native gas as the fee for a batch that unwraps WETH,
  WPOL or WBNB.
- Upgrade authority over Polygon's PoS token proxies (WBTC, DAI, USDT0, USDC.e)
  and Arbitrum's gateway beacon. An upgrade could remove or change the path.

## Sources

- On-chain reads by `eth_call`, `eth_getCode` and `eth_getStorageAt` against
  Ethereum, Polygon, BNB Chain, Base and Arbitrum public RPCs, 2026-10-06.
- `pos-portal` (github.com/maticnetwork/pos-portal) at `3402faa`,
  `contracts/common/NativeMetaTransaction.sol` and `ContextMixin.sol`, cloned
  2026-10-06.
- polygon.blockscout.com returned a Cloudflare challenge for verified source,
  2026-10-06. sourcify.dev answered 200 but returned no sources for the field
  requested.
