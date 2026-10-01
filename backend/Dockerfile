FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy
WORKDIR /srv
# ffmpeg: áudio do WhatsApp
# libreoffice-writer: converte o .docx do escritório em PDF mantendo a
#   formatação original (fonte, recuos, alinhamento) — é o formato em que
#   o documento chega ao cliente para assinar.
# fonts-crosextra-carlito: a Calibri do padrão do escritório é fonte da
#   Microsoft e não existe em servidor Linux. Sem ela, o LibreOffice
#   trocava por uma serifada na hora de gerar o PDF, e o cliente recebia
#   um documento com outra letra e outra quebra de linha do que o
#   advogado aprovou no Word. A Carlito tem as mesmas medidas da
#   Calibri, então a página fica igual nos dois.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libreoffice-writer libreoffice-core fonts-liberation \
        fonts-dejavu-core fonts-crosextra-carlito \
    && rm -rf /var/lib/apt/lists/*

# O apelido que faz o LibreOffice entender "Calibri Light" como Carlito.
# Instalar a fonte não basta: o nome pedido no documento é outro, e sem
# este mapa ele cai na substituição padrão, que é serifada.
COPY docker/fontes-do-escritorio.conf /etc/fonts/conf.d/99-fsc.conf
RUN fc-cache -f >/dev/null
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && playwright install chromium
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
