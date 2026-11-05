import http from 'node:http';
import { Readable } from 'node:stream';
import assert from 'node:assert/strict';
import { NETWORKS } from '@singitai/sdk';
export const encode = value => Buffer.from(JSON.stringify(value)).toString('base64');
export const decode = value => JSON.parse(Buffer.from(value, 'base64').toString());
const handlers = new Map();
let nextPort = 23000;
export function dispatchLocal(input, init) {
  const request = new Request(input, init);
  const handler = handlers.get(new URL(request.url).origin);
  if (!handler) return null;
  return (async () => {
    const body = Buffer.from(await request.arrayBuffer());
    const req = Readable.from([body]);
    req.url = new URL(request.url).pathname;
    req.method = request.method;
    req.headers = Object.fromEntries(request.headers);
    return new Promise((resolve, reject) => {
      req.socket = { destroy: () => reject(new TypeError('Mock connection dropped')) };
      let status = 200;
      const headers = new Headers();
      const res = {
        setHeader(name, value) { headers.set(name, value); },
        writeHead(code, values = {}) {
          status = code;
          for (const [name, value] of Object.entries(values)) headers.set(name, value);
          return res;
        },
        end(text = '') { resolve(new Response(text, { status, headers })); },
      };
      Promise.resolve(handler(req, res)).catch(reject);
    });
  })();
}
export async function listen(handler) {
  const server = http.createServer(handler);
  try {
    await new Promise((resolve, reject) => {
      server.once('error', reject);
      server.listen(0, '127.0.0.1', resolve);
    });
    return { transport: 'loopback HTTP', url: `http://127.0.0.1:${server.address().port}`, close: () => new Promise(resolve => {
      server.close(resolve); server.closeAllConnections();
    }) };
  } catch (error) {
    if (error.code !== 'EPERM') throw error;
    // Restricted sandboxes may deny even loopback listeners. Run the identical handlers in memory.
    const url = `http://127.0.0.1:${nextPort++}`;
    handlers.set(url, handler);
    return { transport: 'in-process (listen EPERM)', url, close: async () => { handlers.delete(url); } };
  }
}
export async function startMerchant({ offer, challenge = x => x, afterPayment = 'ok', receipt = x => x, billed = '4000' }) {
  const requests = [], signatures = [];
  const server = await listen(async (req, res) => {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const signature = req.headers['payment-signature'];
    requests.push({ url: req.url, headers: { ...req.headers }, body: Buffer.concat(chunks).toString() });
    if (req.url === '/pricing.json') {
      res.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify({ amountAtomic: '4000' })); return;
    }
    if (!signature) {
      res.writeHead(402, { 'payment-required': encode(challenge({ x402Version: 2,
        resource: { url: `${server.url}/v1/chat/completions` }, accepts: [offer] })) }).end('{}'); return;
    }
    signatures.push(signature);
    const payment = decode(signature);
    if (afterPayment === 'drop') { req.socket.destroy(); return; }
    if (afterPayment === '402' || afterPayment === '500') {
      res.writeHead(Number(afterPayment)).end('{}'); return;
    }
    const payer = payment.payload.permit2Authorization?.from ?? payment.payload.authorization?.from ?? payment.payload.from;
    const settled = receipt({ network: offer.network, payer, success: true });
    if (settled) res.setHeader('payment-response', encode(settled));
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(afterPayment === 'unreadable' ? '{' : JSON.stringify({
      choices: [{ message: { role: 'assistant', content: 'Mock answer data.' } }], billing: { totalAtomic: billed },
    }));
  });
  return { ...server, requests, signatures };
}
// Read-only fake RPC. Any attempt to broadcast or use another method fails.
export async function startRpc() {
  const calls = [], errors = [];
  const mint = Buffer.alloc(82); mint[44] = 6; mint[45] = 1;
  const server = await listen(async (req, res) => {
    let id;
    try {
      const chunks = []; for await (const chunk of req) chunks.push(chunk);
      const rpc = JSON.parse(Buffer.concat(chunks).toString()); id = rpc.id;
      calls.push(rpc.method);
      let result;
      switch (rpc.method) {
        case 'getAccountInfo':
          assert.equal(rpc.params[0], NETWORKS.solana.asset);
          result = { context: { slot: 7654321 }, value: { data: [mint.toString('base64'), 'base64'],
            executable: false, lamports: 1, owner: 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', rentEpoch: 0, space: 82 } }; break;
        case 'getLatestBlockhash': result = { context: { slot: 7654321 }, value: {
          blockhash: '11111111111111111111111111111111', lastValidBlockHeight: 7654421 } }; break;
        case 'getSlot': result = 7654321; break;
        default: throw new Error(`Unexpected RPC: ${rpc.method}`);
      }
      res.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify({ jsonrpc: '2.0', id, result }));
    } catch (error) {
      errors.push(error);
      res.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify({ jsonrpc: '2.0', id,
        error: { code: -32603, message: error.message } }));
    }
  });
  return { ...server, calls, errors };
}
