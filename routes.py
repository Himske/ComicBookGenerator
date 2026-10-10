import logging
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from image_generation import generate_image
from models import (
    CharacterAttributes,
    CharacterPromptOptions,
    CharacterPromptResponse,
    ComicRequest,
    ComicResponse,
    GeneratedPanels,
    ImageGenerationRequest,
    Panel,
)
from text_generation import TRANSFORMERS_MODEL, generate_text

router = APIRouter()
logger = logging.getLogger("comicbookgenerator")
STATIC_PATH = Path(__file__).parent / "static"
MAX_EXAMPLE_IMAGE_BYTES = 10 * 1024 * 1024
MAX_EXAMPLE_IMAGES = 5


def generate_character_prompt(
    attributes: CharacterAttributes | CharacterPromptOptions,
    example_images: list[bytes] | None = None,
) -> CharacterPromptResponse:
    """Create a character image prompt from attributes and optional reference images."""
    specified_attributes = [
        ("Age", attributes.age),
        ("Gender", attributes.gender),
        ("Hair colour", attributes.hair_colour),
        ("Eye colour", attributes.eye_colour),
        ("Skin colour", attributes.skin_colour),
        ("Body type", attributes.body_type),
    ]
    attribute_details = "\n".join(
        f"{label}: {value}"
        for label, value in specified_attributes
        if value and value.strip()
    )
    messages = [
        {
            "role": "system",
            "content": (
                "Write a single image-generation prompt for a character reference "
                "image. When reference images are provided, use them to guide the "
                "character's visual design while following the explicit attributes. "
                "Return only the prompt without reasoning or commentary."
            ),
        },
        {
            "role": "user",
            "content": (
                "Create one polished image-generation prompt for a character "
                "reference image. Include the character's full-body appearance, "
                "a clear readable pose, and a simple uncluttered background. Keep "
                "the prompt concise and do not add contradictory details. Use the "
                "reference images as the source of truth for any traits not "
                "specified below.\n"
                f"{attribute_details or 'No character traits specified.'}\n"
                f"Specific features: {attributes.specific_features or 'none specified'}\n"
                f"Art style: {attributes.style}"
            ),
        },
    ]
    prompt = generate_text(
        messages,
        images=example_images,
        max_new_tokens=512,
    )
    if not prompt:
        logger.error(
            "Configured Transformers model returned an empty character prompt "
            "model=%s",
            TRANSFORMERS_MODEL,
        )
        raise HTTPException(
            status_code=502,
            detail="The configured text model returned an empty character prompt.",
        )
    return CharacterPromptResponse(prompt=prompt)


async def read_example_images(example_images: list[UploadFile]) -> list[bytes]:
    if len(example_images) > MAX_EXAMPLE_IMAGES:
        raise HTTPException(
            status_code=413,
            detail=f"Upload no more than {MAX_EXAMPLE_IMAGES} example images.",
        )

    images = []
    allowed_content_types = {"image/jpeg", "image/png", "image/webp"}
    for image in example_images:
        if image.content_type not in allowed_content_types:
            raise HTTPException(
                status_code=415,
                detail="Example images must be JPEG, PNG, or WebP files.",
            )
        contents = await image.read(MAX_EXAMPLE_IMAGE_BYTES + 1)
        if len(contents) > MAX_EXAMPLE_IMAGE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Each example image must be 10 MB or smaller.",
            )
        images.append(contents)
    return images


def generate_panels(request: ComicRequest) -> list[Panel]:
    """Generate a comic storyboard using the selected local text model."""
    messages = [
        {
            "role": "system",
            "content": (
                "Create concise, coherent comic panels that advance the story. "
                "Keep characters visually consistent. Return the requested "
                "number of panels and follow the provided JSON schema."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Premise: {request.premise}\n"
                f"Art style: {request.style}\n"
                f"Create exactly {request.panel_count} panels."
            ),
        },
    ]
    response_text = generate_text(
        messages,
        json_schema=GeneratedPanels.model_json_schema(),
        max_new_tokens=2048,
    )
    try:
        generated = GeneratedPanels.model_validate_json(response_text)
    except ValidationError as error:
        logger.exception(
            "Configured Transformers model returned invalid comic JSON model=%s",
            TRANSFORMERS_MODEL,
        )
        raise HTTPException(
            status_code=502,
            detail="The configured text model returned invalid comic JSON.",
        ) from error
    if len(generated.panels) != request.panel_count:
        raise HTTPException(
            status_code=502,
            detail=(
                f"The configured text model returned {len(generated.panels)} "
                f"panels; expected {request.panel_count}."
            ),
        )

    return [
        Panel(number=number, **panel.model_dump())
        for number, panel in enumerate(generated.panels, start=1)
    ]


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/comics", response_model=ComicResponse)
def create_comic(request: ComicRequest):
    return ComicResponse(
        comic_id=str(uuid4()),
        premise=request.premise,
        style=request.style,
        panels=generate_panels(request),
    )


@router.post("/character-prompt", response_model=CharacterPromptResponse)
def create_character_prompt(attributes: CharacterAttributes):
    return generate_character_prompt(attributes)


@router.post(
    "/character-prompt/from-examples",
    response_model=CharacterPromptResponse,
)
async def create_character_prompt_from_examples(
    age: Annotated[str, Form(max_length=100)] = "",
    gender: Annotated[str, Form(max_length=100)] = "",
    hair_colour: Annotated[str, Form(max_length=100)] = "",
    eye_colour: Annotated[str, Form(max_length=100)] = "",
    skin_colour: Annotated[str, Form(max_length=100)] = "",
    body_type: Annotated[str, Form(max_length=100)] = "",
    specific_features: Annotated[str, Form(max_length=500)] = "",
    style: Annotated[
        str, Form(max_length=200)
    ] = "bright, expressive comic art",
    example_images: Annotated[list[UploadFile] | None, File()] = None,
):
    images = await read_example_images(example_images or [])
    entered_attributes = [
        age,
        gender,
        hair_colour,
        eye_colour,
        skin_colour,
        body_type,
    ]
    if not images and any(not value.strip() for value in entered_attributes):
        raise HTTPException(
            status_code=422,
            detail="Provide all six character traits or upload at least one example image.",
        )

    attributes = CharacterPromptOptions(
        age=age or None,
        gender=gender or None,
        hair_colour=hair_colour or None,
        eye_colour=eye_colour or None,
        skin_colour=skin_colour or None,
        body_type=body_type or None,
        specific_features=specific_features,
        style=style,
    )
    return await run_in_threadpool(
        generate_character_prompt, attributes, images or None
    )


@router.post("/images", response_class=Response)
async def create_image(request: ImageGenerationRequest):
    try:
        image_bytes = await run_in_threadpool(generate_image, request.prompt)
    except ModuleNotFoundError as error:
        logger.exception("Image generation dependencies are unavailable")
        raise HTTPException(
            status_code=503,
            detail="Image generation dependencies are not installed. See the setup instructions.",
        ) from error
    except Exception as error:
        logger.exception("Stable Diffusion image generation failed")
        raise HTTPException(
            status_code=500,
            detail="Image generation failed. Check the backend logs for details.",
        ) from error
    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="character.png"'},
    )


@router.get("/", include_in_schema=False)
def frontend():
    return FileResponse(
        STATIC_PATH / "index.html",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/character/traits", include_in_schema=False)
def character_traits_page():
    return FileResponse(
        STATIC_PATH / "character-traits.html",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/character/examples", include_in_schema=False)
def character_examples_page():
    return FileResponse(
        STATIC_PATH / "character-examples.html",
        headers={"Cache-Control": "no-cache"},
    )
