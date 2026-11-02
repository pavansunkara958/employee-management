from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import db
from app.errors import DuplicateEmail, EmployeeNotFound
from app.routes import router

STATUS_TEXT = {400: "Bad Request", 404: "Not Found", 409: "Conflict", 500: "Internal Server Error"}


def error_body(status: int, message: str, field_errors=None):
    return JSONResponse(status_code=status, content={
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "error": STATUS_TEXT.get(status, ""),
        "message": message,
        "fieldErrors": field_errors or [],
    })


@asynccontextmanager
async def lifespan(app: FastAPI):
    if db.engine is None:                 # tests inject their own engine
        db.init_engine()
    db.Base.metadata.create_all(db.engine)
    yield


app = FastAPI(title="Employee Management", lifespan=lifespan)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def on_validation(request: Request, exc: RequestValidationError):
    fields = [{"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
              for e in exc.errors()]
    return error_body(400, "Validation failed", fields)


@app.exception_handler(EmployeeNotFound)
async def on_not_found(request: Request, exc: EmployeeNotFound):
    return error_body(404, f"Employee {exc} not found")


@app.exception_handler(DuplicateEmail)
@app.exception_handler(IntegrityError)                  # race-condition fallback
async def on_duplicate(request: Request, exc: Exception):
    return error_body(409, "Email already exists")


@app.exception_handler(StarletteHTTPException)
async def on_http(request: Request, exc: StarletteHTTPException):
    return error_body(exc.status_code, str(exc.detail))


@app.exception_handler(Exception)
async def on_unexpected(request: Request, exc: Exception):
    return error_body(500, "Unexpected error")          # never leak tracebacks


@app.get("/actuator/health", include_in_schema=False)
def health():
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "UP"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "DOWN"})


# Mounted LAST so it doesn't swallow /api routes
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")