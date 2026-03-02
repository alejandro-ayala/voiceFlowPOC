# Spec: User Preference Profiles & Agent Specialization (F3)

**Contexto:** VoiceFlow PoC — Sistema de Turismo Accesible
**Objetivo:** Añadir una **página modal de configuración** para seleccionar un **perfil activo** que **especializa (ranking/bias)** las respuestas del sistema multi-agente (LangChain), de forma **metadata-driven** y **escalable** (sin cambios de código o mínimo) con persistencia inicial en **LocalStorage** y futura en **BBDD**.
**Actualizado:** 2026-02-17 — Propuesta SDD (pre-implementación)

> ⚠️ **Propuesta pre-implementación (histórica).**
> Este documento contiene decisiones de diseño y alcance, no el contrato operativo final de API.
> Para comportamiento y payload vigente del sistema, consultar `documentation/API_REFERENCE.md` y `documentation/ESTADO_ACTUAL_SISTEMA.md`.

---

## 0. Principios SDD y Reglas

1. **SSOT de configuración:** Los perfiles se definen en un **Profile Registry** (JSON) como fuente de verdad.
2. **No rompe comportamiento actual:** Si no hay perfil configurado, el sistema opera como hoy.
3. **Un perfil activo:** Siempre 0..1 perfil activo por sesión (hasta que el usuario lo cambie).
4. **No bloquea, solo prioriza:** El perfil **solo influye en ranking/selección de opciones**, no filtra ni censura resultados.
5. **Evolución a BBDD:** Persistencia inicial en LocalStorage con contrato estable para migrar a DB sin rehacer el frontend.
6. **Observabilidad:** Log del perfil activo en cada consulta.

---

## 1. Contrato de Datos

### 1.1 Objeto `user_preferences`

Este objeto representa el estado de preferencias del usuario. Debe estar disponible para:

* **Presentation (Capa 1):** UI de modal + etiqueta de perfil activo + LocalStorage.
* **Application (Capa 2):** Inyección de contexto a agentes, resolución de perfiles via ProfileService.
* **Business (Capa 3):** Bias de ranking e interpretación de directivas en agent pipeline.
* **Integration (Capa 4):** Persistencia futura de preferencias en BBDD (Phase 2+).
* **Shared (Capa 5):** Interfaces y modelos transversales (UserPreferences DTO, ProfileResolverInterface).

```json
{
  "user_preferences": {
    "active_profile_id": "string | null",
    "updated_at": "string (ISO8601) | null",
    "source": "local_storage | db | none"
  }
}
```

**Semántica:**

* `active_profile_id = null` → comportamiento actual (sin especialización)
* `source` indica dónde se obtuvo el perfil (para migración futura y debug)

---

### 1.2 Profile Registry (SSOT)

La definición de perfiles vive en un registry metadata-driven. En PoC puede ser:

* **v1:** JSON servido como estático (p.ej. `presentation/static/config/profiles.json`) o endpoint backend simple
* **v2:** tabla BBDD con CRUD y perfiles custom del usuario

**Schema del registry:**

```json
{
  "version": "1.0",
  "profiles": [
    {
      "id": "day_leisure",
      "label": "Ocio diurno",
      "description": "Prioriza planes diurnos, mercados, cafés, experiencias locales y actividades al aire libre.",
      "prompt_directives": [
        "Prioriza opciones de ocio diurno y experiencias locales típicas.",
        "Si el usuario no especifica hora, asume horario diurno por defecto."
      ],
      "ranking_bias": {
        "venue_types": {
          "market": 1.2,
          "park": 1.15,
          "museum": 1.05,
          "restaurant": 1.0,
          "entertainment": 0.95,
          "nightclub": 0.7
        },
        "signals": {
          "family_friendly": 1.1,
          "outdoor": 1.1,
          "late_night": 0.8
        }
      },
      "ui": {
        "icon": "bi-sun",
        "badge_class": "bg-primary"
      },
      "is_user_custom": false
    }
  ]
}
```

#### Campos clave

* `prompt_directives[]`: Instrucciones para inyección en prompt (Opción C: metadata-driven).
* `ranking_bias`: Pesos para ranking (no bloqueo).
* `ui`: iconografía y estilos Bootstrap.
* `is_user_custom`: permite perfiles personalizados en el futuro.

---

### 1.3 Perfiles Iniciales (predefinidos)

Se definen 5 perfiles “built-in” en el registry:

* `day_leisure` — Ocio diurno
* `night_leisure` — Ocio nocturno
* `dining` — Restauración
* `tourism` — Turismo
* `cultural` — Ocio cultural

> Nota: el registry debe permitir añadir perfiles sin tocar código (solo agregando nuevos objetos al JSON/DB).

---

## 2. Lógica de Negocio (Business Layer — Capa 3)

### 2.1 Inyección de Perfil en Contexto de Agentes

Los agentes LangChain deben recibir el perfil activo como **contexto explícito** y determinista en cada llamada.

**Contrato interno sugerido:**

* `agent_context.profile = { id, label, prompt_directives, ranking_bias }` o `null`

**Regla:** si `active_profile_id` no existe en registry → tratar como `null` + log warning.

---

### 2.2 Ranking Bias (sin bloqueo)

El perfil **modifica el orden** o la selección recomendada, sin descartar resultados válidos.

**Ejemplos de aplicación del bias:**

* Si herramientas devuelven múltiples venues, el agente ordena usando `ranking_bias`.
* Si el usuario dice “Dame alternativas en Madrid centro hoy”:

  * `day_leisure`: mercados, cafés, experiencias locales, parques
  * `night_leisure`: conciertos, discotecas, eventos nocturnos
  * `dining`: restaurantes/tabernas
  * `tourism`: museos/lugares emblemáticos
  * `cultural`: museos, exposiciones, galerías

**Regla anti-alucinación:** el perfil no autoriza inventar lugares/eventos. Solo afecta la priorización de resultados reales.

---

### 2.3 Prompt Directives (metadata-driven)

Los `prompt_directives` se concatenan en una sección controlada del system prompt, por ejemplo:

* `SYSTEM: ...`
* `SYSTEM: User Profile Context: <label> ... <directives> ...`
* `SYSTEM: Ranking Policy: preferir X sobre Y, sin bloquear`

Esto evita hardcodear perfiles en código: solo se renderiza la lista de directivas y bias.

---

## 3. Lógica de Aplicación (Application Layer — Capa 2)

### 3.1 Fuente de preferencias (v1 → v2)

**v1 (PoC):**

* Frontend guarda `active_profile_id` en LocalStorage.
* Backend recibe `active_profile_id` en cada request (recomendado) o lo infiere de un header.

**v2 (futuro):**

* Backend guarda/lee preferencias desde DB (por user id cuando exista autenticación).
* Frontend puede seguir usando LocalStorage como cache, pero backend es source of truth.

> Diseño recomendado: **Backend acepta profile_id como input opcional** y lo “normaliza” con registry.

---

### 3.2 API / Integración de Perfil (minimalista)

Sin asumir tu stack exacto, el patrón sería:

* En cada request “chat” / “agent run”, incluir:

  * `user_preferences.active_profile_id`

El backend:

1. resuelve el profile en registry
2. construye `agent_context`
3. invoca LangChain con ese contexto
4. retorna la respuesta habitual + metadata del perfil activo

---

### 3.3 Logging del perfil

En cada ejecución del pipeline:

* `profile_id` (o `none`)
* `source` (`local_storage`, `db`, `none`)
* `request_id` / `conversation_id` (si existe)

**Regla:** logging no debe incluir PII.

---

## 4. Presentación (Presentation Layer — Capa 1)

### 4.1 Modal de configuración

**Componente:** Modal Bootstrap 5.3

Contenido:

* Título: “Preferencias”
* Lista de perfiles (radio list / cards) con:

  * icono (`ui.icon`)
  * `label`
  * `description`
* Botón “Guardar”
* Botón “Cancelar”

**Comportamiento:**

* Al abrir modal: cargar perfiles desde registry (fetch) y `active_profile_id` desde LocalStorage.
* Al guardar: persistir en LocalStorage y actualizar UI (badge/estado).
* No hay preview.

---

### 4.2 Estado visible del perfil activo

El frontend debe “saber” el perfil activo:

* Mostrar badge en UI del chat (opcional pero recomendado): `Perfil: Ocio cultural`
* Incluir `active_profile_id` en cada envío al backend

---

### 4.3 Contrato Frontend → Backend

En cada envío de mensaje (transcripción STT incluida), adjuntar:

```json
{
  "message": "texto transcrito",
  "user_preferences": {
    "active_profile_id": "cultural"
  }
}
```

Si no existe:

```json
{ "user_preferences": { "active_profile_id": null } }
```

---

## 5. Validación Defensiva

### 5.1 Frontend

| Validación                      | Ubicación     | Comportamiento                                  |
| ------------------------------- | ------------- | ----------------------------------------------- |
| `profiles` no carga             | modal         | fallback: lista vacía + mensaje “No disponible” |
| `active_profile_id` desconocido | init UI       | set a `null` y limpiar LocalStorage             |
| LocalStorage inaccesible        | init/guardado | fallback a memoria (solo sesión)                |

### 5.2 Backend

| Validación                  | Ubicación       | Comportamiento                      |
| --------------------------- | --------------- | ----------------------------------- |
| `active_profile_id` ausente | request parser  | tratar como `null`                  |
| id no existe en registry    | resolver perfil | `null` + log warning                |
| registry inválido           | carga config    | fallback a “sin perfil” + log error |

---

## 6. Persistencia & Migración (LocalStorage → BBDD)

### 6.1 Claves LocalStorage (v1)

* `vf_active_profile_id`: string | null
* `vf_active_profile_updated_at`: ISO8601 string

### 6.2 Migración a DB (v2)

Cuando exista modelo User / auth:

* Tabla `user_preferences` o columna `active_profile_id`
* Endpoint:

  * GET preferencias
  * PUT preferencias

**Compatibilidad:** el frontend puede mantener LocalStorage como cache, pero debe poder re-hidratar desde backend.

---

## 7. Extensibilidad: Perfiles Personalizados (futuro)

El registry soporta `is_user_custom=true`.

Requisitos futuros:

* Crear perfiles por usuario (CRUD)
* Validación de schema: `prompt_directives` y `ranking_bias` dentro de límites (evitar prompts peligrosos / demasiado largos)
* Versionado del registry (`version`) para migraciones

---

## 8. Checklist Definition of Done

* ✅ Modal funcional para seleccionar 1 perfil activo
* ✅ Guardado en LocalStorage + persistencia de `updated_at`
* ✅ En cada consulta, se envía `active_profile_id` al backend
* ✅ Backend resuelve perfil via registry y lo inyecta a LangChain Agents
* ✅ El perfil solo afecta ranking/prioridad, no bloquea resultados
* ✅ Si no hay perfil, comportamiento actual intacto
* ✅ Logging por request del `profile_id` (o none)
* ✅ Añadir un perfil nuevo en registry no requiere cambios de código (o mínimo: sin tocar lógica del agente)

---

## 9. Implementación recomendada (por capas, sin rutas concretas)

*(Para mantenerlo SDD y no “vivecoding”, esto es intención, no código aún.)*

* **Capa 1 (Presentation):**

  * `profiles.js` (carga registry + estado actual)
  * `preferences_modal.js` (UI modal + persistencia LocalStorage)
  * `chat.js` (adjunta `user_preferences.active_profile_id` en requests)

* **Capa 2 (Application):**

  * `profile_registry_loader` (carga JSON/DB y cachea)
  * `resolve_active_profile(profile_id)` → `Profile | null`
  * `agent_context_builder` (inyecta directives + bias)

* **Capa 3 (Business / Agents):**

  * Política de ranking consumiendo `ranking_bias` (determinista y explicable)
