import re

from rapidfuzz import fuzz, process

# Agama resmi yang bisa muncul di KTP Indonesia
AGAMA_LIST = [
    "ISLAM",
    "KRISTEN",
    "KATOLIK",
    "HINDU",
    "BUDDHA",
    "BUDHA",
    "KONGHUCU",
]

# Label resmi KTP → sinonim OCR yang umum
_LABEL_ALIASES: dict[str, list[str]] = {
    "AGAMA":             ["AGAMA", "AOAMA"],
    "JENIS KELAMIN":     ["JENIS KELAMIN", "JENISKELAMIN", "JENIS KEL", "JENIS KAMIN"],
    "ALAMAT":            ["ALAMAT", "ALAMA", "ALAMAR", "ALAMAL"],
    "STATUS PERKAWINAN": ["STATUS PERKAWINAN", "STATUS PERKAW", "STATUSPERKAW"],
    "PEKERJAAN":         ["PEKERJAAN", "PEKERJAAAN", "PEKERJAEN"],
    "KEWARGANEGARAAN":   ["KEWARGANEGARAAN", "KEWARG"],
    "NAMA":              ["NAMA", "NAM", "RAMA", "NAMR"],
}


def _find_after_label(lines: list[str], label: str, score_cutoff: int = 72) -> str | None:
    """Cari baris yang mirip dengan `label`, kembalikan baris berikutnya sebagai nilai.
    Berguna ketika OCR salah baca nama field (mis. AGAMA → Aoama).
    """
    aliases = _LABEL_ALIASES.get(label, [label])
    for i, line in enumerate(lines):
        line_up = line.strip().upper()
        for alias in aliases:
            if fuzz.ratio(line_up, alias) >= score_cutoff:
                for j in range(i + 1, min(i + 3, len(lines))):
                    val = lines[j].strip().upper()
                    if val:
                        return val
    return None


def _match_agama(text_list: list[str], score_cutoff: int = 70) -> tuple[str | None, int]:
    """Scan semua baris, cari yang paling mirip dengan salah satu nilai agama resmi.
    Kembalikan (agama_canonical, score) atau (None, 0).
    """
    best_agama, best_score = None, 0
    for line in text_list:
        token = line.strip().upper()
        if len(token) < 4 or len(token) > 20:
            continue
        result = process.extractOne(token, AGAMA_LIST, scorer=fuzz.WRatio, score_cutoff=score_cutoff)
        if result:
            name, score, _ = result
            if score > best_score:
                best_agama, best_score = name, score
    # Normalisasi: BUDHA → BUDDHA
    if best_agama == "BUDHA":
        best_agama = "BUDDHA"
    return best_agama, best_score


def extract_ktp_data(text_list: list[str]) -> dict:
    joined_up = "\n".join(text_list).upper()
    data = {
        "nik": None, "nama": None, "tempat_lahir": None, "tanggal_lahir": None,
        "jenis_kelamin": None, "alamat": None, "rt_rw": None,
        "agama": None, "agama_score": 0,
        "status_perkawinan": None, "pekerjaan": None, "kewarganegaraan": None,
    }

    m = re.search(r'\b\d{16}\b', joined_up)
    if m:
        data["nik"] = m.group(0)

    m = re.search(r'NAMA[\s:]+([A-Z\s\'.]+)', joined_up)
    if m:
        data["nama"] = m.group(1).strip().split('\n')[0]
    else:
        val = _find_after_label(text_list, "NAMA", score_cutoff=70)
        if val:
            data["nama"] = val

    m = re.search(r'([A-Z\s]+),\s*(\d{2}-\d{2}-\d{4})', joined_up)
    if m:
        data["tempat_lahir"] = m.group(1).strip()
        data["tanggal_lahir"] = m.group(2)

    m = re.search(r'JENIS KELAMIN[\s:]+(LAKI-LAKI|PEREMPUAN)', joined_up)
    if m:
        data["jenis_kelamin"] = m.group(1)

    m = re.search(r'ALAMAT[\s:]+([A-Z0-9\s./-]+)', joined_up)
    if m:
        data["alamat"] = m.group(1).strip().split('\n')[0]
    else:
        val = _find_after_label(text_list, "ALAMAT")
        if val:
            data["alamat"] = val

    m = re.search(r'RT[/\s]*RW[\s:]+(\d{1,3})\s*[/\s]\s*(\d{1,3})', joined_up)
    if m:
        data["rt_rw"] = f"{m.group(1)}/{m.group(2)}"

    agama, agama_score = _match_agama(text_list)
    data["agama"] = agama
    data["agama_score"] = agama_score if agama else 0

    m = re.search(r'STATUS PERKAWINAN[\s:]+([A-Z\s]+)', joined_up)
    if m:
        data["status_perkawinan"] = m.group(1).strip().split('\n')[0]
    else:
        val = _find_after_label(text_list, "STATUS PERKAWINAN")
        if val:
            data["status_perkawinan"] = val

    m = re.search(r'PEKERJAAN[\s:]+([A-Z\s/]+)', joined_up)
    if m:
        data["pekerjaan"] = m.group(1).strip().split('\n')[0]
    else:
        val = _find_after_label(text_list, "PEKERJAAN")
        if val:
            data["pekerjaan"] = val

    m = re.search(r'KEWARGANEGARAAN[\s:]+([A-Z]+)', joined_up)
    if m:
        data["kewarganegaraan"] = m.group(1)
    else:
        val = _find_after_label(text_list, "KEWARGANEGARAAN")
        if val:
            data["kewarganegaraan"] = val.split()[0]

    return data
