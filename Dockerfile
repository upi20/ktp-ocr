FROM python:3.11-slim

WORKDIR /app

# System deps for opencv-headless + libpq for psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only first (prevents easyocr from pulling GPU build)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY app ./app
COPY scripts ./scripts

EXPOSE 3000

CMD ["python", "main.py"]
