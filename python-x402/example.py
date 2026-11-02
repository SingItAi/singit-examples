"""Unpaid offer inspection by default; explicitly opt in to wallet payments."""
import base64
import json
import os
import urllib.error
import urllib.request
from singit import SingIt


def paid_client(env=os.environ, **options):
    if env.get("SINGIT_ALLOW_PAID") != "1":
        raise RuntimeError("Paid mode requires SINGIT_ALLOW_PAID=1")
    config = dict(
        evm_private_key=env["AGENT_PRIVATE_KEY"], network="base",
        base_url=env.get("SINGIT_BASE_URL", "https://ask.singitai.app"),
        max_per_call_usd=float(env["SINGIT_MAX_PER_CALL_USD"]),
        max_per_day_usd=float(env["SINGIT_MAX_PER_DAY_USD"]),
    )
    config.update(options)
    return SingIt(**config)


def ask(prompt, client):
    return client.chat(messages=[{"role": "user", "content": prompt}], max_tokens=200)


def free_offers(prompt, env=os.environ):
    body = json.dumps({"messages": [{"role": "user", "content": prompt}], "max_tokens": 200}).encode()
    request = urllib.request.Request(
        env.get("SINGIT_BASE_URL", "https://ask.singitai.app").rstrip("/") + "/v1/chat/completions",
        data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            raise RuntimeError("Expected unpaid HTTP 402, got " + str(response.status))
    except urllib.error.HTTPError as exc:
        with exc:
            if exc.code != 402:
                raise
            challenge = json.loads(base64.b64decode(exc.headers["PAYMENT-REQUIRED"]))
    return [{field: offer[field] for field in ("scheme", "network", "amount")} for offer in challenge["accepts"]]


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="?", default="Hello")
    args = parser.parse_args(argv)
    try:
        if os.environ.get("SINGIT_ALLOW_PAID") == "1":
            answer = ask(args.prompt, paid_client())
            print(answer["choices"][0]["message"]["content"])
            print(answer["payment"])
        else:
            for offer in free_offers(args.prompt):
                print(offer["scheme"], offer["network"], offer["amount"])
        return 0
    except Exception as exc:
        print("Request failed (" + type(exc).__name__ + "). Check offers and client-side limits.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
