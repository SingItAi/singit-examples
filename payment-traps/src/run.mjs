import assert from 'node:assert/strict';
import { SingIt, SingItPaymentError, NETWORKS } from '@singitai/sdk';
import { generatePrivateKey } from 'viem/accounts';
import { generateKeyPairSigner, getTransactionDecoder, verifySignature } from '@solana/kit';
import { startMerchant, startRpc, decode, dispatchLocal } from './mock-merchant.mjs';
import { traps } from './traps.mjs';

export const cases = traps.flatMap(trap => trap.covered === 'no' ? [{ trap, network: null }] :
  (trap.networks ?? ['base', 'solana']).map(network => ({ trap, network })));

export async function runScenario(trap, network) {
  if (trap.covered === 'no') return { trap, network, message: 'not covered', signatures: '—', result: 'not covered' };
  const originalFetch = globalThis.fetch;
  // Applies to SDK fetch and the Solana RPC transport: external traffic cannot escape.
  globalThis.fetch = (input, init) => {
    const url = new URL(input instanceof Request ? input.url : input);
    assert.equal(url.hostname, '127.0.0.1', 'Only loopback traffic is permitted');
    assert.equal(url.protocol, 'http:');
    return dispatchLocal(input, init) ?? originalFetch(input, init);
  };
  let merchant, rpc;
  try {
    const pin = NETWORKS[network];
    const signer = network === 'solana' ? await generateKeyPairSigner() : null;
    rpc = await startRpc();
    const offer = { scheme: 'upto', network: pin.caip, asset: pin.asset, payTo: pin.payTo,
      amount: trap.amount ?? '4000', maxTimeoutSeconds: trap.timeout ?? 120,
      extra: network === 'base' ? { facilitatorAddress: '0x1111111111111111111111111111111111111111',
        name: pin.assetName, version: pin.assetVersion, assetTransferMethod: 'permit2' } : {
        feePayer: (await generateKeyPairSigner()).address, receiverAuthorizer: pin.payTo, withdrawDelay: 120,
        billing: { maxChargeAtomic: trap.amount ?? '4000' } } };
    if (trap.id === 'payee') offer.payTo = `${pin.payTo.slice(0, -1)}${pin.payTo.endsWith('1') ? '2' : '1'}`;
    if (trap.id === 'case') offer.payTo = pin.payTo.replace('a', 'A');
    if (trap.id === 'asset') offer.asset = `${pin.asset.slice(0, -1)}1`;
    merchant = await startMerchant({ offer, billed: trap.billed, afterPayment: trap.afterPayment,
      challenge: challenge => {
        if (trap.id === 'resource') challenge.resource.url += '/different';
        return challenge;
      },
      receipt: receipt => {
        if (trap.id === 'missingReceipt') return null;
        if (trap.id === 'receiptNetwork') receipt.network = 'different:network';
        if (trap.id === 'receiptPayer') receipt.payer = network === 'base'
          ? '0x2222222222222222222222222222222222222222' : offer.extra.feePayer;
        return receipt;
      },
    });
    const client = new SingIt({ network, baseUrl: merchant.url, rpcUrl: rpc.url,
      evmPrivateKey: generatePrivateKey(), solanaSigner: signer,
      maxPerCallUsd: 0.006, maxPerDayUsd: (trap.day ?? 10000) / 1e6 });
    const chat = () => client.chat({ messages: [{ role: 'user', content: 'Local fixture request.' }] });
    if (trap.id === 'price') {
      const listed = await client.pricing();
      assert.equal(listed.amountAtomic, '4000');
      assert.ok(BigInt(listed.amountAtomic) <= BigInt(client.maxPerCallAtomic));
    }
    const before = Math.floor(Date.now() / 1000);
    if (trap.duplicate) {
      for (let i = 1; i <= 2; i++) {
        const answer = await chat();
        assert.equal(answer.payment.amountAtomic, '4000');
        assert.equal(merchant.signatures.length, i, 'One signature per separate successful call');
        assert.equal(client.limiter.remainingAtomic(), 10000n - BigInt(i) * 4000n);
      }
    }
    let error;
    if (trap.pattern) {
      await assert.rejects(chat, thrown => {
        assert.ok(thrown instanceof SingItPaymentError);
        assert.match(thrown.message, trap.pattern); error = thrown; return true;
      });
    } else {
      const answer = await chat();
      assert.equal(answer.payment.amountAtomic, '4000');
      assert.equal(answer.payment.txHash, undefined);
    }
    assert.equal(merchant.signatures.length, trap.signatures);
    assert.equal(client.limiter.remainingAtomic(), trap.remaining);
    if (trap.follow) {
      await assert.rejects(chat, thrown => {
        assert.ok(thrown instanceof SingItPaymentError);
        assert.match(thrown.message, /Daily spend cap reached/); return true;
      });
      assert.equal(merchant.signatures.length, trap.signatures, 'Following call must not sign');
      assert.equal(client.limiter.remainingAtomic(), trap.remaining);
    }
    const expectedRequests = (trap.duplicate ? 5 : trap.signatures + 1) + (trap.follow ? 1 : 0) + (trap.id === 'price' ? 1 : 0);
    assert.equal(merchant.requests.length, expectedRequests, 'No automatic HTTP repeat');
    for (const header of merchant.signatures) {
      const payment = decode(header);
      assert.equal(payment.accepted.amount, '4000');
      assert.equal(payment.accepted.maxTimeoutSeconds, 120);
      if (network === 'base') {
        const auth = payment.payload.permit2Authorization;
        assert.equal(auth.permitted.amount, '4000');
        assert.ok(BigInt(auth.deadline) >= BigInt(before));
        assert.ok(BigInt(auth.deadline) <= BigInt(Math.floor(Date.now() / 1000) + 120));
        assert.match(payment.payload.signature, /^0x[0-9a-f]+$/i);
      } else {
        const transaction = getTransactionDecoder().decode(Buffer.from(payment.payload.openTransaction, 'base64'));
        assert.equal(await verifySignature(signer.keyPair.publicKey, transaction.signatures[signer.address], transaction.messageBytes), true);
        assert.equal(payment.payload.maxAmount, '4000');
      }
    }
    assert.deepEqual(rpc.errors, []);
    if (!trap.signatures || network === 'base') assert.deepEqual(rpc.calls, []);
    else assert.ok(rpc.calls.includes('getLatestBlockhash'));
    // Use the observed error, with volatile connection details removed for reproducible output.
    const message = error ? (trap.afterPayment === 'drop'
      ? error.message.slice(error.message.indexOf('it was not repeated'))
      : error.message.split(' (')[0]) : 'Accepted without receipt';
    return { trap, network, message, signatures: merchant.signatures.length,
      result: `${trap.covered === 'partial' ? 'partial' : 'pass'}; remaining ${client.limiter.remainingAtomic()} atomic; ${trap.signatures ? (trap.id === 'repeat402' ? 'mock refused' : 'mock only, no real charge') : 'unsigned'}` };
  } finally {
    await merchant?.close(); await rpc?.close(); globalThis.fetch = originalFetch;
  }
}
export async function runAll() {
  const results = [];
  for (const { trap, network } of cases) results.push(await runScenario(trap, network));
  return results;
}
export function markdown(results) {
  const escape = value => String(value).replaceAll('|', '\\|').replaceAll('\n', ' ');
  return ['| trap | SingIt check that fired | error code or message (short) | signatures sent | result |',
    '|---|---|---|---|---|', ...results.map(row => `| ${[
      `${row.trap.type}: ${row.trap.scenario}${row.network ? ` (${row.network})` : ''}`,
      row.trap.check, row.message, row.signatures, row.result,
    ].map(escape).join(' | ')} |`)].join('\n');
}
