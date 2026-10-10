from pydantic import BaseModel, Field


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


class CharacterAttributes(BaseModel):
    age: str = Field(min_length=1, max_length=100)
    gender: str = Field(min_length=1, max_length=100)
    hair_colour: str = Field(min_length=1, max_length=100)
    eye_colour: str = Field(min_length=1, max_length=100)
    skin_colour: str = Field(min_length=1, max_length=100)
    body_type: str = Field(min_length=1, max_length=100)
    specific_features: str = Field(default="", max_length=500)
    style: str = Field(default="bright, expressive comic art", max_length=200)


class CharacterPromptOptions(BaseModel):
    age: str | None = Field(default=None, max_length=100)
    gender: str | None = Field(default=None, max_length=100)
    hair_colour: str | None = Field(default=None, max_length=100)
    eye_colour: str | None = Field(default=None, max_length=100)
    skin_colour: str | None = Field(default=None, max_length=100)
    body_type: str | None = Field(default=None, max_length=100)
    specific_features: str = Field(default="", max_length=500)
    style: str = Field(default="bright, expressive comic art", max_length=200)


class CharacterPromptResponse(BaseModel):
    prompt: str


class GeneratedPanel(BaseModel):
    description: str
    dialogue: str = ""
    image_prompt: str


class GeneratedPanels(BaseModel):
    panels: list[GeneratedPanel]
