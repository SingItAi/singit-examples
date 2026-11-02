import ast
import asyncio
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
import openai
import example


def completion(tool=False):
    message = {"role": "assistant", "content": "pong"}
    if tool:
        message = {"role": "assistant", "content": None, "tool_calls": [{
            "id": "call_1", "type": "function", "function": {
                "name": "word_count", "arguments": '{"text":"hello world"}'}}]}
    return {"id": "chatcmpl-local", "object": "chat.completion", "created": 0,
            "model": "deepseek-v4.1-flash", "choices": [{"index": 0, "message": message,
            "finish_reason": "tool_calls" if tool else "stop"}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
            "billing": {"totalAtomic": "100"}}


@pytest.fixture
def env(server):
    return {"SINGIT_BASE_URL": server.url + "/v1", "SINGIT_API_KEY": "sk_singit_offline_fake"}


CASES = [
 (429, "insufficient_quota", "insufficient_quota", "This key's daily limit of 1 USDC is used up, counting requests still running. It starts again at 00:00 UTC, or raise it with a new key.", "RateLimitError", "Daily key cap"),
 (429, "rate_limit_error", "rate_limit_exceeded", "This key sends up to 60 requests a minute. Slow down.", "RateLimitError", "Rate limit"),
 (400, "invalid_request_error", "over_request_limit", "This request may cost up to 0.0500 USDC, above this key's limit of 0.01 USDC per request. Ask for less, or make a key with a higher limit.", "BadRequestError", "lower max_tokens"),
 (401, "authentication_error", "invalid_api_key", "Invalid or revoked API key. Create one in the SingIt app.", "AuthenticationError", "Invalid or revoked"),
 (402, "insufficient_quota", "balance_low", "Prepaid SingIt balance too low.", "APIStatusError", "Settings, API keys"),
 (403, "insufficient_quota", "agent_paused", "Your agent is paused (emergency stop)", "PermissionDeniedError", "owner has paused"),
 (503, "api_error", "payments_paused", "Payments are paused.", "InternalServerError", "Payments are paused"),
 (400, "invalid_request_error", "tools_unsupported", "Tools are not offered yet.", "BadRequestError", "proxy on"),
]


def error_reply(case):
    status, kind, code, message, _, _ = case
    return status, {"error": {"message": message, "type": kind, "code": code}}, {}


def test_success(server, env):
    server.replies = [(200, completion(), {"X-SingIt-Charged-Atomic": "100"})]
    assert example.ask("ping", env) == "pong"
    assert len(server.requests) == 1
    path, headers, body = server.requests[0]
    assert path == "/v1/chat/completions"
    assert headers["Authorization"] == "Bearer sk_singit_offline_fake"
    assert body["model"] == "deepseek-v4.1-flash"
    assert body.get("max_tokens", body.get("max_completion_tokens")) == 200


@pytest.mark.parametrize("case", CASES, ids=[c[2] for c in CASES])
def test_errors(server, env, case):
    server.replies = [error_reply(case)]
    cls = getattr(openai, case[4])
    if Path(example.__file__).parent.name == "litellm-python":
        import litellm
        cls = getattr(litellm, {"APIStatusError": "APIError", "InternalServerError": "ServiceUnavailableError"}.get(case[4], case[4]))
    with pytest.raises(cls) as caught:
        example.ask("ping", env)
    assert case[5] in example.describe_error(caught.value)
    assert "\n" not in example.describe_error(caught.value)
    assert len(server.requests) == 1


def test_snippet():
    root = Path(example.__file__).parent
    snippet = (root / "snippet.py").read_text()
    compile(snippet, "snippet.py", "exec")
    source = (root / "example.py").read_text()
    # Both must use the same SDK calls and the same explicit retry/token settings.
    def calls(text):
        return {ast.unparse(n.func) for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Call)}
    expected = {"python-openai": "client.chat.completions.create", "langchain-python": "ChatOpenAI",
                "litellm-python": "litellm.completion", "openai-agents-python": "OpenAIChatCompletionsModel"}[root.name]
    assert expected in calls(source) & calls(snippet)
    assert "max_tokens=200" in source and "max_tokens=200" in snippet


def test_cli_error(server, env, monkeypatch, capsys):
    for k,v in env.items(): monkeypatch.setenv(k,v)
    server.replies = [error_reply(CASES[0])]
    assert example.main(["ping"]) == 1
    assert "Daily key cap" in capsys.readouterr().out


def test_tool_then_daily_cap(server, env):
    from agents import function_tool
    calls = []
    @function_tool
    def word_count(text: str) -> int:
        """Count words."""
        calls.append(text)
        return len(text.split())
    server.replies = [(200, completion(True), {}), error_reply(CASES[0])]
    with pytest.raises(openai.RateLimitError):
        asyncio.run(example.run_agent("count", env, [word_count]))
    assert calls == ["hello world"]
    assert len(server.requests) == 2
    assert server.requests[1][2]["messages"][-1]["role"] == "tool"


def test_does_not_read_or_write_openai_key(server, env, monkeypatch):
    original_get = os._Environ.__getitem__
    original_set = os._Environ.__setitem__
    def get(self, name):
        assert name != "OPENAI_API_KEY"
        return original_get(self, name)
    def put(self, name, value):
        assert name != "OPENAI_API_KEY"
        return original_set(self, name, value)
    monkeypatch.setattr(os._Environ, "__getitem__", get)
    monkeypatch.setattr(os._Environ, "__setitem__", put)
    server.replies = [(200, completion(), {})]
    assert example.ask("ping", env) == "pong"
