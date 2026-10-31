<div align="center">

# SingIt examples

**Runnable recipes for using SingIt from agent frameworks: the SingIt MCP tools and x402-paid chat.**

[![CI](https://img.shields.io/github/actions/workflow/status/SingItAi/singit-examples/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/SingItAi/singit-examples/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Node](https://img.shields.io/badge/Node-%E2%89%A520-339933?style=flat-square&logo=node.js&logoColor=white)](langchain/package.json)
[![x402](https://img.shields.io/badge/x402-USDC-purple?style=flat-square)](https://x402.org)

[Integrations guide](https://singitai.app/integrations/) · [TypeScript SDK](https://github.com/SingItAi/singit-js) · [Python SDK](https://github.com/SingItAi/singit-python) · [MCP server](https://github.com/SingItAi/singit-mcp)

</div>

Each folder is a standalone package with its own `package.json` and lockfile.

| Example | Framework | What it shows |
|---|---|---|
| [`langchain/`](langchain) | LangChain.js | SingIt MCP tools through `@langchain/mcp-adapters`, and paid chat through `ChatOpenAI` |
| [`vercel-ai-sdk/`](vercel-ai-sdk) | Vercel AI SDK | SingIt MCP tools through the AI SDK's MCP client, and paid chat through an OpenAI-compatible provider |

## Run one

```bash
cd langchain            # or vercel-ai-sdk
npm ci
npm test                # offline, against local mocks
npm start               # free mode: live MCP tools and an unpaid 402 probe
```

Free mode needs no key and makes no payment. It loads the live MCP tools, calls the free `get_price`
tool, and sends one unpaid request to SingIt Ask to print the payment offers it gets back.

## Paid mode

Paid mode spends real USDC on Base and is off unless you set every variable below, with limits you
choose. Do not run it with a wallet you are not willing to spend from.

```bash
export SINGIT_ALLOW_PAID=1
export SINGIT_EVM_PRIVATE_KEY=0x...   # your own wallet, funded with USDC on Base
export SINGIT_MAX_PER_CALL_USD=0.01
export SINGIT_MAX_PER_DAY_USD=1
node src/run.mjs paid "What is x402?"
```

Before anything is signed, the example checks that the offer is on Base, that it pays the expected
SingIt Ask address in the expected USDC contract, and that it is within both ceilings. These checks
are in each example's `src/x402/` folder: a trimmed copy of the guards in
[`@singitai/sdk`](https://github.com/SingItAi/singit-js). The ceilings are client-side and the daily
one lives in memory, so it restarts with the process.

## Not here yet

- Python and other languages: there are no Python examples here yet. The
  [Python SDK](https://github.com/SingItAi/singit-python) has its own README.
- The examples carry their own copy of the guards instead of depending on `@singitai/sdk`, so a fix
  in the SDK has to be copied over by hand.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md). Security problems: email contact@singitai.app, not a public
issue ([SECURITY.md](SECURITY.md)). MIT licensed.
