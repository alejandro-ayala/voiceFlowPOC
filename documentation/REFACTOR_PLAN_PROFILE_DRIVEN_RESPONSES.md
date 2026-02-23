# Roadmap: Sistema de Recomendaciones Profile-Driven

**Fecha:** 18 de Febrero de 2026  
**Versión:** 2.0  
**Objetivo:** Que el sistema recomiende venues/actividades basándose en el perfil activo del usuario, con datos estructurados fiables.

---

## 📋 Tabla de Contenidos

1. [Estado Actual del Sistema](#1-estado-actual-del-sistema)
2. [Roadmap de Implementación (5 Fases)](#2-roadmap-de-implementación)
3. [Guía de Depuración y Validación](#3-guía-de-depuración-y-validación)
4. [Decisiones Arquitectónicas](#4-decisiones-arquitectónicas)
5. [Riesgos y Mitigaciones](#5-riesgos-y-mitigaciones)
6. [Checklist de Validación Final](#6-checklist-de-validación-final)

---

## 1. Estado Actual del Sistema

### 1.1 ¿Qué Funciona? ✅

| Componente | Estado | Evidencia |
|-----------|--------|-----------|
| **UI Selector de Perfiles** | ✅ Funcional | Usuario selecciona `night_leisure`, `cultural`, etc. |
| **Backend recibe Profile** | ✅ Funcional | `backend_adapter.py` resuelve `profile_context` |
| **ProfileService** | ✅ Funcional | Carga `profiles.json` correctamente |
| **Infraestructura completa** | ✅ Funcional | Flujo UI → Backend → Agent funciona |

### 1.2 ¿Qué NO Funciona? ❌

| Problema | Impacto | Severidad |
|----------|---------|-----------|
| **Tools son STUBS** | Devuelven mock data hardcodeado (solo ~10 venues Madrid) | 🔴 Crítico |
| **Profile NO afecta tools** | Tools no reciben ni usan `profile_context` | 🔴 Crítico |
| **NO hay ranking real** | Mismo query + diferentes perfiles → mismos venues | 🔴 Crítico |
| **Profile solo afecta texto** | Cambia tono de respuesta, NO el contenido estructurado | 🟡 Alto |
| **JSON extraction frágil** | Regex-based, falla si LLM no emite bloque ```json | 🟡 Alto |

### 1.3 Diagrama: Dónde se Rompe la Cadena ⚠️

```
┌─────────────────────────────────────────────────────────────────┐
│ USER: "Recomiéndame actividades en Madrid esta noche"          │
│ Profile: night_leisure                                          │
└────────────────────┬────────────────────────────────────────────┘
                     │
        ┌────────────▼──────────────┐
        │ UI → Backend              │  ✅ FUNCIONA
        │ profile_id: night_leisure │
        └────────────┬──────────────┘
                     │
        ┌────────────▼─────────────────────┐
        │ ProfileService                   │  ✅ FUNCIONA
        │ Resuelve profile_context:        │
        │ - prompt_directives              │
        │ - ranking_bias (NO USADO)        │
        └────────────┬─────────────────────┘
                     │
        ┌────────────▼─────────────────────────────────┐
        │ Tools Pipeline                               │  ❌ SE ROMPE AQUÍ
        │ ┌─────────────────────────────────────────┐  │
        │ │ NLU Tool (regex)                        │  │
        │ │ INPUT: user_input                       │  │
        │ │ → Busca en DESTINATION_PATTERNS (10)    │  │  ❌ NO recibe profile
        │ │ → Output: "Madrid centro" (genérico)    │  │  ❌ Mock data
        │ └─────────────────────────────────────────┘  │
        │ ┌─────────────────────────────────────────┐  │
        │ │ Accessibility Tool (lookup DB)          │  │
        │ │ INPUT: nlu_result                       │  │
        │ │ → Lookup ACCESSIBILITY_DB (4 venues)    │  │  ❌ NO recibe profile
        │ │ → Output: datos genéricos               │  │  ❌ Mock data
        │ └─────────────────────────────────────────┘  │
        │ ┌─────────────────────────────────────────┐  │
        │ │ Route Tool (rutas predefinidas)         │  │
        │ │ → ROUTE_DB["Madrid centro"]             │  │  ❌ Mock data
        │ └─────────────────────────────────────────┘  │
        │ ┌─────────────────────────────────────────┐  │
        │ │ Tourism Info Tool (VENUE_DB)            │  │
        │ │ → Lookup 4 venues hardcodeados          │  │  ❌ Mock data
        │ └─────────────────────────────────────────┘  │
        └────────────┬─────────────────────────────────┘
                     │ tool_results (IRRELEVANTES)
                     │
        ┌────────────▼───────────────────────────────┐
        │ Prompt Builder                             │  ⚠️ PARCIAL
        │ Construye prompt con:                      │
        │ - tool_results (mock data)                 │  ❌ Datos irrelevantes
        │ - profile_directives                       │  ✅ Afecta tono
        └────────────┬───────────────────────────────┘
                     │
        ┌────────────▼───────────────────────────────┐
        │ LLM (OpenAI GPT-4)                         │  ⚠️ BYPASS
        │ - Lee tool_results (los IGNORA por irrelevantes)
        │ - Lee profile_directives (ajusta TONO)     │
        │ - Usa conocimiento pre-entrenado           │  ← Genera respuesta
        │ - Emite texto + bloque JSON (opcional)     │
        └────────────┬───────────────────────────────┘
                     │
        ┌────────────▼───────────────────────────────┐
        │ JSON Extraction (regex)                    │  ❌ FRÁGIL
        │ Busca ```json...```                        │
        │ → Si NO lo encuentra: tourism_data = null  │
        └────────────┬───────────────────────────────┘
                     │
        ┌────────────▼───────────────────────────────┐
        │ Response Final                             │
        │ - ai_response: texto del LLM ✅            │
        │ - tourism_data: null (60% casos) ❌        │
        └────────────────────────────────────────────┘
```

### 1.4 Ejemplo Concreto: Query sobre Granada

```bash
# Request
curl -X POST http://localhost:8000/api/v1/chat/message \
  -d '{"message":"Recomiéndame la Alhambra en Granada","user_preferences":{"active_profile_id":"cultural"}}'

# Lo que sucede internamente:
# 1. NLU Tool → "general" (no reconoce Alhambra)
# 2. Accessibility Tool → ACCESSIBILITY_DB["general"] (datos fake de Madrid)
# 3. Route Tool → ROUTE_DB["Madrid centro"] (INCORRECTO!)
# 4. Tourism Info → VENUE_DB["General Madrid"] (IRRELEVANTE)
# 5. LLM → Ignora tools, usa conocimiento pre-entrenado
# 6. Response → Texto OK (habla de Alhambra), pero tourism_data = null

# Conclusión: Funciona "por accidente" porque el LLM tiene conocimiento,
# pero las tools NO aportan nada útil.
```

### 1.5 Resumen Ejecutivo

**El sistema actual es un "prototipo arquitectónico":**
- ✅ La **infraestructura** funciona (capas, flujo de datos, perfiles)
- ❌ Las **tools son teatro** (parecen útiles pero no lo son)
- ❌ El **perfil NO afecta las recomendaciones** (solo el tono textual)
- ⚠️ **Funciona gracias al LLM** (conocimiento pre-entrenado), no por las tools

**Para que sea funcional necesitamos:** Implementar las 5 fases del roadmap.

---

## 2. Roadmap de Implementación

### 1.1 Arquitectura Actual

```
┌─────────────────────────────────────────────────────────────┐
│ Presentation Layer (FastAPI)                                │
│ - /api/v1/chat/message recibe user_preferences              │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ Application Layer                                            │
│ - backend_adapter.py: Resuelve profile_id → profile_context │
│ - Llama a TourismMultiAgent con profile_context             │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ Business Layer - Tourism Multi-Agent                        │
│ 1. _execute_pipeline() → tools (NLU, Accessibility, etc)    │
│ 2. _build_response_prompt() → Prompt con tool_results       │
│ 3. LLM invocation (GPT-4) → texto + JSON block (opcional)   │
│ 4. _extract_structured_data() → busca ```json...```         │
│ 5. canonicalize_tourism_data() → valida con Pydantic        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ Integration Layer                                            │
│ - ProfileService: carga profiles.json                        │
│ - Tools: devuelven JSON (algunos con schema inconsistente)  │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 Problemas Identificados

| # | Problema | Impacto | Severidad |
|---|----------|---------|-----------|
| 1 | El LLM **no siempre incluye bloque JSON** en respuesta | `tourism_data` queda `null` o incompleto | 🔴 Alta |
| 2 | El parsing del bloque JSON es **regex-based** (frágil) | Falla si hay formato incorrecto | 🔴 Alta |
| 3 | `profile_context` **no afecta realmente el ranking** | Perfil solo modifica el texto, no la selección | 🔴 Alta |
| 4 | `tourism_info_tool` devolvía `venue` como **string**, no dict | Canonicalización fallaba | 🟡 Media (parcialmente resuelto) |
| 5 | **No hay validación de que el perfil haya influido** en la respuesta | No hay métricas de sesgo por perfil | 🟡 Media |
| 6 | **Dependencia del LLM para datos estructurados** cuando tools ya los tienen | Costo innecesario y fallos si LLM no coopera | 🟡 Media |

---

## 2. Cambios en Arquitectura

### 2.1 Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────────┐
│ Presentation Layer (FastAPI)                                │
│ - /api/v1/chat/message recibe user_preferences              │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ Application Layer                                            │
│ - backend_adapter.py: Resuelve profile_context              │
│ - profile_context incluye: ranking_bias, expected_types     │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ Business Layer - Tourism Multi-Agent (REFACTOR)             │
│ ┌──────────────────────────────────────────────────────┐    │
│ │ FASE 1: Tool Pipeline (profile-aware)                │    │
│ │ - tools reciben profile_context                      │    │
│ │ - ranking/filtering aplicado aquí                    │    │
│ │ → tool_results + ranked_tourism_data                 │    │
│ └──────────────────────────────────────────────────────┘    │
│ ┌──────────────────────────────────────────────────────┐    │
│ │ FASE 2: LLM Text Generation (conversational)         │    │
│ │ - Genera SOLO texto conversacional                   │    │
│ │ - Input: tool_results + profile_directives           │    │
│ │ → ai_response_text                                   │    │
│ └──────────────────────────────────────────────────────┘    │
│ ┌──────────────────────────────────────────────────────┐    │
│ │ FASE 3: LLM Structured Output (JSON puro) [NUEVO]   │    │
│ │ - Function calling o response_format JSON           │    │
│ │ - Input: tool_results + ranked_tourism_data         │    │
│ │ → structured_json (garantizado válido)              │    │
│ └──────────────────────────────────────────────────────┘    │
│ ┌──────────────────────────────────────────────────────┐    │
│ │ FASE 4: Canonización robusta                        │    │
│ │ - Prioridad: tool_data > llm_json > fallback       │    │
│ │ - Validación Pydantic + retry si falla              │    │
│ │ → tourism_data (siempre válido)                     │    │
│ └──────────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ Integration Layer                                            │
│ - ProfileService: profile_context enriquecido               │
│ - Tools: outputs estandarizados con contracts               │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 Cambios Clave

| Aspecto | Antes | Después |
|---------|-------|---------|
| **LLM Invocations** | 1 llamada (texto + JSON mezclado) | 2 llamadas (texto solo + JSON puro) |
| **JSON Extraction** | Regex en texto | Function calling / response_format |
| **Profile Impact** | Solo en prompt (texto) | En ranking de tools + prompt |
| **Fallback Strategy** | LLM-only si tools fallan | tool_data → llm_json → generic fallback |
| **Validación** | Opcional, sin retry | Pydantic + retry + logs estructurados |

---

## 3. Cambios en Diseño

### 3.1 Diseño Actual vs Propuesto

#### 3.1.1 Flujo de Profile Context

**Actual:**
```python
profile_context = {
    "id": "night_leisure",
    "label": "Ocio nocturno",
    "prompt_directives": [...],
    "ranking_bias": {...}
}
# Se pasa al prompt como texto, NO se usa en tools
```

**Propuesto:**
```python
profile_context = {
    "id": "night_leisure",
    "label": "Ocio nocturno",
    "prompt_directives": [...],
    "ranking_bias": {
        "venue_types": {"nightclub": 1.3, "restaurant": 1.05, ...},
        "signals": {"late_night": 1.3, ...}
    },
    "expected_types": ["nightclub", "entertainment", "restaurant"],  # NUEVO
    "filter_rules": {"min_score": 5.0, "exclude_types": []}  # NUEVO
}
# Se usa en:
# 1. Tools para filtrar/rankear
# 2. Prompt para texto
# 3. LLM structured output para JSON
```

#### 3.1.2 Flujo de Datos Estructurados

**Actual:**
```
Tools → tool_results (strings)
  ↓
LLM (text + json block)
  ↓
Regex extraction (frágil)
  ↓
canonicalize_tourism_data()
  ↓
tourism_data (often null)
```

**Propuesto:**
```
Tools → tool_results (strings) + parsed_tools (dicts)
  ↓
Apply profile ranking/filtering → ranked_tourism_data
  ↓
LLM 1 (text only) → ai_response_text
  ↓
LLM 2 (JSON function call) → structured_json (guaranteed valid)
  ↓
Merge: tool_data (priority) + llm_json (fallback)
  ↓
canonicalize_tourism_data() with retry
  ↓
tourism_data (always valid)
```

---

## 4. Cambios Necesarios por Capa

### 4.1 Presentation Layer

#### Archivos afectados:
- ✅ Sin cambios (ya recibe `user_preferences`)

---

### 4.2 Application Layer

#### 4.2.1 `application/orchestration/backend_adapter.py`

**Cambios:**

1. **Enriquecer `profile_context`**
   ```python
   # ANTES
   profile_context = {
       "id": profile_id,
       "label": profile["label"],
       "prompt_directives": profile["prompt_directives"],
       "ranking_bias": profile["ranking_bias"]
   }
   
   # DESPUÉS
   profile_context = {
       "id": profile_id,
       "label": profile["label"],
       "prompt_directives": profile["prompt_directives"],
       "ranking_bias": profile["ranking_bias"],
       "expected_types": self._extract_top_venue_types(profile["ranking_bias"]),  # NUEVO
       "filter_rules": {  # NUEVO
           "min_score": 5.0,
           "exclude_types": []
       }
   }
   
   def _extract_top_venue_types(self, ranking_bias: dict) -> list[str]:
       """Extract venue types with bias > 1.0 (prioritized)."""
       venue_types = ranking_bias.get("venue_types", {})
       return [vtype for vtype, bias in venue_types.items() if bias > 1.0]
   ```

2. **Log de perfil aplicado**
   ```python
   logger.info(
       "Profile context prepared",
       profile_id=profile_id,
       expected_types=profile_context["expected_types"],
       ranking_applied=True
   )
   ```

**Puntos críticos:**
- Línea ~185: donde se construye `profile_context`
- Línea ~193: donde se llama `agent.process_request(..., profile_context=profile_context)`

---

### 4.3 Business Layer

#### 4.3.1 `business/domains/tourism/agent.py` (REFACTOR MAYOR)

**Cambios estructurales:**

##### **1. Separar LLM invocations**

**ANTES (línea ~175):**
```python
def process_request(
    self, user_input: str, profile_context: Optional[dict] = None
) -> dict:
    tool_results, metadata = self._execute_pipeline(user_input)
    
    # Single LLM call
    prompt = self._build_response_prompt(user_input, tool_results, profile_context)
    llm_response = self.llm.invoke(prompt)
    
    # Extract JSON from text (fragile)
    clean_text, metadata = self._extract_structured_data(llm_response, metadata)
    
    return {"response": clean_text, **metadata}
```

**DESPUÉS:**
```python
def process_request(
    self, user_input: str, profile_context: Optional[dict] = None
) -> dict:
    # 1. Execute tools with profile awareness
    tool_results, metadata = self._execute_pipeline(user_input, profile_context)
    
    # 2. Apply profile ranking/filtering
    ranked_tourism_data = self._apply_profile_ranking(
        metadata.get("tourism_data"),
        profile_context
    )
    metadata["tourism_data"] = ranked_tourism_data
    
    # 3. Generate conversational text (LLM 1)
    text_prompt = self._build_response_prompt(
        user_input, tool_results, profile_context
    )
    ai_response_text = self.llm.invoke(text_prompt).content
    
    # 4. Generate structured JSON (LLM 2 - function calling)
    structured_json = self._generate_structured_data(
        user_input, tool_results, ranked_tourism_data, profile_context
    )
    
    # 5. Merge and canonicalize (with retry)
    final_tourism_data = self._merge_and_canonicalize(
        tool_data=ranked_tourism_data,
        llm_data=structured_json,
        retry_count=2
    )
    
    metadata["tourism_data"] = final_tourism_data
    
    return {"response": ai_response_text, **metadata}
```

##### **2. Nuevo método: `_apply_profile_ranking()`**

```python
def _apply_profile_ranking(
    self,
    tourism_data: Optional[dict],
    profile_context: Optional[dict]
) -> Optional[dict]:
    """Apply profile-based ranking to venues and routes."""
    if not tourism_data or not profile_context:
        return tourism_data
    
    ranking_bias = profile_context.get("ranking_bias", {})
    expected_types = profile_context.get("expected_types", [])
    
    # If venue type matches expected_types, boost score
    venue = tourism_data.get("venue")
    if venue and isinstance(venue, dict):
        venue_type = venue.get("type")
        if venue_type in expected_types:
            # Boost accessibility_score
            current_score = venue.get("accessibility_score", 5.0)
            bias = ranking_bias.get("venue_types", {}).get(venue_type, 1.0)
            venue["accessibility_score"] = min(10.0, current_score * bias)
            venue["profile_boosted"] = True
            logger.info(
                "Venue score boosted by profile",
                venue_type=venue_type,
                bias=bias,
                new_score=venue["accessibility_score"]
            )
    
    # TODO: También rankear routes si hay múltiples opciones
    
    return tourism_data
```

##### **3. Nuevo método: `_generate_structured_data()` con function calling**

```python
from langchain.output_parsers import PydanticOutputParser
from application.models.responses import TourismData

def _generate_structured_data(
    self,
    user_input: str,
    tool_results: dict[str, str],
    ranked_tourism_data: Optional[dict],
    profile_context: Optional[dict]
) -> Optional[dict]:
    """Generate structured JSON using function calling (deterministic)."""
    
    # Define schema for function calling
    tourism_schema = {
        "name": "generate_tourism_data",
        "description": "Generate structured tourism data with venue, routes, and accessibility info",
        "parameters": {
            "type": "object",
            "properties": {
                "venue": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "accessibility_score": {"type": "number"},
                        "certification": {"type": ["string", "null"]},
                        "facilities": {"type": "array", "items": {"type": "string"}},
                        "opening_hours": {"type": "object"},
                        "pricing": {"type": "object"}
                    },
                    "required": ["name", "type"]
                },
                "routes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "transport": {"type": "string"},
                            "line": {"type": ["string", "null"]},
                            "duration": {"type": "string"},
                            "accessibility": {"type": "string"},
                            "cost": {"type": ["string", "null"]},
                            "steps": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                },
                "accessibility": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "string"},
                        "score": {"type": "number"},
                        "certification": {"type": ["string", "null"]},
                        "facilities": {"type": "array", "items": {"type": "string"}},
                        "services": {"type": "object"}
                    }
                }
            }
        }
    }
    
    # Build prompt for structured output
    prompt = f"""Based on the following tool results and user query, generate structured tourism data.

User Query: {user_input}

Tool Results:
NLU: {tool_results.get('nlu', 'N/A')}
Accessibility: {tool_results.get('accessibility', 'N/A')}
Routes: {tool_results.get('routes', 'N/A')}
Venue Info: {tool_results.get('venue info', 'N/A')}

Profile Context: {profile_context.get('label', 'None')}
Expected Venue Types: {profile_context.get('expected_types', [])}

Generate complete tourism data based on these inputs. Prioritize venue types that match the profile.
"""
    
    try:
        # Use function calling
        response = self.llm.invoke(
            prompt,
            functions=[tourism_schema],
            function_call={"name": "generate_tourism_data"}
        )
        
        # Extract function call arguments
        if hasattr(response, 'additional_kwargs'):
            function_call = response.additional_kwargs.get('function_call', {})
            arguments = function_call.get('arguments', '{}')
            structured_data = json.loads(arguments)
            logger.info("Structured data generated via function calling")
            return structured_data
        
    except Exception as e:
        logger.warning("Function calling failed", error=str(e))
    
    return None
```

##### **4. Nuevo método: `_merge_and_canonicalize()` con retry**

```python
def _merge_and_canonicalize(
    self,
    tool_data: Optional[dict],
    llm_data: Optional[dict],
    retry_count: int = 2
) -> Optional[dict]:
    """Merge tool and LLM data, canonicalize with retry."""
    
    # Priority: tool_data > llm_data > None
    candidate = tool_data or llm_data
    
    if not candidate:
        logger.warning("No structured data available from tools or LLM")
        return None
    
    # Try canonicalization with retry
    for attempt in range(retry_count + 1):
        try:
            canonicalized = canonicalize_tourism_data(candidate)
            if canonicalized:
                logger.info("Canonicalization successful", attempt=attempt)
                return canonicalized
        except Exception as e:
            logger.warning(
                "Canonicalization failed",
                attempt=attempt,
                error=str(e)
            )
            if attempt < retry_count:
                # Fallback: try LLM data if tool data failed
                if candidate == tool_data and llm_data:
                    candidate = llm_data
                    logger.info("Retrying with LLM data")
                    continue
            break
    
    logger.error("All canonicalization attempts failed")
    return None
```

**Puntos críticos en `agent.py`:**
- Línea ~56: refactor completo de `process_request()`
- Líneas ~145-175: `_execute_pipeline()` debe pasar `profile_context` a tools
- Nuevo: `_apply_profile_ranking()` (~línea 180)
- Nuevo: `_generate_structured_data()` (~línea 220)
- Nuevo: `_merge_and_canonicalize()` (~línea 280)

---

#### 4.3.2 `business/domains/tourism/tools/*_tool.py` (Profile-aware)

**Cambios en TODOS los tools:**

Añadir parámetro opcional `profile_context` en `_run()`:

**Ejemplo: `tourism_info_tool.py`:**

```python
def _run(self, venue_info: str, profile_context: Optional[dict] = None) -> str:
    """Get comprehensive tourism information."""
    logger.info(
        "Tourism Info Tool: Fetching venue information",
        venue_input=venue_info,
        profile_id=profile_context.get("id") if profile_context else None
    )
    
    venue_name = self._extract_venue_name(venue_info)
    
    # Apply profile filtering
    if profile_context:
        expected_types = profile_context.get("expected_types", [])
        # If venue doesn't match expected types, log and potentially adjust
        venue_type = self._infer_venue_type(venue_name)
        if expected_types and venue_type not in expected_types:
            logger.info(
                "Venue type mismatch with profile",
                venue_type=venue_type,
                expected=expected_types
            )
    
    venue_data = VENUE_DB.get(venue_name, DEFAULT_VENUE)
    
    result = {
        "venue": {
            "name": venue_name,
            "type": self._infer_venue_type(venue_name),
        },
        "opening_hours": venue_data["opening_hours"],
        # ... resto
    }
    
    logger.info("Tourism Info Tool: Information retrieved", result=result)
    return json.dumps(result, indent=2, ensure_ascii=False)
```

**Puntos críticos:**
- `nlu_tool.py` línea ~20
- `accessibility_tool.py` línea ~18
- `route_planning_tool.py` línea ~19
- `tourism_info_tool.py` línea ~23

---

#### 4.3.3 `business/core/canonicalizer.py`

**Cambios:**

1. **Hacer canonicalizador más tolerante**

```python
def canonicalize_tourism_data(raw: Any) -> Optional[Dict[str, Any]]:
    """Return a canonicalized tourism_data dict or None.
    
    Enhanced with:
    - String-to-dict conversion for venue
    - Better error logging
    - Partial success (return partial data instead of None)
    """
    if not raw or not isinstance(raw, dict):
        logger.warning("Canonicalization input invalid", raw_type=type(raw))
        return None

    try:
        venue_raw = raw.get("venue")
        routes_raw = raw.get("routes")
        accessibility_raw = raw.get("accessibility")

        venue = None
        if venue_raw:
            if isinstance(venue_raw, str):
                # NUEVO: Convert string to dict
                venue = {"name": venue_raw, "type": "tourism"}
                logger.info("Converted venue string to dict", venue_name=venue_raw)
            elif isinstance(venue_raw, dict):
                v = {}
                v["name"] = _normalize_text(venue_raw.get("name")) or venue_raw.get("name")
                v["type"] = _normalize_text(venue_raw.get("type")) or venue_raw.get("type") or "tourism"
                v["accessibility_score"] = venue_raw.get("accessibility_score") or venue_raw.get("score")
                v["certification"] = _normalize_text(venue_raw.get("certification")) or venue_raw.get("certification")
                v["facilities"] = _canonicalize_facilities(venue_raw.get("facilities") or venue_raw.get("services"))
                v["opening_hours"] = venue_raw.get("opening_hours")
                v["pricing"] = venue_raw.get("pricing")
                venue = v

        # ... (resto del código igual)

        candidate = {"venue": venue, "routes": routes, "accessibility": accessibility}

        # Validate with Pydantic
        td = TourismData.parse_obj(candidate)
        logger.info("Canonicalization successful", has_venue=bool(venue), has_routes=bool(routes))
        return td.dict()
        
    except Exception as e:
        logger.warning("Canonicalization failed", error=str(e), raw_keys=list(raw.keys()) if isinstance(raw, dict) else None)
        
        # NUEVO: Partial success fallback
        # Return partial data instead of None
        try:
            partial = {
                "venue": venue if venue else None,
                "routes": routes if routes else None,
                "accessibility": accessibility_raw if isinstance(accessibility_raw, dict) else None
            }
            td_partial = TourismData.parse_obj(partial)
            logger.info("Partial canonicalization succeeded")
            return td_partial.dict()
        except Exception:
            pass
        
        return None
```

**Puntos críticos:**
- Línea ~124: handle `venue` como string
- Línea ~206: partial success fallback

---

#### 4.3.4 `business/domains/tourism/prompts/response_prompt.py`

**Cambios:**

1. **Simplificar prompt (solo texto conversacional)**

```python
def build_response_prompt(
    user_input: str,
    tool_results: dict[str, str],
    profile_context: Optional[dict] = None
) -> str:
    """Build the conversational response prompt (text only, no JSON block)."""
    
    profile_section = ""
    if profile_context:
        directives = profile_context.get("prompt_directives", [])
        profile_section = f"""
PERFIL ACTIVO: {profile_context.get("label", "Ninguno")}
Directivas del perfil:
{chr(10).join(f"- {d}" for d in directives)}
"""
    
    return f"""Eres un asistente experto en turismo accesible en España.

{profile_section}

El usuario preguntó: "{user_input}"

He analizado su consulta usando varias herramientas especializadas:

ANÁLISIS DE INTENCIÓN:
{tool_results.get("nlu", "{}")}

ANÁLISIS DE ACCESIBILIDAD:
{tool_results.get("accessibility", "{}")}

PLANIFICACIÓN DE RUTAS:
{tool_results.get("route", "{}")}

INFORMACIÓN TURÍSTICA:
{tool_results.get("tourism_info", "{}")}

Genera una respuesta completa y útil que incluya:
1. Recomendaciones específicas de lugares accesibles (priorizando según el perfil activo)
2. Información práctica sobre rutas y transporte
3. Horarios, precios y servicios de accesibilidad
4. Consejos específicos para las necesidades del usuario

Sé conversacional, útil y enfócate en los aspectos de accesibilidad.
IMPORTANTE: No incluyas bloques JSON en esta respuesta, solo texto conversacional."""
```

**Puntos críticos:**
- Línea ~33: remover instrucciones de JSON
- Añadir sección de perfil activo

---

### 4.4 Integration Layer

#### 4.4.1 `application/services/profile_service.py`

**Cambios:**

1. **Enriquecer método `resolve_profile()` con expected_types y filter_rules**

```python
# En ProfileService (application/services/profile_service.py)
def resolve_profile(self, profile_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Resuelve un profile_id a su contexto enriquecido.
    Ya retorna: {id, label, prompt_directives, ranking_bias}
    
    Propuesta para Fase 3: enriquecer con:
    - expected_types: tipos de venue prioritarios extraídos de ranking_bias
    - filter_rules: reglas de filtrado derivadas del perfil
    """
    if not profile_id:
        return None
    
    profile = self._profiles_by_id.get(profile_id)
    if not profile:
        logger.warning("Unknown profile_id", profile_id=profile_id)
        return None
    
    # Extracción de expected_types desde ranking_bias
    ranking_bias = profile.get("ranking_bias", {})
    venue_types = ranking_bias.get("venue_types", {})
    expected_types = [
        vtype for vtype, bias in venue_types.items() 
        if bias > 1.0  # Solo tipos con boost positivo
    ]
    
    # Construcción de filter_rules
    filter_rules = {
        "min_accessibility_score": 5.0,
        "exclude_venue_types": [],
        "require_certification": False
    }
    
    context = {
        "id": profile_id,
        "label": profile["label"],
        "description": profile.get("description", ""),
        "prompt_directives": profile.get("prompt_directives", []),
        "ranking_bias": ranking_bias,
        "expected_types": expected_types,  # NUEVO
        "filter_rules": filter_rules,       # NUEVO
        "ui": profile.get("ui", {})
    }
    
    logger.info(
        "Profile resolved with ranking context",
        profile_id=profile_id,
        expected_types=expected_types,
        ranking_bias_keys=list(ranking_bias.keys())
    )
    
    return context
```

**Justificación:**
- `resolve_profile()` ya existe en el código y retorna estructura base completa
- Enriquecimiento mantenido en misma capa (Application) con lógica simple
- Para Fase 3, la lógica compleja de ranking va a `ProfileRankingPolicy` en Business layer
- Evita duplicación de método con nombre distinto

**Integración en pipeline (Fase 3):**
```python
# En agent.py:_execute_pipeline()
def _execute_pipeline(self, user_input: str, profile_context: Optional[Dict] = None):
    # ... ejecutar tools ...
    
    # Aplicar ranking si hay profile con directivas
    if profile_context and profile_context.get("expected_types"):
        from business.core.ranking import ProfileRankingPolicy
        ranker = ProfileRankingPolicy()
        # Reordenar venue_results según expected_types y ranking_bias
        venue_results = ranker.apply_ranking(
            venue_results, 
            profile_context["ranking_bias"],
            profile_context["expected_types"]
        )
        metadata["ranking_applied"] = True
        metadata["profile_id"] = profile_context["id"]
    
    return venue_results, metadata
```

**Puntos críticos:**
- Nueva funcionalidad: extracción de `expected_types` directamente en método existente
- Logs adicionales para observabilidad de contexto enriquecido
- Lógica de ranking separada para mantener Single Responsibility Principle

---

### 4.5 Shared Layer

#### 4.5.1 Nuevos contratos en `shared/interfaces/`

**Nuevo archivo:** `shared/interfaces/profile_interface.py`

```python
"""Interface for profile-aware components."""

from abc import ABC, abstractmethod
from typing import Optional


class ProfileAwareComponent(ABC):
    """Base interface for components that use profile context."""
    
    @abstractmethod
    def apply_profile_context(self, profile_context: Optional[dict]) -> None:
        """Apply profile context to component behavior."""
        pass
    
    @abstractmethod
    def get_profile_impact_metrics(self) -> dict:
        """Return metrics showing how profile affected output."""
        pass
```

---

## 5. Plan de Implementación por Fases

---

### Fase 0: Integración de Tools con APIs Reales (PREREQUISITO) ⚠️ 5-7 días ⚠️
**Objetivo:** Que las tools aporten datos REALES, no mock data hardcodeado

**CRÍTICO:** Sin esta fase, el resto del plan NO tendrá efecto. Las tools actuales son stubs que solo funcionan para 4 venues de Madrid.

#### Tareas:
- [ ] **Decisión arquitectónica**: APIs externas vs RAG vs búsqueda web
- [ ] **NLU Tool**: Migrar de regex a spaCy/BERT (NER real en español)
  - Integrar `transformers` pipeline para reconocimiento de entidades
  - Detectar ciudades, monumentos, tipos de actividad dinámicamente
- [ ] **Accessibility Tool**: Google Places API
  - Integrar `googlemaps` client
  - Consultar `wheelchair_accessible_entrance`, `accessibility` fields
  - Cachear resultados (evitar rate limits)
- [ ] **Route Tool**: Google Directions API
  - Integrar `googlemaps.directions()`
  - Modo `transit` con alternativas accesibles
  - Calcular rutas dinámicamente según origen/destino
- [ ] **Tourism Info Tool**: TripAdvisor/Yelp API o Wikipedia
  - Integrar API de información turística
  - Obtener horarios, precios, valoraciones en tiempo real
- [ ] **Error handling**: Rate limits, timeouts, fallbacks
- [ ] **Tests**: Validar que funciona para Granada, Sevilla, Barcelona (no solo Madrid)

**Archivos creados:**
- `integration/external_apis/google_maps_client.py`
- `integration/external_apis/tripadvisor_client.py` (o alternativa)
- `shared/config/api_keys.py`

**Archivos modificados:**
- `business/domains/tourism/tools/nlu_tool.py` (usar spaCy en lugar de regex)
- `business/domains/tourism/tools/accessibility_tool.py` (llamar a Google Places)
- `business/domains/tourism/tools/route_planning_tool.py` (llamar a Directions)
- `business/domains/tourism/tools/tourism_info_tool.py` (llamar a API turística)
- `.env` (añadir API keys: `GOOGLE_MAPS_API_KEY`, etc.)
- `requirements.txt` (añadir `googlemaps`, `spacy`, `transformers`)

**Dependencias de paquetes:**
```bash
poetry add googlemaps spacy transformers
python -m spacy download es_core_news_md
```

**Validación:**
- ✅ Query: "Alhambra Granada" → Devuelve datos reales de Google Places
- ✅ Query: "Catedral Sevilla" → Devuelve rutas desde ubicación actual
- ✅ Query sobre ciudad no hardcodeada → Funciona igual

**Alternativa sin APIs de pago:**
Si no hay presupuesto para APIs, usar **RAG** (Retrieval Augmented Generation):
- Indexar datos de Open Data España en ChromaDB
- Tools buscan en DB vectorial en lugar de APIs externas
- Ver [OPCIÓN B en sección arquitectura](#opción-b-rag-retrieval-augmented-generation-)

---

### Fase 1: Canonización Robusta (1-2 días)
**Objetivo:** Asegurar que `tourism_data` nunca sea `null`

- [ ] Refactor `canonicalizer.py` con tolerancia a strings y partial success
- [ ] Fix `tourism_info_tool.py` para que devuelva siempre objeto `venue`
- [ ] Test: validar que todas las consultas devuelven `tourism_data` válido

**Archivos modificados:**
- `business/core/canonicalizer.py`
- `business/domains/tourism/tools/tourism_info_tool.py`

---

### Fase 2: Separación LLM Text vs JSON (2-3 días)
**Objetivo:** Extracción determinista de JSON estructurado

- [ ] Implementar `_generate_structured_data()` con function calling
- [ ] Simplificar `build_response_prompt()` (solo texto)
- [ ] Implementar `_merge_and_canonicalize()` con retry
- [ ] Test: validar que JSON siempre se extrae correctamente

**Archivos modificados:**
- `business/domains/tourism/agent.py`
- `business/domains/tourism/prompts/response_prompt.py`

---

### Fase 3: Profile-Driven Ranking (2 días)
**Objetivo:** Perfil afecta selección y ranking de venues/routes

- [ ] Implementar `_apply_profile_ranking()`
- [ ] Enriquecer `ProfileService.get_profile_context()`
- [ ] Logs de impacto del perfil
- [ ] Test: misma query con diferentes perfiles → diferentes venues prioritizados

**Archivos modificados:**
- `business/domains/tourism/agent.py`
- `application/services/profile_service.py`

---

### Fase 4: Tools Profile-Aware (1-2 días)
**Objetivo:** Tools reciben y usan `profile_context`

- [ ] Modificar signature de `_run()` en todos los tools
- [ ] Ajustar `_execute_pipeline()` para pasar perfil a tools
- [ ] Test: validar que tools loguean el perfil activo

**Archivos modificados:**
- `business/domains/tourism/tools/nlu_tool.py`
- `business/domains/tourism/tools/accessibility_tool.py`
- `business/domains/tourism/tools/route_planning_tool.py`
- `business/domains/tourism/tools/tourism_info_tool.py`

---

### Fase 5: Tests de Regresión (1-2 días)
**Objetivo:** Validar que cada perfil tiene sesgo medible

- [ ] Dataset de prompts por perfil
- [ ] Golden outputs esperados
- [ ] Test CI: validar sesgo por perfil
- [ ] Métricas: % de coincidencia tipo de venue con perfil

**Archivos nuevos:**
- `tests/test_business/test_profile_impact.py`
- `tests/fixtures/profile_test_cases.json`

---

## 6. Checklist de Validación Final

- [ ] **Respuesta verbal adecuada al perfil**: Night leisure → bares/conciertos
- [ ] **JSON estructurado siempre válido**: `tourism_data != null` en 100% de casos
- [ ] **UI recibe datos canonizados**: Rich cards se renderizan siempre
- [ ] **Perfil afecta ranking**: misma query, diferentes perfiles → diferentes venues top
- [ ] **Logs estructurados**: `profile_id`, `ranking_applied`, `venue_type_match`
- [ ] **Tests CI pasan**: validación de sesgo por perfil

---

## 7. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Function calling no soportado en modelo actual | Media | Alto | Fallback a parsing mejorado con validation |
| Doble llamada LLM aumenta costos | Alta | Medio | Cachear resultados, optimizar tokens |
| Perfil no afecta realmente al LLM | Baja | Alto | Tests automatizados de sesgo |
| Breaking changes en API | Media | Alto | Migración incremental, versioning |

---

## 8. Métricas de Éxito

| Métrica | Actual | Objetivo |
|---------|--------|----------|
| `tourism_data != null` | ~40% | 100% |
| Tiempo respuesta promedio | ~12s | <10s (con cache) |
| Sesgo de perfil medible | 0% | >80% |
| Errores de canonización | ~60% | <5% |
| Tests de regresión | 0 | 25+ casos |

---

## 9. Próximos Pasos Inmediatos

1. ✅ **Aprobar plan** con stakeholders
2. 🔨 **Crear branch:** `feature/profile-driven-responses-refactor`
3. 📋 **Crear issues** en GitHub/Jira para cada fase
4. 🚀 **Fase 1:** Empezar por canonización robusta (cambio menos invasivo)

---

**Autor:** GitHub Copilot (Claude Sonnet 4.5)  
**Revisado por:** [Tu nombre]  
**Última actualización:** 18 Feb 2026
