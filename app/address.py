"""Address matching: pure fuzzy search across the cached master data.

Tidak pakai regex untuk anchoring; mirip pendekatan PHP `similar_text` foreach,
hanya lebih cepat karena `rapidfuzz` ditulis di C++.
"""
from rapidfuzz import fuzz, process

from .db import get_caches


def _best_match(text_up: str, choices: list[tuple], name_idx: int, score_cutoff: int = 80):
    """Cari entry terbaik via partial_ratio terhadap seluruh teks gabungan.

    `partial_ratio` toleran terhadap label yang nempel
    (mis. 'PROVINSIJAWA BARAT' tetap match 'JAWA BARAT').
    """
    if not choices:
        return None, 0
    names = [c[name_idx] for c in choices]
    best = process.extractOne(text_up, names, scorer=fuzz.partial_ratio, score_cutoff=score_cutoff)
    if not best:
        return None, 0
    _, score, idx = best
    return choices[idx], score


def _best_match_lines(lines: list[str], choices: list[tuple], name_idx: int, score_cutoff: int = 80):
    """Iterasi per baris, ambil yang skor fuzzy-nya paling tinggi.

    Equivalent dengan foreach + similar_text di PHP.
    """
    if not choices:
        return None, 0
    names = [c[name_idx] for c in choices]
    best_item, best_score = None, 0
    for line in lines:
        line = line.strip().upper()
        if len(line) < 3:
            continue
        result = process.extractOne(line, names, scorer=fuzz.WRatio, score_cutoff=score_cutoff)
        if result and result[1] > best_score:
            _, best_score, idx = result
            best_item = choices[idx]
    return best_item, best_score


def match_address(joined_text: str) -> dict:
    provinces, regencies, districts, villages = get_caches()
    text_up = joined_text.upper()
    lines = text_up.split('\n')

    result = {
        "provinsi": None, "provinsi_id": None, "provinsi_score": 0,
        "kota_kabupaten": None, "kota_kabupaten_id": None, "kota_kabupaten_score": 0,
        "kecamatan": None, "kecamatan_id": None, "kecamatan_score": 0,
        "kelurahan_desa": None, "kelurahan_desa_id": None, "kelurahan_desa_score": 0,
    }

    # ── Provinsi ─────────────────────────────────────────────────────
    prov, score = _best_match(text_up, provinces, name_idx=1, score_cutoff=80)
    if prov:
        result["provinsi"], result["provinsi_id"], result["provinsi_score"] = prov[1], prov[0], score

    # ── Kota/Kabupaten (dipersempit ke provinsi yg sudah cocok) ──────
    reg_pool = [r for r in regencies if r[1] == result["provinsi_id"]] if result["provinsi_id"] else regencies
    # Coba per-baris dulu (baris seperti "KOTA BANDUNG" akan exact match)
    reg, score = _best_match_lines(lines, reg_pool, name_idx=2, score_cutoff=85)
    if not reg:
        reg, score = _best_match(text_up, reg_pool, name_idx=2, score_cutoff=80)
    if reg:
        result["kota_kabupaten"], result["kota_kabupaten_id"], result["kota_kabupaten_score"] = reg[2], reg[0], score

    # ── Kecamatan (dipersempit ke kota) ──────────────────────────────
    dist_pool = [d for d in districts if d[1] == result["kota_kabupaten_id"]] if result["kota_kabupaten_id"] else districts
    dist, score = _best_match_lines(lines, dist_pool, name_idx=2, score_cutoff=78)
    if dist:
        result["kecamatan"], result["kecamatan_id"], result["kecamatan_score"] = dist[2], dist[0], score

    # ── Kelurahan/Desa (dipersempit ke kecamatan) ────────────────────
    vill_pool = [v for v in villages if v[1] == result["kecamatan_id"]] if result["kecamatan_id"] else villages
    vill, score = _best_match_lines(lines, vill_pool, name_idx=2, score_cutoff=78)
    if vill:
        result["kelurahan_desa"], result["kelurahan_desa_id"], result["kelurahan_desa_score"] = vill[2], vill[0], score

    return result
