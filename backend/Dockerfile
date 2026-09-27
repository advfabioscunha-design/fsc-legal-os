FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy
WORKDIR /srv
# ffmpeg: áudio do WhatsApp
# libreoffice-writer: converte o .docx do escritório em PDF mantendo a
#   formatação original (fonte, recuos, alinhamento) — é o formato em que
#   o documento chega ao cliente para assinar.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libreoffice-writer libreoffice-core fonts-liberation \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && playwright install chromium
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
