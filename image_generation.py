from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline

LOCAL_LORA_PATH = Path(__file__).parent / "models" / "RealisticAnimeIXL_v2.safetensors"
DEFAULT_MODEL_ID = (
    str(LOCAL_LORA_PATH)
    if LOCAL_LORA_PATH.is_file()
    else "stable-diffusion-v1-5/stable-diffusion-v1-5"
)
MODEL_ID = os.getenv(
    "DIFFUSERS_MODEL",
    DEFAULT_MODEL_ID,
)
SDXL_BASE_MODEL = os.getenv(
    "DIFFUSERS_BASE_MODEL",
    "stabilityai/stable-diffusion-xl-base-1.0",
)

_pipeline: StableDiffusionPipeline | StableDiffusionXLPipeline | None = None
_is_sdxl = False
_pipeline_lock = Lock()
logger = logging.getLogger("comicbookgenerator")


def _load_sdxl_lora(pipeline, model_path: Path) -> None:
    state_dict, network_alphas, metadata = pipeline.lora_state_dict(
        str(model_path),
        unet_config=pipeline.unet.config,
        return_lora_metadata=True,
    )
    unet_state_dict = {
        key: value for key, value in state_dict.items() if key.startswith("unet.")
    }
    skipped_keys = len(state_dict) - len(unet_state_dict)
    if not unet_state_dict:
        raise ValueError(f"No U-Net LoRA weights were found in {model_path.name}.")

    pipeline.load_lora_into_unet(
        unet_state_dict,
        network_alphas=network_alphas,
        unet=pipeline.unet,
        metadata=metadata,
        _pipeline=pipeline,
    )
    if skipped_keys:
        logger.warning(
            "Loaded U-Net LoRA weights from %s; skipped %d text-encoder weights "
            "because this checkpoint is not compatible with the current "
            "Diffusers text-encoder adapter loader",
            model_path.name,
            skipped_keys,
        )


def _fit_prompt_to_tokenizer(prompt: str, tokenizer) -> tuple[str, int]:
    token_count = len(tokenizer.tokenize(prompt))
    max_length = tokenizer.model_max_length
    special_token_count = tokenizer.num_special_tokens_to_add(pair=False)
    if token_count + special_token_count <= max_length:
        return prompt, 0

    encoded = tokenizer(
        prompt,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
    fitted_prompt = tokenizer.decode(
        encoded.input_ids[0],
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )
    return fitted_prompt, token_count + special_token_count - max_length


def _load_pipeline(torch):
    global _is_sdxl

    from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    model_path = Path(MODEL_ID)

    if model_path.is_file() and model_path.suffix.lower() == ".safetensors":
        from safetensors import safe_open

        with safe_open(str(model_path), framework="pt", device="cpu") as checkpoint:
            metadata = checkpoint.metadata() or {}
            is_lora = any(key.startswith("lora_") for key in checkpoint.keys())

        architecture = metadata.get("modelspec.architecture", "").lower()
        is_sdxl = "sdxl" in architecture or "stable-diffusion-xl" in architecture
        if is_lora:
            if not is_sdxl:
                raise ValueError(
                    "The configured LoRA checkpoint is not marked as an SDXL adapter."
                )
            pipeline = StableDiffusionXLPipeline.from_pretrained(
                SDXL_BASE_MODEL,
                torch_dtype=dtype,
                use_safetensors=True,
            )
            _load_sdxl_lora(pipeline, model_path)
        elif is_sdxl:
            pipeline = StableDiffusionXLPipeline.from_single_file(
                str(model_path),
                torch_dtype=dtype,
            )
        else:
            pipeline = StableDiffusionPipeline.from_single_file(
                str(model_path),
                torch_dtype=dtype,
            )
    elif model_path.is_file():
        pipeline = StableDiffusionPipeline.from_single_file(
            str(model_path),
            torch_dtype=dtype,
        )
    else:
        pipeline = StableDiffusionPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=dtype,
            use_safetensors=True,
        )

    _is_sdxl = isinstance(pipeline, StableDiffusionXLPipeline)
    if device == "cuda" and _is_sdxl:
        pipeline.enable_model_cpu_offload()
    else:
        pipeline.to(device)
        pipeline.enable_attention_slicing()
    return pipeline


def generate_image(prompt: str) -> bytes:
    """Generate a PNG using the configured local Stable Diffusion pipeline."""
    global _pipeline

    with _pipeline_lock:
        import torch

        if _pipeline is None:
            _pipeline = _load_pipeline(torch)

        prompt_arguments = {"prompt": prompt}
        if _is_sdxl:
            original_prompt = prompt
            prompt, first_removed = _fit_prompt_to_tokenizer(
                original_prompt, _pipeline.tokenizer
            )
            prompt_2, second_removed = _fit_prompt_to_tokenizer(
                original_prompt, _pipeline.tokenizer_2
            )
            prompt_arguments = {"prompt": prompt, "prompt_2": prompt_2}
            if first_removed or second_removed:
                logger.warning(
                    "Image prompt exceeded SDXL's 77-token encoder limit; "
                    "truncated %d tokens for encoder 1 and %d for encoder 2",
                    first_removed,
                    second_removed,
                )

        result = _pipeline(
            **prompt_arguments,
            height=1024 if _is_sdxl else 512,
            width=1024 if _is_sdxl else 512,
            num_inference_steps=20,
        )
        image = result.images[0]

    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
