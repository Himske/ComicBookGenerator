import logging
import os
from contextvars import ContextVar, Token
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import RequestResponseEndpoint

from routes import router

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


logger = logging.getLogger("comicbookgenerator")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
logger.propagate = False
if not logger.handlers:
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
        )
    )
    log_handler.addFilter(RequestIdFilter())
    logger.addHandler(log_handler)

app = FastAPI(title="Comic Generator API", version="0.1.0")
FRONTEND_PATH = Path(__file__).parent / "static" / "index.html"
app.mount("/static", StaticFiles(directory=FRONTEND_PATH.parent), name="static")
app.include_router(router)


@app.middleware("http")
async def log_requests(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    request_id = uuid4().hex
    token: Token[str] = request_id_context.set(request_id)
    started_at = perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        status_code = response.status_code
        log_level = (
            logging.ERROR
            if status_code >= 500
            else logging.WARNING
            if status_code >= 400
            else logging.INFO
        )
        logger.log(
            log_level,
            "Request completed method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            status_code,
            (perf_counter() - started_at) * 1000,
        )
        return response
    except Exception:
        logger.exception(
            "Unhandled request error method=%s path=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            (perf_counter() - started_at) * 1000,
        )
        raise
    finally:
        request_id_context.reset(token)
