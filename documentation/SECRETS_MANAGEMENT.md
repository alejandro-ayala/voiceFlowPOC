# Gestion de Secrets - VoiceFlow Tourism PoC

**Fecha**: 12 de Febrero de 2026
**Estado**: Implementado
**Herramientas**: git-crypt (local) + GitHub Secrets (CI/CD)

---

## Contexto y decision

### Problema

El proyecto requiere credenciales de servicios externos para funcionar en modo real:

| Secret | Servicio | Uso |
|--------|----------|-----|
| `AZURE_SPEECH_KEY` | Azure Speech Services | Transcripcion de audio (STT) |
| `AZURE_SPEECH_REGION` | Azure Speech Services | Region del recurso Azure |
| `OPENAI_API_KEY` | OpenAI GPT-4 | LangChain multi-agent system |

Hasta ahora, estas credenciales se gestionaban manualmente: cada desarrollador copiaba `.env.example` a `.env` y rellenaba las keys. Esto implica:

- Configuracion manual tras cada clonado
- Riesgo de desincronizacion entre desarrolladores
- Imposibilidad de ejecutar tests de integracion en CI sin configuracion adicional

### Decision

Se adopta un enfoque en dos niveles:

1. **Local (git-crypt)**: El archivo `.env` se almacena cifrado en el repositorio. Al clonar y desbloquear con la clave simetrica, las credenciales estan disponibles sin pasos manuales.

2. **CI/CD (GitHub Secrets)**: Las credenciales se configuran como secrets en GitHub Actions. El pipeline no depende de git-crypt.

### Alternativas evaluadas

| Enfoque | Complejidad | Autocontenido | Elegido |
|---------|-------------|---------------|---------|
| `.env` manual (anterior) | Baja | No | No |
| **git-crypt** | Baja | Si | **Si** |
| sops + age | Media | Si | No (sobredimensionado para PoC) |
| Azure Key Vault | Alta | No (requiere infra cloud) | No (futuro produccion) |
| dotenvx | Media | Si | No (menos maduro) |

**Razon**: git-crypt es transparente (cifra/descifra automaticamente), no requiere cambios en el flujo de trabajo, y es suficiente para un equipo reducido.

---

## Arquitectura de secrets

```
                    ┌─────────────────────┐
                    │   Repositorio Git    │
                    │                     │
                    │  .env (cifrado)     │──── git-crypt ────► .env (descifrado)
                    │  .env.example       │                     en working directory
                    │                     │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
              ┌─────▼─────┐        ┌─────▼─────┐
              │   LOCAL    │        │   CI/CD   │
              │            │        │           │
              │ git-crypt  │        │  GitHub   │
              │ unlock     │        │  Secrets  │
              │ <key-file> │        │           │
              └────────────┘        └───────────┘
```

### Que se cifra

| Archivo | Cifrado | Razon |
|---------|---------|-------|
| `.env` | Si (git-crypt) | Contiene API keys reales |
| `.env.example` | No | Template sin secrets (valores placeholder) |

### Que NO se cifra

- Configuracion no sensible (`STT_SERVICE`, `LOG_LEVEL`, etc.) esta en `.env.example`
- La clave simetrica de git-crypt (`voiceflow-git-crypt.key`) **NUNCA** va al repositorio

---

## Setup: Primera vez (mantenedor)

### Prerrequisitos

```bash
sudo apt install git-crypt   # Ubuntu/Debian
brew install git-crypt        # macOS
```

### Paso 1: Inicializar git-crypt

```bash
cd voiceFlowPOC
git-crypt init
```

Esto genera una clave simetrica interna en `.git/git-crypt/`.

### Paso 2: Configurar archivos a cifrar

Crear o editar `.gitattributes`:

```
.env filter=git-crypt diff=git-crypt
```

### Paso 3: Actualizar .gitignore

Eliminar `.env` y `*.env` del `.gitignore` para que git-crypt pueda trackear el archivo:

```gitignore
# ANTES (ya no aplica):
# .env
# *.env

# AHORA: .env se gestiona cifrado via git-crypt
# Solo excluir archivos .env temporales o de backup
*.env.local
*.env.backup
```

### Paso 4: Crear el .env con credenciales reales

```bash
cp .env.example .env
# Editar .env con las credenciales reales
```

### Paso 5: Commitear (se cifra automaticamente)

```bash
git add .env .gitattributes
git commit -m "feat: add encrypted .env with git-crypt"
```

Para verificar que esta cifrado:

```bash
# Esto muestra contenido cifrado (binario)
git show HEAD:.env | file -
# Debe decir: "data" o "PGP" (no texto plano)
```

### Paso 6: Exportar la clave

```bash
git-crypt export-key ~/voiceflow-git-crypt.key
```

**IMPORTANTE**: Guardar esta clave en un lugar seguro:
- Password manager (1Password, Bitwarden, etc.)
- USB cifrado
- **NUNCA** en el repositorio ni en GitHub

---

## Setup: Nuevo desarrollador

```bash
# 1. Clonar el repo
git clone https://github.com/alejandro-ayala/voiceFlowPOC.git
cd voiceFlowPOC

# 2. Desbloquear secrets (necesita el key file del mantenedor)
git-crypt unlock /ruta/a/voiceflow-git-crypt.key

# 3. Verificar
cat .env   # Debe mostrar las credenciales en texto plano

# 4. Listo - todo funciona
poetry run python presentation/server_launcher.py
```

---

## Setup: GitHub Secrets (CI/CD)

El pipeline de CI/CD no usa git-crypt. Las credenciales se configuran directamente en GitHub.

### Paso 1: Configurar secrets en GitHub

Ir a: `Settings > Secrets and variables > Actions > New repository secret`

| Secret name | Valor |
|-------------|-------|
| `OPENAI_API_KEY` | Key real de OpenAI |
| `AZURE_SPEECH_KEY` | Key 1 de Azure Speech Services |
| `AZURE_SPEECH_REGION` | Region del recurso (ej: `westeurope`) |

### Paso 2: Uso en workflows

```yaml
# .github/workflows/ci.yml
jobs:
  test-integration:
    runs-on: ubuntu-latest
    env:
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      AZURE_SPEECH_KEY: ${{ secrets.AZURE_SPEECH_KEY }}
      AZURE_SPEECH_REGION: ${{ secrets.AZURE_SPEECH_REGION }}
    steps:
      - uses: actions/checkout@v4
      - run: pytest tests/ -m integration
```

**Nota**: El job actual `docker-build-validate` usa `OPENAI_API_KEY=dummy_key` porque corre en modo simulacion. Los secrets reales solo seran necesarios cuando se anadan tests de integracion con APIs externas (Fase 3).

---

## Operaciones habituales

### Actualizar una credencial

```bash
# Editar .env normalmente (ya esta descifrado en tu working directory)
vim .env

# Commitear (se cifra automaticamente al hacer push)
git add .env
git commit -m "chore: update Azure Speech key"
git push
```

### Verificar estado de cifrado

```bash
# Ver archivos gestionados por git-crypt
git-crypt status

# Verificar que .env esta cifrado en el repo
git-crypt status .env
# Debe mostrar: "encrypted: .env"
```

### Anadir un nuevo secret

1. Anadir la variable a `.env` y a `.env.example` (con valor placeholder)
2. Si es necesario en CI, anadir como GitHub Secret
3. Documentar en esta tabla:

| Variable | En `.env` | En GitHub Secrets | Descripcion |
|----------|-----------|-------------------|-------------|
| `AZURE_SPEECH_KEY` | Si | Si | API key Azure Speech |
| `AZURE_SPEECH_REGION` | Si | Si | Region Azure |
| `OPENAI_API_KEY` | Si | Si | API key OpenAI |
| `STT_SERVICE` | Si | No (no es secret) | Backend STT seleccionado |

### Bloquear el repo (re-cifrar localmente)

```bash
git-crypt lock
# Ahora .env vuelve a estar cifrado en tu working directory
# Util si vas a dejar el equipo desatendido
```

---

## Seguridad

### Que protege git-crypt

- Los archivos marcados en `.gitattributes` se cifran con AES-256 antes de almacenarse en Git
- En GitHub, el contenido de `.env` aparece como binario ilegible
- Solo quienes tienen el key file pueden descifrar

### Que NO protege git-crypt

- Si un commit anterior tenia `.env` en texto plano, ese historial sigue expuesto
- git-crypt no protege la memoria ni el disco local (una vez desbloqueado, `.env` esta en texto plano)
- Si la clave simetrica se compromete, todos los secrets quedan expuestos

### Rotacion de credenciales

Si una key se compromete:

1. Rotar la credencial en el servicio (Azure Portal, OpenAI Dashboard)
2. Actualizar `.env` y commitear
3. Actualizar el GitHub Secret correspondiente
4. Si la clave git-crypt se comprometio: re-inicializar git-crypt (ver documentacion oficial)

---

## Escalabilidad futura

Cuando el proyecto pase a produccion real, considerar:

| Mejora | Cuando | Complejidad |
|--------|--------|-------------|
| GitHub Environments (staging/prod) | Fase 5 completa (deploy) | Baja |
| Azure Key Vault | Produccion con datos de usuarios | Media |
| Rotacion automatica de keys | Produccion | Media-Alta |
| SOPS + age (reemplaza git-crypt) | Equipo > 5 personas | Media |

---

## Documentacion relacionada

- [ROADMAP.md](ROADMAP.md) - Plan de evolucion del proyecto
- [DEVELOPMENT.md](DEVELOPMENT.md) - Guia de desarrollo (variables de entorno)
- [AZURE_SETUP_GUIDE.md](AZURE_SETUP_GUIDE.md) - Configuracion de Azure Speech Services
