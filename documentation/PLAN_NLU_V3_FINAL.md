# Plan de Implementación NLU v3 — Multi-Provider Architecture

**Fecha**: 27 de Febrero de 2026
**Rama**: `feature/nlu-tool-implementation`
**Basado en**: Plan v2 + Review arquitectónica + decisiones de diseño iteradas
**Estado**: Listo para ejecución

---

## Decisiones de diseño ya tomadas

Estas decisiones se debatieron y acordaron previamente. No están abiertas a interpretación:

| Decisión | Valor | Motivo |
|---|---|---|
| Provider a implementar ahora | **OpenAI function calling** | Menor esfuerzo, mayor accuracy, sin patterns manuales |
| Modelo para NLU call | `gpt-4o-mini` | Suficiente para clasificación, 20x más barato que gpt-4 |
| SDK para provider OpenAI | `openai` directo (AsyncOpenAI) | Más portable que LangChain; sin dependencia adicional |
| Fallback inmediato | Keyword matching actual | Ya existe en `nlu_tool.py` + `nlu_patterns.py`, zero effort |
| Provider futuro (fase 2) | Rules + NLP (spaCy Matcher + TF-IDF) | Offline, sin costo, latencia baja |
| Provider futuro (fase 3) | ML supervisado (scikit-learn) | Entrenado en corpus etiquetado |
| Portabilidad del subsistema NLU | Diseño preparado + documentado, no paquete independiente | Pragmatismo: refactorizar a paquete cuando se necesite |
| NLU y NER | Separadas, paralelas (`asyncio.gather`) | Responsabilidades distintas, ritmos de evolución distintos |
| EntityResolver | Obligatorio, con reglas formales | Punto de mayor complejidad; no puede quedar ad-hoc |
| Tests | Co-located con cada commit | Nunca mergear implementación sin cobertura |

---

# 1. PRINCIPIOS DE DISEÑO

## 1.1 Objetivos técnicos

1. Reemplazar el keyword matching actual (`TourismNLUTool._run()`) por un provider NLU basado en OpenAI function calling que clasifique intents y extraiga slots de negocio.
2. Mantener el patrón `Interface → Provider → Factory → Tool` validado con NER.
3. Tipar fuertemente la salida NLU con Pydantic (`NLUResult`).
4. Paralelizar NLU y NER (`asyncio.gather`) ya que ambas consumen texto crudo de forma independiente.
5. Formalizar la reconciliación de entidades NLU/NER con un `EntityResolver` obligatorio.
6. Diseñar la arquitectura para que añadir un provider nuevo (rules, ML) sea implementar una clase + registrar en factory, sin tocar capas superiores.

## 1.2 Non-goals (esta iteración)

- No implementar provider rules + NLP (spaCy Matcher + TF-IDF). Queda documentado como fase 2.
- No implementar provider ML supervisado. Queda documentado como fase 3.
- No fusionar NLU y NER en una sola tool.
- No migrar tools stub (Accessibility, Routes, Venue Info) a APIs externas.
- No extraer el subsistema NLU como paquete independiente (sí preparar el diseño).
- No implementar dashboard Prometheus/Grafana (sí exponer métricas en logs estructurados).

## 1.3 Restricciones operativas

| Restricción | Detalle |
|---|---|
| Capa Business no importa `openai` ni `spacy` | Solo depende de `NLUServiceInterface` (shared) |
| Capa Shared no tiene lógica | Solo contratos Pydantic + ABC interfaces |
| Capa Integration implementa providers | OpenAI, keyword fallback, futuros providers |
| Capa Application hace wiring | DI via factory, feature flags, shadow mode |
| Backward compatible | El endpoint `/api/v1/chat/message` no rompe shape existente |
| Sin dependencias nuevas | `openai` ya es dependencia transitiva via `langchain_openai` |

## 1.4 SLOs definidos

| Métrica | Target | Medición |
|---|---|---|
| **Latencia NLU p95 (OpenAI)** | < 1500ms | Log `nlu_latency_ms` por request |
| **Latencia NLU p95 (keyword fallback)** | < 5ms | Log `nlu_latency_ms` por request |
| **Accuracy intent (corpus eval)** | > 90% con OpenAI provider | `pytest` con corpus etiquetado |
| **Fallback rate** | < 10% de requests en `general_query` | Log `nlu_status=fallback` |
| **Disponibilidad NLU** | 99% (degrada a keyword si OpenAI cae) | `is_service_available()` check |
| **Pipeline total p95** | < 8s (NLU+NER+tools+LLM síntesis) | Log `pipeline_total_ms` |

---

# 2. ARQUITECTURA PROPUESTA

## 2.1 Diagrama de componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                        shared/                                  │
│                                                                 │
│  interfaces/nlu_interface.py    models/nlu_models.py            │
│  ┌─────────────────────────┐   ┌────────────────────────────┐   │
│  │  NLUServiceInterface    │   │  NLUResult                 │   │
│  │  ├ analyze_text()       │   │  NLUEntitySet              │   │
│  │  ├ is_service_available │   │  NLUAlternative            │   │
│  │  ├ get_supported_langs  │   │  ResolvedEntities          │   │
│  │  └ get_service_info     │   │                            │   │
│  └─────────────────────────┘   └────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                        │ implements
        ┌───────────────┼───────────────────────┐
        ▼               ▼                       ▼
┌──────────────┐ ┌──────────────┐  ┌────────────────────────┐
│ OpenAINLU    │ │ KeywordNLU   │  │ SpacyRuleNLU (fase 2)  │
│ Service      │ │ Service      │  │ MLClassifierNLU(fase 3) │
│ (integration)│ │ (integration)│  │ (integration)           │
└──────┬───────┘ └──────┬───────┘  └────────────────────────┘
       │                │
       └────────┬───────┘
                ▼
     ┌─────────────────────┐
     │  NLUServiceFactory   │    ← registry pattern
     │  (integration)       │    ← create_from_settings()
     └──────────┬──────────┘
                │
                ▼
     ┌─────────────────────┐
     │  TourismNLUTool      │    ← LangChain BaseTool wrapper
     │  (business)          │    ← delegates to NLUServiceInterface
     └──────────┬──────────┘
                │
                ▼
     ┌─────────────────────┐
     │  TourismMultiAgent   │    ← orchestrates pipeline
     │  (business)          │    ← asyncio.gather(NLU, NER)
     │                      │    ← EntityResolver merges results
     └─────────────────────┘
```

## 2.2 Flujo detallado paso a paso

```
User Input (raw text)
    │
    ├─── asyncio.gather ────────────────────────┐
    │                                            │
    ▼                                            ▼
[NLU Tool]                                [NER Tool]
 │                                         │
 │ delegates to                            │ delegates to
 │ NLUServiceInterface                     │ NERServiceInterface
 │                                         │
 ▼                                         ▼
[OpenAINLUService]                    [SpacyNERService]
 │ GPT-4o-mini function calling        │ spaCy es_core_news_md
 │ → intent + entities                 │ → locations + top_location
 │                                     │
 │ ┌─ fails? ──────────┐              │
 │ │ KeywordNLUService  │              │
 │ │ (auto-fallback)    │              │
 │ └────────────────────┘              │
 │                                     │
 ▼                                     ▼
NLUResult{                        NER dict{
  status, intent,                   locations[],
  confidence, entities,             top_location,
  alternatives[]                    status
}                                 }
    │                                  │
    └──────────┬───────────────────────┘
               ▼
        [EntityResolver]
         merge NLU entities + NER locations
         deterministic rules (table §4.2)
               │
               ▼
        ResolvedEntities{
          destination,
          locations[],
          accessibility,
          timeframe, ...
          resolution_source{},
          conflicts[]
        }
               │
    ┌──────────┼──────────────┐
    ▼          ▼              ▼
[Accessibility] [Routes]  [Venue Info]
    │          │              │
    └──────────┼──────────────┘
               ▼
        [LLM Synthesis] (GPT-4)
               │
               ▼
        ChatResponse
```

## 2.3 Responsabilidades por capa

| Capa | Componente | Qué hace | Qué NO hace |
|---|---|---|---|
| **Shared** | `NLUServiceInterface` | Define contrato async | No tiene lógica |
| **Shared** | `NLUResult`, `NLUEntitySet`, etc. | Modelos Pydantic tipados | No importa nada de integration/ |
| **Integration** | `OpenAINLUService` | Llama a OpenAI, parsea response | No sabe del pipeline ni de tools |
| **Integration** | `KeywordNLUService` | Clasificación por keywords (legacy) | No importa spaCy ni openai |
| **Integration** | `NLUServiceFactory` | Registry + create_from_settings | No decide cuál usar (eso lo hace settings) |
| **Business** | `TourismNLUTool` | Wrapper LangChain BaseTool | No importa OpenAI ni spaCy |
| **Business** | `EntityResolver` | Merge NLU + NER con reglas | No llama a servicios externos |
| **Business** | `TourismMultiAgent` | Orquesta pipeline, asyncio.gather | No sabe qué provider NLU se usa |
| **Application** | `dependencies.py` | Wiring DI via factory | No implementa lógica NLU |
| **Application** | `backend_adapter.py` | Feature flags, shadow mode | No conoce providers concretos |

## 2.4 Contratos tipados (Pydantic)

### `shared/models/nlu_models.py`

```python
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class NLUAlternative(BaseModel):
    """Alternative intent classification with confidence."""

    intent: str
    confidence: float = Field(ge=0.0, le=1.0)


class NLUEntitySet(BaseModel):
    """Business entities extracted by NLU.

    Portability note: this model is domain-agnostic at the structural level.
    The field names (destination, accessibility, etc.) are tourism-specific.
    To port to another domain, create a new EntitySet model with domain fields
    and use it in a domain-specific NLUResult subclass.
    """

    destination: Optional[str] = None
    accessibility: Optional[str] = None
    timeframe: Optional[str] = None
    transport_preference: Optional[str] = None
    budget: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class NLUResult(BaseModel):
    """Canonical output of any NLU provider.

    Every provider (OpenAI, keyword, spaCy, ML) MUST return this exact model.
    This is the single contract between Integration and Business layers.
    """

    status: Literal["ok", "fallback", "error"] = "ok"
    intent: str = "general_query"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    entities: NLUEntitySet = Field(default_factory=NLUEntitySet)
    alternatives: list[NLUAlternative] = Field(default_factory=list)
    provider: str = "unknown"
    model: str = "unknown"
    language: str = "es"
    analysis_version: str = "nlu_v3.0"
    latency_ms: int = 0


class ResolvedEntities(BaseModel):
    """Output of EntityResolver after merging NLU + NER.

    Each field tracks its source via resolution_source dict,
    enabling post-hoc analysis of resolver decisions.
    """

    destination: Optional[str] = None
    locations: list[str] = Field(default_factory=list)
    top_location: Optional[str] = None
    accessibility: Optional[str] = None
    timeframe: Optional[str] = None
    transport_preference: Optional[str] = None
    budget: Optional[str] = None
    resolution_source: dict[str, str] = Field(default_factory=dict)
    conflicts: list[str] = Field(default_factory=list)
```

### `shared/interfaces/nlu_interface.py`

```python
from abc import ABC, abstractmethod
from typing import Optional

from shared.models.nlu_models import NLUResult


class NLUServiceInterface(ABC):
    """Contract for NLU services: intent classification + slot extraction.

    Portability note: this interface is provider-agnostic. Any NLU backend
    (LLM, rules, ML classifier) implements this same contract. The Business
    layer depends ONLY on this interface, never on concrete providers.

    Provider lifecycle:
    1. Implement this interface in integration/external_apis/
    2. Register in NLUServiceFactory
    3. Set VOICEFLOW_NLU_PROVIDER=<name> in env
    4. Business layer automatically uses it via DI

    Future providers to implement:
    - "spacy_rule_hybrid": spaCy Matcher + TF-IDF similarity (offline, low latency)
    - "ml_classifier": scikit-learn trained on labeled corpus (offline, medium accuracy)
    """

    @abstractmethod
    async def analyze_text(
        self,
        text: str,
        language: Optional[str] = None,
        profile_context: Optional[dict] = None,
    ) -> NLUResult:
        """Classify intent and extract business entities from text.

        Args:
            text: Raw user input (no preprocessing needed).
            language: ISO 639-1 code. None = use provider default.
            profile_context: Optional user profile for ranking bias (future use).

        Returns:
            NLUResult with intent, entities, confidence, and provider metadata.
        """
        ...

    @abstractmethod
    def is_service_available(self) -> bool:
        """Report if the provider is ready (API key set, model loaded, etc.)."""
        ...

    @abstractmethod
    def get_supported_languages(self) -> list[str]:
        """Return list of language codes this provider can handle."""
        ...

    @abstractmethod
    def get_service_info(self) -> dict:
        """Return provider metadata: name, model, version, status."""
        ...
```

---

# 3. ESTRATEGIA DE CLASIFICACIÓN DE INTENTS

## 3.1 Provider principal: OpenAI function calling

### Arquitectura

```
Raw user text
    │
    ▼
OpenAI API (gpt-4o-mini)
  ├ system prompt: classification instructions
  ├ user message: raw text (NO preprocessing)
  ├ tools: [classify_tourism_request function schema]
  └ tool_choice: forced ("classify_tourism_request")
    │
    ▼
Structured JSON response (schema-validated by OpenAI)
    │
    ▼
Parse into NLUResult
```

### Implementación concreta

```python
# integration/external_apis/openai_nlu_service.py

import json
import time
from typing import Any, Optional

import structlog
from openai import AsyncOpenAI

from integration.configuration.settings import Settings
from shared.interfaces.nlu_interface import NLUServiceInterface
from shared.models.nlu_models import NLUAlternative, NLUEntitySet, NLUResult

logger = structlog.get_logger(__name__)

# --- Function calling schema (the "brain" of classification) ---

NLU_FUNCTION_SCHEMA = {
    "name": "classify_tourism_request",
    "description": "Classify a tourism user request into intent and extract entities",
    "parameters": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "route_planning",
                    "event_search",
                    "restaurant_search",
                    "accommodation_search",
                    "general_query",
                ],
                "description": (
                    "Primary user intent. "
                    "route_planning: user wants to go somewhere or find transport. "
                    "event_search: user looks for events, concerts, activities. "
                    "restaurant_search: user wants to eat or find restaurants. "
                    "accommodation_search: user needs hotel or lodging. "
                    "general_query: generic tourism question or unclassifiable."
                ),
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "How confident you are in the intent classification (0.0 to 1.0)",
            },
            "destination": {
                "type": "string",
                "nullable": True,
                "description": "Specific place, venue, or area mentioned (e.g. 'Museo del Prado', 'Retiro'). Null if none mentioned.",
            },
            "accessibility": {
                "type": "string",
                "enum": ["wheelchair", "visual_impairment", "hearing_impairment", "cognitive"],
                "nullable": True,
                "description": "Accessibility requirement if mentioned. Null if none.",
            },
            "timeframe": {
                "type": "string",
                "enum": ["today", "today_morning", "today_afternoon", "today_evening", "tomorrow", "this_weekend"],
                "nullable": True,
                "description": "When the user wants to do the activity. Null if not specified.",
            },
            "transport_preference": {
                "type": "string",
                "enum": ["metro", "bus", "walk", "taxi"],
                "nullable": True,
                "description": "Preferred transport mode if mentioned. Null if none.",
            },
            "alternative_intent": {
                "type": "string",
                "enum": [
                    "route_planning",
                    "event_search",
                    "restaurant_search",
                    "accommodation_search",
                    "general_query",
                ],
                "nullable": True,
                "description": "Secondary intent if the message could be interpreted another way. Null if unambiguous.",
            },
            "alternative_confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "nullable": True,
                "description": "Confidence for the alternative intent.",
            },
        },
        "required": ["intent", "confidence"],
    },
}

NLU_SYSTEM_PROMPT = (
    "You are an NLU classifier for an accessible tourism assistant focused on Spain. "
    "Classify the user's intent and extract relevant entities. "
    "Be precise with destination names — use the full official name when possible "
    "(e.g., 'Museo del Prado' not just 'Prado'). "
    "Detect accessibility needs even when expressed indirectly "
    "(e.g., 'mi madre va en silla de ruedas' → wheelchair). "
    "The user may write in Spanish or English."
)


class OpenAINLUService(NLUServiceInterface):
    """NLU provider using OpenAI function calling for intent + slot extraction.

    Uses gpt-4o-mini with forced function calling to guarantee structured output.
    The function schema (NLU_FUNCTION_SCHEMA) defines the complete intent taxonomy
    and entity types — to add a new intent or entity, update the schema only.

    Portability note: to use this provider in another project, copy this file
    and nlu_interface.py + nlu_models.py. Change NLU_FUNCTION_SCHEMA to match
    your domain's intents and entities.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or Settings()
        self._provider_name = "openai"
        self._model = self._settings.nlu_openai_model  # "gpt-4o-mini"
        self._default_language = self._settings.nlu_default_language

        # Initialize async client
        api_key = self._settings.openai_api_key
        self._client = AsyncOpenAI(api_key=api_key) if api_key else None

        if not self._client:
            logger.warning("OpenAI NLU: no API key configured, provider unavailable")

    async def analyze_text(
        self,
        text: str,
        language: Optional[str] = None,
        profile_context: Optional[dict] = None,
    ) -> NLUResult:
        """Classify intent and extract entities via OpenAI function calling."""
        if not text or not text.strip():
            return NLUResult(
                status="error",
                provider=self._provider_name,
                model=self._model,
                language=language or self._default_language,
            )

        if not self.is_service_available():
            logger.warning("openai_nlu_unavailable")
            return NLUResult(
                status="error",
                provider=self._provider_name,
                model=self._model,
                language=language or self._default_language,
            )

        start = time.perf_counter()

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                max_tokens=200,
                messages=[
                    {"role": "system", "content": NLU_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                tools=[{"type": "function", "function": NLU_FUNCTION_SCHEMA}],
                tool_choice={"type": "function", "function": {"name": "classify_tourism_request"}},
            )

            latency_ms = int((time.perf_counter() - start) * 1000)

            # Parse function call arguments
            tool_call = response.choices[0].message.tool_calls[0]
            args = json.loads(tool_call.function.arguments)

            # Build alternatives
            alternatives = []
            alt_intent = args.get("alternative_intent")
            alt_conf = args.get("alternative_confidence")
            if alt_intent and alt_conf:
                alternatives.append(NLUAlternative(intent=alt_intent, confidence=alt_conf))

            result = NLUResult(
                status="ok",
                intent=args["intent"],
                confidence=args.get("confidence", 0.9),
                entities=NLUEntitySet(
                    destination=args.get("destination"),
                    accessibility=args.get("accessibility"),
                    timeframe=args.get("timeframe"),
                    transport_preference=args.get("transport_preference"),
                ),
                alternatives=alternatives,
                provider=self._provider_name,
                model=self._model,
                language=language or self._default_language,
                latency_ms=latency_ms,
            )

            logger.info(
                "nlu_analysis_complete",
                provider=result.provider,
                model=result.model,
                intent=result.intent,
                confidence=result.confidence,
                status=result.status,
                entity_count=sum(1 for v in result.entities.model_dump(exclude={"extra"}).values() if v),
                latency_ms=latency_ms,
                classification_layer="openai_function_calling",
            )

            return result

        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.error("openai_nlu_error", error=str(e), latency_ms=latency_ms)
            return NLUResult(
                status="error",
                provider=self._provider_name,
                model=self._model,
                language=language or self._default_language,
                latency_ms=latency_ms,
            )

    def is_service_available(self) -> bool:
        """Available when OpenAI client is configured."""
        return self._client is not None

    def get_supported_languages(self) -> list[str]:
        """GPT-4o-mini supports all major languages natively."""
        return ["es", "en", "fr", "de", "it", "pt", "ca", "eu", "gl"]

    def get_service_info(self) -> dict:
        return {
            "provider": self._provider_name,
            "model": self._model,
            "available": self.is_service_available(),
            "default_language": self._default_language,
            "classification_method": "function_calling",
            "analysis_version": "nlu_v3.0",
        }
```

### ¿Por qué function calling y no JSON en el prompt?

| Aspecto | JSON libre en prompt | Function calling (elegido) |
|---|---|---|
| Schema garantizado | No — puede inventar campos | Sí — la API valida contra el schema |
| Intents válidos | Puede inventar valores | Restringido al `enum` definido |
| Parsing | Puede fallar (JSON mal formado) | Siempre JSON válido |
| Prompt engineering | Instrucciones largas para formateo | Schema es autodescriptivo |
| Costo tokens | Más tokens en prompt explicando formato | Schema va en `tools`, no en tokens de prompt |

## 3.2 Fallback: keyword matching (provider legacy)

Cuando OpenAI no está disponible (sin API key, timeout, rate limit), se usa el clasificador keyword existente, encapsulado como un `NLUServiceInterface`:

```python
# integration/external_apis/keyword_nlu_service.py

class KeywordNLUService(NLUServiceInterface):
    """Fallback NLU using simple keyword matching.

    This is the Gen-1 approach already present in the codebase
    (nlu_patterns.py), wrapped to comply with NLUServiceInterface.
    It exists as emergency degradation — not as a quality provider.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or Settings()
        self._provider_name = "keyword"
        self._default_language = self._settings.nlu_default_language

    async def analyze_text(self, text: str, language=None, profile_context=None) -> NLUResult:
        text_lower = text.lower() if text else ""

        intent = self._match_intent(text_lower)
        destination = self._match_destination(text_lower)
        accessibility = self._match_accessibility(text_lower)

        confidence = 0.70 if intent != "general_query" else 0.0
        status = "ok" if intent != "general_query" else "fallback"

        return NLUResult(
            status=status,
            intent=intent,
            confidence=confidence,
            entities=NLUEntitySet(
                destination=destination,
                accessibility=accessibility,
            ),
            provider=self._provider_name,
            model="keyword_patterns",
            language=language or self._default_language,
        )

    # _match_intent, _match_destination, _match_accessibility:
    # Exact same logic as current TourismNLUTool._match_pattern
    # and _extract_destination, using INTENT_PATTERNS,
    # DESTINATION_PATTERNS, ACCESSIBILITY_PATTERNS from nlu_patterns.py
```

## 3.3 Auto-fallback en la factory

La factory gestiona la cadena de fallback de forma transparente:

```python
# integration/external_apis/nlu_factory.py

class NLUServiceFactory:

    _service_registry = {
        "openai": OpenAINLUService,
        "keyword": KeywordNLUService,
    }

    @classmethod
    def create_from_settings(cls, settings=None) -> NLUServiceInterface:
        """Create NLU provider with automatic fallback chain.

        If the configured provider is unavailable (e.g., no API key),
        falls back to keyword provider.
        """
        runtime_settings = settings or Settings()
        provider = runtime_settings.nlu_provider  # e.g., "openai"

        service = cls.create_service(provider, settings=runtime_settings)

        if not service.is_service_available():
            logger.warning(
                "nlu_provider_unavailable_falling_back",
                configured=provider,
                fallback="keyword",
            )
            service = cls.create_service("keyword", settings=runtime_settings)

        return service
```

## 3.4 Taxonomía de intents (v3.0)

| Intent | Descripción | Ejemplo ES | Ejemplo EN |
|---|---|---|---|
| `route_planning` | Quiere llegar a un lugar o buscar transporte | "Cómo llego al Prado en metro?" | "How do I get to Retiro?" |
| `event_search` | Busca eventos, conciertos, actividades | "Qué conciertos hay este finde?" | "Any events this weekend?" |
| `restaurant_search` | Busca dónde comer | "Restaurante accesible cerca del centro" | "Accessible restaurant nearby" |
| `accommodation_search` | Busca alojamiento | "Hotel con accesibilidad en Madrid" | "Wheelchair-accessible hotel" |
| `general_query` | Consulta genérica o no clasificable | "Qué me recomiendas?" | "What should I visit?" |

**Para añadir un intent nuevo**: actualizar el `enum` en `NLU_FUNCTION_SCHEMA["parameters"]["properties"]["intent"]["enum"]` y su `description`. No requiere cambios en ninguna otra capa.

## 3.5 Manejo de multi-intent

**Decisión**: se retorna un solo intent primario + `alternatives`.

- Input: "Quiero visitar el Prado y luego cenar cerca"
- Output: `intent: "route_planning"`, `alternatives: [{intent: "restaurant_search", confidence: 0.75}]`
- El pipeline consume solo el intent primario.
- El campo `alternative_intent` en el function schema le pide al modelo que capture el segundo intent si existe.

## 3.6 Manejo de idiomas

El provider OpenAI soporta cualquier idioma nativamente. No necesita configuración por idioma. El campo `language` en `NLUResult` refleja el idioma solicitado para trazabilidad.

El provider keyword solo funciona bien en español (los patterns están en español). Para otros idiomas retorna `general_query` con `status=fallback`.

---

# 4. ENTITY RESOLVER — ESPECIFICACIÓN FORMAL

## 4.1 Interfaz

```python
# business/domains/tourism/entity_resolver.py

import structlog
from shared.models.nlu_models import NLUResult, ResolvedEntities

logger = structlog.get_logger(__name__)


class EntityResolver:
    """Merge NLU business entities with NER location extractions.

    Stateless, deterministic resolver with explicit precedence rules.
    Every decision is logged via resolution_source and conflicts fields.

    Design note: this class lives in Business layer because it encodes
    domain-specific merge rules (e.g., "NLU normalized destination wins
    over NER raw extraction"). The interface types (NLUResult, ResolvedEntities)
    live in Shared layer.
    """

    def resolve(
        self,
        nlu_result: NLUResult,
        ner_locations: list[str],
        ner_top_location: str | None,
    ) -> ResolvedEntities:
        """Apply merge rules and return resolved entities with full traceability."""
        ...
```

## 4.2 Tabla de decisión

| # | NLU `destination` | NER `top_location` | Resultado | `resolution_source` | Lógica |
|---|---|---|---|---|---|
| 1 | `None` | `None` | `None` | `"none"` | Nada que resolver |
| 2 | `None` | `"Prado"` | `"Prado"` | `"ner"` | Solo NER tiene dato |
| 3 | `"Museo del Prado"` | `None` | `"Museo del Prado"` | `"nlu"` | Solo NLU tiene dato |
| 4 | `"Museo del Prado"` | `"Museo del Prado"` | `"Museo del Prado"` | `"both_agree"` | Coincidencia exacta |
| 5 | `"Museo del Prado"` | `"Prado"` | `"Museo del Prado"` | `"nlu_normalized"` | NER contenido en NLU → NLU gana (más completo) |
| 6 | `"Museo del Prado"` | `"Retiro"` | `"Museo del Prado"` | `"nlu_preferred"` | Conflicto real → NLU preferido (normalización de negocio) |
| 7 | `"general"` / `None`-like | `"Retiro"` | `"Retiro"` | `"ner_override"` | NLU genérico, NER específico → NER gana |

## 4.3 Implementación de reglas

```python
def resolve(self, nlu_result, ner_locations, ner_top_location) -> ResolvedEntities:
    nlu_dest = nlu_result.entities.destination
    conflicts = []
    resolution_source = {}

    # --- DESTINATION RESOLUTION ---
    GENERIC_DESTINATIONS = {"general", "general_query", "madrid centro", None}

    if not nlu_dest and not ner_top_location:
        # Rule 1: both absent
        resolved_dest = None
        resolution_source["destination"] = "none"

    elif not nlu_dest and ner_top_location:
        # Rule 2: only NER
        resolved_dest = ner_top_location
        resolution_source["destination"] = "ner"

    elif nlu_dest and not ner_top_location:
        # Rule 3: only NLU
        resolved_dest = nlu_dest
        resolution_source["destination"] = "nlu"

    elif self._names_match(nlu_dest, ner_top_location):
        # Rules 4 & 5: agreement (exact or fuzzy)
        resolved_dest = nlu_dest  # NLU version preferred (normalized)
        resolution_source["destination"] = "both_agree"

    elif nlu_dest.lower().strip() in GENERIC_DESTINATIONS:
        # Rule 7: NLU generic, NER specific → NER wins
        resolved_dest = ner_top_location
        resolution_source["destination"] = "ner_override"
        conflicts.append(f"NLU='{nlu_dest}' generic, NER='{ner_top_location}' specific → NER used")

    else:
        # Rule 6: genuine conflict → NLU wins (business normalization)
        resolved_dest = nlu_dest
        resolution_source["destination"] = "nlu_preferred"
        conflicts.append(f"Conflict: NLU='{nlu_dest}' vs NER='{ner_top_location}' → NLU preferred")

    # --- OTHER ENTITIES: passthrough from NLU ---
    for field in ("accessibility", "timeframe", "transport_preference", "budget"):
        value = getattr(nlu_result.entities, field, None)
        resolution_source[field] = "nlu" if value else "none"

    if conflicts:
        logger.warning("entity_resolver_conflicts", conflicts=conflicts)

    return ResolvedEntities(
        destination=resolved_dest,
        locations=ner_locations,
        top_location=ner_top_location,
        accessibility=nlu_result.entities.accessibility,
        timeframe=nlu_result.entities.timeframe,
        transport_preference=nlu_result.entities.transport_preference,
        budget=nlu_result.entities.budget,
        resolution_source=resolution_source,
        conflicts=conflicts,
    )

@staticmethod
def _names_match(nlu_name: str, ner_name: str) -> bool:
    """Fuzzy containment match."""
    a, b = nlu_name.lower().strip(), ner_name.lower().strip()
    return a == b or b in a or a in b
```

## 4.4 Ejemplos concretos

**Ejemplo 1 — Acuerdo total:**
```
Input:  "Quiero una ruta accesible al Museo del Prado"
NLU:    destination="Museo del Prado", accessibility="wheelchair"
NER:    top_location="Museo del Prado", locations=["Museo del Prado"]
Result: destination="Museo del Prado", source={"destination":"both_agree"}, conflicts=[]
```

**Ejemplo 2 — NLU genérico, NER específico:**
```
Input:  "Qué puedo visitar en Madrid?"
NLU:    destination=None, intent="general_query"
NER:    top_location="Madrid", locations=["Madrid"]
Result: destination="Madrid", source={"destination":"ner"}, conflicts=[]
```

**Ejemplo 3 — Conflicto real:**
```
Input:  "Llévame al Retiro, quiero ver el Prado también"
NLU:    destination="Parque del Retiro" (first entity detected by LLM)
NER:    top_location="Retiro", locations=["Retiro", "Prado"]
Result: destination="Parque del Retiro", source={"destination":"both_agree"}, conflicts=[]
        locations=["Retiro", "Prado"]  ← NER preserves both
```

**Ejemplo 4 — Solo NER (destino fuera del dominio):**
```
Input:  "Información sobre la Alhambra"
NLU:    destination="Alhambra" (OpenAI lo extrae correctamente)
NER:    top_location="Alhambra"
Result: destination="Alhambra", source={"destination":"both_agree"}, conflicts=[]
```

---

# 5. PLAN DE COMMITS REORGANIZADO

## Commit 1 — Contratos NLU + Modelos Pydantic + Settings + Tests de contrato

**Objetivo**: Establecer los cimientos: interfaz, modelos tipados, configuración. Verificable de forma aislada sin ningún provider.

**Archivos a crear:**
- `shared/interfaces/nlu_interface.py`
- `shared/models/__init__.py`
- `shared/models/nlu_models.py`
- `tests/test_shared/test_nlu_interface.py`
- `tests/test_shared/test_nlu_models.py`

**Archivos a modificar:**
- `shared/interfaces/__init__.py` (export `NLUServiceInterface`)
- `integration/configuration/settings.py` (añadir campos `nlu_*`)
- `.env.example` (documentar variables NLU)

**Settings a añadir en `settings.py`:**
```python
# NLU settings
nlu_enabled: bool = Field(default=True, description="Enable NLU service")
nlu_provider: str = Field(default="openai", description="NLU provider: openai, keyword")
nlu_default_language: str = Field(default="es", description="Default NLU language")
nlu_openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model for NLU classification")
nlu_confidence_threshold: float = Field(default=0.40, description="Min confidence for non-fallback")
nlu_fallback_intent: str = Field(default="general_query", description="Intent when below threshold")
nlu_shadow_mode: bool = Field(default=False, description="Run new NLU + old keyword in parallel, compare")
```

**Tests incluidos en este commit:**
- `test_nlu_interface.py`:
  - `NLUServiceInterface` is abstract with expected methods.
  - A concrete mock implementation satisfies the contract.
- `test_nlu_models.py`:
  - `NLUResult` validates confidence [0,1], status literal, defaults.
  - `NLUResult` JSON round-trip (serialize → deserialize).
  - `NLUEntitySet` with all fields None is valid.
  - `ResolvedEntities` with empty conflicts/resolution_source is valid.
  - Invalid confidence (< 0 or > 1) raises `ValidationError`.
- Settings parsing:
  - `nlu_provider` defaults to "openai".
  - `nlu_openai_model` defaults to "gpt-4o-mini".

**Validación:**
```bash
poetry run ruff check shared/ integration/
poetry run ruff format --check shared/ integration/
poetry run pytest tests/test_shared/ -v --tb=short
```

**Mensaje de commit:**
```
feat(shared,integration): add NLU interface, typed Pydantic models, and NLU env settings
```

---

## Commit 2 — OpenAI NLU provider + Keyword fallback provider + Factory + Tests unitarios

**Objetivo**: Implementar ambos providers y la factory con auto-fallback. Verificar clasificación real contra OpenAI y clasificación keyword.

**Archivos a crear:**
- `integration/external_apis/openai_nlu_service.py`
- `integration/external_apis/keyword_nlu_service.py`
- `integration/external_apis/nlu_factory.py`
- `tests/test_integration/test_openai_nlu_service.py`
- `tests/test_integration/test_keyword_nlu_service.py`
- `tests/test_integration/test_nlu_factory.py`

**Archivos a modificar:**
- `integration/external_apis/__init__.py` (exports)

**Tests incluidos en este commit:**

`test_openai_nlu_service.py`:
- Mock de `AsyncOpenAI` para tests sin API key.
- Verifica que function calling response se parsea a `NLUResult` correctamente.
- Verifica que error de API retorna `NLUResult(status="error")`.
- Verifica que input vacío retorna `NLUResult(status="error")`.
- Verifica que `is_service_available()` retorna False sin API key.
- **(Opcional, marcado `@pytest.mark.integration`)**: test real contra OpenAI con 3-5 frases, solo si `OPENAI_API_KEY` está disponible.

`test_keyword_nlu_service.py`:
- Intents ES: 5+ frases con intent esperado.
- Fallback: input ambiguo retorna `general_query`.
- Entities: destination, accessibility extraction.

`test_nlu_factory.py`:
- `create_from_settings()` con provider "openai".
- `create_from_settings()` con provider "keyword".
- Provider inválido raises `ValueError`.
- Auto-fallback: si OpenAI no disponible, retorna keyword.
- `register_service()` con provider custom.
- `get_available_services()` listing.

**Validación:**
```bash
poetry run ruff check integration/
poetry run ruff format --check integration/
poetry run pytest tests/test_integration/test_openai_nlu_service.py tests/test_integration/test_keyword_nlu_service.py tests/test_integration/test_nlu_factory.py -v
```

**Mensaje de commit:**
```
feat(integration): implement OpenAI and keyword NLU providers with pluggable factory
```

---

## Commit 3 — EntityResolver + Refactor NLUTool + Paralelización NLU||NER + Tests

**Objetivo**: Integrar NLU en el pipeline de negocio. Refactorizar `TourismNLUTool` para delegar al service. Implementar EntityResolver. Paralelizar NLU y NER.

**Archivos a crear:**
- `business/domains/tourism/entity_resolver.py`
- `tests/test_business/test_entity_resolver.py`
- `tests/test_business/test_tourism_nlu_tool.py`

**Archivos a modificar:**
- `business/domains/tourism/tools/nlu_tool.py` (refactor: delega a NLUServiceInterface)
- `business/domains/tourism/agent.py` (parallelización NLU||NER, EntityResolver)

**Cambio clave en `agent.py` — paralelización:**
```python
# Antes (secuencial):
nlu_raw = self.nlu._run(user_input)
ner_raw = self.location_ner._run(user_input)

# Después (paralelo):
import asyncio

async def _parallel_nlu_ner(self, user_input, language="es"):
    nlu_coro = self.nlu_service.analyze_text(user_input, language=language)
    ner_coro = self.ner_service.extract_locations(user_input, language=language)
    return await asyncio.gather(nlu_coro, ner_coro)

nlu_result, ner_result = asyncio.run(self._parallel_nlu_ner(user_input))
resolved = EntityResolver().resolve(nlu_result, ner_result.get("locations", []), ner_result.get("top_location"))
```

**Tests incluidos en este commit:**

`test_entity_resolver.py`:
- Los 7 escenarios de la tabla de decisión (§4.2).
- Edge: both None, NLU="general", fuzzy match "Prado"↔"Museo del Prado".
- Verifica `conflicts` y `resolution_source` en cada caso.
- Verifica que `locations[]` siempre preserva el raw NER list.

`test_tourism_nlu_tool.py`:
- Mock de `NLUServiceInterface` inyectado en tool.
- Verifica JSON output tiene fields `intent`, `entities`, `confidence`.
- Verifica fallback cuando service no disponible.

**Validación:**
```bash
poetry run ruff check business/
poetry run pytest tests/test_business/test_entity_resolver.py tests/test_business/test_tourism_nlu_tool.py -v
```

**Mensaje de commit:**
```
refactor(business): add EntityResolver, parallelize NLU+NER, decouple TourismNLUTool
```

---

## Commit 4 — Wiring DI + Feature flags + Shadow mode + Docs

**Objetivo**: Conectar al runtime, feature flags, shadow mode, documentación actualizada.

**Archivos a modificar:**
- `shared/utils/dependencies.py` (añadir `get_nlu_service()`, pasar a `get_backend_adapter()`)
- `application/orchestration/backend_adapter.py` (inyectar NLU, shadow mode)
- `documentation/API_REFERENCE.md`
- `documentation/DEVELOPMENT.md`

**DI wiring:**
```python
# dependencies.py
def get_nlu_service(settings: Settings = Depends(get_settings)) -> Optional[NLUServiceInterface]:
    if not settings.nlu_enabled:
        return None
    from integration.external_apis.nlu_factory import NLUServiceFactory
    return NLUServiceFactory.create_from_settings(settings)

def get_backend_adapter(settings: Settings = Depends(get_settings)) -> BackendInterface:
    ner_service = get_ner_service(settings)
    nlu_service = get_nlu_service(settings)
    return LocalBackendAdapter(settings, ner_service=ner_service, nlu_service=nlu_service)
```

**Shadow mode (en backend_adapter):**
```python
# When nlu_shadow_mode=True:
# 1. Run OLD keyword NLU → used for actual response
# 2. Run NEW OpenAI NLU → result only logged, not used
# 3. Compare and log differences
#
# When nlu_shadow_mode=False:
# 1. Run configured NLU provider → used for actual response
```

**Validación:**
```bash
poetry run ruff check .
# Smoke test with real endpoint
curl -s -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Content-Type: application/json" \
  -d '{"message":"Quiero una ruta accesible al Museo del Prado"}' | python -m json.tool
```

**Mensaje de commit:**
```
feat(application): wire NLU via DI, add shadow mode and feature flags
```

---

## Commit 5 — Tests e2e + Corpus de evaluación + Hardening

**Objetivo**: Cobertura e2e, corpus etiquetado, property-based tests, validación de accuracy.

**Archivos a crear:**
- `tests/test_application/test_chat_nlu_integration.py`
- `tests/test_business/test_tourism_agent_nlu_ner_merge.py`
- `tests/fixtures/nlu_evaluation_corpus.json`
- `tests/test_integration/test_nlu_evaluation.py`

**Archivos a modificar:**
- `tests/conftest.py` (fixtures NLU)

**Tests incluidos:**

1. **e2e API** (`test_chat_nlu_integration.py`):
   - POST `/chat/message` con `use_real_agents=False`.
   - Response has `intent`, `entities`, `pipeline_steps` con NLU step.
   - Backward compatible: existing fields still present.

2. **Pipeline NLU+NER merge** (`test_tourism_agent_nlu_ner_merge.py`):
   - Mock NLU + mock NER → EntityResolver runs.
   - Resolved entities appear in metadata.

3. **Evaluation corpus** (`nlu_evaluation_corpus.json` + `test_nlu_evaluation.py`):
   - 80+ labeled examples (see §6.1).
   - Test: accuracy > 90% on corpus (with OpenAI provider).
   - Test: accuracy > 70% with keyword fallback.

4. **Property-based** (in `test_nlu_models.py`):
   - For any NLUResult, `intent` is never None, `confidence` in [0,1].

**Validación final:**
```bash
poetry run pytest tests/ -v --tb=short
poetry run ruff check . && poetry run ruff format --check .
poetry run mypy shared/ integration/ business/ application/ --ignore-missing-imports
```

**Mensaje de commit:**
```
test: add e2e coverage, evaluation corpus, and property-based tests for NLU pipeline
```

---

# 6. TESTING & EVALUATION STRATEGY

## 6.1 Corpus de evaluación

`tests/fixtures/nlu_evaluation_corpus.json` — 80+ examples:

**Distribución mínima:**
- 20 `route_planning` (ES) — variaciones: "cómo llegar", "ruta a", "quiero ir", "transporte a"
- 15 `event_search` (ES) — variaciones: "eventos", "conciertos", "qué hacer", "actividades"
- 10 `restaurant_search` (ES) — variaciones: "dónde comer", "restaurante", "cenar"
- 10 `accommodation_search` (ES) — variaciones: "hotel", "alojamiento", "dormir"
- 10 `general_query` (ES) — variaciones: "recomiéndame", "qué visitar", saludos
- 5 multi-intent (ES) — "visitar X y cenar cerca"
- 5 edge cases — vacío, gibberish, prompt injection
- 5 English — basic intent classification in EN

## 6.2 Métricas de éxito

| Métrica | Keyword (baseline) | OpenAI (target) |
|---|---|---|
| Intent accuracy | Medido en Commit 5 | > 90% |
| Entity extraction F1 | Medido en Commit 5 | > 85% |
| Fallback rate | Medido en Commit 5 | < 10% |

## 6.3 Tests de integración real con OpenAI

Marcados con `@pytest.mark.integration` y condicionados a la presencia de `OPENAI_API_KEY`:

```python
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No API key")
async def test_openai_nlu_real_classification():
    """Verify real OpenAI classification with known inputs."""
    service = OpenAINLUService(settings=Settings())
    result = await service.analyze_text("Cómo llego al Museo del Prado en silla de ruedas?")
    assert result.intent == "route_planning"
    assert result.entities.destination is not None
    assert result.entities.accessibility == "wheelchair"
    assert result.status == "ok"
```

---

# 7. OBSERVABILIDAD Y OPERACIÓN

## 7.1 Logs estructurados

Cada análisis NLU emite:

```python
logger.info(
    "nlu_analysis_complete",
    request_id=request_id,              # correlation
    provider="openai",                  # or "keyword"
    model="gpt-4o-mini",               # or "keyword_patterns"
    language="es",
    intent="route_planning",
    confidence=0.95,
    status="ok",                        # ok | fallback | error
    entity_count=3,
    latency_ms=820,
    classification_layer="openai_function_calling",  # or "keyword_matching"
)
```

EntityResolver emite:

```python
logger.info(
    "entity_resolver_result",
    request_id=request_id,
    destination="Museo del Prado",
    resolution_source="both_agree",
    conflict_count=0,
)
```

## 7.2 Shadow mode comparison log

```python
logger.info(
    "nlu_shadow_comparison",
    request_id=request_id,
    old_provider="keyword",
    old_intent="route_planning",
    new_provider="openai",
    new_intent="route_planning",
    new_confidence=0.95,
    agreement=True,
    text_preview="Quiero una ruta accesible al...",
)
```

## 7.3 Correlation IDs

```python
import uuid
import structlog

request_id = str(uuid.uuid4())
structlog.contextvars.bind_contextvars(request_id=request_id)
# All subsequent logs in this request chain will include request_id
```

## 7.4 Feature flags

| Flag | Default | Efecto |
|---|---|---|
| `VOICEFLOW_NLU_ENABLED` | `true` | Kill switch completo → keyword fallback |
| `VOICEFLOW_NLU_PROVIDER` | `openai` | Selección de provider |
| `VOICEFLOW_NLU_SHADOW_MODE` | `false` | Shadow comparison mode |
| `VOICEFLOW_NLU_OPENAI_MODEL` | `gpt-4o-mini` | Modelo para OpenAI NLU |
| `VOICEFLOW_NLU_CONFIDENCE_THRESHOLD` | `0.40` | Umbral para fallback intent |

---

# 8. ESTRATEGIA DE ROLLBACK

## 8.1 Fases de rollout

```
Fase 0: nlu_enabled=false
        (estado actual, keyword matching via TourismNLUTool)
   │
   ▼
Fase 1: nlu_enabled=true, nlu_shadow_mode=true
        (OpenAI NLU ejecuta en paralelo pero NO afecta resultado)
        (analizar logs 24-48h: agreement rate, latencia, errores)
   │
   ▼
Fase 2: nlu_enabled=true, nlu_shadow_mode=false
        (OpenAI NLU provee resultado real)
        (keyword fallback automático si OpenAI falla)
   │
   ▼
Fase 3: eliminar keyword NLU legacy (futuro, cuando NLU v3 sea estable)
```

## 8.2 Rollback instantáneo

```bash
# Rollback total a keyword matching (sin redeploy)
export VOICEFLOW_NLU_ENABLED=false

# Rollback a shadow mode (sin redeploy)
export VOICEFLOW_NLU_SHADOW_MODE=true

# Cambiar provider sin redeploy
export VOICEFLOW_NLU_PROVIDER=keyword
```

## 8.3 Auditabilidad

Cada response incluye en `metadata.tool_outputs.nlu`:
```json
{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "analysis_version": "nlu_v3.0",
  "classification_layer": "openai_function_calling",
  "latency_ms": 820,
  "status": "ok"
}
```

---

# 9. GOBERNANZA Y VERSIONADO

## 9.1 Versionado

| Componente | Formato | Actual | Cuándo se incrementa |
|---|---|---|---|
| `analysis_version` | `nlu_vMAJOR.MINOR` | `nlu_v3.0` | MAJOR: nuevo provider o cambio de taxonomía. MINOR: ajuste de schema/prompts |
| Function schema | Inline en `openai_nlu_service.py` | v1 | Cuando cambia taxonomía de intents |
| Corpus evaluación | `tests/fixtures/nlu_evaluation_corpus.json` | 80+ examples | Cuando se añade intent o se detecta gap |

## 9.2 Cómo añadir un nuevo intent

1. Añadir al `enum` en `NLU_FUNCTION_SCHEMA` + actualizar `description`.
2. Añadir keywords al `KeywordNLUService` para fallback.
3. Añadir 10+ ejemplos al corpus de evaluación.
4. Bump `analysis_version` minor.
5. Verificar accuracy > 90%.

## 9.3 Cómo añadir un nuevo provider (e.g., spaCy rules, ML)

1. Crear `integration/external_apis/<provider>_nlu_service.py` que implemente `NLUServiceInterface`.
2. Registrar en `NLUServiceFactory._service_registry`.
3. Documentar en `NLU_SYSTEM_PROMPT` docstring de la interfaz.
4. Configurar via `VOICEFLOW_NLU_PROVIDER=<name>`.
5. Ningún cambio en Business ni Application.

**Guía detallada para los dos providers futuros:**

### Fase 2: Provider spaCy Rules + TF-IDF (offline)

```
Cuándo: cuando se necesite NLU sin dependencia de API externa
Esfuerzo: ~300 líneas de código + patterns por idioma

Implementación:
- Layer 1: spaCy Matcher con patterns lematizados (ver plan v2 §3.2)
- Layer 2: TF-IDF cosine similarity contra corpus de referencia (ver plan v2 §3.3)
- Dependencia adicional: scikit-learn

Ventajas vs keyword: entiende variaciones morfológicas, similarity semántica
Ventajas vs OpenAI: offline, 0 costo, <50ms latencia
Desventajas: patterns manuales por idioma, accuracy ~85% vs ~95% de OpenAI
```

### Fase 3: Provider ML supervisado (trained classifier)

```
Cuándo: cuando exista corpus etiquetado de 500+ ejemplos
Esfuerzo: ~200 líneas + pipeline de training

Implementación:
- TF-IDF + LogisticRegression (scikit-learn)
- Entrenado offline, serializado con joblib
- Cargado en __init__() del provider

Ventajas: accuracy potencialmente >OpenAI para dominio específico
Desventajas: requiere corpus grande, re-training al cambiar dominio
```

---

# 10. IMPACTO OPERATIVO

## 10.1 Memoria

| Componente | Memoria | Notas |
|---|---|---|
| `openai` SDK client | ~5 MB | Async HTTP client |
| `es_core_news_md` (NER, ya cargado) | ~50 MB | No cambia — ya se paga por NER |
| `KeywordNLUService` | < 1 MB | Diccionarios en memoria |
| **Total incremental** | **~5 MB** | Mínimo — no carga modelos nuevos |

## 10.2 Latencia

| Operación | Estimación | Notas |
|---|---|---|
| OpenAI NLU (gpt-4o-mini) p50 | 600-900ms | Network + inference |
| OpenAI NLU p95 | 1000-1500ms | Picos de carga |
| Keyword NLU p50 | < 2ms | Local, sin I/O |
| NLU + NER paralelo (asyncio.gather) | max(NLU, NER) | ~600-900ms si OpenAI, ~50ms si keyword |
| Pipeline total con OpenAI NLU | 4-7s | NLU(0.8s) ‖ NER(0.05s) + tools(0.1s) + LLM(3-5s) |

## 10.3 Costo por request

| Componente | Costo/request | Notas |
|---|---|---|
| NLU (gpt-4o-mini) | ~$0.0003 | ~200 tokens in, ~50 out |
| LLM synthesis (gpt-4) | ~$0.03-0.05 | ~2000 tokens in, ~500 out |
| **Total pipeline** | **~$0.03-0.05** | Dominado por síntesis, NLU es despreciable |

## 10.4 Docker build

**Sin impacto.** No se descargan modelos nuevos. El SDK `openai` ya es dependencia transitiva via `langchain_openai`. No hay cambios en `Dockerfile`.

## 10.5 Concurrencia

- `AsyncOpenAI` es thread-safe y async-native.
- `KeywordNLUService` es stateless (read-only dicts).
- `EntityResolver` es stateless.
- Safe para concurrencia sin locks.

---

# 11. PLAN DE EJECUCIÓN FINAL

## 11.1 Roadmap

| Fase | Commits | Entregable |
|---|---|---|
| **Fase 1: Contratos** | Commit 1 | Interfaz + modelos + settings + tests |
| **Fase 2: Providers** | Commit 2 | OpenAI + keyword + factory + tests |
| **Fase 3: Pipeline** | Commit 3 | EntityResolver + paralelización + tests |
| **Fase 4: Wiring** | Commit 4 | DI + shadow mode + docs |
| **Fase 5: Validación** | Commit 5 | Corpus + e2e + hardening |
| **Fase 6: Rollout** | Post-merge | Shadow → activación |

## 11.2 Riesgos residuales

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| OpenAI API latencia alta (>2s) | Baja | Medio | Auto-fallback a keyword vía factory |
| OpenAI API down | Baja | Medio | Auto-fallback a keyword vía factory |
| gpt-4o-mini clasificación incorrecta | Baja | Bajo | Corpus eval catch regressions; alternatives field |
| Rate limiting OpenAI | Baja (POC) | Medio | Keyword fallback; low volume en POC |

## 11.3 Criterios de "Ready for Production"

- [ ] Los 5 commits mergeados.
- [ ] `poetry run pytest tests/ -v` — 100% passing.
- [ ] `poetry run ruff check . && poetry run ruff format --check .` — clean.
- [ ] Corpus evaluación: accuracy > 90% con OpenAI provider.
- [ ] Corpus evaluación: accuracy > 70% con keyword fallback.
- [ ] Shadow mode ejecutado sin errores.
- [ ] Documentación actualizada.
- [ ] Feature flags documentados en `.env.example`.
- [ ] API contract backward compatible verificado.

---

## Apéndice A: Comandos rápidos

```bash
# Lint
poetry run ruff check . && poetry run ruff format --check .

# Tests por capa
poetry run pytest tests/test_shared/ -v -m unit
poetry run pytest tests/test_integration/ -v
poetry run pytest tests/test_business/ -v
poetry run pytest tests/test_application/ -v

# Tests de evaluación (requiere OPENAI_API_KEY)
poetry run pytest tests/test_integration/test_nlu_evaluation.py -v -s

# Type check
poetry run mypy shared/ integration/ business/ application/ --ignore-missing-imports

# Smoke test
curl -s -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Content-Type: application/json" \
  -d '{"message":"Quiero una ruta accesible al Museo del Prado"}' \
  | python -m json.tool

# Shadow mode logs
docker compose logs app | grep "nlu_shadow_comparison" | tail -20
```

## Apéndice B: Variables de entorno (.env.example)

```bash
# NLU Configuration
VOICEFLOW_NLU_ENABLED=true
VOICEFLOW_NLU_PROVIDER=openai
VOICEFLOW_NLU_DEFAULT_LANGUAGE=es
VOICEFLOW_NLU_OPENAI_MODEL=gpt-4o-mini
VOICEFLOW_NLU_CONFIDENCE_THRESHOLD=0.40
VOICEFLOW_NLU_FALLBACK_INTENT=general_query
VOICEFLOW_NLU_SHADOW_MODE=false
```

## Apéndice C: Diagrama de providers (presente y futuro)

```
                    NLUServiceInterface
                    (shared/interfaces/)
                           │
           ┌───────────────┼───────────────┬──────────────────┐
           │               │               │                  │
    OpenAINLUService  KeywordNLU    SpacyRuleNLU(*)    MLClassifierNLU(*)
    (gpt-4o-mini)     Service       (Matcher+TF-IDF)   (scikit-learn)
    [IMPLEMENTADO]    [IMPLEMENTADO]  [FASE 2]           [FASE 3]
           │               │               │                  │
           └───────┬───────┘               └────────┬─────────┘
                   │                                │
           NLUServiceFactory                  NLUServiceFactory
           (registro actual)                  (registro futuro)

    (*) = documentado en §9.3, no implementado en esta iteración
```
