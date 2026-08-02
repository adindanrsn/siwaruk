# Gunakan image Python resmi
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements dan install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kodenya
COPY . .

# Set environment variable agar output log Flask langsung tampil
ENV PYTHONUNBUFFERED=1

# Jalankan server menggunakan Gunicorn
# Cloud Run menyediakan environment variable PORT secara otomatis (default 8080)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 run:app