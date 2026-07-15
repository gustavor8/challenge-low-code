# =======================================================
# Stage 1: Build Angular Frontend
# =======================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copiar arquivos de configuração do npm e do projeto
COPY frontend/package*.json ./
RUN npm ci

# Copiar código fonte e buildar em produção
COPY frontend/ ./
RUN npm run build -- --configuration=production

# =======================================================
# Stage 2: Run Python Backend + Serve Frontend Static
# =======================================================
FROM python:3.10-slim
WORKDIR /app

# Instalar dependências de sistema necessárias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fonte do backend
COPY backend/app ./app

# Copiar assets do frontend compilados no Stage 1 para a pasta static
COPY --from=frontend-builder /app/frontend/dist/argos-armazem/browser ./static

# Expor a porta que o Uvicorn usará
EXPOSE 8080

# Inicializar o servidor uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
