# Payment traps

Offline scenarios against the installed `@singitai/sdk` **0.1.1**, using our own mock merchant and
throwaway keys generated for every scenario (`viem.generatePrivateKey` and Solana Kit signers).
No funded wallets, facilitator, chain broadcast, or real payments are involved. External fetches
are rejected; HTTP and fake RPC use only `127.0.0.1`.

These tests check the behaviour of the SingIt SDK and SingIt routes. They say nothing about other agents or wallets, and they are not a benchmark of anyone else.

Scenarios are written by us against our own code, with a mock merchant: they show that the guards
fire, not that every real merchant behaves like the mock. Route behaviour here is simulated,
not a test of the deployed service. Only the eight type names come from the public
[Agent Money Benchmark](https://agentmoneybench.com). No tasks, prose, prices, or tables from that
site are used. All fixture amounts and scenarios are ours. The two extra labels are our own.

Run with Node 20 or newer:

```sh
cd payment-traps
npm ci
npm test
npm start
```

`npm start` executes all scenarios and assertions and prints the observed mapping below. Each
covered scenario is also an individual `node:test` test. The final test compares this README table
with the report built from those same actual test results. There are no fabricated error codes:
SDK 0.1.1 exposes `SingItPaymentError` messages. Some messages omit their parenthesized allowance detail;
connection details are omitted to keep output reproducible. To refresh the table after a deliberate
scenario change, paste `npm start`'s table between the report markers and run the tests again.

`src/mock-merchant.mjs` normally starts actual loopback HTTP merchant and RPC servers. If the
sandbox denies listening with `EPERM`, it dispatches fetches in process through the same handlers,
including their request/header recording. This fallback models connection loss with a rejected
fetch; it does not test the operating system's HTTP transport. Both transports run the real SDK
signing code. Solana uses a read-only fake mint, slot, and blockhash RPC, verifies the resulting
transaction signature, and never broadcasts. Base signs locally without any RPC calls. All signing
paths in this table run on both networks; the case-only payee refusal is specifically Solana.
The scenarios use `upto`, which allows settlement below the signed ceiling; `exact` is not exercised.

In the table, signatures are PAYMENT-SIGNATURE headers actually received by the mock merchant,
not claims about settlement. Remaining allowance is in micro-USDC. All rows say whether anything
was signed; no row involves a real charge. A mock 200 is only a claimed settlement, and an unresolved
payment could have settled in a real deployment. A 402 releases the reservation because the SDK
treats it as proof of refusal; this assumption is not independently verified here.

<!-- report:start -->
| trap | SingIt check that fired | error code or message (short) | signatures sent | result |
|---|---|---|---|---|
| price above listed: Listed price within cap; challenge above cap (base) | selectOffer: per-call ceiling | Offer amount 7000 exceeds the configured per-call ceiling | 0 | pass; remaining 10000 atomic; unsigned |
| price above listed: Listed price within cap; challenge above cap (solana) | selectOffer: per-call ceiling | Offer amount 7000 exceeds the configured per-call ceiling | 0 | pass; remaining 10000 atomic; unsigned |
| price above listed: Invoice above signed ceiling (base) | Invoice ceiling validation | The invoice does not match the offered ceiling; treating the payment as unresolved | 1 | pass; remaining 6000 atomic; mock only, no real charge |
| price above listed: Invoice above signed ceiling (solana) | Invoice ceiling validation | The invoice does not match the offered ceiling; treating the payment as unresolved | 1 | pass; remaining 6000 atomic; mock only, no real charge |
| charged again after payment: 402 after signed request (base) | Single paid send; release on 402 | The merchant refused the payment | 1 | pass; remaining 10000 atomic; mock refused |
| charged again after payment: 402 after signed request (solana) | Single paid send; release on 402 | The merchant refused the payment | 1 | pass; remaining 10000 atomic; mock refused |
| charged again after payment: Application repeats successful chat; third call capped (base) | DailyLimiter.reserve | Daily spend cap reached: 8000 already spent today, 4000 more would exceed 10000 micro-USDC. | 2 | partial; remaining 2000 atomic; mock only, no real charge |
| charged again after payment: Application repeats successful chat; third call capped (solana) | DailyLimiter.reserve | Daily spend cap reached: 8000 already spent today, 4000 more would exceed 10000 micro-USDC. | 2 | partial; remaining 2000 atomic; mock only, no real charge |
| expired quote: Timeout window 0 (base) | selectOffer: timeout window | Unexpected payment timeout window in the offer. | 0 | partial; remaining 10000 atomic; unsigned |
| expired quote: Timeout window 0 (solana) | selectOffer: timeout window | Unexpected payment timeout window in the offer. | 0 | partial; remaining 10000 atomic; unsigned |
| expired quote: Timeout window 601 (base) | selectOffer: timeout window | Unexpected payment timeout window in the offer. | 0 | partial; remaining 10000 atomic; unsigned |
| expired quote: Timeout window 601 (solana) | selectOffer: timeout window | Unexpected payment timeout window in the offer. | 0 | partial; remaining 10000 atomic; unsigned |
| expired quote: Timeout window 1.5 (base) | selectOffer: timeout window | Unexpected payment timeout window in the offer. | 0 | partial; remaining 10000 atomic; unsigned |
| expired quote: Timeout window 1.5 (solana) | selectOffer: timeout window | Unexpected payment timeout window in the offer. | 0 | partial; remaining 10000 atomic; unsigned |
| lookalike payee: One-character recipient difference (base) | selectOffer: payee pin | Unexpected payee | 0 | pass; remaining 10000 atomic; unsigned |
| lookalike payee: One-character recipient difference (solana) | selectOffer: payee pin | Unexpected payee | 0 | pass; remaining 10000 atomic; unsigned |
| lookalike payee: Recipient case difference (solana) | selectOffer: case-sensitive Solana payee | Unexpected payee | 0 | pass; remaining 10000 atomic; unsigned |
| wrong asset (extra): Different asset address (base) | selectOffer: asset pin | Unexpected payment asset | 0 | pass; remaining 10000 atomic; unsigned |
| wrong asset (extra): Different asset address (solana) | selectOffer: asset pin | Unexpected payment asset | 0 | pass; remaining 10000 atomic; unsigned |
| receipt mismatch: Receipt names another network (base) | Receipt network validation | The settlement receipt does not match this request; treating the payment as unresolved. | 1 | pass; remaining 6000 atomic; mock only, no real charge |
| receipt mismatch: Receipt names another network (solana) | Receipt network validation | The settlement receipt does not match this request; treating the payment as unresolved. | 1 | pass; remaining 6000 atomic; mock only, no real charge |
| receipt mismatch: Receipt names another payer (base) | Receipt payer validation | The settlement receipt does not match this request; treating the payment as unresolved. | 1 | pass; remaining 6000 atomic; mock only, no real charge |
| receipt mismatch: Receipt names another payer (solana) | Receipt payer validation | The settlement receipt does not match this request; treating the payment as unresolved. | 1 | pass; remaining 6000 atomic; mock only, no real charge |
| receipt mismatch: Missing receipt accepted (base) | Receipt header optional | Accepted without receipt | 1 | partial; remaining 6000 atomic; mock only, no real charge |
| receipt mismatch: Missing receipt accepted (solana) | Receipt header optional | Accepted without receipt | 1 | partial; remaining 6000 atomic; mock only, no real charge |
| paid but not delivered: Paid response: 500; following call capped (base) | Single paid send; DailyLimiter.reserve | Paid request returned HTTP 500; it was not repeated, and its ceiling stays counted against the daily cap in case it settled. | 1 | pass; remaining 2000 atomic; mock only, no real charge |
| paid but not delivered: Paid response: 500; following call capped (solana) | Single paid send; DailyLimiter.reserve | Paid request returned HTTP 500; it was not repeated, and its ceiling stays counted against the daily cap in case it settled. | 1 | pass; remaining 2000 atomic; mock only, no real charge |
| paid but not delivered: Paid response: drop; following call capped (base) | Single paid send; DailyLimiter.reserve | it was not repeated and its ceiling stays counted against the daily cap. | 1 | pass; remaining 2000 atomic; mock only, no real charge |
| paid but not delivered: Paid response: drop; following call capped (solana) | Single paid send; DailyLimiter.reserve | it was not repeated and its ceiling stays counted against the daily cap. | 1 | pass; remaining 2000 atomic; mock only, no real charge |
| paid but not delivered: Paid response: unreadable; following call capped (base) | Invoice validation; DailyLimiter.reserve | The invoice does not match the offered ceiling; treating the payment as unresolved | 1 | pass; remaining 2000 atomic; mock only, no real charge |
| paid but not delivered: Paid response: unreadable; following call capped (solana) | Invoice validation; DailyLimiter.reserve | The invoice does not match the offered ceiling; treating the payment as unresolved | 1 | pass; remaining 2000 atomic; mock only, no real charge |
| over budget (extra): Per-call cap (base) | selectOffer: per-call ceiling | Offer amount 7000 exceeds the configured per-call ceiling | 0 | pass; remaining 10000 atomic; unsigned |
| over budget (extra): Per-call cap (solana) | selectOffer: per-call ceiling | Offer amount 7000 exceeds the configured per-call ceiling | 0 | pass; remaining 10000 atomic; unsigned |
| over budget (extra): Daily cap below offer (base) | DailyLimiter.reserve | Daily spend cap reached: 0 already spent today, 4000 more would exceed 3000 micro-USDC. | 0 | pass; remaining 3000 atomic; unsigned |
| over budget (extra): Daily cap below offer (solana) | DailyLimiter.reserve | Daily spend cap reached: 0 already spent today, 4000 more would exceed 3000 micro-USDC. | 0 | pass; remaining 3000 atomic; unsigned |
| resource mismatch (extra): Challenge names another URL (base) | selectOffer: resource URL | The challenge names a different resource than the one called. | 0 | pass; remaining 10000 atomic; unsigned |
| resource mismatch (extra): Challenge names another URL (solana) | selectOffer: resource URL | The challenge names a different resource than the one called. | 0 | pass; remaining 10000 atomic; unsigned |
| wrong data delivered: Content quality | Caller responsibility | not covered | — | not covered |
| hidden instructions: Instructions inside answer data | Consuming agent responsibility | not covered | — | not covered |
<!-- report:end -->

Coverage and limits:

- **price above listed — covered within the configured ceiling.** The pricing endpoint lists an
  amount within the call cap, while the subsequent challenge exceeds it: `selectOffer` refuses
  before signing. The SDK enforces the caller's cap, not equality to a previous price listing.
  An invoice above the signed offer is detected after payment as unresolved. This cannot prevent
  settlement of up to the already signed ceiling; it bounds the authorization and retains that
  ceiling in the daily allowance, without sending another payment.
- **charged again after payment — partial.** A 402 after a signed request raises an error, releases
  the reservation, and does not repeat the paid request. After a successful 200, a second application
  `chat()` is a new separate paid call, with one signature for each call. There is no application
  duplicate detection. The tests show two successful calls counted against the daily cap and the
  third refused without signing. Framework retries should therefore be disabled.
- **expired quote — partial.** Windows of zero, more than 600 seconds, and non-integer seconds are
  refused before signing. Successful Base signatures are checked for a bounded deadline; Solana
  signs transactions using the fake recent blockhash and configured window. The SDK has no
  wall-clock check of a quote's own expiry beyond the signed validity window. Facilitator-side
  rejection of an expired signature is not tested here; Solana cluster lifetime enforcement is
  also not tested.
- **lookalike payee — covered for the tested pins.** A one-character payee change is rejected on
  both networks using `NETWORKS`. Solana also rejects case-only changes. A different asset address
  is rejected too, listed as the extra label "wrong asset".
  EVM address case alone is deliberately not an error.
- **receipt mismatch — partial.** A different receipt network or payer leaves the payment
  unresolved and the full ceiling counted, with one signature and no repeat. A missing receipt
  header is accepted and is explicitly tested. Receipt success, transaction confirmation, and
  actual chain settlement are not independently verified by these tests.
- **paid but not delivered — covered for the tested failures.** HTTP 500, dropped fetch/connection,
  and malformed JSON all retain the ceiling. A following request that exceeds the remaining cap
  is refused without another signature. Invalid JSON is an unreadable invoice; the report shows
  the SDK's actual unresolved message (it does not literally say “not repeated” for that branch).
  Request counts prove no repeat in all three cases.
- **wrong data delivered — not covered.** The SDK pays for and returns what the merchant answers;
  judging content is the caller's job, and nothing here tests whether a bad answer is detected.
- **hidden instructions — not covered.** Text in a paid answer is returned to the caller verbatim
  as data. The SDK does not interpret it. Prompt-injection defence belongs to the consuming agent.
- **over budget (extra) — covered.** Separate daily and per-call cap refusals run on both networks.
- **resource mismatch (extra) — covered.** An offer naming a different resource URL is rejected
  before signing on both networks.

Allowance assertions use the public `client.limiter.remainingAtomic()` method; no private fields
are inspected. Client-side limits in SDK 0.1.1 are **in memory, per instance/process and UTC day**.
Restarting or making another instance resets the counter; there is no persistent spend log in
this version. These tests do not demonstrate durable accounting, on-chain spending controls,
real merchant honesty, real delivery, or production seller health checks.
