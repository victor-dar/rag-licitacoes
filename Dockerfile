FROM python:3.11-slim

WORKDIR /app

# torch só CPU: a imagem padrão traz CUDA e passa de 4 GB
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ingest ingest
COPY api api

ENV HF_HOME=/cache/hf
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
