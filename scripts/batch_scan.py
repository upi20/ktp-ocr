"""Scan KTP: satu file spesifik atau seluruh folder.

Penggunaan — satu file:
    python -m scripts.batch_scan data-training-ktp/KTP-aas-hasanah.jpg
    python -m scripts.batch_scan data-training-ktp/KTP-aas-hasanah.jpg --no-db
    python -m scripts.batch_scan data-training-ktp/KTP-aas-hasanah.jpg --print   # tampilkan ke stdout saja

Penggunaan — folder:
    python -m scripts.batch_scan
    python -m scripts.batch_scan --input data-training-ktp --output data-training-ktp-hasil
    python -m scripts.batch_scan --no-db    # skip address matching (tanpa Postgres)
    python -m scripts.batch_scan --force    # re-scan file yang sudah ada hasilnya
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from app.config import API_KEY  # noqa: F401  (set env threading dulu)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan KTP: file tunggal atau batch folder")
    parser.add_argument("file", nargs="?", help="Path file gambar (opsional; jika diisi, mode single-file)")
    parser.add_argument("--input", default="data-training-ktp", help="Folder input gambar (mode batch)")
    parser.add_argument("--output", default="data-training-ktp-hasil", help="Folder output JSON")
    parser.add_argument("--no-db", action="store_true", help="Lewati matching alamat (tanpa Postgres)")
    parser.add_argument("--force", action="store_true", help="Tulis ulang meskipun JSON sudah ada")
    parser.add_argument("--print", dest="print_only", action="store_true", help="Tampilkan hasil ke stdout, tidak tulis JSON")
    args = parser.parse_args()

    # Lazy import agar tidak load torch saat --help
    from app.ocr import warmup
    from app.service import scan_ktp_file

    if args.no_db:
        import app.db as db_mod
        db_mod._provinces = []
        db_mod._regencies = []
        db_mod._districts = []
        db_mod._villages = []
    else:
        from app.db import init_pool, load_address_caches
        init_pool()
        load_address_caches()

    warmup()

    # ── MODE SINGLE FILE ──────────────────────────────────────────────
    if args.file:
        fp = Path(args.file)
        if not fp.is_file():
            print(f"File tidak ditemukan: {fp}", file=sys.stderr)
            return 2
        t0 = time.time()
        try:
            payload = scan_ktp_file(str(fp))
            payload["_meta"] = {"source_file": fp.name, "elapsed_seconds": round(time.time() - t0, 3)}
            output = json.dumps(payload, ensure_ascii=False, indent=2)
            if args.print_only:
                print(output)
            else:
                out_dir = Path(args.output)
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / (fp.stem + ".json")
                out_path.write_text(output)
                print(f"OK  {fp.name} ({payload['_meta']['elapsed_seconds']}s) → {out_path}")
        except Exception as e:
            print(f"FAIL {fp.name}: {e}", file=sys.stderr)
            return 1
        return 0

    # ── MODE BATCH FOLDER ────────────────────────────────────────────
    in_dir = Path(args.input)
    out_dir = Path(args.output)
    if not in_dir.is_dir():
        print(f"Folder input tidak ditemukan: {in_dir}", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in in_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not files:
        print(f"Tidak ada gambar di {in_dir}")
        return 0

    print(f"Memproses {len(files)} file dari {in_dir} → {out_dir}")
    total_t = 0.0
    ok = 0
    skipped = 0
    failed = 0

    for i, fp in enumerate(files, 1):
        out_path = out_dir / (fp.stem + ".json")
        if out_path.exists() and not args.force:
            print(f"[{i}/{len(files)}] SKIP {fp.name} (hasil sudah ada)")
            skipped += 1
            continue

        t0 = time.time()
        try:
            payload = scan_ktp_file(str(fp))
            payload["_meta"] = {
                "source_file": fp.name,
                "elapsed_seconds": round(time.time() - t0, 3),
            }
            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
            dt = time.time() - t0
            total_t += dt
            ok += 1
            nik = payload.get("extracted_data", {}).get("nik")
            print(f"[{i}/{len(files)}] OK   {fp.name} ({dt:.2f}s) nik={nik}")
        except Exception as e:
            failed += 1
            print(f"[{i}/{len(files)}] FAIL {fp.name}: {e}", file=sys.stderr)

    avg = (total_t / ok) if ok else 0.0
    print(f"\nSelesai. ok={ok} skipped={skipped} failed={failed} avg={avg:.2f}s/file")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
