"""Service layer: orkestrasi OCR → ekstraksi → match alamat.

Dipakai oleh API maupun script batch (training).
"""
import gc
import re

import numpy as np
from rapidfuzz import fuzz

from .address import match_address
from .extractor import extract_ktp_data
from .ocr import auto_orient, decode_image, preprocess, run_ocr, run_ocr_digits


def scan_ktp_bytes(buf: bytes, expected_nik: str | None = None) -> dict:
    img = decode_image(buf)
    if img is None:
        raise ValueError("File gambar tidak valid")
    return _scan(img, expected_nik)


def scan_ktp_file(path: str, expected_nik: str | None = None) -> dict:
    with open(path, "rb") as f:
        return scan_ktp_bytes(f.read(), expected_nik)


def _compare_nik(expected: str, ocr_nik: str | None) -> dict:
    expected_clean = re.sub(r"\D", "", expected or "")
    ocr_clean = re.sub(r"\D", "", ocr_nik or "")
    score = round(fuzz.ratio(expected_clean, ocr_clean), 2) if expected_clean and ocr_clean else 0.0
    return {
        "input_nik": expected_clean or None,
        "ocr_nik": ocr_clean or None,
        "similarity_score": score,
        "is_match": score == 100.0,
    }


def _scan(img: np.ndarray, expected_nik: str | None = None) -> dict:
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

    payload = {
        "status": "success",
        "raw_text": results,
        "extracted_data": data_ktp,
        "address_match": address,
    }

    if expected_nik is not None:
        payload["nik_comparison"] = _compare_nik(expected_nik, data_ktp.get("nik"))

    return payload
