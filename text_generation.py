from __future__ import annotations

import io
import json
import logging
import os
from threading import Lock
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger("comicbookgenerator")

TRANSFORMERS_MODEL = os.getenv("TRANSFORMERS_MODEL", "Qwen/Qwen3.5-4B")

_transformers_model: Any = None
_transformers_processor: Any = None
_transformers_lock = Lock()


def _load_transformers_model() -> tuple[Any, Any]:
    global _transformers_model, _transformers_processor

    if _transformers_model is None or _transformers_processor is None:
        try:
            import torch
            from transformers import AutoModelForImageTextToText, AutoProcessor
        except ModuleNotFoundError as error:
            logger.exception("Transformers model dependencies are unavailable")
            raise HTTPException(
                status_code=503,
                detail=(
                    "Transformers image-text generation dependencies are not "
                    "installed. Run uv sync and retry."
                ),
            ) from error

        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        _transformers_model = AutoModelForImageTextToText.from_pretrained(
            TRANSFORMERS_MODEL,
            dtype=dtype,
            device_map="auto",
        )
        _transformers_processor = AutoProcessor.from_pretrained(TRANSFORMERS_MODEL)

    return _transformers_model, _transformers_processor


def _generate_with_transformers(
    messages: list[dict[str, str]],
    images: list[bytes] | None,
    json_schema: dict[str, Any] | None,
    max_new_tokens: int,
) -> str:
    try:
        import torch
    except ModuleNotFoundError as error:
        logger.exception("PyTorch is unavailable for Transformers generation")
        raise HTTPException(
            status_code=503,
            detail="PyTorch is not installed. Run uv sync and retry.",
        ) from error

    with _transformers_lock:
        model, processor = _load_transformers_model()
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
            user_message["content"] = [
                *[_image_content(image) for image in images],
                {"type": "text", "text": user_message["content"]},
            ]

        if json_schema:
            system_message = next(
                message for message in chat_messages if message["role"] == "system"
            )
            system_message["content"] += (
                "\nReturn only valid JSON matching this schema, with no markdown "
                "fences or extra text:\n"
                f"{json.dumps(json_schema)}"
            )

        encoded = processor.apply_chat_template(
            chat_messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device)
        input_length = encoded["input_ids"].shape[1]
        with torch.inference_mode():
            generated_ids = model.generate(
                **encoded,
                max_new_tokens=max_new_tokens,
                do_sample=False,
            )
        output = processor.batch_decode(
            generated_ids[:, input_length:],
            skip_special_tokens=True,
        )[0].strip()
    return output


def _image_content(image_data: bytes) -> dict[str, Any]:
    try:
        from PIL import Image
    except ModuleNotFoundError as error:
        logger.exception("Pillow is unavailable for image prompt processing")
        raise HTTPException(
            status_code=503,
            detail="Pillow is not installed. Run uv sync and retry.",
        ) from error

    with Image.open(io.BytesIO(image_data)) as image:
        return {"type": "image", "image": image.convert("RGB")}


def generate_text(
    messages: list[dict[str, str]],
    *,
    images: list[bytes] | None = None,
    json_schema: dict[str, Any] | None = None,
    max_new_tokens: int = 1024,
) -> str:
    return _generate_with_transformers(
        messages,
        images,
        json_schema,
        max_new_tokens,
    )
