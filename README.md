# Comic Book Generator

## Text generation

Install the project dependencies and start the API:

```powershell
uv sync
uv run uvicorn main:app --reload
```

The app sends text prompts and optional reference images to the configured
Ollama server, using `qwen3.5:4b` by default. Start Ollama and pull the model
before using the text generation endpoints:

```powershell
ollama pull qwen3.5:4b
```

Set `OLLAMA_HOST` and `OLLAMA_MODEL` before starting the API to use another
Ollama server or model tag:

```powershell
$env:OLLAMA_HOST = "http://localhost:11434"
$env:OLLAMA_MODEL = "qwen3.5:4b"
uv run uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) for the comic generator.
Use the navigation to open separate pages for character prompts from traits or
example images.

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
configured Ollama model. The Ollama server must have the selected model pulled
before calling these endpoints.

Backend requests are logged with a request ID, HTTP status, and duration.
Unhandled exceptions and model-backend failures include tracebacks. The ID is
also returned in the `X-Request-ID` response header. Set `LOG_LEVEL` (for
example, `DEBUG` or `WARNING`) to adjust the application log level. Logs are
written to `logs/comicbookgenerator.log` as well as the console, with rotation
at 5 MB and three backup files. Set `LOG_FILE` to an absolute path or a path
relative to the project directory to change the log file location.
