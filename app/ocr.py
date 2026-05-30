import cv2
import easyocr
import numpy as np

from .config import OCR_BATCH_SIZE, OCR_MAX_DIM

_reader: easyocr.Reader | None = None

# Keyword KTP untuk scoring orientasi gambar
_KTP_KEYWORDS = frozenset(["NIK", "NAMA", "ALAMAT", "AGAMA", "JENIS", "PROVINSI", "KABUPATEN", "KOTA"])


def get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(['id', 'en'], gpu=False)
    return _reader


def warmup() -> None:
    try:
        dummy = np.zeros((64, 256), dtype=np.uint8)
        get_reader().readtext(dummy, detail=0, batch_size=1)
    except Exception:
        pass


def preprocess(img: np.ndarray) -> np.ndarray:
    """Grayscale + CLAHE. Skip heavy denoise for speed."""
    h, w = img.shape[:2]
    if max(h, w) > OCR_MAX_DIM:
        scale = OCR_MAX_DIM / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def decode_image(buf: bytes) -> np.ndarray | None:
    nparr = np.frombuffer(buf, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


def _score_for_ktp(gray: np.ndarray) -> int:
    """Hitung berapa keyword KTP yang ditemukan OCR — untuk scoring orientasi."""
    texts = get_reader().readtext(gray, detail=0, batch_size=OCR_BATCH_SIZE)
    joined = " ".join(t.upper() for t in texts)
    return sum(1 for kw in _KTP_KEYWORDS if kw in joined)


def auto_orient(img: np.ndarray) -> np.ndarray:
    """Koreksi orientasi portrait ke landscape.

    KTP selalu landscape (w > h). Jika foto portrait, coba 90° CW dulu.
    Jika kurang confident (< 3 keyword), bandingkan dengan 90° CCW.
    """
    h, w = img.shape[:2]
    if w >= h:
        return img  # Sudah landscape, tidak perlu rotasi

    cw  = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    ccw = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

    # Thumbnail untuk scoring cepat (max 600px sisi terpanjang)
    new_h, new_w = w, h  # Dimensi setelah rotasi 90°
    scale = min(1.0, 600 / max(new_h, new_w))
    tw, th = int(new_w * scale), int(new_h * scale)

    gray_cw = cv2.cvtColor(cv2.resize(cw, (tw, th), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    score_cw = _score_for_ktp(gray_cw)

    if score_cw >= 3:
        return cw  # Cukup confident, skip check CCW

    gray_ccw = cv2.cvtColor(cv2.resize(ccw, (tw, th), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    score_ccw = _score_for_ktp(gray_ccw)

    return cw if score_cw >= score_ccw else ccw


def run_ocr(gray: np.ndarray) -> list[str]:
    return get_reader().readtext(gray, detail=0, paragraph=False, batch_size=OCR_BATCH_SIZE)


def run_ocr_digits(gray: np.ndarray) -> list[str]:
    return get_reader().readtext(
        gray, detail=0, allowlist='0123456789', batch_size=OCR_BATCH_SIZE
    )
