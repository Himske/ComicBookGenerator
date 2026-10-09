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

Open [http://localhost:8000](http://localhost:8000) for the comic generator
form. Submit a premise, panel count, and art style to generate and display the
comic beneath the form.

The API connects to Ollama at `http://localhost:11434` and uses the downloaded
`qwen3.5:4b` model by default. Set `OLLAMA_HOST` and `OLLAMA_MODEL` before
starting the API to use a different local Ollama server or Qwen model tag. For
example:

```powershell
$env:OLLAMA_MODEL = "qwen2.5:7b"
uv run uvicorn main:app --reload
```

The selected model must be available to the Ollama server before calling
`POST /comics`.