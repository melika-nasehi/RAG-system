
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# "gemini" , "ollama"
#BACKEND = os.getenv("LLM_BACKEND", "ollama")
BACKEND = os.getenv("LLM_BACKEND", "gemini")


GEMINI_MODEL = "gemini-3.5-flash-lite"
OLLAMA_MODEL = "qwen3:4b"

AGENTROUTER_MODEL = "deepseek-v4-flash"
AGENTROUTER_BASE_URL = "https://agentrouter.org/v1"

TEMPERATURE = 0.1


def _load_env():
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _generate_gemini(system_prompt, user_message, max_retries=3):
    from google import genai
    from google.genai import types
    from google.genai.errors import ClientError
    import time

    _load_env()
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not found — check .env")

    client = genai.Client(api_key=api_key, vertexai=False)

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=TEMPERATURE,
                ),
            )
            return response.text
        except ClientError as error:
            if "RESOURCE_EXHAUSTED" in str(error) and attempt < max_retries - 1:
                wait = 15 * (attempt + 1)
                print(f"    rate limited, waiting {wait}s...", flush=True)
                time.sleep(wait)
                continue
            raise


def _generate_ollama(system_prompt, user_message):
    import ollama

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        options={"temperature": TEMPERATURE},
        keep_alive="30m",
    )
    return response["message"]["content"]


def _generate_agentrouter(system_prompt, user_message):
    from openai import OpenAI

    _load_env()
    api_key = os.environ.get("AGENTROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("AGENTROUTER_API_KEY not found — check .env")

    client = OpenAI(api_key=api_key, base_url=AGENTROUTER_BASE_URL)
    response = client.chat.completions.create(
        model=AGENTROUTER_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=TEMPERATURE,
    )
    return response.choices[0].message.content


def generate(system_prompt, user_message, backend=None):
    chosen = backend or BACKEND

    if chosen == "gemini":
        return _generate_gemini(system_prompt, user_message)
    if chosen == "ollama":
        return _generate_ollama(system_prompt, user_message)
    if chosen == "agentrouter":
        return _generate_agentrouter(system_prompt, user_message)

    raise ValueError(f"unknown backend: {chosen}")


def active_backend():
    return {
        "gemini": f"gemini / {GEMINI_MODEL}",
        "ollama": f"ollama / {OLLAMA_MODEL}",
        "agentrouter": f"agentrouter / {AGENTROUTER_MODEL}",
    }.get(BACKEND, BACKEND)