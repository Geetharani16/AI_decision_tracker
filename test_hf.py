import requests
import os

key = os.getenv("OPENROUTER_API_KEY")

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

data = {
    "model": "mistralai/mistral-7b-instruct",
    "messages": [
        {"role": "user", "content": "Say hello in one sentence"}
    ]
}

r = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers=headers,
    json=data
)

print(r.status_code)
print(r.text)
