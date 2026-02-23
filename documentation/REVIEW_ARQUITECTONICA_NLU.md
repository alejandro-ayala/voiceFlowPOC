# Revisión Arquitectónica — PLAN_IMPLEMENTACION_NLU_5_COMMITS

**Fecha de revisión**: 25 de Febrero de 2026
**Documento revisado**: `documentation/PLAN_IMPLEMENTACION_NLU_5_COMMITS.md`
**Rol**: Principal Software Architect

---

## 1. RESUMEN EJECUTIVO

| Dimensión | Valoración |
|---|---|
| **Calidad general del plan** | **7.5 / 10** |
| **Madurez del diseño** | Medio-alto para un POC; insuficiente para producción |
| **Riesgo de implementación** | Medio — acotado por precedente NER, pero con gaps operativos |

El plan es **sólido en su estructura de capas y en la aplicación de patrones ya probados** (factory, interface, DI) calcados del precedente NER. Eso reduce riesgo de ejecución. Sin embargo, **subestima la complejidad del problema NLU frente al NER**, tiene gaps significativos en observabilidad avanzada, gestión de modelos y estrategia de rollback, y deja sin resolver preguntas clave sobre cómo se implementará realmente la clasificación de intents (el "cerebro" del cambio).

**Principales riesgos:**
1. La lógica de clasificación de intent queda vagamente definida como "spaCy + reglas + scikit-learn opcional" — sin especificar cómo se entrena, qué features se usan, ni qué precisión se espera.
2. El `EntityResolver` / merge policy NLU↔NER es el punto de mayor complejidad y menor detalle en el plan.
3. El Commit 5 (tests) al final crea un ciclo peligroso: se implementan 4 commits sin red de seguridad automatizada.

---

## 2. ASPECTOS POSITIVOS

### 2.1 Reutilización de patrones probados
El plan replica fielmente la arquitectura NER existente (`NERServiceInterface` → `SpacyNERService` → `NERServiceFactory` → `LocationNERTool`). Esto no es accidental: el equipo ya validó que el patrón interface + factory + DI funciona en este codebase. **Reducir incertidumbre arquitectónica es una decisión acertada.**

### 2.2 Separación NLU vs NER bien justificada (§2.5)
La decisión de NO fusionar NLU y NER está correctamente argumentada:
- Responsabilidades ortogonales (clasificación semántica vs. extracción de spans).
- Ritmos de evolución distintos.
- Mejor observabilidad por etapa.

Esto es **la decisión más importante del documento** y es correcta.

### 2.3 Contrato canónico explícito (§2.3)
Definir el schema JSON de salida antes de implementar es buena práctica de diseño por contrato. El campo `alternatives` y `status` con estados `ok|fallback|error` muestran pensamiento defensivo.

### 2.4 Configuración externalizada coherente
Las variables `VOICEFLOW_NLU_*` siguen la convención existente (`VOICEFLOW_NER_*`) y el patrón de `model_map` JSON ya validado. La configurabilidad por entorno sin cambio de código es el enfoque correcto.

### 2.5 Non-goals explícitos (§1)
Declarar qué NO se hará es tan importante como lo que sí se hará. Excluir function-calling estructurado, fusión NLU/NER y migración de tools stub reduce scope creep.

---

## 3. ASPECTOS NEGATIVOS / DEBILIDADES

### 3.1 La clasificación de intent es una caja negra

El plan dice "spaCy para análisis lingüístico + reglas deterministas + clasificador ligero opcional (scikit-learn)". Esto es **tres estrategias distintas sin definir cuál es la primaria ni cómo interactúan**:

- ¿spaCy se usa solo para tokenización/lemas o también para clasificación vía `TextCategorizer`?
- ¿Las "reglas deterministas" son los mismos `INTENT_PATTERNS` actuales reescritos, o algo nuevo?
- ¿El clasificador scikit-learn es "fase 2/3" pero el plan tiene 5 commits — cuándo se implementa realmente?

**Impacto:** El cambio más importante del plan (pasar de keyword matching a algo mejor) queda sin especificar. Un implementador podría terminar con keyword matching ligeramente mejorado disfrazado de "NLU híbrida".

### 3.2 El `EntityResolver` está infradefinido

La sección §2.5 propone un `EntityResolver` con "reglas explícitas" para reconciliar NLU y NER, pero:
- No define las reglas.
- No especifica qué pasa cuando NLU dice `destination: "Museo del Prado"` y NER dice `top_location: "Prado"` (¿son iguales? ¿quién gana?).
- No define la interfaz del resolver ni su ubicación exacta en el pipeline.
- El archivo `business/domains/tourism/entity_resolver.py` aparece como "(Opcional)" en el Commit 3.

**Impacto:** El merge policy es donde vive la complejidad real del sistema dual NLU+NER. Dejarlo como opcional es un riesgo.

### 3.3 Confidence score sin calibración

El plan habla de `confidence: 0.87` y `VOICEFLOW_NLU_CONFIDENCE_THRESHOLD=0.60`, pero:
- No define cómo se calcula el confidence score.
- Un clasificador basado en reglas no produce probabilidades calibradas.
- Si spaCy hace matching de patterns, el score puede ser binario (matched/not matched), no un float significativo.
- Sin un dataset de evaluación, el threshold 0.60 es un número arbitrario.

**Impacto:** El sistema de confidence/fallback puede dar falsa sensación de control sin aportar valor real.

### 3.4 Tests al final = deuda técnica estructural

Los 5 commits siguen un patrón `implementar → implementar → implementar → implementar → testear`. Esto contradice las mejores prácticas por dos razones:
1. Los commits 1-4 se mergean sin cobertura — cualquier regresión se descubre tarde.
2. El Commit 5 concentra toda la carga de testing, incentivando tests superficiales por presión de cierre.

### 3.5 `analyze_text()` retorna `dict` — pérdida de type safety

La interfaz propuesta define `analyze_text(...) -> dict`. En un codebase que usa Pydantic extensivamente, retornar un dict crudo pierde las garantías de validación. El contrato canónico (§2.3) debería ser un `NLUResult(BaseModel)`, no un dict que "se espera" que tenga cierta forma.

### 3.6 Ambigüedad en `intent_map` configurable

`VOICEFLOW_NLU_INTENT_MAP={...}` aparece en la configuración pero nunca se define su contenido ni su propósito. ¿Es un mapeo de labels internos a labels de API? ¿Un override de la taxonomía de intents? ¿Una tabla de aliases?

---

## 4. GAPS NO CUBIERTOS

### 4.1 Escalabilidad
- **No se menciona carga de modelos spaCy en memoria.** Un modelo `es_core_news_md` ocupa ~50MB. Si se agregan idiomas, la huella crece linealmente. No hay estrategia de eviction ni lazy loading por idioma.
- **No hay consideración de concurrencia.** `run_in_executor()` funciona para NER porque es stateless, pero si el clasificador scikit-learn tiene estado mutable, hay riesgo de race conditions.
- **No hay caching de resultados NLU.** Si el mismo texto se procesa dos veces (retry, re-render), se repite todo el pipeline.

### 4.2 Observabilidad
- Los logs estructurados (§3) son un mínimo viable. Faltan:
  - **Métricas agregadas** (histogramas de latencia, distribución de intents, tasa de fallback).
  - **Tracing distribuido** (correlation IDs entre NLU y NER para una misma request).
  - **Alertas** sobre degradación (si fallback rate > X%, notificar).
  - **Dashboard** o exportación a Prometheus/Grafana/similar.

### 4.3 Seguridad
- **Inyección de prompts:** El campo `text` se pasa directamente a spaCy y luego al LLM. No hay sanitización ni detección de prompt injection.
- **Validación de inputs:** `profile_context: Optional[dict]` es un dict abierto sin schema. Superficie de ataque si se expone al cliente.
- **Model poisoning:** Si se permite configurar `NLU_MODEL_MAP` por env, un atacante con acceso al entorno puede sustituir modelos.

### 4.4 Manejo de errores
- El plan menciona "degradación graceful" pero no define la cadena de fallback completa:
  - ¿Si spaCy falla al cargar el modelo? → ¿keyword fallback?
  - ¿Si el factory no encuentra el provider? → ¿excepción o fallback?
  - ¿Si la latencia excede un timeout? → ¿circuit breaker?
- No hay timeout configurable para la operación NLU.

### 4.5 Testing
- **No hay dataset de evaluación.** Sin un corpus etiquetado de intents/entities, no se puede medir si la NLU mejoró respecto al keyword matching.
- **No hay tests de regresión del pipeline completo** que verifiquen que el flujo end-to-end no se rompe.
- **No hay property-based testing** para el contrato NLU (e.g., "para cualquier input, el output siempre tiene `intent` y `status`").
- **No hay tests de performance** (latencia p95/p99 bajo carga).

### 4.6 Rollback
- **No hay feature flag granular.** `VOICEFLOW_NLU_ENABLED=true/false` es un kill switch, pero no permite rollback parcial (e.g., "usar nueva NLU solo para intent, mantener keyword matching para entities").
- **No hay estrategia de canary/blue-green** para la transición.
- **No hay mecanismo de shadow mode** (ejecutar nueva NLU en paralelo con la vieja y comparar resultados sin afectar producción).

### 4.7 Gestión de versiones de modelos
- `analysis_version: "nlu_v2"` aparece en el contrato pero no se define qué significa ni cómo se incrementa.
- No hay versionado semántico del modelo NLU ni de la taxonomía de intents.
- No hay mecanismo para auditar qué versión procesó cada request (más allá del log).

### 4.8 Gobernanza de modelos NLU
- ¿Quién define la taxonomía de intents? ¿Puede crecer sin límite?
- ¿Cómo se agrega un nuevo intent? ¿Requiere despliegue o es configurable?
- ¿Quién valida que un cambio en patterns no rompe intents existentes?

### 4.9 Costos operativos
- El plan no menciona impacto en tiempos de build Docker (bootstrap de modelos spaCy).
- El `Dockerfile` actual ya descarga modelos NER en build time; agregar modelos NLU puede duplicar el tiempo.
- No hay estimación de impacto en latencia del pipeline completo.

### 4.10 SLA/SLO
- No se define latencia máxima aceptable para la etapa NLU.
- No se define accuracy mínima esperada.
- No se define disponibilidad target del servicio NLU.

---

## 5. RIESGOS EN PRODUCCIÓN

### 5.1 Riesgos operativos

| Riesgo | Probabilidad | Impacto | Detalle |
|---|---|---|---|
| Modelo spaCy no disponible en runtime | Media | Alto | Si el modelo no se descarga en build time o se corrompe, NLU falla silenciosamente |
| Memory pressure por modelos en RAM | Media | Medio | 2 modelos NER + 2 modelos NLU = ~200MB solo en modelos spaCy |
| Logs sin rotación saturan disco | Baja | Medio | Logging estructurado por request sin política de retención |

### 5.2 Riesgos de performance

| Riesgo | Probabilidad | Impacto | Detalle |
|---|---|---|---|
| NLU agrega latencia significativa al pipeline | Alta | Medio | Hoy el pipeline tiene 5 etapas; NLU mejorada puede duplicar la latencia de la etapa 1 |
| Cold start de modelos spaCy | Media | Alto | Primera request tras deploy carga modelos en memoria (~2-5s) |
| Sin paralelización NLU/NER | Media | Medio | Ambas etapas son independientes pero se ejecutan secuencialmente |

### 5.3 Riesgos de acoplamiento

| Riesgo | Probabilidad | Impacto | Detalle |
|---|---|---|---|
| Tools downstream asumen shape específico de NLU | Alta | Alto | AccessibilityTool y RoutePlanningTool parsean JSON de NLU con heurísticas frágiles |
| `EntityResolver` crea acoplamiento implícito NLU↔NER | Media | Medio | Si la lógica de merge cambia, afecta a todos los consumidores downstream |

### 5.4 Riesgos de dependencia externa

| Riesgo | Probabilidad | Impacto | Detalle |
|---|---|---|---|
| spaCy breaking changes en minor version | Baja | Alto | El plan no fija versiones de spaCy ni de modelos |
| Incompatibilidad modelo-librería | Media | Alto | Actualizar spaCy sin actualizar modelos (o viceversa) produce errores silenciosos |

### 5.5 Riesgos organizacionales

| Riesgo | Probabilidad | Impacto | Detalle |
|---|---|---|---|
| Scope creep hacia scikit-learn | Alta | Medio | "Clasificador ligero opcional" invita a agregar complejidad de ML training sin infraestructura |
| Expectativas infladas | Media | Alto | El nombre "NLU robusta" puede crear expectativas que keyword+spaCy patterns no cumplen |

---

## 6. MEJORAS PROPUESTAS

### 6.1 Definir explícitamente el algoritmo de clasificación de intent

Antes de implementar, el plan debería especificar:

```
Intent Classification Strategy:
1. Rule layer: spaCy Matcher patterns (deterministic, high precision)
   - Fires first, produces confidence=1.0 if matched
2. Fallback layer: TF-IDF + LogisticRegression (scikit-learn)
   - Trained offline on labeled corpus
   - Produces calibrated probabilities
3. Default: general_query with confidence=0.0
```

Sin esto, el implementador está adivinando.

### 6.2 Hacer el `EntityResolver` obligatorio, no opcional

Promover de "(Opcional)" a **pieza central** del Commit 3. Definir la interfaz:

```python
class EntityResolver:
    def resolve(self, nlu_result: NLUResult, ner_result: NERResult) -> ResolvedEntities:
        """Merge NLU entities with NER extractions using priority rules."""
```

Con reglas explícitas documentadas (e.g., "NER `top_location` tiene prioridad sobre NLU `destination` cuando ambos están presentes y difieren").

### 6.3 Reorganizar commits: tests junto a implementación

**Propuesta de reorganización:**

| Commit | Contenido |
|---|---|
| 1 | Contratos NLU + settings + **tests de contrato** |
| 2 | Proveedor NLU + Factory + **tests unitarios del proveedor** |
| 3 | Refactor NLUTool + EntityResolver + **tests de integración NLU↔NER** |
| 4 | Wiring DI + API + docs + **test e2e del endpoint** |
| 5 | **Hardening**: edge cases, performance benchmarks, shadow mode |

Esto convierte cada commit en una unidad atómica verificable.

### 6.4 Tipar el retorno de `analyze_text()`

```python
class NLUResult(BaseModel):
    status: Literal["ok", "fallback", "error"]
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    entities: dict[str, Any]
    alternatives: list[dict[str, Any]] = []
    provider: str
    model: str
    language: str
    analysis_version: str

class NLUServiceInterface(ABC):
    @abstractmethod
    async def analyze_text(self, text: str, ...) -> NLUResult: ...
```

### 6.5 Agregar shadow mode para transición segura

```python
VOICEFLOW_NLU_SHADOW_MODE=true  # Ejecuta nueva NLU + vieja, compara, logea diferencias
```

Esto permite validar la nueva NLU con tráfico real antes de activarla.

### 6.6 Paralelizar NLU y NER

Ambas etapas toman `raw text` como input y son independientes. Ejecutarlas en paralelo con `asyncio.gather()` reduciría latencia del pipeline:

```python
nlu_result, ner_result = await asyncio.gather(
    nlu_tool.arun(user_input),
    ner_tool.arun(user_input)
)
```

### 6.7 Definir un corpus mínimo de evaluación

Crear un archivo `tests/fixtures/nlu_evaluation_corpus.json` con al menos 50-100 ejemplos etiquetados (intent + entities esperados) para medir precision/recall antes y después del cambio.

---

## 7. PREGUNTAS CRÍTICAS QUE DEBERÍAN RESPONDERSE

1. **¿Cuál es la precisión actual del keyword matching y cuál es el target mínimo para la nueva NLU?** Sin baseline ni target, no se puede medir éxito.

2. **¿Cómo se entrena el clasificador de intent?** Si es rule-based, ¿quién escribe las reglas? Si es ML, ¿de dónde sale el training data?

3. **¿Qué pasa cuando un usuario envía un mensaje multi-intent?** (e.g., "Quiero visitar el Prado y luego cenar cerca") — ¿se retorna solo el primer intent? ¿Se soportan múltiples intents?

4. **¿El campo `alternatives` se usa downstream o es solo informativo?** Si ningún consumidor lo usa, es dead code.

5. **¿Cuál es el budget de latencia para la etapa NLU?** El pipeline actual ya tiene 5 etapas + LLM. ¿Cuántos ms puede agregar NLU sin degradar UX?

6. **¿Se ha validado que spaCy `es_core_news_md` tiene calidad suficiente para el dominio turismo en español?** Los modelos genéricos pueden fallar en vocabulario de dominio.

7. **¿Cómo se manejan idiomas no soportados?** Si un usuario escribe en francés y `NLU_MODEL_MAP` solo tiene `es` y `en`, ¿qué ocurre?

8. **¿El `analysis_version` se incrementa manualmente o automáticamente?** ¿Quién es responsable de versionarlo?

9. **¿Se ha estimado el impacto en tiempo de build del Dockerfile?** Agregar modelos NLU spaCy al bootstrap puede sumar 1-3 minutos al CI.

10. **¿La interfaz `analyze_text` es sync o async?** El plan no lo especifica, pero el NER usa async. La inconsistencia crearía fricción.

---

## 8. RECOMENDACIÓN FINAL

### ¿Está listo para implementarse?
**No en su estado actual.** El plan es una buena estructura de ejecución (qué archivos crear/modificar, en qué orden) pero es un **plan de commits, no un plan de diseño**. Le falta la especificación técnica del componente más importante: cómo funciona realmente la clasificación de intents.

### ¿Requiere rediseño?
**Rediseño parcial**, no completo. La estructura de capas, los patrones y la secuencia de commits son correctos. Lo que falta es:

1. **Especificación del algoritmo de clasificación** (§6.1) — sin esto, el plan es un esqueleto sin cerebro.
2. **Definición rigurosa del EntityResolver** (§6.2) — sin esto, el merge NLU↔NER será ad-hoc.
3. **Tests co-located con implementación** (§6.3) — sin esto, los commits 1-4 son riesgosos.
4. **Tipado fuerte del contrato** (§6.4) — incoherente con las convenciones Pydantic del proyecto.

### Siguientes pasos recomendados

| Paso | Acción | Prioridad |
|---|---|---|
| 1 | Definir el algoritmo de intent classification con pseudocódigo y ejemplos | **Crítica** |
| 2 | Crear corpus de evaluación mínimo (50+ ejemplos etiquetados) | **Crítica** |
| 3 | Especificar reglas del EntityResolver con tabla de decisión | **Alta** |
| 4 | Reorganizar commits para incluir tests en cada uno | **Alta** |
| 5 | Definir `NLUResult` como Pydantic model, no dict | **Media** |
| 6 | Agregar shadow mode al plan de rollout | **Media** |
| 7 | Documentar budget de latencia y SLO mínimos | **Media** |
| 8 | Evaluar paralelización NLU ‖ NER | **Baja** |
