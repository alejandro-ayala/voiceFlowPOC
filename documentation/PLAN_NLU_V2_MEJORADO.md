# Plan de Implementación NLU v2 — Intent + Slots (Mejorado)

**Fecha**: 25 de Febrero de 2026
**Rama**: `feature/nlu-tool-implementation`
**Basado en**: `PLAN_IMPLEMENTACION_NLU_5_COMMITS.md` + `REVIEW_ARQUITECTONICA_NLU.md`
**Estado**: Listo para ejecución

---

## 1. PRINCIPIOS DE DISENO

### 1.1 Objetivos tcnicos

1. Reemplazar el keyword matching actual (`TourismNLUTool` + `nlu_patterns.py`) por una NLU hbrida rule+NLP que clasifique intents y extraiga slots de negocio.
2. Mantener el patrn `Interface → Provider → Factory → Tool` ya validado con NER.
3. Tipar fuertemente la salida NLU con Pydantic (`NLUResult`).
4. Paralelizar NLU y NER (`asyncio.gather`) ya que ambas consumen texto crudo.
5. Formalizar la reconciliacin de entidades NLU/NER con un `EntityResolver` obligatorio.
6. Incluir tests en cada commit — nunca mergear implementacin sin cobertura.

### 1.2 Non-goals (esta iteracin)

- No entrenar un modelo ML supervisado (scikit-learn/TextCategorizer). Queda como fase posterior.
- No fusionar NLU y NER en una sola tool.
- No migrar tools stub (Accessibility, Routes, Venue Info) a APIs externas.
- No implementar function-calling estructurado con el LLM.
- No implementar dashboard Prometheus/Grafana (s exponer mtricas en logs).

### 1.3 Restricciones operativas

| Restriccin | Detalle |
|---|---|
| Capa Business no importa spaCy | Solo depende de `NLUServiceInterface` (shared) |
| Capa Shared no tiene lgica | Solo contratos Pydantic + ABC interfaces |
| Capa Integration implementa providers | spaCy, reglas de dominio, carga de modelos |
| Capa Application hace wiring | DI via factory, feature flags, shadow mode |
| Backward compatible | El endpoint `/api/v1/chat/message` no rompe shape existente |
| Docker build < 8 min | Reusar modelos spaCy ya descargados para NER (mismos modelos) |

### 1.4 SLOs definidos

| Mtrica | Target | Medicin |
|---|---|---|
| **Latencia NLU p95** | < 50ms (excluyendo cold start) | Log `nlu_latency_ms` por request |
| **Latencia NLU cold start** | < 3s (primera request carga modelo) | Log `nlu_model_load_ms` |
| **Accuracy intent (corpus eval)** | > 85% en corpus de 80+ ejemplos | `pytest` con corpus etiquetado |
| **Fallback rate** | < 20% de requests en `general_query` | Log `nlu_status=fallback` |
| **Disponibilidad NLU** | 99.5% (mismo que app principal) | `is_service_available()` check |
| **Pipeline total p95** | < 6s (NLU+NER+tools+LLM) | Log `pipeline_total_ms` |

---

## 2. ARQUITECTURA PROPUESTA

### 2.1 Flujo de datos (texto)

```
User Input (texto crudo)
        |
        +-------------------+-------------------+
        |                                       |
   [NLU Service]                         [NER Service]
   (SpacyNLUService)                     (SpacyNERService)
        |                                       |
   NLUResult{                            NERResult{
     intent,                               locations[],
     confidence,                           top_location
     entities{destination,               }
       accessibility, timeframe,
       transport_preference},
     alternatives[]
   }                                            |
        |                                       |
        +-------------------+-------------------+
                            |
                    [EntityResolver]
                    merge NLU entities + NER locations
                            |
                    ResolvedEntities{
                      destination (normalizado),
                      locations[] (raw NER),
                      accessibility,
                      timeframe,
                      transport_preference,
                      resolution_source{}
                    }
                            |
              +-------------+-------------+
              |             |             |
        [Accessibility] [Routes]    [Venue Info]
              |             |             |
              +-------------+-------------+
                            |
                    [LLM Synthesis]
                            |
                    ChatResponse
```

### 2.2 Paralelizacin NLU || NER

NLU y NER son independientes: ambas toman `raw_text` como input. Ejecutarlas en paralelo reduce latencia del pipeline en ~30-50ms.

```python
# En TourismMultiAgent._execute_pipeline()
import asyncio

async def _execute_parallel_analysis(self, user_input: str, language: str) -> tuple:
    """Run NLU and NER in parallel since both consume raw text."""
    nlu_coro = self.nlu_service.analyze_text(user_input, language=language)
    ner_coro = self.ner_service.extract_locations(user_input, language=language)
    nlu_result, ner_result = await asyncio.gather(nlu_coro, ner_coro)
    return nlu_result, ner_result
```

### 2.3 Responsabilidades por capa

| Capa | Archivos | Responsabilidad |
|---|---|---|
| **Shared** | `shared/interfaces/nlu_interface.py`, `shared/models/nlu_models.py` | Contrato `NLUServiceInterface` (ABC) + modelos Pydantic `NLUResult`, `NLUEntitySet`, `NLUAlternative` |
| **Integration** | `integration/external_apis/spacy_nlu_service.py`, `integration/external_apis/nlu_factory.py`, `integration/configuration/settings.py` | `SpacyNLUService` (provider concreto), `NLUServiceFactory` (registry), settings `nlu_*` |
| **Business** | `business/domains/tourism/tools/nlu_tool.py`, `business/domains/tourism/entity_resolver.py` | `TourismNLUTool` (wrapper LangChain), `EntityResolver` (merge NLU+NER) |
| **Application** | `shared/utils/dependencies.py`, `application/orchestration/backend_adapter.py` | DI wiring, feature flags, shadow mode |

### 2.4 Contratos tipados (Pydantic)

#### `shared/models/nlu_models.py`

```python
from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class NLUAlternative(BaseModel):
    """Alternative intent classification."""
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)


class NLUEntitySet(BaseModel):
    """Business entities extracted by NLU."""
    destination: Optional[str] = None
    accessibility: Optional[str] = None
    timeframe: Optional[str] = None
    transport_preference: Optional[str] = None
    budget: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class NLUResult(BaseModel):
    """Canonical output of the NLU service."""
    status: Literal["ok", "fallback", "error"] = "ok"
    intent: str = "general_query"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    entities: NLUEntitySet = Field(default_factory=NLUEntitySet)
    alternatives: list[NLUAlternative] = Field(default_factory=list)
    provider: str = "unknown"
    model: str = "unknown"
    language: str = "es"
    analysis_version: str = "nlu_v2.0"
    latency_ms: int = 0


class ResolvedEntities(BaseModel):
    """Output of EntityResolver after merging NLU + NER."""
    destination: Optional[str] = None
    locations: list[str] = Field(default_factory=list)
    top_location: Optional[str] = None
    accessibility: Optional[str] = None
    timeframe: Optional[str] = None
    transport_preference: Optional[str] = None
    budget: Optional[str] = None
    resolution_source: dict[str, str] = Field(default_factory=dict)
    # ^ maps each field to its source: "nlu", "ner", "merged"
    conflicts: list[str] = Field(default_factory=list)
    # ^ human-readable list of conflicts detected
```

#### `shared/interfaces/nlu_interface.py`

```python
from abc import ABC, abstractmethod
from typing import Optional

from shared.models.nlu_models import NLUResult


class NLUServiceInterface(ABC):
    """Contract for NLU services: intent classification + slot extraction."""

    @abstractmethod
    async def analyze_text(
        self,
        text: str,
        language: Optional[str] = None,
        profile_context: Optional[dict] = None,
    ) -> NLUResult:
        """Classify intent and extract business entities from text."""
        ...

    @abstractmethod
    def is_service_available(self) -> bool:
        """Report if the NLU provider is ready."""
        ...

    @abstractmethod
    def get_supported_languages(self) -> list[str]:
        """Return supported language codes."""
        ...

    @abstractmethod
    def get_service_info(self) -> dict:
        """Return provider metadata (name, model, status)."""
        ...
```

---

## 3. ESTRATEGIA DE CLASIFICACIN DE INTENTS (DEFINICIN FORMAL)

### 3.1 Arquitectura del clasificador: dos capas secuenciales

```
Input text
    |
    v
[Layer 1: spaCy Matcher — reglas deterministas]
    |
    +-- match? --> Intent con confidence = 0.95
    |
    +-- no match?
          |
          v
    [Layer 2: spaCy lemma + TF-IDF cosine similarity]
          |
          +-- similarity >= threshold? --> Intent con confidence = similarity_score
          |
          +-- similarity < threshold? --> "general_query" con confidence = similarity_score, status = "fallback"
```

### 3.2 Layer 1: spaCy Matcher (reglas deterministas, alta precisin)

Usa `spacy.matcher.Matcher` con patterns lingsticos (no keyword `in` simple).
Los patterns operan sobre tokens lematizados, lo que les da robustez frente a variaciones morfolgicas.

**Patterns de ejemplo (ES):**

```python
INTENT_MATCHER_PATTERNS = {
    "route_planning": [
        # "cmo llegar al Prado" / "quiero ir al museo"
        [{"LEMMA": {"IN": ["cmo", "como"]}}, {"LEMMA": "llegar"}],
        [{"LEMMA": {"IN": ["querer", "necesitar"]}}, {"LEMMA": "ir"}],
        [{"LEMMA": "ruta"}, {"OP": "?", "POS": "ADP"}],
        [{"LEMMA": "transporte"}, {"OP": "?", "POS": "ADP"}],
    ],
    "event_search": [
        [{"LEMMA": {"IN": ["evento", "concierto", "espectculo", "festival"]}}],
        [{"LEMMA": {"IN": ["buscar", "encontrar"]}}, {"OP": "*"}, {"LEMMA": {"IN": ["evento", "actividad"]}}],
    ],
    "restaurant_search": [
        [{"LEMMA": {"IN": ["restaurante", "comer", "cenar", "comida", "gastronoma"]}}],
        [{"LEMMA": "dnde"}, {"OP": "*"}, {"LEMMA": {"IN": ["comer", "cenar"]}}],
    ],
    "accommodation_search": [
        [{"LEMMA": {"IN": ["hotel", "alojamiento", "hostal", "dormir", "hospedaje"]}}],
    ],
}
```

**Ejecucin:**

```python
def _classify_by_rules(self, doc: spacy.tokens.Doc) -> tuple[str | None, float]:
    """Layer 1: deterministic Matcher patterns.

    Returns:
        (intent, confidence) or (None, 0.0) if no rule matched.
    """
    matches = self._matcher(doc)
    if not matches:
        return None, 0.0

    # Group matches by intent, pick the one with most token coverage
    intent_scores: dict[str, int] = {}
    for match_id, start, end in matches:
        intent_name = self._nlp.vocab.strings[match_id]
        span_length = end - start
        intent_scores[intent_name] = max(intent_scores.get(intent_name, 0), span_length)

    best_intent = max(intent_scores, key=intent_scores.get)
    return best_intent, 0.95  # Fixed high confidence for rule matches
```

### 3.3 Layer 2: Lemma-based TF-IDF cosine similarity (fallback semntico)

Cuando Layer 1 no produce match, se usa un enfoque vectorial ligero: se pre-computan vectores TF-IDF de frases prototipo por intent y se compara con el input lematizado.

**Corpus de referencia (precalculado en `__init__`):**

```python
INTENT_REFERENCE_CORPUS = {
    "route_planning": [
        "quiero llegar destino transporte ruta camino indicacin",
        "cmo ir lugar metro bus autobs",
        "necesito ruta accesible silla rueda",
    ],
    "event_search": [
        "buscar evento concierto actividad espectculo plan ocio",
        "qu hay hoy noche fin semana cultura",
    ],
    "restaurant_search": [
        "restaurante comer comida cenar gastronoma tapas bar",
        "dnde comer cerca zona accesible celaco vegetariano",
    ],
    "accommodation_search": [
        "hotel alojamiento hostal dormir habitacin reserva noche",
        "buscar hotel accesible adaptado",
    ],
    "general_query": [
        "informacin general turismo ciudad visitar conocer",
        "qu recomiendas sugerencia ayuda consulta",
    ],
}
```

**Algoritmo:**

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class SpacyNLUService:
    def __init__(self, ...):
        # Pre-compute TF-IDF vectors for reference corpus
        all_docs = []
        self._intent_labels = []
        self._intent_doc_indices = {}  # intent -> list of doc indices

        idx = 0
        for intent, phrases in INTENT_REFERENCE_CORPUS.items():
            start_idx = idx
            for phrase in phrases:
                all_docs.append(phrase)
                idx += 1
            self._intent_doc_indices[intent] = list(range(start_idx, idx))
            self._intent_labels.append(intent)

        self._tfidf = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            max_features=500,
        )
        self._reference_matrix = self._tfidf.fit_transform(all_docs)

    def _classify_by_similarity(self, doc) -> tuple[str, float]:
        """Layer 2: TF-IDF cosine similarity against reference corpus.

        Returns:
            (best_intent, confidence_score)
        """
        # Lemmatize input
        lemmatized = " ".join([token.lemma_.lower() for token in doc if not token.is_stop and not token.is_punct])

        if not lemmatized.strip():
            return "general_query", 0.0

        input_vec = self._tfidf.transform([lemmatized])
        similarities = cosine_similarity(input_vec, self._reference_matrix)[0]

        # Compute per-intent score as max similarity across intent's reference docs
        intent_scores = {}
        for intent, indices in self._intent_doc_indices.items():
            intent_scores[intent] = float(np.max(similarities[indices]))

        best_intent = max(intent_scores, key=intent_scores.get)
        best_score = intent_scores[best_intent]

        return best_intent, round(best_score, 4)
```

### 3.4 Combinacin de layers y clculo de confidence

```python
async def analyze_text(self, text: str, language: str | None = None, ...) -> NLUResult:
    doc = await self._process_text(text, language)

    # Layer 1: deterministic rules
    rule_intent, rule_confidence = self._classify_by_rules(doc)

    if rule_intent is not None:
        # Rule matched: high confidence, include alternatives from Layer 2
        sim_intent, sim_confidence = self._classify_by_similarity(doc)
        alternatives = []
        if sim_intent != rule_intent and sim_confidence > 0.3:
            alternatives.append(NLUAlternative(intent=sim_intent, confidence=sim_confidence))

        return NLUResult(
            status="ok",
            intent=rule_intent,
            confidence=rule_confidence,  # 0.95 for rule matches
            entities=self._extract_entities(doc, text),
            alternatives=alternatives,
            ...
        )

    # Layer 2: similarity-based classification
    sim_intent, sim_confidence = self._classify_by_similarity(doc)
    threshold = self._confidence_threshold  # from settings, default 0.40

    if sim_confidence >= threshold:
        status = "ok"
    else:
        status = "fallback"
        sim_intent = self._fallback_intent  # "general_query"

    # Build alternatives: all intents above 0.2 except the best
    alternatives = self._build_alternatives(doc, exclude=sim_intent)

    return NLUResult(
        status=status,
        intent=sim_intent,
        confidence=sim_confidence,
        entities=self._extract_entities(doc, text),
        alternatives=alternatives,
        ...
    )
```

### 3.5 Extraccin de entidades (slots)

La extraccin de slots usa una combinacin de: spaCy NER entities del doc + Matcher patterns de dominio + regex de normalizacin.

```python
def _extract_entities(self, doc, raw_text: str) -> NLUEntitySet:
    """Extract business entities from spaCy doc."""

    # 1. Destination: from spaCy NER (LOC/GPE/FAC/ORG) + domain patterns
    destination = self._extract_destination(doc, raw_text)

    # 2. Accessibility: from matcher patterns
    accessibility = self._extract_accessibility(raw_text)

    # 3. Timeframe: regex-based normalization
    timeframe = self._extract_timeframe(raw_text)

    # 4. Transport preference: from matcher patterns
    transport = self._extract_transport(raw_text)

    return NLUEntitySet(
        destination=destination,
        accessibility=accessibility,
        timeframe=timeframe,
        transport_preference=transport,
    )

def _extract_destination(self, doc, raw_text: str) -> str | None:
    """Extract destination using spaCy NER + domain vocabulary.

    Priority:
    1. Domain-specific venue patterns (exact match, high precision)
    2. spaCy NER entities (LOC/GPE/FAC/ORG)
    3. None if nothing found
    """
    text_lower = raw_text.lower()

    # Domain patterns first (from configurable DESTINATION_VOCABULARY)
    for venue_name, keywords in self._destination_vocabulary.items():
        if any(kw in text_lower for kw in keywords):
            return venue_name

    # spaCy NER fallback
    location_ents = [ent.text for ent in doc.ents if ent.label_ in {"LOC", "GPE", "FAC", "ORG"}]
    if location_ents:
        return location_ents[0]  # First entity as primary destination

    return None

def _extract_timeframe(self, raw_text: str) -> str | None:
    """Normalize temporal expressions to canonical values."""
    text_lower = raw_text.lower()
    TIMEFRAME_MAP = {
        "today_morning": ["esta maana", "hoy por la maana", "this morning"],
        "today_afternoon": ["esta tarde", "hoy por la tarde", "this afternoon"],
        "today_evening": ["esta noche", "hoy por la noche", "tonight", "this evening"],
        "today": ["hoy", "today"],
        "tomorrow": ["maana", "tomorrow"],
        "this_weekend": ["fin de semana", "este finde", "weekend"],
    }
    for canonical, patterns in TIMEFRAME_MAP.items():
        if any(p in text_lower for p in patterns):
            return canonical
    return None

def _extract_accessibility(self, raw_text: str) -> str | None:
    """Extract accessibility requirement."""
    text_lower = raw_text.lower()
    ACCESSIBILITY_MAP = {
        "wheelchair": ["silla de ruedas", "wheelchair", "movilidad reducida"],
        "visual_impairment": ["visual", "ciego", "ciega", "braille", "baja visin"],
        "hearing_impairment": ["auditivo", "sordo", "sorda", "lengua de seas", "seas"],
        "cognitive": ["cognitivo", "cognitiva", "lectura fcil"],
    }
    for canonical, patterns in ACCESSIBILITY_MAP.items():
        if any(p in text_lower for p in patterns):
            return canonical
    return None

def _extract_transport(self, raw_text: str) -> str | None:
    """Extract transport preference."""
    text_lower = raw_text.lower()
    TRANSPORT_MAP = {
        "metro": ["metro", "suburbano"],
        "bus": ["autobs", "autobus", "bus"],
        "walk": ["andando", "caminando", "a pie", "walking"],
        "taxi": ["taxi", "vtc", "uber", "cabify"],
    }
    for canonical, patterns in TRANSPORT_MAP.items():
        if any(p in text_lower for p in patterns):
            return canonical
    return None
```

### 3.6 Manejo de multi-intent

**Decisin:** En esta iteracin, se retorna **un solo intent primario** + `alternatives` con sus scores. El pipeline consume solo el intent primario.

**Justificacin:** El pipeline downstream (Accessibility, Routes, Venue Info) no est diseado para procesar mltiples intents en paralelo. Soportar multi-intent requerira un re-diseo del orchestrator.

**Comportamiento:**
- Input: "Quiero visitar el Prado y luego cenar cerca"
- Output: `intent: "route_planning"` (por la seal de desplazamiento), `alternatives: [{intent: "restaurant_search", confidence: 0.72}]`
- El campo `alternatives` queda disponible para consumo futuro.

### 3.7 Manejo de idiomas no soportados

```python
async def analyze_text(self, text: str, language: str | None = None, ...) -> NLUResult:
    selected_lang = (language or self._default_language).lower()

    if selected_lang not in self._model_map:
        logger.warning("nlu_unsupported_language", language=selected_lang, supported=list(self._model_map.keys()))
        # Fallback to default language model — best effort
        selected_lang = self._default_language

    # Continue with selected_lang...
```

**Comportamiento:** Si se pide francs y solo hay `es`/`en`, se usa el modelo del idioma por defecto (`es`). Se logea un warning. El `NLUResult.language` refleja el idioma realmente usado, no el solicitado, para trazabilidad.

### 3.8 Cadena de fallback completa

```
1. spaCy modelo configurado (es_core_news_md)
   |-- falla carga? --> intenta fallback_model (es_core_news_sm)
       |-- falla carga? --> keyword fallback (sin spaCy)
           |-- keyword match? --> intent + confidence=0.70
           |-- no match? --> general_query + status=error
```

```python
def _keyword_fallback(self, text: str) -> NLUResult:
    """Emergency fallback when spaCy is completely unavailable.

    Uses simple keyword matching (similar to current TourismNLUTool)
    to provide basic service degradation.
    """
    text_lower = text.lower()

    KEYWORD_INTENTS = {
        "route_planning": ["ruta", "llegar", "cmo", "ir", "transporte"],
        "event_search": ["evento", "concierto", "actividad"],
        "restaurant_search": ["restaurante", "comer", "comida"],
        "accommodation_search": ["hotel", "alojamiento", "dormir"],
    }

    for intent, keywords in KEYWORD_INTENTS.items():
        if any(kw in text_lower for kw in keywords):
            return NLUResult(
                status="fallback",
                intent=intent,
                confidence=0.70,
                entities=self._extract_entities_keyword_mode(text),
                provider=self._provider_name,
                model="keyword_fallback",
                language=self._default_language,
            )

    return NLUResult(
        status="error",
        intent="general_query",
        confidence=0.0,
        provider=self._provider_name,
        model="keyword_fallback",
        language=self._default_language,
    )
```

---

## 4. ENTITY RESOLVER — ESPECIFICACIN FORMAL

### 4.1 Interfaz

```python
# business/domains/tourism/entity_resolver.py

from shared.models.nlu_models import NLUResult, NLUEntitySet, ResolvedEntities
import structlog

logger = structlog.get_logger(__name__)


class EntityResolver:
    """Merge NLU business entities with NER location extractions.

    Deterministic, stateless resolver with explicit precedence rules.
    All conflict decisions are logged for post-hoc tuning.
    """

    def resolve(
        self,
        nlu_result: NLUResult,
        ner_locations: list[str],
        ner_top_location: str | None,
    ) -> ResolvedEntities:
        """Apply merge rules and return resolved entities."""
        ...
```

### 4.2 Tabla de decisin

| # | NLU `destination` | NER `top_location` | NER `locations[]` | Resultado `destination` | `resolution_source["destination"]` |
|---|---|---|---|---|---|
| 1 | `None` | `None` | `[]` | `None` | `"none"` |
| 2 | `None` | `"Prado"` | `["Prado"]` | `"Prado"` | `"ner"` |
| 3 | `"Museo del Prado"` | `None` | `[]` | `"Museo del Prado"` | `"nlu"` |
| 4 | `"Museo del Prado"` | `"Museo del Prado"` | `[...]` | `"Museo del Prado"` | `"both_agree"` |
| 5 | `"Museo del Prado"` | `"Prado"` | `[...]` | `"Museo del Prado"` | `"nlu_normalized"` |
| 6 | `"Museo del Prado"` | `"Retiro"` | `["Retiro", "Prado"]` | `"Museo del Prado"` | `"nlu_preferred"` |
| 7 | `"general"` | `"Retiro"` | `["Retiro"]` | `"Retiro"` | `"ner_override"` |

### 4.3 Reglas de precedencia

```python
def resolve(self, nlu_result, ner_locations, ner_top_location) -> ResolvedEntities:
    nlu_dest = nlu_result.entities.destination
    conflicts = []
    resolution_source = {}

    # --- DESTINATION RESOLUTION ---
    resolved_dest = None

    # Rule 1: Both absent
    if not nlu_dest and not ner_top_location:
        resolved_dest = None
        resolution_source["destination"] = "none"

    # Rule 2: Only NER present
    elif not nlu_dest and ner_top_location:
        resolved_dest = ner_top_location
        resolution_source["destination"] = "ner"

    # Rule 3: Only NLU present
    elif nlu_dest and not ner_top_location:
        resolved_dest = nlu_dest
        resolution_source["destination"] = "nlu"

    # Rule 4-7: Both present
    else:
        if self._names_match(nlu_dest, ner_top_location):
            # Rules 4 & 5: Agreement (exact or fuzzy)
            resolved_dest = nlu_dest  # NLU version is normalized
            resolution_source["destination"] = "both_agree"
        elif nlu_dest.lower() in ("general", "general_query", "madrid centro"):
            # Rule 7: NLU is generic, NER is specific -> NER wins
            resolved_dest = ner_top_location
            resolution_source["destination"] = "ner_override"
            conflicts.append(
                f"NLU destination '{nlu_dest}' overridden by NER '{ner_top_location}'"
            )
        else:
            # Rule 6: Genuine conflict -> NLU wins (business normalization)
            resolved_dest = nlu_dest
            resolution_source["destination"] = "nlu_preferred"
            conflicts.append(
                f"Conflict: NLU='{nlu_dest}' vs NER='{ner_top_location}'. NLU preferred."
            )

    # --- OTHER ENTITIES (passthrough from NLU) ---
    resolution_source["accessibility"] = "nlu" if nlu_result.entities.accessibility else "none"
    resolution_source["timeframe"] = "nlu" if nlu_result.entities.timeframe else "none"
    resolution_source["transport_preference"] = "nlu" if nlu_result.entities.transport_preference else "none"

    # --- LOG CONFLICTS ---
    if conflicts:
        logger.warning("entity_resolver_conflicts", conflicts=conflicts,
                       nlu_dest=nlu_dest, ner_top=ner_top_location)

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
    """Fuzzy match: NLU 'Museo del Prado' matches NER 'Prado'."""
    nlu_lower = nlu_name.lower().strip()
    ner_lower = ner_name.lower().strip()
    return (
        nlu_lower == ner_lower
        or ner_lower in nlu_lower
        or nlu_lower in ner_lower
    )
```

### 4.4 Ejemplos concretos

**Ejemplo 1 — Acuerdo total:**
```
Input: "Quiero una ruta accesible al Museo del Prado"
NLU:  destination="Museo del Prado", accessibility="wheelchair", intent="route_planning"
NER:  locations=["Museo del Prado"], top_location="Museo del Prado"

Output:
  destination="Museo del Prado"
  resolution_source={"destination": "both_agree", "accessibility": "nlu"}
  conflicts=[]
```

**Ejemplo 2 — NLU genrico, NER especfico:**
```
Input: "Qu puedo visitar en Madrid?"
NLU:  destination="Madrid centro", intent="general_query"
NER:  locations=["Madrid"], top_location="Madrid"

Output:
  destination="Madrid"
  resolution_source={"destination": "ner_override"}
  conflicts=["NLU destination 'Madrid centro' overridden by NER 'Madrid'"]
```

**Ejemplo 3 — Conflicto real:**
```
Input: "Llvame al Retiro, quiero ver el Prado tambin"
NLU:  destination="Parque del Retiro" (first match in patterns)
NER:  locations=["Retiro", "Prado"], top_location="Retiro"

Output:
  destination="Parque del Retiro"
  resolution_source={"destination": "both_agree"}
  conflicts=[]
  # locations preserva ambos: ["Retiro", "Prado"]
```

**Ejemplo 4 — Solo NER:**
```
Input: "Informacin sobre la Alhambra"
NLU:  destination=None (Alhambra not in domain vocabulary)
NER:  locations=["Alhambra"], top_location="Alhambra"

Output:
  destination="Alhambra"
  resolution_source={"destination": "ner"}
  conflicts=[]
```

---

## 5. PLAN DE COMMITS REORGANIZADO

### Commit 1 — Contratos NLU + Settings + Tests de contrato

**Objetivo**: Introducir la interfaz NLU, los modelos Pydantic tipados y la configuracin NLU por entorno. Verificable de forma aislada.

**Archivos a crear:**
- `shared/interfaces/nlu_interface.py`
- `shared/models/__init__.py`
- `shared/models/nlu_models.py`
- `tests/test_shared/test_nlu_interface.py`
- `tests/test_shared/test_nlu_models.py`

**Archivos a modificar:**
- `shared/interfaces/__init__.py` (export nuevo)
- `integration/configuration/settings.py` (aadir `nlu_*` settings)
- `.env.example` (documentar variables NLU)
- `tests/test_shared/test_ner_interface.py` (aadir tests de parsing NLU settings)

**Tests incluidos:**
- `test_nlu_interface.py`: Verifica que `NLUServiceInterface` es abstracta con los mtodos esperados. Verifica que una implementacin concreta mock pasa type check.
- `test_nlu_models.py`: Verifica validacin de `NLUResult` (confidence 0-1, status literal, defaults). Verifica serializacin/deserializacin JSON round-trip. Verifica `ResolvedEntities` con campos opcionales.
- Settings: Verifica parseo de `nlu_model_map`, `nlu_intent_map` con JSON vlido/invlido/vaco.

**Riesgos mitigados:** Contrato ambiguo (ahora tipado con Pydantic). Settings mal parseados (tests de edge cases JSON).

**Validacin:**
```bash
poetry run ruff check shared/ integration/
poetry run ruff format --check shared/ integration/
poetry run pytest tests/test_shared/ -v --tb=short
```

**Mensaje de commit:**
```
feat(shared,integration): add typed NLU interface, Pydantic models, and env-driven NLU settings
```

---

### Commit 2 — Provider NLU + Factory + Tests unitarios

**Objetivo**: Implementar el clasificador hbrido (rules + TF-IDF similarity) y la factory extensible, con tests unitarios completos.

**Archivos a crear:**
- `integration/external_apis/spacy_nlu_service.py`
- `integration/external_apis/nlu_factory.py`
- `integration/external_apis/nlu_reference_corpus.py` (corpus TF-IDF por intent)
- `tests/test_integration/test_spacy_nlu_service.py`
- `tests/test_integration/test_nlu_factory.py`

**Archivos a modificar:**
- `integration/external_apis/__init__.py` (exports)
- `pyproject.toml` (aadir `scikit-learn` como dependencia)

**Detalle de `SpacyNLUService`:**
- Constructor: carga modelo spaCy (reutiliza cach de NER si mismo modelo), inicializa Matcher con patterns, pre-computa TF-IDF matrix.
- `analyze_text()`: Layer1 rules → Layer2 similarity → fallback keyword.
- `_extract_entities()`: destination + accessibility + timeframe + transport.
- Reutilizacin de modelos: Si NER ya carg `es_core_news_md`, NLU lo reutiliza del mismo cach (inyectado via settings o singleton).

**Detalle de `NLUServiceFactory`:**
- Idntica estructura a `NERServiceFactory`: registry, `create_service()`, `create_from_settings()`, `register_service()`.

**Tests incluidos:**
- `test_spacy_nlu_service.py`:
  - Intent classification ES: 10+ frases conocidas con intent esperado.
  - Intent classification EN: 5+ frases bsicas.
  - Fallback cuando input es ambiguo.
  - Entity extraction: destination, accessibility, timeframe, transport.
  - Confidence score ranges: rules >0.9, similarity 0.3-0.9, fallback <0.3.
  - Keyword fallback cuando spaCy no est disponible (`SPACY_AVAILABLE=False`).
  - Idioma no soportado: fallback a default.
- `test_nlu_factory.py`:
  - Create from settings.
  - Create with invalid provider raises ValueError.
  - Register custom provider.
  - Available services listing.

**Riesgos mitigados:** Clasificador ambiguo (ahora con tests explcitos). Acoplamiento a spaCy (factory desacopla).

**Validacin:**
```bash
poetry run ruff check integration/
poetry run ruff format --check integration/
poetry run pytest tests/test_integration/test_spacy_nlu_service.py tests/test_integration/test_nlu_factory.py -v
```

**Mensaje de commit:**
```
feat(integration): implement hybrid NLU provider (rules + TF-IDF) with pluggable factory
```

---

### Commit 3 — EntityResolver + Refactor NLUTool + Tests de integracin NLU↔NER

**Objetivo**: Migrar `TourismNLUTool` para delegar al service NLU, implementar `EntityResolver` con reglas explcitas, y verificar la integracin NLU+NER.

**Archivos a crear:**
- `business/domains/tourism/entity_resolver.py`
- `tests/test_business/test_entity_resolver.py`
- `tests/test_business/test_tourism_nlu_tool.py`

**Archivos a modificar:**
- `business/domains/tourism/tools/nlu_tool.py` (refactor: delega a NLUServiceInterface)
- `business/domains/tourism/tools/__init__.py` (export)
- `business/domains/tourism/agent.py` (paralelizacin NLU||NER, integrar EntityResolver)

**Refactor de `TourismNLUTool`:**

```python
class TourismNLUTool(BaseTool):
    """NLU tool that delegates to pluggable NLUServiceInterface."""

    name: str = "tourism_nlu"
    description: str = "Analyze user intent and extract tourism entities"
    nlu_service: Optional[NLUServiceInterface] = None

    def _get_nlu_service(self) -> NLUServiceInterface:
        if self.nlu_service is not None:
            return self.nlu_service
        from integration.external_apis.nlu_factory import NLUServiceFactory
        return NLUServiceFactory.create_from_settings()

    def _run(self, user_input: str) -> str:
        """Sync wrapper: runs async analyze_text via asyncio."""
        import asyncio
        import time

        start = time.perf_counter()
        service = self._get_nlu_service()
        result: NLUResult = asyncio.run(service.analyze_text(user_input))
        result.latency_ms = int((time.perf_counter() - start) * 1000)

        # Return as JSON string for LangChain tool protocol
        return result.model_dump_json(indent=2)

    async def _arun(self, user_input: str) -> str:
        """Async version."""
        import time

        start = time.perf_counter()
        service = self._get_nlu_service()
        result: NLUResult = await service.analyze_text(user_input)
        result.latency_ms = int((time.perf_counter() - start) * 1000)

        return result.model_dump_json(indent=2)
```

**Integracin en `TourismMultiAgent`:**

```python
# agent.py — cambio clave en _execute_pipeline

def _execute_pipeline(self, user_input, profile_context=None):
    import asyncio

    # 1. NLU + NER en paralelo
    nlu_result, ner_raw = asyncio.run(self._parallel_analysis(user_input))

    # 2. EntityResolver
    resolver = EntityResolver()
    resolved = resolver.resolve(
        nlu_result=nlu_result,
        ner_locations=ner_raw.get("locations", []),
        ner_top_location=ner_raw.get("top_location"),
    )

    # 3. Continue pipeline with resolved entities...
```

**Tests incluidos:**
- `test_entity_resolver.py`: Los 7 escenarios de la tabla de decisin. Edge cases: ambos None, NLU generic, fuzzy match. Verifica `conflicts` y `resolution_source`.
- `test_tourism_nlu_tool.py`: Mock de NLUServiceInterface. Verifica JSON output shape. Verifica fallback cuando service no disponible.

**Riesgos mitigados:** EntityResolver ad-hoc (ahora con reglas formales y tests). Backward compat (output JSON mantiene `intent` y `entities` keys).

**Validacin:**
```bash
poetry run ruff check business/
poetry run pytest tests/test_business/test_entity_resolver.py tests/test_business/test_tourism_nlu_tool.py -v
```

**Mensaje de commit:**
```
refactor(business): add EntityResolver, decouple TourismNLUTool from keyword patterns
```

---

### Commit 4 — Wiring DI + Feature flags + Shadow mode + API contract + Docs

**Objetivo**: Conectar todo al runtime, aadir feature flags granulares y shadow mode, actualizar docs.

**Archivos a crear:**
- (ninguno nuevo)

**Archivos a modificar:**
- `shared/utils/dependencies.py` (aadir `get_nlu_service()`)
- `application/orchestration/backend_adapter.py` (inyectar NLU service, shadow mode)
- `integration/configuration/settings.py` (aadir `nlu_shadow_mode`)
- `documentation/API_REFERENCE.md`
- `documentation/design/02_integration_layer_design.md`
- `documentation/design/03_business_layer_design.md`
- `documentation/DEVELOPMENT.md`

**Feature flags en settings:**

```python
# integration/configuration/settings.py — nuevos campos

# NLU settings
nlu_enabled: bool = Field(default=True, description="Enable NLU service")
nlu_provider: str = Field(default="spacy_rule_hybrid", description="NLU provider name")
nlu_default_language: str = Field(default="es", description="Default NLU language")
nlu_model_map: str = Field(
    default='{"es":"es_core_news_md","en":"en_core_web_sm"}',
    description="JSON mapping language->model for NLU",
)
nlu_confidence_threshold: float = Field(default=0.40, description="Min confidence for non-fallback")
nlu_fallback_intent: str = Field(default="general_query", description="Intent when confidence below threshold")
nlu_shadow_mode: bool = Field(
    default=False,
    description="Run new NLU in parallel with old keyword NLU, log differences, use old results",
)
```

**Shadow mode en backend_adapter:**

```python
# Cuando nlu_shadow_mode=True:
# 1. Ejecuta OLD keyword NLU (resultado usado para response)
# 2. Ejecuta NEW SpacyNLU en paralelo (resultado solo logeado)
# 3. Compara intents y logea diferencias

if self.settings.nlu_shadow_mode:
    old_result = old_nlu_tool._run(text)
    new_result = await new_nlu_service.analyze_text(text)

    if old_result_intent != new_result.intent:
        logger.info(
            "nlu_shadow_comparison",
            old_intent=old_result_intent,
            new_intent=new_result.intent,
            new_confidence=new_result.confidence,
            text_preview=text[:100],
            agreement=False,
        )

    # Use OLD result for actual response (safe rollout)
    return old_result
```

**DI wiring en dependencies.py:**

```python
def get_nlu_service(settings: Settings = Depends(get_settings)) -> NLUServiceInterface:
    """Dependency injection for NLU provider resolved through registry/factory."""
    if not settings.nlu_enabled:
        return None  # TourismNLUTool will use keyword fallback
    from integration.external_apis.nlu_factory import NLUServiceFactory
    return NLUServiceFactory.create_from_settings(settings)

def get_backend_adapter(settings: Settings = Depends(get_settings)) -> BackendInterface:
    ner_service = get_ner_service(settings)
    nlu_service = get_nlu_service(settings)
    return LocalBackendAdapter(settings, ner_service=ner_service, nlu_service=nlu_service)
```

**Validacin:**
```bash
poetry run ruff check .
# Smoke test endpoint
curl -s -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Content-Type: application/json" \
  -d '{"message":"Quiero una ruta accesible al Museo del Prado"}' | python -m json.tool
```

**Mensaje de commit:**
```
feat(application): wire NLU service via DI, add shadow mode and feature flags
```

---

### Commit 5 — Tests e2e + Corpus de evaluacin + Hardening

**Objetivo**: Cobertura e2e, corpus de evaluacin etiquetado, tests de performance, property-based testing.

**Archivos a crear:**
- `tests/test_application/test_chat_nlu_integration.py`
- `tests/test_business/test_tourism_agent_nlu_ner_merge.py`
- `tests/fixtures/nlu_evaluation_corpus.json`
- `tests/test_integration/test_nlu_evaluation.py`

**Archivos a modificar:**
- `tests/conftest.py` (aadir fixtures para NLU mock)

**Tests incluidos:**

1. **e2e API** (`test_chat_nlu_integration.py`):
   - Request real al endpoint `/api/v1/chat/message` con `use_real_agents=False`.
   - Verifica que response tiene `intent`, `entities`, `pipeline_steps` con NLU step.
   - Verifica backward compatibility: los campos existentes siguen presentes.

2. **Pipeline completo** (`test_tourism_agent_nlu_ner_merge.py`):
   - Mock de NLU service + mock de NER service.
   - Verifica que EntityResolver se ejecuta y sus resultados aparecen en metadata.
   - Verifica que tools downstream reciben datos resueltos.

3. **Corpus de evaluacin** (`nlu_evaluation_corpus.json` + `test_nlu_evaluation.py`):
   - 80+ ejemplos etiquetados (ver seccin 6).
   - Test que verifica accuracy > 85% en el corpus.
   - Test que reporta confusion matrix por intent.

4. **Property-based** (en `test_nlu_models.py`):
   - Para cualquier string input, `NLUResult` siempre tiene `intent` y `status`.
   - `confidence` siempre est en [0.0, 1.0].
   - `entities` nunca es None (puede ser empty `NLUEntitySet`).

**Validacin final:**
```bash
poetry run pytest tests/ -v --tb=short
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy shared/ integration/ business/ application/ --ignore-missing-imports
```

**Mensaje de commit:**
```
test: add e2e, evaluation corpus, and property-based tests for NLU pipeline
```

---

## 6. TESTING & EVALUATION STRATEGY

### 6.1 Dataset mnimo etiquetado

El archivo `tests/fixtures/nlu_evaluation_corpus.json` contiene 80+ ejemplos:

```json
[
  {
    "text": "Quiero una ruta accesible al Museo del Prado",
    "expected_intent": "route_planning",
    "expected_entities": {"destination": "Museo del Prado", "accessibility": "wheelchair"},
    "language": "es",
    "category": "happy_path"
  },
  {
    "text": "Dnde puedo cenar cerca del Retiro?",
    "expected_intent": "restaurant_search",
    "expected_entities": {"destination": "Parque del Retiro"},
    "language": "es",
    "category": "happy_path"
  },
  {
    "text": "Hola, qu tal?",
    "expected_intent": "general_query",
    "expected_entities": {},
    "language": "es",
    "category": "edge_case"
  },
  {
    "text": "I want to visit the Prado Museum",
    "expected_intent": "route_planning",
    "expected_entities": {"destination": "Museo del Prado"},
    "language": "en",
    "category": "english"
  },
  {
    "text": "Quiero visitar el Prado y luego cenar cerca",
    "expected_intent": "route_planning",
    "expected_entities": {"destination": "Museo del Prado"},
    "language": "es",
    "category": "multi_intent"
  }
]
```

**Distribucin mnima:**
- 20 route_planning (ES)
- 15 event_search (ES)
- 10 restaurant_search (ES)
- 10 accommodation_search (ES)
- 10 general_query (ES)
- 5 multi-intent (ES)
- 5 edge cases (empty, gibberish, injection)
- 5 English

### 6.2 Mtricas de xito

| Mtrica | Baseline (keyword) | Target (NLU v2) |
|---|---|---|
| Intent accuracy (corpus) | Medido en Commit 5 | > 85% |
| Entity extraction F1 | Medido en Commit 5 | > 80% |
| Fallback rate | Medido en Commit 5 | < 20% |
| Latencia p50 NLU | N/A | < 25ms |
| Latencia p95 NLU | N/A | < 50ms |

### 6.3 Test de evaluacin automatizada

```python
# tests/test_integration/test_nlu_evaluation.py

@pytest.mark.integration
def test_nlu_intent_accuracy_above_threshold():
    """NLU must achieve >85% intent accuracy on evaluation corpus."""
    corpus = load_evaluation_corpus()
    service = SpacyNLUService(settings=test_settings)

    correct = 0
    total = 0
    mismatches = []

    for example in corpus:
        result = asyncio.run(service.analyze_text(example["text"], language=example["language"]))
        total += 1
        if result.intent == example["expected_intent"]:
            correct += 1
        else:
            mismatches.append({
                "text": example["text"],
                "expected": example["expected_intent"],
                "got": result.intent,
                "confidence": result.confidence,
            })

    accuracy = correct / total

    # Log mismatches for debugging
    if mismatches:
        for m in mismatches:
            logger.warning("nlu_eval_mismatch", **m)

    assert accuracy >= 0.85, (
        f"NLU accuracy {accuracy:.2%} below 85% threshold. "
        f"Mismatches: {len(mismatches)}/{total}"
    )
```

### 6.4 Property-based testing

```python
# tests/test_shared/test_nlu_models.py

from hypothesis import given, strategies as st

@given(st.text(min_size=0, max_size=500))
def test_nlu_result_always_valid_for_any_input(text):
    """NLUResult construction never raises for valid field ranges."""
    result = NLUResult(
        intent="general_query",
        confidence=0.5,
        status="ok",
    )
    assert result.intent is not None
    assert 0.0 <= result.confidence <= 1.0
    assert result.status in ("ok", "fallback", "error")

@given(st.floats(min_value=-100, max_value=100))
def test_confidence_clamped_to_valid_range(value):
    """Confidence outside [0,1] must raise ValidationError."""
    if 0.0 <= value <= 1.0:
        NLUResult(confidence=value)  # should pass
    else:
        with pytest.raises(ValidationError):
            NLUResult(confidence=value)
```

---

## 7. OBSERVABILIDAD Y OPERACIN

### 7.1 Logs estructurados (structlog)

Cada invocacin de NLU emite un log con campos fijos:

```python
logger.info(
    "nlu_analysis_complete",
    provider=result.provider,
    model=result.model,
    language=result.language,
    intent=result.intent,
    confidence=result.confidence,
    status=result.status,
    entity_count=len([v for v in result.entities.model_dump().values() if v]),
    latency_ms=result.latency_ms,
    classification_layer="rules" | "similarity" | "keyword_fallback",
    fallback_reason=fallback_reason,  # None if status=ok
)
```

### 7.2 Mtricas expuestas (Prometheus-style via logs)

Estas mtricas se calculan de los logs estructurados. En un entorno de produccin se exportaran va `prometheus_client` o similar. Por ahora, el log es la fuente.

| Mtrica | Tipo | Labels |
|---|---|---|
| `nlu_requests_total` | Counter | `provider`, `language`, `status` |
| `nlu_intent_total` | Counter | `intent`, `classification_layer` |
| `nlu_latency_ms` | Histogram | `provider`, `language` |
| `nlu_confidence` | Histogram | `intent` |
| `nlu_fallback_total` | Counter | `fallback_reason` |
| `entity_resolver_conflicts_total` | Counter | `resolution_source` |

### 7.3 Correlation IDs

Cada request a `/api/v1/chat/message` genera un `request_id` (UUID) que se propaga a:
- NLU log
- NER log
- EntityResolver log
- Pipeline steps metadata

```python
# En backend_adapter.py
import uuid

request_id = str(uuid.uuid4())
structlog.contextvars.bind_contextvars(request_id=request_id)
```

### 7.4 Shadow mode (detalle operativo)

| Configuracin | Comportamiento |
|---|---|
| `nlu_enabled=true, nlu_shadow_mode=false` | NLU nueva activa, keyword desactivado |
| `nlu_enabled=true, nlu_shadow_mode=true` | Ambas ejecutan, keyword provee resultado, NLU nueva solo se logea |
| `nlu_enabled=false` | Keyword NLU original (sin cambios) |

**Log de shadow comparison:**
```python
logger.info(
    "nlu_shadow_comparison",
    request_id=request_id,
    old_intent=old_intent,
    new_intent=new_result.intent,
    new_confidence=new_result.confidence,
    agreement=(old_intent == new_result.intent),
    text_preview=text[:100],
)
```

### 7.5 Feature flags granulares

| Flag | Default | Efecto |
|---|---|---|
| `VOICEFLOW_NLU_ENABLED` | `true` | Kill switch completo |
| `VOICEFLOW_NLU_SHADOW_MODE` | `false` | Shadow comparison mode |
| `VOICEFLOW_NLU_PROVIDER` | `spacy_rule_hybrid` | Seleccin de provider |
| `VOICEFLOW_NLU_CONFIDENCE_THRESHOLD` | `0.40` | Umbral para fallback |
| `VOICEFLOW_NLU_FALLBACK_INTENT` | `general_query` | Intent por defecto en fallback |

---

## 8. ESTRATEGIA DE ROLLBACK

### 8.1 Fases de rollout

```
Fase 0: nlu_enabled=false (estado actual, keyword matching)
   |
   v
Fase 1: nlu_enabled=true, nlu_shadow_mode=true
   - NLU nueva corre en paralelo pero no afecta resultado
   - Analizar logs de shadow comparison durante 24-48h
   - Validar: agreement rate > 80%, latency < 50ms p95
   |
   v
Fase 2: nlu_enabled=true, nlu_shadow_mode=false
   - NLU nueva provee resultado real
   - Monitorear fallback rate, latencia, errores
   - Mantener keyword fallback activo internamente
   |
   v
Fase 3: Eliminar keyword NLU legacy (commit futuro)
   - Solo cuando NLU v2 es estable por 1+ semanas
```

### 8.2 Rollback instantneo

En cualquier momento:
```bash
# Rollback a keyword matching
export VOICEFLOW_NLU_ENABLED=false
# O rollback a shadow mode
export VOICEFLOW_NLU_SHADOW_MODE=true
```

Sin redeploy de cdigo. Solo cambio de variable de entorno + restart del container.

### 8.3 Auditabilidad por request

Cada response incluye en `metadata.tool_outputs.nlu`:
```json
{
  "provider": "spacy_rule_hybrid",
  "model": "es_core_news_md",
  "analysis_version": "nlu_v2.0",
  "classification_layer": "rules",
  "latency_ms": 23
}
```

Esto permite auditar post-hoc qu versin proces cada request.

---

## 9. GOBERNANZA Y VERSIONADO DE MODELOS

### 9.1 Versionado semntico

| Componente | Formato | Ejemplo | Cundo se incrementa |
|---|---|---|---|
| `analysis_version` | `nlu_vMAJOR.MINOR` | `nlu_v2.0` | MAJOR: cambio de taxonoma de intents. MINOR: ajuste de patterns/corpus |
| Modelo spaCy | Fijado en `pyproject.toml` | `spacy>=3.7,<3.8` | Solo con PR explcito + tests de regresin |
| Taxonoma de intents | Lista en `nlu_reference_corpus.py` | 5 intents definidos | Solo con PR + actualizacin de corpus de evaluacin |

### 9.2 Poltica de actualizacin

1. **Agregar nuevo intent**: Requiere PR con (a) nuevos patterns en Matcher, (b) nuevas frases en corpus TF-IDF, (c) 10+ ejemplos en corpus de evaluacin, (d) tests actualizados, (e) `analysis_version` minor bump.
2. **Cambiar modelo spaCy**: Requiere PR con (a) bump en `pyproject.toml`, (b) run completo de corpus de evaluacin, (c) comparacin de accuracy antes/despus.
3. **Modificar EntityResolver rules**: Requiere PR con (a) nuevos test cases en tabla de decisin, (b) log review de conflictos existentes.

### 9.3 Taxonoma de intents (v2.0)

| Intent | Descripcin | Ejemplo |
|---|---|---|
| `route_planning` | Usuario quiere llegar a un lugar | "Cmo llego al Prado?" |
| `event_search` | Usuario busca eventos/actividades | "Qu conciertos hay este finde?" |
| `restaurant_search` | Usuario busca dnde comer | "Restaurante accesible cerca del centro" |
| `accommodation_search` | Usuario busca alojamiento | "Hotel con accesibilidad en Madrid" |
| `general_query` | Consulta genrica o no clasificable | "Qu me recomiendas?" |

**Intents NO incluidos en v2.0** (candidatos para v2.1):
- `weather_query`
- `emergency_info`
- `transport_status`

---

## 10. IMPACTO OPERATIVO

### 10.1 Memoria estimada

| Componente | Memoria | Notas |
|---|---|---|
| `es_core_news_md` (NER + NLU compartido) | ~50 MB | Se carga 1 vez, shared entre NER y NLU |
| `en_core_web_sm` (si se usa) | ~12 MB | Lazy load, solo si hay requests EN |
| TF-IDF matrix (500 features, ~15 docs) | < 1 MB | Pre-computada en init |
| Matcher patterns | < 1 MB | En memoria |
| **Total incremental vs actual** | **< 2 MB** | El modelo spaCy ya est cargado por NER |

**Clave:** NLU reutiliza el mismo modelo spaCy que NER. No se duplica la carga de `es_core_news_md`. Se comparte va cach de modelos.

### 10.2 Latencia estimada

| Operacin | Estimacin | Notas |
|---|---|---|
| spaCy `nlp(text)` (modelo ya en cach) | 5-15ms | Depende de longitud de texto |
| Matcher patterns | 1-3ms | Determinista, O(patterns * tokens) |
| TF-IDF transform + cosine similarity | 1-2ms | Matrix pequea (~15 docs) |
| Entity extraction | 2-5ms | Patterns + NER entities del doc |
| **Total NLU p50** | **10-25ms** | |
| **Total NLU p95** | **25-50ms** | Textos largos o primer request |
| **Cold start (carga modelo)** | **2-4s** | Solo primera request tras deploy |

**Optimizacin del cold start:** Pre-cargar el modelo en `initialize_services()` al startup de la app:

```python
# shared/utils/dependencies.py
async def initialize_services():
    # ... existing code ...
    # Pre-warm NLU model
    nlu_service = get_nlu_service(settings)
    if nlu_service and nlu_service.is_service_available():
        await nlu_service.analyze_text("warmup", language=settings.nlu_default_language)
        logger.info("NLU model pre-warmed")
```

### 10.3 Impacto en Docker build

| Cambio | Impacto en build time |
|---|---|
| spaCy models | **0 segundos adicionales** — se reutiliza `es_core_news_md` ya descargado para NER |
| scikit-learn | **+15-30 segundos** — nueva dependencia pip (ya incluye numpy como dep transitiva de spaCy) |
| Archivos Python nuevos | Despreciable |

**Accin necesaria:** Verificar que `pyproject.toml` ya tiene `scikit-learn` como dependencia o aadirlo. NO se necesita cambiar el `Dockerfile` ni el `ARG SPACY_MODELS`.

### 10.4 Concurrencia

- `SpacyNLUService.analyze_text()` es **async** va `run_in_executor()`.
- spaCy `nlp()` es thread-safe para read-only inference (no modifica el modelo).
- TF-IDF vectorizer es read-only despus de `fit_transform()` en init.
- Matcher es read-only despus de `add()` en init.
- **Conclusin:** Safe para concurrencia sin locks adicionales.

### 10.5 Caching

En esta iteracin: **no se implementa cach de resultados NLU.**

**Justificacin:** La latencia estimada (10-25ms p50) es suficientemente baja para no justificar la complejidad de un cach (invalidacin, keys, memoria). Se recomienda evaluar en v2.1 si la latencia real excede los SLOs.

---

## 11. PLAN DE EJECUCIN FINAL

### 11.1 Roadmap por fases

| Fase | Commits | Duracin estimada | Entregable |
|---|---|---|---|
| **Fase 1: Fundamentos** | Commit 1 | 1 sesin | Contratos + settings + tests |
| **Fase 2: Core NLU** | Commit 2 | 1-2 sesiones | Provider funcional + factory + tests |
| **Fase 3: Integracin** | Commit 3 | 1-2 sesiones | EntityResolver + pipeline refactored + tests |
| **Fase 4: Wiring** | Commit 4 | 1 sesin | DI + shadow mode + docs |
| **Fase 5: Validacin** | Commit 5 | 1-2 sesiones | Corpus eval + e2e + hardening |
| **Fase 6: Rollout** | Post-merge | 24-48h observacin | Shadow mode → activacin |

### 11.2 Riesgos residuales

| Riesgo | Probabilidad | Mitigacin |
|---|---|---|
| Accuracy < 85% en corpus real | Media | Iterar patterns/corpus antes de merge. Ajustar threshold. |
| Latencia > 50ms p95 | Baja | Modelo ya est cargado por NER; el overhead incremental es mnimo. |
| TF-IDF similarity pobre para ES | Media | Los patterns de Layer 1 cubren los casos ms comunes; Layer 2 es fallback. |
| scikit-learn dependency conflicts | Baja | numpy ya es dep transitiva de spaCy; scikit-learn es compatible. |

### 11.3 Criterios de "Ready for Production"

- [ ] Los 5 commits mergeados en `feature/nlu-tool-implementation`.
- [ ] `poetry run pytest tests/ -v` — 100% passing.
- [ ] `poetry run ruff check . && poetry run ruff format --check .` — clean.
- [ ] Corpus de evaluacin: accuracy > 85%.
- [ ] Latencia NLU p95 < 50ms (medida en tests de integracin).
- [ ] Shadow mode ejecutado 24h+ sin errores.
- [ ] Shadow comparison: agreement rate > 80% con keyword NLU.
- [ ] Documentacin actualizada (`API_REFERENCE.md`, `DEVELOPMENT.md`).
- [ ] Feature flag `nlu_shadow_mode` documentado en `.env.example`.
- [ ] EntityResolver: 0 conflictos no resueltos en logs de shadow mode.

---

## Apndice A: Comandos rpidos

```bash
# Lint completo
poetry run ruff check . && poetry run ruff format --check .

# Tests por capa
poetry run pytest tests/test_shared/ -v -m unit
poetry run pytest tests/test_integration/ -v -m integration
poetry run pytest tests/test_business/ -v
poetry run pytest tests/test_application/ -v

# Evaluacin de accuracy
poetry run pytest tests/test_integration/test_nlu_evaluation.py -v -s

# Type check
poetry run mypy shared/ integration/ business/ application/ --ignore-missing-imports

# Smoke test API
curl -s -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Content-Type: application/json" \
  -d '{"message":"Quiero una ruta accesible al Museo del Prado"}' \
  | python -m json.tool

# Verificar shadow mode logs
docker compose logs app | grep "nlu_shadow_comparison" | tail -20
```

## Apndice B: Dependencias a aadir

```toml
# pyproject.toml
[tool.poetry.dependencies]
scikit-learn = "^1.4"
# spaCy ya est presente; no se necesitan modelos adicionales
```

## Apndice C: Variables de entorno (.env.example)

```bash
# NLU Configuration
VOICEFLOW_NLU_ENABLED=true
VOICEFLOW_NLU_PROVIDER=spacy_rule_hybrid
VOICEFLOW_NLU_DEFAULT_LANGUAGE=es
VOICEFLOW_NLU_MODEL_MAP={"es":"es_core_news_md","en":"en_core_web_sm"}
VOICEFLOW_NLU_CONFIDENCE_THRESHOLD=0.40
VOICEFLOW_NLU_FALLBACK_INTENT=general_query
VOICEFLOW_NLU_SHADOW_MODE=false
```
