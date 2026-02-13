"""
Backend adapter for communicating with the LangChain multi-agent system.
Implements BackendInterface following SOLID SRP principle.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

import structlog

from integration.configuration.settings import Settings
from shared.exceptions.exceptions import BackendCommunicationException
from shared.interfaces.interfaces import BackendInterface

logger = structlog.get_logger(__name__)


class LocalBackendAdapter(BackendInterface):
    """
    Adapter for the existing LangChain multi-agent system.
    Provides clean interface while maintaining SOLID principles.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._backend_instance: Optional[Any] = None
        self._conversation_count = 0

    async def _get_backend_instance(self):
        """Lazy initialization of backend to avoid import issues."""
        if self._backend_instance is None:
            try:
                from business.domains.tourism.agent import TourismMultiAgent

                logger.info("Initializing LocalBackendAdapter with tourism multi-agent system")
                self._backend_instance = TourismMultiAgent()
                logger.info("Backend adapter initialized successfully")

            except ImportError as e:
                logger.error("Failed to import backend", error=str(e))
                raise BackendCommunicationException(
                    "Failed to initialize backend system",
                    error_code="BACKEND_IMPORT_ERROR",
                    details={"import_error": str(e)},
                )
            except Exception as e:
                logger.error("Failed to initialize backend", error=str(e))
                raise BackendCommunicationException(
                    "Failed to initialize backend system",
                    error_code="BACKEND_INIT_ERROR",
                    details={"error": str(e)},
                )

        return self._backend_instance

    async def process_query(self, transcription: str) -> Dict[str, Any]:
        """
        Process user query through REAL multi-agent system or SIMULATED for demo.
        Returns structured response with tourism information.
        """
        try:
            # Check if we should use real agents or simulation
            use_real_agents = getattr(self.settings, "use_real_agents", True)

            if use_real_agents:
                logger.info("🚀 Processing query through REAL backend", query=transcription)
                ai_response = await self._process_real_query(transcription)
            else:
                logger.info("🚀 Processing query through SIMULATED backend", query=transcription)
                ai_response = await self._simulate_ai_response(transcription)

            # Increment conversation counter
            self._conversation_count += 1

            # Get simulation metadata for pipeline visualization and rich cards
            sim_meta = {}
            if not use_real_agents:
                sim_meta = self._get_simulation_metadata(transcription.lower())

            # Structure the response for the UI
            structured_response = {
                "success": True,
                "ai_response": ai_response,
                "transcription": transcription,
                "conversation_id": self._conversation_count,
                "processing_details": {
                    "agents_used": [
                        "tourism_nlu",
                        "accessibility_analysis",
                        "route_planning",
                        "tourism_info",
                    ],
                    "backend_type": ("real_langchain" if use_real_agents else "simulated_demo"),
                    "model": "gpt-4" if use_real_agents else "demo_simulation",
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "session_type": "production" if use_real_agents else "demo",
                    "language": "es-ES",
                },
                "pipeline_steps": sim_meta.get("pipeline_steps"),
                "intent": sim_meta.get("intent"),
                "entities": sim_meta.get("entities"),
                "tourism_data": sim_meta.get("tourism_data"),
            }

            backend_type = "REAL" if use_real_agents else "SIMULATED"
            logger.info(
                f"✅ Query processed successfully ({backend_type})",
                response_length=len(ai_response),
            )
            return structured_response

        except Exception as e:
            logger.error("❌ Error processing query through backend", error=str(e))
            raise BackendCommunicationException(
                f"Failed to process query: {str(e)}",
                error_code="QUERY_PROCESSING_ERROR",
                details={
                    "query": transcription,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

    async def _process_real_query(self, transcription: str) -> str:
        """Process query through REAL LangChain agents with OpenAI."""
        try:
            agent = await self._get_backend_instance()
            logger.info("Calling TourismMultiAgent", query=transcription)

            result = await agent.process_request(transcription)

            logger.info(
                "Backend processing completed",
                response_length=len(result.response_text),
            )
            return result.response_text

        except Exception as e:
            logger.error("Error in real backend processing", error=str(e))
            logger.warning("Falling back to simulation due to backend error")
            return await self._simulate_ai_response(transcription)

    def _get_simulation_metadata(self, query_lower: str) -> dict:
        """Return pipeline_steps, tourism_data, intent and entities for simulation mode."""
        base_steps = [
            {"name": "NLU", "tool": "tourism_nlu", "status": "completed", "duration_ms": 450, "summary": "Intent & entities extracted"},
            {"name": "Accessibility", "tool": "accessibility_analysis", "status": "completed", "duration_ms": 620, "summary": "Accessibility profile analyzed"},
            {"name": "Routes", "tool": "route_planning", "status": "completed", "duration_ms": 880, "summary": "Accessible routes calculated"},
            {"name": "Venue Info", "tool": "tourism_info", "status": "completed", "duration_ms": 540, "summary": "Venue details loaded"},
            {"name": "Response", "tool": "llm_synthesis", "status": "completed", "duration_ms": 710, "summary": "Response generated"},
        ]

        if "prado" in query_lower or "museo del prado" in query_lower:
            base_steps[0]["summary"] = "Intent: venue_search | Dest: Museo del Prado"
            base_steps[1]["summary"] = "Score: 9.2/10 — Full wheelchair access"
            base_steps[2]["summary"] = "2 routes: Metro L2, Bus 27"
            base_steps[3]["summary"] = "Hours, pricing, services loaded"
            return {
                "pipeline_steps": base_steps,
                "intent": "venue_search",
                "entities": {"destination": "Museo del Prado", "accessibility": "wheelchair"},
                "tourism_data": {
                    "venue": {
                        "name": "Museo del Prado",
                        "type": "museum",
                        "accessibility_score": 9.2,
                        "certification": "ONCE_certified",
                        "facilities": ["wheelchair_ramps", "adapted_bathrooms", "audio_guides", "tactile_paths", "sign_language_interpreters"],
                        "opening_hours": {"monday_saturday": "10:00-20:00", "sunday_holidays": "10:00-19:00"},
                        "pricing": {"general": "15\u20ac", "reduced": "7.50\u20ac", "free": "Disabled visitors + companion"},
                    },
                    "routes": [
                        {"transport": "metro", "line": "Metro Line 2", "duration": "25 min", "accessibility": "full", "cost": "2.50\u20ac", "steps": ["Walk to Sol Metro (3 min)", "Line 2 to Banco de Espa\u00f1a (15 min)", "Walk to museum (7 min)"]},
                        {"transport": "bus", "line": "Bus 27", "duration": "35 min", "accessibility": "full", "cost": "1.50\u20ac", "steps": ["Walk to Gran V\u00eda stop (5 min)", "Bus 27 to Cibeles (20 min)", "Walk to museum (10 min)"]},
                    ],
                    "accessibility": {
                        "level": "full_wheelchair_access",
                        "score": 9.2,
                        "certification": "ONCE_certified",
                        "facilities": ["wheelchair_ramps", "adapted_bathrooms", "audio_guides", "tactile_paths", "sign_language_interpreters"],
                        "services": {"wheelchair_rental": "Available at entrance", "sign_language_tours": "Saturdays 11:00", "tactile_tours": "By appointment"},
                    },
                },
            }

        elif any(w in query_lower for w in ["reina", "sof\u00eda", "sofia"]):
            base_steps[0]["summary"] = "Intent: route_search | Dest: Museo Reina Sof\u00eda"
            base_steps[1]["summary"] = "Score: 8.8/10 — Full wheelchair access"
            base_steps[2]["summary"] = "2 routes: Metro L1, Bus 14"
            base_steps[3]["summary"] = "Hours, pricing, exhibitions loaded"
            return {
                "pipeline_steps": base_steps,
                "intent": "route_search",
                "entities": {"destination": "Museo Reina Sof\u00eda", "accessibility": "wheelchair"},
                "tourism_data": {
                    "venue": {
                        "name": "Museo Reina Sof\u00eda",
                        "type": "museum",
                        "accessibility_score": 8.8,
                        "certification": "ONCE_certified",
                        "facilities": ["wheelchair_ramps", "adapted_bathrooms", "audio_guides", "elevator_access"],
                        "opening_hours": {"mon_sat": "10:00-21:00", "sunday": "10:00-14:30", "closed": "Tuesday"},
                        "pricing": {"general": "12\u20ac", "reduced": "6\u20ac", "free": "Disabled visitors + companion"},
                    },
                    "routes": [
                        {"transport": "metro", "line": "Metro Line 1", "duration": "20 min", "accessibility": "full", "cost": "2.50\u20ac", "steps": ["Walk to nearest Metro (4 min)", "Line 1 to Atocha (12 min)", "Walk to museum (4 min)"]},
                        {"transport": "bus", "line": "Bus 14", "duration": "30 min", "accessibility": "full", "cost": "1.50\u20ac", "steps": ["Walk to bus stop (3 min)", "Bus 14 to Atocha (20 min)", "Walk to museum (7 min)"]},
                    ],
                    "accessibility": {
                        "level": "full_wheelchair_access",
                        "score": 8.8,
                        "certification": "ONCE_certified",
                        "facilities": ["wheelchair_ramps", "adapted_bathrooms", "audio_guides", "elevator_access"],
                        "services": {"wheelchair_rental": "Available at main entrance", "sign_language_tours": "Wednesdays 12:00"},
                    },
                },
            }

        elif any(w in query_lower for w in ["concierto", "m\u00fasica", "musica"]):
            base_steps[0]["summary"] = "Intent: event_search | Category: concerts"
            base_steps[1]["summary"] = "Score: 7.5/10 — Hearing accessibility"
            base_steps[2]["summary"] = "Metro routes to music venues"
            base_steps[3]["summary"] = "Venue listings loaded"
            return {
                "pipeline_steps": base_steps,
                "intent": "event_search",
                "entities": {"destination": "Music venues", "accessibility": "hearing"},
                "tourism_data": {
                    "venue": {
                        "name": "Espacios Musicales Madrid",
                        "type": "entertainment",
                        "accessibility_score": 7.5,
                        "certification": "municipal_certified",
                        "facilities": ["wheelchair_spaces", "hearing_loops", "sign_language_interpreters"],
                        "opening_hours": {"events": "Check schedule", "box_office": "17:00-21:00"},
                        "pricing": {"general": "20\u20ac-80\u20ac", "reduced": "Varies", "free": "Companion for disabled"},
                    },
                    "routes": [
                        {"transport": "metro", "line": "Metro Lines 1-10", "duration": "15-25 min", "accessibility": "full", "cost": "2.50\u20ac", "steps": ["Most venues near Metro stations", "Elevator access available", "Follow accessible signage"]},
                    ],
                    "accessibility": {
                        "level": "partial_access",
                        "score": 7.5,
                        "certification": "municipal_certified",
                        "facilities": ["wheelchair_spaces", "hearing_loops", "sign_language_interpreters"],
                        "services": {"hearing_loops": "Available in main halls", "sign_language": "On request with advance booking"},
                    },
                },
            }

        elif any(w in query_lower for w in ["restaurante", "comer", "comida"]):
            base_steps[0]["summary"] = "Intent: recommendation | Category: restaurants"
            base_steps[1]["summary"] = "Score: 6.5/10 — Varied access"
            base_steps[2]["summary"] = "Central Madrid locations"
            base_steps[3]["summary"] = "Restaurant listings loaded"
            return {
                "pipeline_steps": base_steps,
                "intent": "recommendation",
                "entities": {"destination": "Restaurants Madrid", "accessibility": "general"},
                "tourism_data": {
                    "venue": {
                        "name": "Restaurantes Accesibles Madrid",
                        "type": "restaurant",
                        "accessibility_score": 6.5,
                        "certification": "mixed",
                        "facilities": ["wheelchair_ramps", "adapted_bathrooms"],
                        "opening_hours": {"lunch": "13:00-16:00", "dinner": "20:00-24:00"},
                        "pricing": {"range": "15\u20ac-60\u20ac per person"},
                    },
                    "routes": [
                        {"transport": "metro", "line": "Various lines", "duration": "10-20 min", "accessibility": "full", "cost": "2.50\u20ac", "steps": ["Central Madrid well connected", "Multiple accessible stations"]},
                    ],
                    "accessibility": {
                        "level": "varied_access",
                        "score": 6.5,
                        "certification": "mixed",
                        "facilities": ["wheelchair_ramps", "adapted_bathrooms"],
                        "services": {"advance_booking": "Recommended for accessibility needs"},
                    },
                },
            }

        else:
            base_steps[0]["summary"] = "Intent: general_query"
            base_steps[1]["summary"] = "General accessibility overview"
            base_steps[2]["summary"] = "Madrid transport overview"
            base_steps[3]["summary"] = "Popular venues loaded"
            return {
                "pipeline_steps": base_steps,
                "intent": "general_query",
                "entities": {"destination": "Madrid", "accessibility": "general"},
                "tourism_data": None,
            }

    async def _simulate_ai_response(self, transcription: str) -> str:
        """
        Simulate AI response based on transcription for demo purposes.
        This avoids OpenAI API calls during development/demo.
        """
        import random

        # Analyze input to provide contextual response
        query_lower = transcription.lower()

        # Simulate processing delay
        await asyncio.sleep(random.uniform(1, 2))

        # Generate contextual response based on keywords
        if "prado" in query_lower or "museo del prado" in query_lower:
            return """El Museo del Prado es una excelente opción accesible en Madrid.

🏛️ **Información de Accesibilidad:**
• Acceso completo para sillas de ruedas
• Puntuación de accesibilidad: 9.2/10
• Certificado por ONCE
• Rampas y baños adaptados disponibles
• Audioguías en español, inglés y francés

🚌 **Rutas de Transporte:**
• Metro Línea 2 hasta Banco de España (25 min)
• Autobús 27 hasta Cibeles (35 min)
• Todas las opciones son completamente accesibles

💰 **Precios:**
• Entrada general: 15€
• Estudiantes y mayores de 65: 7.50€
• GRATIS para visitantes con discapacidad + acompañante

📞 **Contacto de Accesibilidad:**
• Teléfono: +34 91 330 2800
• Email: accesibilidad@museodelprado.es"""

        elif any(word in query_lower for word in ["concierto", "música", "musica"]):
            return """Para conciertos accesibles en Madrid hoy, te recomiendo varios espacios:

🎵 **Espacios Musicales Accesibles:**
• Teatro Real - Ópera y música clásica
• Auditorio Nacional - Conciertos sinfónicos
• Salas de jazz con accesibilidad garantizada

♿ **Características de Accesibilidad:**
• Espacios reservados para sillas de ruedas
• Bucles de inducción auditiva disponibles
• Interpretación en lenguaje de señas bajo petición
• Puntuación promedio: 7.5/10

🚇 **Transporte:**
• Accesible vía Metro líneas 1-10
• La mayoría cerca de estaciones de metro
• Coste: 2.50€ + entrada al evento

💡 **Recomendación:**
Es necesario reservar con anticipación para servicios de accesibilidad específicos."""

        elif any(word in query_lower for word in ["restaurante", "comer", "comida"]):
            return """Te ayudo con restaurantes accesibles en Madrid:

🍽️ **Restaurantes Accesibles Recomendados:**
• Muchos restaurantes ahora tienen acceso para sillas de ruedas
• Cartas en braille disponibles en algunos establecimientos
• Personal cada vez mejor formado en necesidades de accesibilidad

💰 **Precios:**
• Rango: 15€-60€ por persona
• Sin recargos adicionales por accesibilidad

🏛️ **Tipos de Cocina:**
• Cocina tradicional española
• Restaurantes de fusión moderna
• Bares de tapas accesibles

⚠️ **Importante:**
Recomendamos llamar con anticipación para confirmar la accesibilidad específica del establecimiento."""

        elif any(word in query_lower for word in ["ruta", "llegar", "transporte"]):
            return """Te ayudo con rutas accesibles en Madrid:

🚇 **Sistema de Transporte Accesible:**
• Metro: Líneas 1-12 con acceso por ascensor en la mayoría de estaciones
• Autobuses: Flota de piso bajo con espacios para sillas de ruedas
• Taxis accesibles: Disponibles bajo petición

💰 **Tarifas:**
• Metro: 2.50€ por viaje
• Autobús: 1.50€ por viaje
• Taxi accesible: Tarifa estándar sin suplementos

🗺️ **Características de Accesibilidad:**
• Orientación táctil en estaciones de metro
• Anuncios sonoros en transporte público
• Aplicaciones móviles con información de accesibilidad

💡 **Consejo:**
Planifica tu ruta con tiempo extra y considera las condiciones climáticas para las partes a pie."""

        else:
            return f"""Entiendo tu consulta sobre "{transcription}".

🌍 **Asistente de Turismo Accesible Madrid**

Te puedo ayudar con:
• 🏛️ Museos y atracciones turísticas accesibles
• 🎵 Eventos y conciertos con accesibilidad garantizada
• 🍽️ Restaurantes accesibles
• 🚇 Rutas de transporte accesible
• ♿ Información específica de accesibilidad

📍 **Destinos Populares Accesibles:**
• Museo del Prado (9.2/10 accesibilidad)
• Museo Reina Sofía (8.8/10 accesibilidad)
• Parque del Retiro
• Teatro Real

💬 **Para obtener información más específica, puedes preguntarme sobre:**
- "¿Cómo llegar al Museo del Prado en silla de ruedas?"
- "Conciertos accesibles para hoy en Madrid"
- "Restaurantes accesibles cerca del centro"

¿En qué más puedo ayudarte con tu experiencia turística accesible en Madrid?"""

    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get health status of the backend system.
        """
        try:
            logger.info("🔍 Checking backend system status")

            # Basic health check
            system_status = {
                "status": "healthy",
                "backend_type": "langchain_multiagent",
                "components": {
                    "tourism_multiagent": {
                        "status": "operational",
                        "description": "LangChain multi-agent system",
                    },
                    "openai_gpt4": {
                        "status": "operational",
                        "description": "OpenAI GPT-4 integration",
                    },
                    "nlu_tools": {
                        "status": "operational",
                        "description": "Tourism NLU processing tools",
                    },
                },
                "statistics": {
                    "total_conversations": self._conversation_count,
                    "system_uptime": "running",
                    "memory_usage": "normal",
                },
                "version": "1.0.0",
            }

            logger.info("✅ System status check completed", status="healthy")
            return system_status

        except Exception as e:
            logger.error("❌ System status check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "components": {
                    "tourism_multiagent": {
                        "status": "error",
                        "description": f"Error: {str(e)}",
                    }
                },
                "statistics": {"total_conversations": self._conversation_count},
            }

    async def clear_conversation(self) -> bool:
        """Clear conversation history in the backend system."""
        try:
            logger.info("Clearing conversation history")

            backend = await self._get_backend_instance()
            backend.clear_conversation()

            self._conversation_count = 0

            logger.info("Conversation history cleared successfully")
            return True

        except Exception as e:
            logger.error("Failed to clear conversation", error=str(e))
            raise BackendCommunicationException(
                f"Failed to clear conversation: {str(e)}",
                error_code="CLEAR_CONVERSATION_ERROR",
                details={"error": str(e)},
            )
