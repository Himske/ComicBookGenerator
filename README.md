# Comic Book Generator

## Text generation

Install the project dependencies and start the API:

```powershell
uv sync
uv run uvicorn main:app --reload
```

Set `TRANSFORMERS_MODEL` to select another compatible image-text-to-text model.
The app loads the multimodal Qwen3.5 4B model directly with Transformers,
downloads its weights from Hugging Face on first use, and does not require an
Ollama installation or server. The model runs on available accelerated
hardware, or entirely on CPU; CPU generation can be considerably slower. Model
weights require several gigabytes of disk space and are cached locally.

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
in-process Transformers model, which is downloaded and loaded automatically
the first time a generation endpoint is called.

## Generate a character image

After generating a character prompt on either character page, select
**Generate image from prompt** to create a PNG with the local Diffusers
pipeline. The app detects the local
`models/RealisticAnimeIXL_v2.safetensors` file and uses it by default when
present. That file is an SDXL LoRA adapter, so Diffusers also downloads the
`stabilityai/stable-diffusion-xl-base-1.0` base model on first use. Set
`DIFFUSERS_MODEL` to select another checkpoint/adapter or compatible Diffusers
model, and set `DIFFUSERS_BASE_MODEL` to choose a different SDXL base for the
LoRA. For example:

```powershell
$env:DIFFUSERS_MODEL = "C:\Models\my-adapter.safetensors"
$env:DIFFUSERS_BASE_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
uv run uvicorn main:app --reload
```

Full single-file checkpoints are loaded with Diffusers' `from_single_file`;
LoRA adapters are applied to their compatible base model. The currently
included adapter is SDXL and generates 1024 × 1024 images. Its U-Net weights
are loaded; its text-encoder weights are skipped because Diffusers cannot
currently map this checkpoint's text-encoder ranks. CUDA is used when
available, with model CPU offloading for SDXL to reduce VRAM use; CPU fallback
is supported but can be considerably slower. Model weights require several
gigabytes of disk space and are cached locally. Install the project
dependencies with `uv sync` after updating the project so the PEFT package
required for LoRA loading is installed. SDXL prompts are limited to each
text encoder's 77-token input window; the backend logs when it trims a longer
prompt to avoid silently losing the end of the prompt inside Diffusers.

`POST /images` accepts JSON with a `prompt` string and returns a PNG image.

Backend requests are logged with a request ID, HTTP status, and duration.
Unhandled exceptions and model-backend failures include tracebacks. The ID is
also returned in the `X-Request-ID` response header. Set `LOG_LEVEL` (for
example, `DEBUG` or `WARNING`) to adjust the application log level. Logs are
written to `logs/comicbookgenerator.log` as well as the console, with rotation
at 5 MB and three backup files. Set `LOG_FILE` to an absolute path or a path
relative to the project directory to change the log file location.
