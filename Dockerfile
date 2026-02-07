#############################################
# Builder stage
#############################################
FROM python:3.11-slim AS builder
WORKDIR /app

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

# Copiamos solo requirements
COPY requirements.txt requirements-ui.txt ./

# Instalamos pip/setuptools/wheel y precompilamos ruedas
RUN pip install --upgrade pip setuptools wheel \
 && mkdir /wheels \
 && pip wheel --no-build-isolation -r requirements.txt -w /wheels \
 && pip wheel --no-build-isolation -r requirements-ui.txt -w /wheels


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

# Copiamos ruedas precompiladas
COPY --from=builder /wheels /wheels
COPY requirements.txt requirements-ui.txt ./

# Instalamos offline
RUN pip install --no-index --find-links /wheels -r requirements.txt \
 && pip install --no-index --find-links /wheels -r requirements-ui.txt

# Copiamos la app
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
