# Specs — User Current Location (GPS) in Pipeline

**Fecha:** 2026-03-10
**Estado:** DRAFT — listo para implementación
**Objetivo:** Permitir que el usuario envíe sus coordenadas GPS reales, que fluyan de forma transparente por todo el sistema y sean usadas por `DirectionsTool` (origen del viaje) y `OverpassAccessibilityService` (radio de búsqueda), manteniendo el mismo contrato de datos que cualquier otra localización.

---

## 1. Motivación y alcance

El sistema ya tiene `GeocodingServiceInterface` con `reverse_geocode()` y `ToolPipelineContext` con `profile_context`. El origen de las rutas en `DirectionsTool` se resuelve hoy con:

```python
# directions_tool.py:66-69
@staticmethod
def _resolve_origin(ctx: ToolPipelineContext) -> str:
    if ctx.profile_context:
        return ctx.profile_context.get("location", "Madrid centro")
    return "Madrid centro"
```

**El problema:** `"Madrid centro"` es siempre el origen de ruta, independientemente de dónde esté físicamente el usuario. Para una app de turismo accesible, el origen real cambia el tiempo estimado, el transporte disponible y la ruta wheelchair.

**El límite de esta fase:** Solo el frontend envía GPS. No se implementa geofencing, tracking continuo ni actualización automática. Una sola posición por sesión/request.

---

## 2. Diseño de la solución

### Principio guía
> Las coordenadas GPS del usuario siguen **exactamente el mismo flujo** que cualquier otra localización: se convierten a `GeocodedLocation` y se almacenan en `ToolPipelineContext`. El resto del pipeline no distingue si el origen fue GPS, texto libre o perfil.

### Flujo de datos end-to-end

```
Browser GPS API
    │ {latitude, longitude, accuracy}
    ▼
ChatMessageRequest.user_location (nuevo campo)
    │ UserLocationInput(latitude, longitude, accuracy)
    ▼
BackendAdapter.process_query(transcription, user_location=...)
    │ GeocodingService.reverse_geocode(lat, lng)  → GeocodedLocation
    ▼
profile_context["user_location_geocoded"] = GeocodedLocation
    │
    ▼
ToolPipelineContext.user_location (nuevo campo Optional[GeocodedLocation])
    │
    ├── DirectionsTool._resolve_origin()  → usa lat/lng directos (sin re-geocodificar)
    └── OverpassAccessibilityService._resolve_coordinates() → lat/lng directos
```

---

## 3. Modelo de datos

### 3.1 Nuevo modelo de input

**Archivo:** `application/models/requests.py`

```python
class UserLocationInput(BaseModel):
    """GPS coordinates sent by the frontend (device Geolocation API)."""

    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    accuracy_meters: Optional[float] = Field(
        default=None, ge=0.0,
        description="Horizontal accuracy in meters from device GPS. "
                    "Used to assess reliability: >100m = low confidence."
    )
    source: str = Field(
        default="device_gps",
        description="Origin of coordinates: 'device_gps' | 'manual_input' | 'ip_geolocation'"
    )
```

### 3.2 Extender `ChatMessageRequest`

**Archivo:** `application/models/requests.py` — clase existente `ChatMessageRequest`

```python
class ChatMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None
    user_preferences: Optional[UserPreferences] = None
    user_location: Optional[UserLocationInput] = None  # ← NUEVO
```

**Sin romper compatibilidad:** `user_location=None` es el estado por defecto. Todos los clientes actuales siguen funcionando.

### 3.3 Extender `ToolPipelineContext`

**Archivo:** `shared/models/tool_models.py` — clase existente

```python
class ToolPipelineContext(BaseModel):
    user_input: str
    language: str = "es"
    profile_context: Optional[dict[str, Any]] = None

    # NEW: resolved GPS origin of the user (already geocoded)
    user_location: Optional[GeocodedLocation] = None

    # Stage 1: NLU + NER
    nlu_result: Optional[NLUResult] = None
    ...
```

`GeocodedLocation` ya existe en `shared/models/tool_models.py` desde la implementación del geocoding service. No se añade ninguna nueva dependencia.

---

## 4. Cambios por capa

### 4.1 Presentation — Frontend

**Archivo:** `presentation/static/js/app.js` (o equivalente)

```javascript
// Nuevo: solicitar GPS antes de enviar el mensaje
async function getUserLocation() {
    return new Promise((resolve) => {
        if (!navigator.geolocation) {
            resolve(null);
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (pos) => resolve({
                latitude: pos.coords.latitude,
                longitude: pos.coords.longitude,
                accuracy_meters: pos.coords.accuracy,
                source: "device_gps"
            }),
            () => resolve(null),          // Permiso denegado → null (graceful)
            { timeout: 5000, maximumAge: 60000 }  // Cache 1 min, timeout 5s
        );
    });
}

// En sendMessage() / handleAudioSubmit():
const userLocation = await getUserLocation();

const payload = {
    message: transcription,
    user_preferences: { active_profile_id: activeProfileId },
    user_location: userLocation   // null si GPS no disponible
};
```

**Consideraciones UX:**
- El permiso GPS debe pedirse al inicio de la sesión, no en cada mensaje.
- Si el usuario deniega el permiso → `user_location = null` → el sistema usa "Madrid centro" como antes.
- `maximumAge: 60000` evita requests repetidos al GPS físico dentro de la misma sesión.

**Feature flag frontend** (opcional, recomendado):
```javascript
const GPS_ENABLED = window.VOICEFLOW_CONFIG?.gpsEnabled ?? false;
const userLocation = GPS_ENABLED ? await getUserLocation() : null;
```

---

### 4.2 Application — API Route

**Archivo:** `application/api/chat.py` (o equivalente donde se manejan los requests)

El endpoint de chat ya recibe `ChatMessageRequest`. Solo hay que pasar el nuevo campo:

```python
@router.post("/chat")
async def chat_endpoint(
    request: ChatMessageRequest,
    backend: BackendInterface = Depends(get_backend_adapter),
):
    profile_id = request.user_preferences.active_profile_id if request.user_preferences else None
    response = await backend.process_query(
        transcription=request.message,
        active_profile_id=profile_id,
        user_location=request.user_location,   # ← NUEVO parámetro
    )
    return response
```

---

### 4.3 Application — BackendAdapter

**Archivo:** `application/orchestration/backend_adapter.py`

#### 4.3.1 Actualizar la firma de `process_query`

```python
async def process_query(
    self,
    transcription: str,
    active_profile_id: Optional[str] = None,
    user_location: Optional["UserLocationInput"] = None,  # ← NUEVO
) -> Dict[str, Any]:
```

#### 4.3.2 Resolver GPS → `GeocodedLocation`

```python
# Dentro de process_query, antes de llamar al agente:
resolved_user_location: Optional[GeocodedLocation] = None

if user_location is not None:
    try:
        from integration.external_apis.geocoding_factory import GeocodingServiceFactory
        geo_svc = GeocodingServiceFactory.create_from_settings(settings=self.settings)
        resolved_user_location = await geo_svc.reverse_geocode(
            latitude=user_location.latitude,
            longitude=user_location.longitude,
            language="es",
        )
        logger.info(
            "user_location_resolved",
            lat=user_location.latitude,
            lng=user_location.longitude,
            accuracy=user_location.accuracy_meters,
            formatted_address=resolved_user_location.formatted_address,
        )
    except Exception as exc:
        logger.warning("user_location_resolution_failed", error=str(exc))
        # Degradación silenciosa: continúa sin GPS
```

> **Nota de implementación:** El geocoding service ya está creado en `_get_backend_instance()`. Extraerlo como atributo de instancia (`self._geocoding_service`) evita recrearlo en cada request.

#### 4.3.3 Pasar a `_process_real_query`

```python
ai_response = await self._process_real_query(
    transcription,
    profile_context=profile_context,
    user_location=resolved_user_location,  # ← NUEVO
)
```

#### 4.3.4 Pasar al agente

```python
async def _process_real_query(
    self,
    transcription: str,
    profile_context: Optional[Dict[str, Any]] = None,
    user_location: Optional[GeocodedLocation] = None,  # ← NUEVO
) -> str:
    agent = await self._get_backend_instance()
    result = await agent.process_request(
        transcription,
        profile_context=profile_context,
        user_location=user_location,  # ← NUEVO
    )
    return result
```

---

### 4.4 Business — TourismMultiAgent

**Archivo:** `business/domains/tourism/agent.py`

#### 4.4.1 Actualizar `process_request`

```python
async def process_request(
    self,
    user_input: str,
    profile_context: Optional[dict] = None,
    user_location: Optional[GeocodedLocation] = None,  # ← NUEVO
) -> str:
    ...
    return await self._execute_pipeline_async(
        user_input,
        profile_context=profile_context,
        user_location=user_location,
    )
```

#### 4.4.2 Inyectar en `ToolPipelineContext`

```python
async def _execute_pipeline_async(
    self,
    user_input: str,
    profile_context: Optional[dict] = None,
    user_location: Optional[GeocodedLocation] = None,  # ← NUEVO
) -> str:
    ...
    ctx = ToolPipelineContext(
        user_input=user_input,
        language="es",
        profile_context=profile_context,
        user_location=user_location,   # ← NUEVO
    )
    ...
```

---

### 4.5 Business — DirectionsTool

**Archivo:** `business/domains/tourism/tools/directions_tool.py`

Este es el cambio más relevante para el usuario: el origen real en vez de "Madrid centro".

```python
@staticmethod
def _resolve_origin(ctx: ToolPipelineContext) -> str:
    # Priority 1: GPS coordinates from user device → use formatted_address directly
    # (ORS will geocode this address back to coords via GeocodingService)
    if ctx.user_location and ctx.user_location.confidence >= 0.5:
        addr = ctx.user_location.formatted_address
        if addr and addr not in ("", "Madrid, España"):
            return addr

    # Priority 2: Profile-level location (e.g. "Barrio de Salamanca, Madrid")
    if ctx.profile_context:
        return ctx.profile_context.get("location", "Madrid centro")

    return "Madrid centro"
```

**Alternativa más eficiente** (evita re-geocodificar algo que ya tenemos en coordenadas):

Dado que `OpenRouteDirectionsService._resolve_coords()` llamará al geocoding service con el address resultante, y `OverpassAccessibilityService` también lo hará, es más limpio pasar las coordenadas **directamente** a través del contexto. Se puede hacer añadiendo un helper en `DirectionsTool`:

```python
@staticmethod
def _resolve_origin_coords(ctx: ToolPipelineContext) -> Optional[tuple[float, float]]:
    """Return raw GPS coords for the user's current location if available.

    When present, ORS and Overpass can use these directly without a geocoding round-trip.
    """
    if ctx.user_location and ctx.user_location.confidence >= 0.5:
        return (ctx.user_location.latitude, ctx.user_location.longitude)
    return None
```

Y en `execute()`:

```python
routes = await self._service.get_directions(
    origin=origin,
    destination=destination,
    mode="transit",
    accessibility_profile=accessibility_profile,
    language=ctx.language,
    origin_coords=self._resolve_origin_coords(ctx),  # ← NUEVO hint
)
```

Para usar esto, `DirectionsServiceInterface.get_directions()` necesita un parámetro opcional `origin_coords: Optional[tuple[float, float]] = None` y `OpenRouteDirectionsService._resolve_coords()` priorizaría las coords directas.

> **Recomendación:** Implementar primero el enfoque de `formatted_address` (más simple, no cambia la interface). Añadir `origin_coords` hint como optimización en una segunda iteración.

---

### 4.6 Integration — OverpassAccessibilityService

`OverpassAccessibilityService._resolve_coordinates()` ya tiene la lógica correcta:

```python
async def _resolve_coordinates(self, location, latitude, longitude, language):
    # Priority 1: Explicit lat/lng → ya soportado
    if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
        return (float(latitude), float(longitude))
    # Priority 2: Geocoding service lookup → ya soportado
    ...
```

El cambio está en **`AccessibilityEnrichmentTool`**, que debe pasar las coords del usuario cuando el lugar de búsqueda es la posición actual:

```python
# accessibility_enrichment_tool.py — método execute()
routes = await self._service.enrich_accessibility(
    place_name=place_name,
    place_id=place_id,
    location=location,
    latitude=ctx.place.location_lat if ctx.place else None,
    longitude=ctx.place.location_lng if ctx.place else None,
    language=ctx.language,
)
```

Esto ya funciona para el destino. Para búsquedas de accesibilidad centradas en el **usuario** (ej. "¿qué hay accesible cerca de mí?"), el tool debería usar `ctx.user_location`:

```python
# Si no hay un lugar específico pero sí hay GPS del usuario:
if not place_name and ctx.user_location:
    latitude = ctx.user_location.latitude
    longitude = ctx.user_location.longitude
    place_name = ctx.user_location.formatted_address or "Ubicación actual"
```

---

## 5. Gestión del geocoding service en BackendAdapter

Actualmente el geocoding service se crea dentro de `_get_backend_instance()` (lazy, en la primera request). Para `user_location`, se necesita en `process_query()`. La solución correcta es promoverlo a atributo de instancia:

```python
class LocalBackendAdapter(BackendInterface):
    def __init__(self, ...):
        ...
        self._geocoding_service: Optional[GeocodingServiceInterface] = None

    async def _get_geocoding_service(self) -> GeocodingServiceInterface:
        """Lazy-init geocoding service (independent of full backend init)."""
        if self._geocoding_service is None:
            from integration.external_apis.geocoding_factory import GeocodingServiceFactory
            self._geocoding_service = GeocodingServiceFactory.create_from_settings(
                settings=self.settings
            )
        return self._geocoding_service
```

Luego en `_get_backend_instance()` reusar `self._geocoding_service` en vez de crear uno nuevo.

---

## 6. Feature flag

**Añadir a `integration/configuration/settings.py`:**

```python
gps_user_location_enabled: bool = Field(
    default=True,
    description="Accept GPS coordinates from frontend and use them as route origin. "
                "Set to False to always use profile/default location.",
)
```

**Uso en BackendAdapter:**

```python
if user_location is not None and self.settings.gps_user_location_enabled:
    resolved_user_location = await ...
```

---

## 7. Consideraciones de seguridad y privacidad

| Riesgo | Mitigación |
|---|---|
| Coordenadas GPS en logs | Loguear solo con precision reducida (2 decimales ≈ 1km) |
| GPS injection (coords manipuladas) | Validación de rango Pydantic (`ge=-90, le=90`) — ya cubierto en `UserLocationInput` |
| Almacenamiento de posición | No persistir `user_location` en conversación history |
| Consentimiento usuario | El permiso lo gestiona el browser (`navigator.geolocation`) — fuera del scope backend |
| Accuracy baja (>100m) | `accuracy_meters` disponible para que el sistema advierta al usuario |

---

## 8. Tests requeridos

### Unit tests

| Test | Archivo sugerido |
|---|---|
| `UserLocationInput` — validación de coordenadas fuera de rango | `test_shared/test_request_models.py` |
| `DirectionsTool._resolve_origin` con `ctx.user_location` presente | `test_business/test_directions_tool.py` |
| `DirectionsTool._resolve_origin` sin GPS → fallback a profile → fallback a default | ídem |
| `ToolPipelineContext` — serialización round-trip con `user_location` | `test_shared/test_tool_models.py` |

### Integration tests

| Test | Archivo sugerido |
|---|---|
| `BackendAdapter.process_query` con `user_location` → `resolved_user_location` en pipeline | `test_integration/test_backend_adapter_gps.py` |
| `BackendAdapter.process_query` con `user_location=None` → comportamiento idéntico al actual | ídem |
| `BackendAdapter.process_query` con GPS y `gps_user_location_enabled=False` → GPS ignorado | ídem |
| `reverse_geocode` falla → degradación silenciosa, pipeline continúa | ídem |

### E2E / smoke

- Request HTTP con `user_location` → respuesta con tiempo de ruta desde GPS (verificar en `raw_tool_results["routes"]`)
- Request HTTP sin `user_location` → comportamiento idéntico al estado actual

---

## 9. Plan de implementación (orden sugerido)

| Step | Cambio | Archivo(s) | Esfuerzo |
|---|---|---|---|
| 1 | `UserLocationInput` model | `application/models/requests.py` | 15 min |
| 2 | `ChatMessageRequest.user_location` field | ídem | 5 min |
| 3 | `ToolPipelineContext.user_location` field | `shared/models/tool_models.py` | 5 min |
| 4 | `gps_user_location_enabled` setting | `integration/configuration/settings.py` | 5 min |
| 5 | `BackendAdapter._get_geocoding_service()` lazy init | `application/orchestration/backend_adapter.py` | 20 min |
| 6 | `BackendAdapter.process_query` — resolver GPS | ídem | 30 min |
| 7 | `BackendAdapter._process_real_query` — pasar a agente | ídem | 10 min |
| 8 | `TourismMultiAgent.process_request` — pasar a pipeline | `business/domains/tourism/agent.py` | 15 min |
| 9 | `DirectionsTool._resolve_origin` — priorizar GPS | `business/domains/tourism/tools/directions_tool.py` | 20 min |
| 10 | Frontend GPS API integration | `presentation/static/js/app.js` | 45 min |
| 11 | Tests (unit + integration) | varios | 90 min |
| **Total** | | | **~4h** |

---

## 10. Criterios de aceptación (DoD)

- [ ] Frontend obtiene GPS y lo envía en el request (permiso denegado → funciona sin GPS)
- [ ] `ChatMessageRequest` acepta y valida `user_location` correctamente
- [ ] Las coordenadas GPS se resuelven a `GeocodedLocation` vía `reverse_geocode`
- [ ] `DirectionsTool` usa el `formatted_address` del GPS como origen en lugar de "Madrid centro"
- [ ] Si GPS no disponible → comportamiento idéntico al estado actual (sin regresión)
- [ ] `gps_user_location_enabled=False` desactiva toda la feature sin tocar código
- [ ] Las coordenadas GPS no aparecen literales en logs de producción (máx. 2 decimales)
- [ ] Tests pasan: unit (models + directions_tool) + integration (backend_adapter) + suite completa sin regresión
- [ ] El campo `source: "device_gps"` está presente en `user_location.source` en el contexto del pipeline

---

## 11. Decisiones pendientes (fuera de scope de esta fase)

| Decisión | Opciones | Recomendación |
|---|---|---|
| Mostrar al usuario "Usando tu ubicación actual" | UI badge en frontend | Sencillo con el campo `source` |
| Persistir GPS por sesión (no re-pedir en cada mensaje) | Session storage frontend | Frontend only, no afecta backend |
| Soporte multi-location (X→Z→Y desde GPS) | `ctx.waypoints: list[GeocodedLocation]` en pipeline | Fase posterior |
| Geocoding inverso con Google Maps API | Añadir `GoogleGeocodingService` a la factory | Fase posterior, mejor calidad en ES |
