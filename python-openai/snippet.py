import os
from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("SINGIT_BASE_URL", "https://app.singitai.app/v1"),
    api_key=os.environ["SINGIT_API_KEY"],
    max_retries=0,
)
reply = client.chat.completions.create(
    model=os.environ.get("SINGIT_MODEL", "deepseek-v4.1-flash"),
    messages=[{"role": "user", "content": "Reply with one word: pong"}],
    max_tokens=200,
)
print(reply.choices[0].message.content)
