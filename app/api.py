import asyncio
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import API_KEY, REQUEST_TIMEOUT
from .db import close_pool, init_pool, load_address_caches
from .ocr import warmup
from .service import scan_ktp_bytes


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_pool()
    load_address_caches()
    warmup()
    yield
    close_pool()


app = FastAPI(lifespan=lifespan)


class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"status": "error", "message": f"Request timeout setelah {REQUEST_TIMEOUT} detik"},
            )


app.add_middleware(TimeoutMiddleware)


def verify_api_key(x_api_key: str = Header(...)):
    if not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="API key tidak valid")


@app.get("/")
async def root():
    return "works"


@app.post("/scan-ktp")
async def scan_ktp(file: UploadFile = File(...), _: None = Depends(verify_api_key)):
    try:
        contents = await file.read()
        try:
            payload = scan_ktp_bytes(contents)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        return JSONResponse(content=payload)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
