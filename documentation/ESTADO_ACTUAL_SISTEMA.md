# Estado Actual del Sistema: Profile-Driven Tourism Recommendations

**Fecha:** 18 de Febrero de 2026  
**Versión:** 1.0  
**Objetivo:** Documentar claramente qué funciona y qué NO funciona en el sistema actual

---

## 📊 Resumen Ejecutivo

| Componente | Estado | Funcional? | Notas |
|-----------|--------|-----------|-------|
| **UI Selector de Perfiles** | ✅ Implementado | ✅ **SÍ** funciona | Usuario puede seleccionar profile_id desde UI |
| **Backend recibe Profile** | ✅ Implementado | ✅ **SÍ** funciona | `backend_adapter.py` recibe y resuelve profile_context |
| **ProfileService** | ✅ Implementado | ✅ **SÍ** funciona | Carga profiles.json correctamente |
| **Profile → Tools** | ❌ NO implementado | ❌ **NO** funciona | Tools NO reciben ni usan profile_context |
| **Tools con datos reales** | ❌ Son STUBS | ❌ **NO** funciona | Mock data hardcodeado, solo Madrid |
| **Profile → Ranking** | ❌ NO implementado | ❌ **NO** funciona | No hay ranking real de venues |
| **Profile → LLM texto** | ⚠️ Parcial | ⚠️ **PARCIAL** | Solo afecta tono, no contenido estructurado |
| **JSON extraction** | ⚠️ Regex-based | ⚠️ **FRÁGIL** | Falla si LLM no emite bloque ```json |

---

## 1. Infraestructura de Perfiles: ✅ FUNCIONANDO

### ¿Qué SÍ funciona?

#### 1.1 Flujo UI → Backend
```
┌─────────────────────────────────────────────────────────────┐
│ UI (templates/index.html)                                   │
│ - Selector de perfiles: night_leisure, cultural, etc.      │
│ - Envía: {"active_profile_id": "night_leisure"}            │
└────────────────────┬────────────────────────────────────────┘
                     │ POST /api/v1/chat/message
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Application Layer (backend_adapter.py)                      │
│ - Recibe user_preferences                                   │
│ - Llama ProfileService.get_profile_by_id()                  │
│ - Construye profile_context con:                            │
│   * prompt_directives                                       │
│   * ranking_bias (NO USADO actualmente)                     │
└────────────────────┬────────────────────────────────────────┘
                     │ profile_context
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Business Layer (agent.py)                                   │
│ - Recibe profile_context                                    │
│ - Lo usa en _build_response_prompt() → SOLO TEXTO          │
│ - LLM lee prompt con directives del perfil                  │
└─────────────────────────────────────────────────────────────┘
```

**✅ Verificado:**
- [ProfileService](../application/services/profile_service.py) carga profiles.json correctamente
- [backend_adapter.py#L185-L195](../application/orchestration/backend_adapter.py) construye profile_context
- [agent.py](../business/domains/tourism/agent.py) recibe profile_context como parámetro
- Logs muestran: `profile_resolved: true`, `active_profile_id: "night_leisure"`

---

## 2. Tools (Herramientas): ❌ SON STUBS (Mock Data)

### ⚠️ PROBLEMA CRÍTICO: Las tools NO aportan datos reales

#### 2.1 Estado Actual de las Tools

```python
# business/domains/tourism/data/nlu_patterns.py
DESTINATION_PATTERNS = {
    "Museo del Prado": ["prado", "museo del prado"],
    "Museo Reina Sofía": ["reina sofía", "reina sofia"],
    "Museo Thyssen": ["thyssen"],
    # ... SOLO 10 VENUES HARDCODEADOS
}
```

```python
# business/domains/tourism/data/venue_data.py
VENUE_DB = {
    "Museo del Prado": {...},
    "Museo Reina Sofía": {...},
    "Espacios musicales Madrid": {...},
    "General Madrid": {...}
    # SOLO 4 VENUES CON MOCK DATA
}
```

#### 2.2 ¿Qué NO funciona?

| Tool | Problema | Impacto |
|------|----------|---------|
| **NLU Tool** | Usa regex + diccionario hardcodeado | Solo reconoce ~10 venues de Madrid |
| **Accessibility Tool** | Lookup en `ACCESSIBILITY_DB` (4 venues) | Devuelve mock data genérico |
| **Route Tool** | Lookup en `ROUTE_DB` (rutas predefinidas) | No escala a otras ciudades |
| **Tourism Info Tool** | Lookup en `VENUE_DB` (4 venues) | Horarios/precios son FAKE |

#### 2.3 Ejemplo: Query sobre Granada

```bash
# Query: "Recomiéndame la Alhambra en Granada"

# NLU Tool detecta: "general" (no reconoce Alhambra)
# Accessibility Tool devuelve: ACCESSIBILITY_DB["general"] (mock data)
# Route Tool devuelve: ROUTE_DB["Madrid centro"] (INCORRECTO!)
# Tourism Info Tool devuelve: VENUE_DB["General Madrid"] (IRRELEVANTE)

# Resultado: Tools NO aportan nada útil
# El LLM usa su conocimiento pre-entrenado para responder
```

#### 2.4 Diagrama del Problema

```
┌──────────────────────────────────────────────────────────┐
│ USER: "Recomiéndame la Alhambra en Granada"             │
└────────────────────┬─────────────────────────────────────┘
                     │
        ┌────────────▼──────────────────┐
        │ Tools (Mock Data)              │
        │ - NLU: "general"               │  ← NO reconoce Alhambra
        │ - Accessibility: mock generic  │  ← Datos fake
        │ - Routes: Madrid centro        │  ← INCORRECTO
        │ - Info: "General Madrid"       │  ← IRRELEVANTE
        └────────────┬──────────────────┘
                     │ (Datos ignorados)
                     ▼
        ┌────────────────────────────────┐
        │ LLM (GPT-4)                    │
        │ - Lee el prompt con tools      │
        │ - IGNORA tools (datos irrelevantes) │
        │ - Usa conocimiento pre-entrenado │  ← Alhambra Granada
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │ Respuesta: Info sobre Alhambra │  ← Funciona
        │ (pero SIN datos estructurados) │  ← tourism_data = null
        └────────────────────────────────┘
```

**Conclusión:** 
- ✅ El LLM puede responder sobre cualquier ciudad (usa su conocimiento)
- ❌ Las tools NO aportan nada, son "teatro arquitectónico"
- ❌ NO hay datos estructurados fiables (tourism_data a menudo null)

---

## 3. Profile Context: ⚠️ SOLO AFECTA TEXTO, NO DATOS

### ¿Qué NO funciona?

#### 3.1 Profile NO afecta las tools

```python
# En agent.py (línea ~54)
def _execute_pipeline(self, user_input: str):
    # PROBLEMA: NO pasa profile_context a las tools
    nlu_result = self.nlu._run(user_input)
    accessibility_result = self.accessibility._run(nlu_result)
    route_result = self.route._run(accessibility_result)
    info_result = self.tourism_info._run(route_result)
```

**Resultado:**
- Las tools devuelven SIEMPRE los mismos datos (mock data genérico)
- El profile_id NO afecta qué venues se recomiendan
- NO hay ranking ni filtering por perfil

#### 3.2 Profile SÍ afecta el prompt (texto)

```python
# En response_prompt.py (línea ~33)
def build_response_prompt(..., profile_context):
    profile_section = f"""
PERFIL ACTIVO: {profile_context.get("label")}
Directivas del perfil:
{chr(10).join(f"- {d}" for d in directives)}
"""
```

**Resultado:**
- El LLM lee las directivas del perfil
- Ajusta el **tono** de la respuesta (más enfocado en ocio nocturno si profile=night_leisure)
- PERO: No afecta qué venues se seleccionan (porque tools son stubs)

#### 3.3 Ejemplo: Mismo Query, Diferentes Perfiles

```bash
# Query: "Recomiéndame actividades en Madrid esta noche"

# Con profile="night_leisure":
# → LLM menciona bares, discotecas (TONO ajustado)
# → Pero tools devolvieron "Museo del Prado" (DATOS no ajustados)
# → Contradicción entre texto y datos estructurados

# Con profile="cultural":
# → LLM menciona museos, exposiciones (TONO ajustado)
# → Pero tools devolvieron "Museo del Prado" (MISMOS DATOS)
# → NO hay sesgo real en los datos
```

---

## 4. JSON Extraction: ⚠️ FRÁGIL (Regex-based)

### Problema: El LLM no siempre emite JSON

```python
# agent.py (línea ~182)
def _extract_structured_data(self, llm_text: str, metadata: dict):
    match = re.search(r"```json\s*(\{.*?\})\s*```", llm_text, re.DOTALL)
    if not match:
        return llm_text, metadata  # ← NO JSON → tourism_data = null
```

**Casos de fallo:**
1. LLM emite JSON sin bloque ``` → regex no lo detecta
2. LLM emite JSON con formato incorrecto → JSON.loads() falla
3. LLM NO emite JSON → Se pierde toda la estructura

**Resultado:**
- `tourism_data` es `null` en ~60% de los casos
-UI no puede renderizar rich cards
- Pérdida de información estructurada

---

## 5. ¿Qué FUNCIONA en la práctica?

### ✅ Lo que SÍ funciona

1. **Conversación básica**: El LLM responde coherentemente (usa su conocimiento)
2. **Infraestructura técnica**: FastAPI, Docker, STT, todo funcional
3. **Flujo de datos**: UI → Backend → Agent → LLM → Response funciona
4. **Profiles (estructural)**: La infraestructura está lista, solo falta conexión con tools

### ❌ Lo que NO funciona

1. **Profile-driven recommendations**: El perfil NO afecta qué se recomienda
2. **Tools útiles**: Son stubs que NO aportan datos reales
3. **Escalabilidad**: Solo funciona para <10 venues de Madrid hardcodeados
4. **Datos estructurados**: tourism_data a menudo null (JSON extraction frágil)

---

## 6. Roadmap: ¿Qué hace falta?

### Prioridad 1: Fase 0 - Tools con APIs Reales ⚠️
**SIN ESTO, NADA MÁS TIENE SENTIDO**

- [ ] Integrar Google Maps API (Places + Directions)
- [ ] Integrar spaCy para NER real (no regex)
- [ ] Integrar API de turismo (TripAdvisor/Yelp)
- [ ] Tests: Validar que funciona para Granada, Sevilla, Barcelona

**Estimación:** 5-7 días  
**Archivos:** `business/domains/tourism/tools/*.py`, `integration/external_apis/`

### Prioridad 2: Profile → Tools → Ranking
- [ ] Modificar tools para recibir `profile_context`
- [ ] Implementar ranking/filtering por perfil
- [ ] Validar que perfil afecta venues seleccionados

**Estimación:** 2-3 días  
**Depende de:** Fase 0 completada

### Prioridad 3: JSON Extraction Robusta
- [ ] Usar function calling (OpenAI) en lugar de regex
- [ ] Garantizar JSON siempre válido
- [ ] Canonización con retry logic

**Estimación:** 2-3 días  
**Depende de:** Fase 0 completada

---

## 7. Decisiones Pendientes

### Decisión 1: ¿Qué estrategia para tools?

| Opción | Pros | Contras | Coste |
|--------|------|---------|-------|
| **A: APIs Externas** | Datos reales, actualizados | Coste por uso, rate limits | $$$ medio |
| **B: RAG (DB local)** | Sin coste APIs, privacidad | Mantenimiento manual | $ bajo |
| **C: Búsqueda web** | Coverage total | Precisión variable | $$ medio |

**Recomendación:** Empezar con **A (APIs)** para PoC, migrar a **B (RAG)** para producción.

### Decisión 2: ¿Cuándo implementar Fase 0?

- **Opción A:** Ahora (prerequisito para que profiles funcione)
- **Opción B:** Después (primero arreglar JSON extraction)

**Recomendación:** **Opción A** - Sin tools reales, el resto del plan no tiene sentido.

---

## 8. Conclusiones

### Estado del Sistema: "Prototipo Arquitectónico Funcional"

El sistema actual es un **prototipo arquitectónico** que demuestra:
- ✅ La estructura en capas funciona
- ✅ La integración LangChain + OpenAI funciona
- ✅ El flujo de perfiles está implementado (infraestructura)

**PERO:**
- ❌ Las tools son stubs (mock data)
- ❌ El perfil NO afecta realmente las recomendaciones
- ❌ NO escala a otras ciudades sin hardcodear datos

### Siguiente Paso Crítico

**Implementar Fase 0: Integración con APIs reales**

Sin esto, el sistema es "humo y espejos" - parece funcional pero no lo es.

---

**Autor:** GitHub Copilot (Claude Sonnet 4.5)  
**Revisado:** [Tu nombre]  
**Última actualización:** 18 Feb 2026
