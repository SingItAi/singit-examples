import os
from singit import SingIt

if os.environ.get("SINGIT_ALLOW_PAID") != "1":
    raise RuntimeError("Paid mode requires SINGIT_ALLOW_PAID=1")
client = SingIt(
    evm_private_key=os.environ["AGENT_PRIVATE_KEY"], network="base",
    max_per_call_usd=float(os.environ["SINGIT_MAX_PER_CALL_USD"]),
    max_per_day_usd=float(os.environ["SINGIT_MAX_PER_DAY_USD"]),
)
answer = client.chat(messages=[{"role": "user", "content": "Hello"}], max_tokens=200)
print(answer["choices"][0]["message"]["content"])
print(answer["payment"])
