"""Thin entrypoint. Import config dulu agar env thread di-set sebelum
modul-modul lain memuat torch / opencv / easyocr.
"""
from app.config import API_KEY  # noqa: F401
from app.api import app  # noqa: F401


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3000, timeout_keep_alive=300)
