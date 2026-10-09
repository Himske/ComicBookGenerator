import os
from pathlib import Path
from uuid import uuid4

import ollama
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Comic Generator API", version="0.1.0")
FRONTEND_PATH = Path(__file__).parent / "static" / "index.html"

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")


class ComicRequest(BaseModel):
    premise: str = Field(min_length=5, max_length=2_000)
    panel_count: int = Field(default=4, ge=1, le=12)
    style: str = Field(default="bright, expressive comic art", max_length=200)


class Panel(BaseModel):
    number: int
    description: str
    dialogue: str = ""
    image_prompt: str


class ComicResponse(BaseModel):
    comic_id: str
    premise: str
    style: str
    panels: list[Panel]


class GeneratedPanel(BaseModel):
    description: str
    dialogue: str = ""
    image_prompt: str


class GeneratedPanels(BaseModel):
    panels: list[GeneratedPanel]


def generate_panels(request: ComicRequest) -> list[Panel]:
    """Generate a comic storyboard using the configured local Ollama model."""
    response = ollama.Client(host=OLLAMA_HOST).chat(
        model=OLLAMA_MODEL,
        messages=[
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
        ],
        format=GeneratedPanels.model_json_schema(),
    )
    generated = GeneratedPanels.model_validate_json(response.message.content)
    if len(generated.panels) != request.panel_count:
        raise HTTPException(
            status_code=502,
            detail=(
                "The configured Ollama model returned "
                f"{len(generated.panels)} panels; expected {request.panel_count}."
            ),
        )

    return [
        Panel(number=number, **panel.model_dump())
        for number, panel in enumerate(generated.panels, start=1)
    ]


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/comics", response_model=ComicResponse)
def create_comic(request: ComicRequest):
    return ComicResponse(
        comic_id=str(uuid4()),
        premise=request.premise,
        style=request.style,
        panels=generate_panels(request),
    )


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND_PATH)
