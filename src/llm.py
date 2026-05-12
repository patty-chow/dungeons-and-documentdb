"""LLM chat client -- Anthropic Claude (preferred) or OpenAI fallback.

The provider is auto-detected from env vars:
  - ANTHROPIC_API_KEY present -> Anthropic Claude.
  - OPENAI_API_KEY present    -> OpenAI chat completions.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def _provider() -> str:
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    raise RuntimeError(
        "No LLM provider configured. Set ANTHROPIC_API_KEY (preferred) "
        "or OPENAI_API_KEY in your .env file."
    )


def provider_name() -> str:
    """Friendly name of the configured LLM provider."""
    return _provider()


def chat(system: str, user: str, max_tokens: int = 600) -> str:
    """Single-turn chat. Returns the assistant's text reply."""
    if _provider() == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in resp.content if hasattr(block, "text")
        )

    # OpenAI fallback
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content or ""
