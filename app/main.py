"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.departments import router as departments_router
from app.db import init_db
from app.logging_config import get_logger, setup_logging
from app.services.department import ConflictError, DepartmentNotFoundError

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan: init on startup."""
    init_db()
    yield
    # shutdown if needed


app = FastAPI(
    title="Organizational Structure API",
    description="API for departments and employees (tree structure).",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(departments_router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect to API documentation."""
    return RedirectResponse(url="/docs", status_code=302)


@app.exception_handler(DepartmentNotFoundError)
def department_not_found_handler(
    request: Request,
    exc: DepartmentNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc) or "Department not found"},
    )


@app.exception_handler(ConflictError)
def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc)},
    )


@app.exception_handler(ValueError)
def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}
