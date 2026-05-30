# KTP OCR API

REST API untuk membaca dan mengekstrak data dari foto KTP (Kartu Tanda Penduduk) Indonesia secara otomatis menggunakan EasyOCR + fuzzy matching + database alamat.

## Fitur

- **OCR akurat** — EasyOCR dengan model bahasa Indonesia + Inggris
- **Auto-rotate** — mendeteksi dan memperbaiki foto KTP yang diambil dalam posisi portrait
- **Fuzzy matching label** — tahan terhadap misread OCR (contoh: `AOAMA` tetap dikenali sebagai `AGAMA`, `RAMA` sebagai `NAMA`)
- **Validasi agama** — closed-list 7 agama resmi Indonesia dengan confidence score
- **Address matching berjenjang** — Provinsi → Kota/Kabupaten → Kecamatan → Kelurahan/Desa dari database PostgreSQL (80.000+ wilayah)
- **REST API** siap production dengan autentikasi API key
- **Batch scan** — proses satu file atau seluruh folder sekaligus untuk keperluan training/QA

---

## Prasyarat

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- PostgreSQL dengan tabel data wilayah Indonesia (lihat [Setup Database](#setup-database))

---

## Setup Database

Buat database PostgreSQL dan isi dengan data wilayah. Struktur tabel yang dibutuhkan:

```sql
-- Provinsi
CREATE TABLE address_provinces (
    id   VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- Kabupaten / Kota
CREATE TABLE address_regencies (
    id          VARCHAR(10) PRIMARY KEY,
    province_id VARCHAR(10) NOT NULL REFERENCES address_provinces(id),
    name        VARCHAR(100) NOT NULL
);

-- Kecamatan
CREATE TABLE address_districts (
    id         VARCHAR(10) PRIMARY KEY,
    regency_id VARCHAR(10) NOT NULL REFERENCES address_regencies(id),
    name       VARCHAR(100) NOT NULL
);

-- Kelurahan / Desa
CREATE TABLE address_villages (
    id          VARCHAR(10) PRIMARY KEY,
    district_id VARCHAR(10) NOT NULL REFERENCES address_districts(id),
    name        VARCHAR(100) NOT NULL
);
```

> Data wilayah Indonesia dapat diunduh dari [cahyadsn/wilayah](https://github.com/cahyadsn/wilayah) atau [emsifa/wilayah-indonesia](https://github.com/emsifa/wilayah-indonesia).

---

## Instalasi

### 1. Clone repository

```bash
git clone https://github.com/iseplutpinur/ktp-ocr.git
cd ktp-ocr
```

### 2. Konfigurasi environment

Edit nilai environment di `docker-compose.yml`:

```yaml
environment:
  KTP_API_KEY: "ganti-dengan-api-key-rahasia-anda"
  KTP_DB_DSN: "host=host.docker.internal port=5432 dbname=ktp user=postgres password=yourpassword"
```

Seluruh variabel konfigurasi yang tersedia:

| Variabel | Default | Keterangan |
|---|---|---|
| `KTP_API_KEY` | `8ismillaH` | API key untuk autentikasi request |
| `KTP_DB_DSN` | *(lihat docker-compose.yml)* | DSN koneksi PostgreSQL |
| `KTP_REQUEST_TIMEOUT` | `300` | Timeout request dalam detik |
| `KTP_OCR_MAX_DIM` | `1280` | Ukuran maksimum sisi terpanjang gambar sebelum OCR |
| `KTP_OCR_BATCH_SIZE` | `8` | Batch size EasyOCR |

### 3. Build dan jalankan

```bash
docker compose up -d --build
```

Proses build pertama kali memakan waktu sekitar 5–10 menit karena mengunduh model PyTorch CPU dan EasyOCR. Build selanjutnya jauh lebih cepat karena layer di-cache.

### 4. Verifikasi

```bash
curl http://localhost:3000/
# → "works"
```

---

## Penggunaan API

### Endpoint

```
POST /scan-ktp
```

### Header

| Header | Wajib | Keterangan |
|---|---|---|
| `X-Api-Key` | ✓ | API key yang dikonfigurasi di `KTP_API_KEY` |
| `Content-Type` | ✓ | `multipart/form-data` |

### Body

| Field | Tipe | Keterangan |
|---|---|---|
| `file` | file | Gambar KTP (`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`) |

### Contoh Request

**cURL:**

```bash
curl -X POST http://localhost:3000/scan-ktp \
  -H "X-Api-Key: 8ismillaH" \
  -F "file=@/path/to/ktp.jpg"
```

**Python (requests):**

```python
import requests

with open("ktp.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:3000/scan-ktp",
        headers={"X-Api-Key": "8ismillaH"},
        files={"file": f},
    )
print(response.json())
```

**PHP (Guzzle):**

```php
$client = new \GuzzleHttp\Client();
$response = $client->post('http://localhost:3000/scan-ktp', [
    'headers'   => ['X-Api-Key' => '8ismillaH'],
    'multipart' => [[
        'name'     => 'file',
        'contents' => fopen('/path/to/ktp.jpg', 'r'),
        'filename' => 'ktp.jpg',
    ]],
]);
echo $response->getBody();
```

**JavaScript (fetch):**

```js
const form = new FormData();
form.append('file', fileInput.files[0]);

const res = await fetch('http://localhost:3000/scan-ktp', {
  method: 'POST',
  headers: { 'X-Api-Key': '8ismillaH' },
  body: form,
});
const data = await res.json();
```

### Contoh Response

```json
{
  "status": "success",
  "raw_text": [
    "PROVINSI JAWA BARAT",
    "KABUPATEN BANDUNG",
    "NIK",
    "3204350502060002",
    "Nama",
    "AZ BURHANUDIN",
    ...
  ],
  "extracted_data": {
    "nik": "3204350502060002",
    "nama": "AZ BURHANUDIN",
    "tempat_lahir": "BANDUNG",
    "tanggal_lahir": "05-02-2006",
    "jenis_kelamin": "LAKI-LAKI",
    "alamat": "KP CIPEDES",
    "rt_rw": "002/007",
    "agama": "ISLAM",
    "agama_score": 100.0,
    "status_perkawinan": "BELUM KAWIN",
    "pekerjaan": "PELAJAR/MAHASISWA",
    "kewarganegaraan": "WNI"
  },
  "address_match": {
    "provinsi": "JAWA BARAT",
    "provinsi_id": "32",
    "provinsi_score": 90.0,
    "kota_kabupaten": "KABUPATEN BANDUNG",
    "kota_kabupaten_id": "3204",
    "kota_kabupaten_score": 100.0,
    "kecamatan": "PASEH",
    "kecamatan_id": "3204080",
    "kecamatan_score": 100.0,
    "kelurahan_desa": "CIPEDES",
    "kelurahan_desa_id": "3204080010",
    "kelurahan_desa_score": 100.0
  }
}
```

### Kode Status HTTP

| Kode | Keterangan |
|---|---|
| `200` | Berhasil |
| `400` | File gambar tidak valid |
| `401` | API key salah atau tidak disertakan |
| `504` | Request timeout (melebihi `KTP_REQUEST_TIMEOUT`) |
| `500` | Error internal server |

---

## Batch Scan (Training / QA)

Batch scan dijalankan langsung di dalam container.

### Scan satu file

```bash
# Simpan hasil ke folder output
docker compose exec app python -m scripts.batch_scan data-training-ktp/ktp.jpg

# Tampilkan ke stdout saja (tidak tulis file)
docker compose exec app python -m scripts.batch_scan data-training-ktp/ktp.jpg --print

# Skip address matching (tanpa koneksi DB)
docker compose exec app python -m scripts.batch_scan data-training-ktp/ktp.jpg --no-db
```

### Scan seluruh folder

```bash
# Default: input=data-training-ktp, output=data-training-ktp-hasil
docker compose exec app python -m scripts.batch_scan

# Folder kustom
docker compose exec app python -m scripts.batch_scan --input /path/input --output /path/output

# Re-scan ulang file yang sudah ada hasilnya
docker compose exec app python -m scripts.batch_scan --force

# Tanpa address matching
docker compose exec app python -m scripts.batch_scan --no-db
```

Hasil setiap gambar disimpan sebagai file JSON dengan nama yang sama di folder output. File yang sudah ada di-skip secara default (tanpa `--force`).

### Struktur folder training

```
ktp-ocr/
├── data-training-ktp/          # Letakkan gambar KTP di sini
│   ├── KTP-nama-user-timestamp.jpg
│   └── ...
└── data-training-ktp-hasil/    # Hasil JSON otomatis tersimpan di sini
    ├── KTP-nama-user-timestamp.json
    └── ...
```

---

## Struktur Proyek

```
ktp-ocr/
├── main.py                  # Entrypoint — jalankan uvicorn
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── app/
│   ├── config.py            # Environment variables & thread settings
│   ├── db.py                # Connection pool PostgreSQL + cache data wilayah
│   ├── ocr.py               # EasyOCR reader, preprocessing, auto-rotate
│   ├── extractor.py         # Ekstraksi field KTP dari raw OCR text
│   ├── address.py           # Fuzzy matching alamat ke database wilayah
│   ├── service.py           # Orkestrasi: OCR → ekstrak → match alamat
│   └── api.py               # FastAPI routes + middleware
└── scripts/
    └── batch_scan.py        # CLI batch scan untuk training / QA
```

---

## Cara Kerja

```
Gambar KTP
    │
    ▼
[auto_orient]  ← deteksi portrait, scoring thumbnail OCR, rotasi jika perlu
    │
    ▼
[preprocess]   ← resize (max 1280px), CLAHE contrast enhancement
    │
    ▼
[EasyOCR]      ← readtext, output list of string per baris
    │
    ├──→ [extractor]  ← fuzzy label matching, regex fallback, agama closed-list
    │
    └──→ [address]    ← rapidfuzz: provinsi → kota → kecamatan → kelurahan
```

---

## Resource yang Dibutuhkan

| Resource | Rekomendasi |
|---|---|
| CPU | 4 core (dikonfigurasi di `docker-compose.yml`) |
| RAM | 4–8 GB |
| Disk | ~4 GB (image Docker + model EasyOCR) |
| GPU | Tidak wajib — berjalan di CPU |

Waktu scan rata-rata: **4–8 detik per gambar** di CPU (tergantung resolusi dan orientasi).

---

## Lisensi

[MIT](LICENSE) © 2026 Isep Lutpi Nur
