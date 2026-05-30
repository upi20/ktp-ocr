"""Service layer: orkestrasi OCR → ekstraksi → match alamat.

Dipakai oleh API maupun script batch (training).
"""
import gc
import re

import numpy as np

from .address import match_address
from .extractor import extract_ktp_data
from .ocr import auto_orient, decode_image, preprocess, run_ocr, run_ocr_digits


def scan_ktp_bytes(buf: bytes) -> dict:
    img = decode_image(buf)
    if img is None:
        raise ValueError("File gambar tidak valid")
    return _scan(img)


def scan_ktp_file(path: str) -> dict:
    with open(path, "rb") as f:
        return scan_ktp_bytes(f.read())


def _scan(img: np.ndarray) -> dict:
    img = auto_orient(img)
    gray = preprocess(img)
    del img

    results = run_ocr(gray)
    data_ktp = extract_ktp_data(results)

    if not data_ktp.get("nik"):
        try:
            for d in run_ocr_digits(gray):
                m = re.search(r'\d{16}', d)
                if m:
                    data_ktp["nik"] = m.group(0)
                    break
        except Exception:
            pass

    del gray
    gc.collect()

    address = match_address("\n".join(results))

    return {
        "status": "success",
        "raw_text": results,
        "extracted_data": data_ktp,
        "address_match": address,
    }
