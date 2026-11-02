import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage


def make_llm(env):
    return ChatOpenAI(
        model=env.get("SINGIT_MODEL", "deepseek-v4.1-flash"),
        base_url=env.get("SINGIT_BASE_URL", "https://app.singitai.app/v1"),
        api_key=key(env),
        max_retries=0,
        max_tokens=200,
        timeout=5.0,
    )


def ask(prompt, env=os.environ):
    llm = make_llm(env)
    return llm.invoke(prompt).content


def word_count(text: str) -> int:
    """Count the words in text."""
    return len(text.split())


def ask_with_tool(prompt, env=os.environ):
    llm = make_llm(env).bind_tools([word_count])
    messages = [("user", prompt)]
    answer = llm.invoke(messages)
    messages.append(answer)
    for call in answer.tool_calls:
        if call["name"] != "word_count":
            raise ValueError("Unknown tool")
        result = word_count(**call["args"])
        messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
    return llm.invoke(messages).content

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
    
    args = parser.parse_args(argv)
    try:
        print(ask(args.prompt))
        return 0
    except Exception as exc:
        print(describe_error(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
