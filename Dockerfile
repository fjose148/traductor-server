FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt-lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Exponer puerto 7860 (Puerto por defecto en Hugging Face Spaces / Docker)
EXPOSE 7860

# Comando para iniciar la API FastAPI en puerto 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
