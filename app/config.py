import os

# Batasi thread CPU dari torch/numpy/opencv agar tidak spawn banyak worker
os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("MKL_NUM_THREADS", "8")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "8")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "8")

API_KEY = os.environ.get("KTP_API_KEY", "8ismillaH")

DB_DSN = os.environ.get(
    "KTP_DB_DSN",
    "host=host.docker.internal port=5432 dbname=ktp user=upi password=12345678",
)

REQUEST_TIMEOUT = int(os.environ.get("KTP_REQUEST_TIMEOUT", "300"))

OCR_MAX_DIM = int(os.environ.get("KTP_OCR_MAX_DIM", "1280"))
OCR_BATCH_SIZE = int(os.environ.get("KTP_OCR_BATCH_SIZE", "8"))
