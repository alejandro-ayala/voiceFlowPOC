#!/bin/bash
set -e

echo "========================================"
echo "  VoiceFlow Tourism PoC - Starting"
echo "========================================"
echo "Environment: ${VOICEFLOW_DEBUG:-false}"
echo "Real agents: ${VOICEFLOW_USE_REAL_AGENTS:-false}"
echo "Host: ${HOST:-0.0.0.0}"
echo "Port: ${VOICEFLOW_PORT:-8000}"
echo "Log level: ${VOICEFLOW_LOG_LEVEL:-INFO}"
echo "========================================"

# Copiar .env.example si no existe .env
if [ ! -f /app/.env ] && [ -f /app/.env.example ]; then
    echo "⚠️  No .env found, using .env.example as template"
    cp /app/.env.example /app/.env
fi

# Verificar que las dependencias críticas están disponibles
echo "✓ Checking Python dependencies..."
python -c "import fastapi; import uvicorn; print('✓ Core dependencies OK')" || {
    echo "❌ ERROR: Missing critical dependencies"
    exit 1
}

# Verificar que ffmpeg está disponible (necesario para pydub)
echo "✓ Checking system dependencies..."
which ffmpeg > /dev/null || {
    echo "⚠️  WARNING: ffmpeg not found. Audio processing may fail."
}

# Verificar variables de entorno críticas (opcional, solo warning)
if [ -z "$OPENAI_API_KEY" ] && [ "$VOICEFLOW_USE_REAL_AGENTS" = "true" ]; then
    echo "⚠️  WARNING: OPENAI_API_KEY not set but VOICEFLOW_USE_REAL_AGENTS=true"
    echo "    The application will fail when trying to use real AI agents."
fi

if [ -z "$AZURE_SPEECH_KEY" ]; then
    echo "⚠️  WARNING: AZURE_SPEECH_KEY not set"
    echo "    Azure Speech Services will not be available for transcription."
fi

echo "========================================"
echo "✓ All checks passed. Starting application..."
echo "========================================"
echo ""

# Ejecutar comando principal (CMD del Dockerfile)
exec "$@"
