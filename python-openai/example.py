import os
from openai import OpenAI


def ask(prompt, env=os.environ):
    client = OpenAI(
        base_url=env.get("SINGIT_BASE_URL", "https://app.singitai.app/v1"),
        api_key=key(env),
        max_retries=0,
        timeout=5.0,
    )
    with client:
        reply = client.chat.completions.create(
            model=env.get("SINGIT_MODEL", "deepseek-v4.1-flash"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        return reply.choices[0].message.content


def stream_answer(prompt, env=os.environ):
    # Require a finish_reason as well as transport completion: the SDK accepts EOF
    # without [DONE], which otherwise silently returns a partial answer.
    with OpenAI(base_url=env.get("SINGIT_BASE_URL", "https://app.singitai.app/v1"),
                api_key=key(env), max_retries=0, timeout=2.0) as client:
        parts = []
        finished = False
        try:
            with client.chat.completions.create(
                model=env.get("SINGIT_MODEL", "deepseek-v4.1-flash"),
                messages=[{"role": "user", "content": prompt}], max_tokens=200, stream=True,
            ) as stream:
                for chunk in stream:
                    for choice in chunk.choices:
                        parts.append(choice.delta.content or "")
                        finished = finished or choice.finish_reason is not None
        except Exception as exc:
            raise StreamEndedEarly() from exc
        if not finished:
            raise StreamEndedEarly()
        return "".join(parts)

ERRORS = {
    "insufficient_quota": "Daily key cap used up; resets at 00:00 UTC. Raise it with a new key.",
    "rate_limit_exceeded": "Rate limit: slow down (60 requests a minute).",
    "over_request_limit": "Per-request limit: lower max_tokens, send less input, pick a cheaper model, or make a key with a higher per-request limit.",
    "invalid_api_key": "Invalid or revoked API key; create one in the SingIt app.",
    "balance_low": "Prepaid balance too low; top up in the SingIt app, Settings, API keys.",
    "agent_paused": "Returned when the owner has paused their agent.",
    "payments_paused": "Payments are paused; try again later.",
    "tools_unsupported": "Tools are not offered yet; the server needs its proxy on.",
}


def describe_error(exc) -> str:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error", body)
        if isinstance(error, dict) and error.get("code") in ERRORS:
            return ERRORS[error["code"]]
    # LiteLLM may retain the HTTP response rather than OpenAI's parsed body.
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            code = response.json().get("error", {}).get("code")
            if code in ERRORS:
                return ERRORS[code]
        except (ValueError, AttributeError):
            pass
    # Match specific codes before insufficient_quota, which is also an error type.
    codes = [code for code in ERRORS if code != "insufficient_quota"] + ["insufficient_quota"]
    detail = str(exc) + " " + str(getattr(exc, "__context__", ""))
    for code in codes:
        message = ERRORS[code]
        if code in detail:
            return message
    if isinstance(exc, StreamEndedEarly):
        return "The stream ended early; the answer may be incomplete."
    return "Request failed (" + type(exc).__name__ + "). Check configuration and connectivity."


class StreamEndedEarly(RuntimeError):
    pass


def key(env):
    value = env["SINGIT_API_KEY"]
    if not value.startswith("sk_singit_"):
        raise ValueError("SINGIT_API_KEY must start with sk_singit_")
    return value


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="?", default="Reply with one word: pong")
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(stream_answer(args.prompt) if args.stream else ask(args.prompt))
        return 0
    except Exception as exc:
        print(describe_error(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
