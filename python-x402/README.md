# SingIt x402 wallet payments with client-side limits

Standalone Python 3.10+ example.

```bash
cd python-x402
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
```

Free mode sends one unpaid POST and prints the 402 offers' scheme, network and atomic
amount (USDC has six decimals). It does not call `SingIt.pricing()`, sign, or construct a
wallet client.

```bash
python example.py "Hello"
```

Paid mode spends real USDC and was NOT run for this repo. To opt in with your own funded
Base wallet, choose explicit limits:

```bash
export SINGIT_ALLOW_PAID=1
export AGENT_PRIVATE_KEY=REPLACE_WITH_YOUR_PRIVATE_KEY
export SINGIT_MAX_PER_CALL_USD=0.01
export SINGIT_MAX_PER_DAY_USD=1
python example.py "Hello"
```

`SINGIT_BASE_URL` overrides the default https://ask.singitai.app (without `/v1`).
`paid_client` refuses to construct the SDK unless `SINGIT_ALLOW_PAID=1`. The SDK checks
network, asset, payTo and ceilings before signing. The guards are client-side; the daily
counter is in memory, per client instance and UTC day, and resets on restart. Reuse one
client for multiple calls. A successful call prints the answer and `answer["payment"]`.
Solana needs `singit[svm]` and `exact`. No framework adapters exist for Python.

The local tests use Base Sepolia offers and throwaway keys, with no chain or facilitator.
They have not been run against the live service. This example pays per call from your own wallet
through x402; for the prepaid API-key route, see `python-openai/`.
