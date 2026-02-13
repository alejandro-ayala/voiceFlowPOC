#############################################
# Builder stage
#############################################
FROM python:3.11-slim AS builder
WORKDIR /build

# Dependencias de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    libasound2-dev \
    libpulse-dev \
    libssl-dev \
    libcurl4-openssl-dev \
    libgomp1 \
    libicu-dev \
 && rm -rf /var/lib/apt/lists/*

# Instalar Poetry (sin virtualenv — instala al Python del sistema)
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false
RUN pip install --no-cache-dir poetry

# Copiar solo archivos de dependencias para cache de Docker layers
COPY pyproject.toml poetry.lock ./

# Instalar dependencias de producción al site-packages del sistema
RUN poetry install --only main --no-root


#############################################
# Runtime stage (final image)
#############################################
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0

# Dependencias runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    libasound2 \
    libpulse0 \
    libpulse-mainloop-glib0 \
    libstdc++6 \
    libatomic1 \
    libunwind8 \
    libnss3 \
    libcurl4 \
    ca-certificates \
    tzdata \
    libgomp1 \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Copiar paquetes instalados del builder (site-packages + binarios)
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copiar la app
COPY . /app

# Dar permisos de ejecución a los scripts
RUN chmod +x /app/docker/scripts/entrypoint.sh /app/docker/scripts/healthcheck.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD ["/app/docker/scripts/healthcheck.sh"]

EXPOSE 8000

# Entrypoint para validaciones previas al inicio
ENTRYPOINT ["/app/docker/scripts/entrypoint.sh"]

# Comando por defecto
CMD ["python", "presentation/server_launcher.py", "--host", "0.0.0.0"]
