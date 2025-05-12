FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    netcat-traditional \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Crear directorio para uploads
RUN mkdir -p /app/uploads

# Copiar aplicación
COPY . .

# Script para esperar a que los servicios estén disponibles
COPY ./scripts/wait-for-services.sh /wait-for-services.sh
RUN chmod +x /wait-for-services.sh

# Puerto para la API
EXPOSE 8000

# Comando por defecto
CMD ["/wait-for-services.sh", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
