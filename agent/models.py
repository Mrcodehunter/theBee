"""models.py — registry of chat model backends the agent can run on.

Adding a new provider is a matter of adding an entry to AVAILABLE_MODELS and
a branch in build_llm(); everything else (graph, tools, UI) is provider-
agnostic and just deals in model ids.

Every provider here has a free tier, but every one of them also needs an API
key from that provider (there is no bundled zero-signup default anymore —
that used to be the local Ollama entry). Set at least one of the env vars
below (directly or via agent/.env) before the agent will actually respond.
"""

import os

AVAILABLE_MODELS = [
    {
        "id": "ollama-cloud-gpt-oss-20b",
        "label": "GPT-OSS 20B (Ollama Cloud, free)",
        "provider": "ollama-cloud",
        "model": "gpt-oss:20b-cloud",
    },
    {
        "id": "gemini-3-5-flash",
        "label": "Gemini 3.5 Flash (free)",
        "provider": "google",
        "model": "gemini-3.5-flash",
    },
    {
        "id": "groq-llama-3-3-70b",
        "label": "Llama 3.3 70B (Groq, free)",
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
    },
    {
        "id": "openrouter-llama-3-3-70b",
        "label": "Llama 3.3 70B (OpenRouter, free)",
        "provider": "openrouter",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
    },
    {"id": "claude-sonnet-5", "label": "Claude Sonnet 5", "provider": "anthropic", "model": "claude-sonnet-5"},
]

DEFAULT_MODEL_ID = "groq-llama-3-3-70b"

# Which env var proves a provider is configured.
_PROVIDER_ENV_VAR = {
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "ollama-cloud": "OLLAMA_API_KEY",
}

_BY_ID = {m["id"]: m for m in AVAILABLE_MODELS}


def get_model_info(model_id: str) -> dict:
    if model_id not in _BY_ID:
        raise ValueError(f"Unknown model id: {model_id}")
    return _BY_ID[model_id]


def is_available(model_id: str) -> bool:
    """Whether this model can actually be used right now (e.g. API key set)."""
    info = _BY_ID.get(model_id)
    if info is None:
        return False
    env_var = _PROVIDER_ENV_VAR.get(info["provider"])
    return bool(os.environ.get(env_var)) if env_var else True


def list_models() -> list[dict]:
    return [{**m, "available": is_available(m["id"])} for m in AVAILABLE_MODELS]


# Of the registered models, only these actually accept image input — Groq's
# llama-3.3-70b-versatile, OpenRouter's free Llama, and Ollama Cloud's
# gpt-oss:20b-cloud are all text-only. Tools that need vision (see
# tools/image_tools.py) use this instead of whatever model the user
# happens to be chatting with, so image analysis works regardless of the
# active conversation model.
VISION_CAPABLE_MODELS = ["claude-sonnet-5", "gemini-3-5-flash"]


def get_vision_model_id() -> str | None:
    """First vision-capable model that's actually configured, or None."""
    return next((m for m in VISION_CAPABLE_MODELS if is_available(m)), None)


def build_llm(model_id: str):
    """Construct the raw (un-bound) chat model for a given model id."""
    info = get_model_info(model_id)
    provider = info["provider"]

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=info["model"], temperature=0)

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model=info["model"], temperature=0)

    if provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(model=info["model"], temperature=0)

    if provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=info["model"],
            temperature=0,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY"),
        )

    if provider == "ollama-cloud":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=info["model"],
            temperature=0,
            base_url="https://ollama.com",
            client_kwargs={"headers": {"Authorization": f"Bearer {os.environ.get('OLLAMA_API_KEY', '')}"}},
        )

    raise ValueError(f"Unknown provider for model id: {model_id}")
