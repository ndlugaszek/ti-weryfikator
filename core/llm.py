import os
import json
import requests
from typing import Optional, Tuple, Iterator

FREE_MODELS = [
    "cohere/north-mini-code:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
]

def stream_openrouter_completion(
    prompt: str,
    system_prompt: str,
    api_key: str,
    model: Optional[str] = None
) -> Tuple[Iterator[str], str]:
    target_model = model or FREE_MODELS[0]
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "HTTP-Referer": "https://share.streamlit.io",
        "X-Title": "TI-Weryfikator-Akademicki",
        "Content-Type": "application/json"
    }
    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "stream": True
    }
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        data=json.dumps(payload),
        stream=True,
        timeout=25
    )
    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter status {resp.status_code}: {resp.text}")

    def generator():
        for line in resp.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8")
            if line_str.startswith("data: "):
                data_content = line_str[6:].strip()
                if data_content == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_content)
                    delta = chunk["choices"][0].get("delta", {}).get("content", "")
                    if delta:
                        yield delta
                except Exception:
                    continue

    return generator(), target_model
