"""
main.py — FastAPI application entry-point.

Responsibilities:
  - Create the FastAPI app with metadata.
  - Configure CORS for local frontend development origins (R18).
  - Register all routers.
  - Auto-create database tables on startup (R6).
  - Override FastAPI's default 422 validation error format with the
    unified error envelope (R16).
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.database import Base, engine
from app.routers import boards, tasks

# ---------------------------------------------------------------------------
# Database table creation (R6)
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="WPP Media Task Manager API",
    description="Mini Task Management Application — Study Case API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS (R18) — allow the Vite dev server and typical CRA ports
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Unified validation error handler (R16)
# Override FastAPI default 422 to use our error envelope
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = ".".join(str(loc) for loc in first.get("loc", [])[1:]) or None
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": first.get("msg", "Validation failed"),
            "field": field,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Normalize all HTTPException responses to the unified error envelope (R16).
    Routers raise HTTPException with detail={error, message, field};
    this handler promotes those keys to root-level so the contract matches
    the documented shape: {"error": "...", "message": "...", "field": null}.
    """
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": detail.get("error", "HTTP_ERROR"),
                "message": detail.get("message", "An error occurred"),
                "field": detail.get("field", None),
            },
        )
    # Fallback for plain-string detail values (FastAPI internals, 404 on unknown routes, etc.)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": str(detail) if detail else f"HTTP {exc.status_code}",
            "field": None,
        },
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(boards.router)
app.include_router(tasks.router)


# ---------------------------------------------------------------------------
# Health-check endpoint
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": "wpp-taskmanager-api"}
