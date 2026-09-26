from __future__ import annotations

import os

import requests


def summarize(prompt: str, timeout: int = 45) -> str:
    key = os.environ["GROQ_API_KEY"]
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions", timeout=timeout,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        },
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

