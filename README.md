# Comic Book Generator

## Run with a local Qwen model

Install [Ollama](https://ollama.com/download), start its local service, then
download the Qwen model:

```powershell
ollama pull qwen3.5:4b
```

Install the project dependencies and start the API:

```powershell
uv sync
uv run uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) for the comic generator.
Use the navigation to open separate pages for character prompts from traits or
example images.

The API connects to Ollama at `http://localhost:11434` and uses the downloaded
`qwen3.5:4b` model by default. Set `OLLAMA_HOST` and `OLLAMA_MODEL` before
starting the API to use a different local Ollama server or Qwen model tag. For
example:

```powershell
$env:OLLAMA_MODEL = "qwen3.5:4b"
uv run uvicorn main:app --reload
```

## Create a character image prompt

`POST /character-prompt` creates a character reference-image prompt from JSON
attributes: `age`, `gender`, `hair_colour`, `eye_colour`, `skin_colour`, and
`body_type`. Optional `specific_features` and `style` fields provide additional
direction.

To create a prompt from example images, send
`multipart/form-data` to `POST /character-prompt/from-examples`, attaching each
image as `example_images`. Character attributes are optional when images are
provided and can be included to guide the result. Without images, all six
attributes are required. The endpoint accepts up to five JPEG, PNG, or WebP
images, each up to 10 MB. Both endpoints return a `prompt` string and use the
configured local Ollama model.

The selected model must be available to the Ollama server before calling these
generation endpoints.

Backend requests are logged with a request ID, HTTP status, and duration.
Unhandled exceptions and Ollama failures include tracebacks. The ID is also
returned in the `X-Request-ID` response header. Set `LOG_LEVEL` (for example,
`DEBUG` or `WARNING`) to adjust the application log level.
