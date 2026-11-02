import os
from openai import AsyncOpenAI
from agents import Agent, ModelSettings, OpenAIChatCompletionsModel, Runner, set_tracing_disabled, function_tool

set_tracing_disabled(True)  # default tracing sends runs to OpenAI and uses OPENAI_API_KEY


async def run_agent(prompt, env=os.environ, tools=None):
    async with AsyncOpenAI(
        base_url=env.get("SINGIT_BASE_URL", "https://app.singitai.app/v1"),
        api_key=key(env),
        max_retries=0,
        timeout=5.0,
    ) as client:
        agent = Agent(
            name="singit-agent",
            instructions="Answer in one word.",
            model=OpenAIChatCompletionsModel(model=env.get("SINGIT_MODEL", "deepseek-v4.1-flash"), openai_client=client),
            model_settings=ModelSettings(max_tokens=200),
            tools=tools or [],
        )
        return await Runner.run(agent, prompt)


def ask(prompt, env=os.environ):
    import asyncio
    return asyncio.run(run_agent(prompt, env)).final_output

ERRORS = {
    "insufficient_quota": "Daily key cap used up; resets at 00:00 UTC. Raise it with a new key.",
    "rate_limit_exceeded": "Rate limit: slow down (60 requests a minute).",
    "over_request_limit": "Per-request limit: lower max_tokens, send less input, pick a cheaper model, or make a key with a higher per-request limit.",
    "invalid_api_key": "Invalid or revoked API key; create one in the SingIt app.",
    "balance_low": "Prepaid balance too low; top up in the SingIt app, Settings, API keys.",
    "agent_paused": "The owner has paused their agent (emergency stop); nothing is charged.",
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
