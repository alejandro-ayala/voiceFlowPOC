#!/usr/bin/env python3
"""
Simple test server for VoiceFlow PoC
Creates a basic FastAPI server to test the frontend components
"""

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import asyncio
import json
from pathlib import Path

# Create FastAPI app
app = FastAPI(title="VoiceFlow PoC - Test Server")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup static files and templates
static_path = Path(__file__).parent / "web_ui" / "static"
templates_path = Path(__file__).parent / "web_ui" / "templates"

if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

templates = Jinja2Templates(directory=str(templates_path))

# Simple routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "VoiceFlow PoC",
        "debug": True,
        "environment": "development"
    })

@app.get("/api/v1/health/system")
async def health_system():
    return {"healthy": True, "service": "VoiceFlow PoC", "timestamp": "2023-12-03T10:00:00Z"}

@app.get("/api/v1/health/backend")
async def health_backend():
    return {"healthy": True, "service": "Backend (Demo Mode)", "timestamp": "2023-12-03T10:00:00Z"}

@app.get("/api/v1/health/audio")
async def health_audio():
    return {"healthy": True, "service": "Audio Processing", "timestamp": "2023-12-03T10:00:00Z"}

@app.post("/api/v1/audio/transcribe")
async def transcribe_audio(audio_file: UploadFile = File(...)):
    # Simulate processing time
    await asyncio.sleep(1)
    
    # Return simulated transcription
    return {
        "success": True,
        "transcription": "Esta es una transcripción simulada de su audio",
        "confidence": 0.92,
        "language": "es-ES",
        "duration": 3.5,
        "processing_time": 1.2,
        "message": "Audio transcribed successfully"
    }

@app.post("/api/v1/audio/validate")
async def validate_audio(audio_file: UploadFile = File(...)):
    return {
        "success": True,
        "valid": True,
        "format": "audio/webm",
        "duration": 3.5,
        "file_size": len(await audio_file.read()),
        "message": "Audio file validated successfully"
    }

@app.post("/api/v1/chat/message")
async def send_message(request: Request):
    data = await request.json()
    message = data.get("message", "")
    
    # Simulate processing time
    await asyncio.sleep(2)
    
    # Generate demo response based on input
    demo_responses = {
        "esta es una transcripción simulada de su audio": "¡Perfecto! He recibido su consulta sobre turismo. Como asistente turístico, puedo ayudarle a planificar su viaje. ¿Le interesa información sobre lugares específicos como museos, restaurantes, o rutas accesibles?",
        "museo": "¡Excelente elección! Madrid tiene museos increíbles. El Museo del Prado cuenta con acceso completo para sillas de ruedas, audioguías en múltiples idiomas, y visitas guiadas especializadas. El horario es de 10:00-20:00 y los domingos hasta las 19:00. ¿Le gustaría que le ayude a planificar la ruta más accesible?",
        "restaurante": "Para restaurantes accesibles en Madrid, le recomiendo varios con excelente acceso: Casa Botín (el más antiguo del mundo), La Barraca (paella tradicional), y Taberna El Sur (tapas auténticas). Todos tienen acceso para sillas de ruedas y personal capacitado. ¿Qué tipo de cocina prefiere?",
        "ruta": "Puedo ayudarle a planificar rutas accesibles por Madrid. La línea de metro tiene ascensores en la mayoría de estaciones, y hay autobuses de piso bajo. Para el centro histórico, recomiendo la ruta: Sol → Plaza Mayor → Palacio Real → Templo de Debod. ¿Desde qué punto quiere empezar?"
    }
    
    # Find matching response
    response_text = "Como asistente turístico especializado en accesibilidad, estoy aquí para ayudarle. Puedo proporcionarle información sobre museos, restaurantes, rutas de transporte público, y atracciones turísticas accesibles en Madrid. ¿En qué puedo asistirle específicamente?"
    
    for key, value in demo_responses.items():
        if key in message.lower():
            response_text = value
            break
    
    return {
        "success": True,
        "conversation_id": data.get("conversation_id", "demo_conv_123"),
        "user_message": message,
        "ai_response": response_text,
        "confidence": 0.94,
        "processing_time": 2.1,
        "message": "Message processed successfully"
    }

@app.get("/api/v1/chat/demo/responses")
async def get_demo_responses():
    return {
        "success": True,
        "sample_responses": [
            {
                "input": "¿Qué museos puedo visitar en Madrid?",
                "response": "Madrid tiene museos increíbles como el Prado, Reina Sofía y Thyssen, todos con excelente accesibilidad.",
                "confidence": 0.95
            },
            {
                "input": "¿Cómo llego al Museo del Prado?",
                "response": "Puede llegar en metro (Línea 2, estación Banco de España) o autobús. Ambas opciones son completamente accesibles.",
                "confidence": 0.92
            }
        ]
    }

if __name__ == "__main__":
    print("""
🎤 VoiceFlow PoC - Simple Test Server
====================================
Starting server at: http://127.0.0.1:8000
API Documentation: http://127.0.0.1:8000/docs
====================================
""")
    
    uvicorn.run(
        "test_server:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True,
        log_level="info"
    )
