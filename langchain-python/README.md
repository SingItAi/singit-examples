# LangChain ChatOpenAI and a function tool round trip

Standalone Python 3.10+ example.

```bash
cd langchain-python
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
```

The key route pays from a prepaid SingIt balance. Key caps are checked by SingIt's
server, not onchain. The Base contract limits what SingIt can buy from the owner's wallet,
for example balance top-ups. Tools and real streaming only work when the server has its proxy on.

```bash
export SINGIT_API_KEY=sk_singit_REPLACE_WITH_YOUR_KEY
# Optional: SINGIT_MODEL (default deepseek-v4.1-flash)
# Optional: SINGIT_BASE_URL (default https://app.singitai.app/v1)
python example.py "Reply with one word: pong"
```

No default key is supplied; keys are never printed. Retries are disabled. Errors print a
one-line explanation and exit non-zero. `snippet.py` is the literal website snippet;
`example.py` is safe to import and exposes `ask(prompt, env=os.environ)`.

`ask_with_tool(prompt)` binds `word_count`, runs the requested function locally, and sends its result back. Only expose tools you intend to let the model run.

| Status | Code | Meaning |
|---|---|---|
| 429 | `insufficient_quota` | Daily key cap used up, including requests still running; resets at 00:00 UTC. |
| 429 | `rate_limit_exceeded` | Slow down: 60 requests a minute. |
| 400 | `over_request_limit` | Lower max_tokens, send less input, pick a cheaper model, or make a key with a higher per-request limit. |
| 401 | `invalid_api_key` | Invalid or revoked key; create one in the SingIt app. |
| 402 | `balance_low` | Top up the prepaid balance in the SingIt app, Settings, API keys. |
| 403 | `agent_paused` | The owner has paused their agent (emergency stop); nothing is charged. |
| 503 | `payments_paused` | Payments are paused. |
| 400 | `tools_unsupported` | Tools are not offered yet; server proxy is off. |

Not run against the live service in this repo: the tests use a local mock; run it yourself with a small key.
