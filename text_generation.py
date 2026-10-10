from __future__ import annotations

import logging
import os
from typing import Any

import ollama
from fastapi import HTTPException

logger = logging.getLogger("comicbookgenerator")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")


def generate_text(
    messages: list[dict[str, str]],
    *,
    images: list[bytes] | None = None,
    json_schema: dict[str, Any] | None = None,
    max_new_tokens: int = 1024,
) -> str:
    chat_messages: list[dict[str, Any]] = [
        {"role": message["role"], "content": message["content"]}
        for message in messages
    ]
    if images:
        user_message = next(
            message
            for message in reversed(chat_messages)
            if message["role"] == "user"
        )
        user_message["images"] = images

    try:
        response = ollama.Client(host=OLLAMA_HOST).chat(
            model=OLLAMA_MODEL,
            messages=chat_messages,
            format=json_schema or "",
            options={"num_predict": max_new_tokens},
            think=False,
        )
    except ollama.RequestError as error:
        logger.exception("Ollama connection failed during text generation")
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to the configured Ollama server: {error}",
        ) from error
    except ollama.ResponseError as error:
        logger.exception("Ollama rejected text generation")
        raise HTTPException(
            status_code=502,
            detail=f"Ollama could not generate a response: {error.error}",
        ) from error

    return response.message.content.strip()
