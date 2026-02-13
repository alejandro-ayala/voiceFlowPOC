# Guía de Configuración Azure Speech Services

Esta guía te llevará paso a paso desde la creación de la cuenta Azure hasta la ejecución exitosa del agente STT.

## 📋 Requisitos Previos

- Cuenta de email institucional (para Azure for Students) o personal
- Python 3.9+ instalado
- Git (opcional, para clonar el proyecto)

## 🚀 Paso 1: Crear Cuenta Azure (Azure for Students)

### Opción A: Azure for Students (Recomendado - Sin tarjeta de crédito)

1. **Visitar el portal Azure for Students:**
   - Ir a: https://azure.microsoft.com/es-es/free/students/
   - Hacer clic en "Activar ahora"

2. **Registrarse con email institucional:**
   - Usar tu email universitario (@universidad.edu, etc.)
   - Seguir el proceso de verificación académica
   - Azure verificará automáticamente tu estatus de estudiante

3. **Créditos incluidos:**
   - $100 USD en créditos Azure
   - 12 meses de servicios gratuitos
   - No requiere tarjeta de crédito

### Opción B: Cuenta Azure Gratuita (Requiere tarjeta)

1. **Si no tienes acceso a Azure for Students:**
   - Ir a: https://azure.microsoft.com/es-es/free/
   - Registrarse con cuenta personal
   - Requiere tarjeta de crédito (no se cobra, solo verificación)
   - $200 USD en créditos por 30 días

## 🏗️ Paso 2: Crear Recurso de Speech Services

### 2.1 Acceder al Portal Azure

1. **Iniciar sesión:**
   - Ir a: https://portal.azure.com
   - Iniciar sesión con tu cuenta Azure

2. **Navegar al dashboard principal:**
   - Deberías ver el panel principal de Azure

### 2.2 Crear el Recurso Speech

1. **Crear nuevo recurso:**
   ```
   Portal Azure → "Crear un recurso" → Buscar "Speech Services"
   ```

2. **Configurar el recurso:**
   - **Suscripción:** Azure for Students (o tu suscripción)
   - **Grupo de recursos:** Crear nuevo → Nombre: `rg-voiceflow-poc`
   - **Región:** Ver **🚨 IMPORTANTE** abajo para elegir región correcta
   - **Nombre:** `speech-voiceflow-poc-[tu-nombre]`
   - **Plan de tarifa:** `F0 (Free)` - **¡IMPORTANTE!**

   **🚨 IMPORTANTE - Regiones para Azure for Students:**
   
   Azure for Students tiene restricciones de región. Prueba estas regiones **EN ESTE ORDEN**:
   
   1. **`West Europe`** (recomendada para España/Europa)
   2. **`West US 2`** (alternativa confiable)
   3. **`Central US`** (si las anteriores fallan)
   4. **`South Central US`** (última opción)
   
   **⚠️ NO uses `East US` con Azure for Students - causará el error que experimentaste**

3. **Verificar configuración:**
   ```
   Suscripción: Azure for Students
   Grupo de recursos: rg-voiceflow-poc
   Región: West Europe (o alguna de las alternativas arriba)
   Nombre: speech-voiceflow-poc-[tu-nombre]
   Plan de tarifa: F0 (Free) ← 5 horas/mes gratis
   ```

4. **Crear el recurso:**
   - Clic en "Revisar y crear"
   - Clic en "Crear"
   - Esperar 1-2 minutos hasta que se despliegue

### 2.3 Obtener las Credenciales

1. **Ir al recurso creado:**
   - En el portal Azure, ir a "Todos los recursos"
   - Buscar y hacer clic en `speech-voiceflow-poc-[tu-nombre]`

2. **Obtener las claves:**
   - En el menú izquierdo: `Administración de recursos` → `Claves y punto de conexión`
   - Anotar los siguientes valores:


   **📝 NOTA:** La región en el `.env` debe coincidir EXACTAMENTE con la región donde creaste el recurso.
   
   **⚠️ IMPORTANTE:** Guarda estas credenciales de forma segura.

## 🔧 Paso 3: Configurar el Proyecto

### 3.1 Preparar el Entorno

1. **Clonar o descargar el proyecto:**
   ```bash
   # Si tienes git
   git clone [url-del-proyecto]
   cd VoiceFlowPOC
   
   # O descargar y extraer el ZIP
   ```

2. **Instalar dependencias:**
   ```bash
   poetry install
   ```

### 3.2 Configurar Variables de Entorno

1. **Copiar archivo de configuración:**
   ```bash
   cp .env.example .env
   ```

2. **Editar archivo `.env`:**
   ```env
   # Azure Speech Services Configuration
   AZURE_SPEECH_KEY=TU_CLAVE_AQUI
   AZURE_SPEECH_REGION=westeurope
   
   # STT Service Configuration
   STT_SERVICE=azure
   
   # Audio Configuration
   SUPPORTED_FORMATS=wav,mp3,m4a,flac,ogg
   DEFAULT_SAMPLE_RATE=16000
   DEFAULT_CHANNELS=1
   
   # Logging
   LOG_LEVEL=INFO
   ```

   **⚠️ IMPORTANTE:**
   - Reemplazar `TU_CLAVE_AQUI` con tu CLAVE 1 de Azure
   - Reemplazar `westeurope` con la región exacta donde creaste tu recurso

## 🎵 Paso 4: Preparar Audio de Prueba

### 4.1 Obtener Audio de Prueba

**Opción A: Grabar tu propia voz**
```bash
# En Windows, usar Grabadora de sonidos
# Grabar 10-15 segundos diciendo algo como:
# "Hola, esta es una prueba del agente de voz a texto para el proyecto de turismo accesible"
# Guardar como: ejemplos/audio_prueba.wav
```

**Opción B: Usar audio de muestra online**
```bash
# Descargar audio de prueba en español
# Guardar en: ejemplos/audio_prueba.wav
```

**Opción C: Convertir audio existente**
```bash
# Si tienes FFmpeg instalado
ffmpeg -i tu_audio.mp3 -ar 16000 -ac 1 ejemplos/audio_prueba.wav
```

### 4.2 Verificar el Audio

```bash
# Verificar que el archivo existe
ls ejemplos/audio_prueba.wav

# Ver información del archivo (si tienes FFmpeg)
ffprobe ejemplos/audio_prueba.wav
```

## 🧪 Paso 5: Probar la Configuración

### 5.1 Test Básico de Conexión

Crear archivo `test_azure_connection.py`:

```python
"""
Test básico de conexión con Azure Speech Services
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar configuración
load_dotenv()

# Agregar src al path
sys.path.append(str(Path(__file__).parent / "src"))

async def test_azure_connection():
    """Test básico de conexión con Azure"""
    
    print("🔍 === TEST DE CONEXIÓN AZURE ===")
    
    # 1. Verificar variables de entorno
    print("\n1. Verificando configuración...")
    
    azure_key = os.getenv('AZURE_SPEECH_KEY')
    azure_region = os.getenv('AZURE_SPEECH_REGION')
    stt_service = os.getenv('STT_SERVICE')
    
    print(f"   STT_SERVICE: {stt_service}")
    print(f"   AZURE_SPEECH_REGION: {azure_region}")
    print(f"   AZURE_SPEECH_KEY: {'✅ Configurada' if azure_key else '❌ No encontrada'}")
    
    if not azure_key or not azure_region:
        print("\n❌ ERROR: Configuración incompleta")
        print("   Verifica tu archivo .env")
        return False
    
    # 2. Verificar importaciones
    print("\n2. Verificando dependencias...")
    try:
        import azure.cognitiveservices.speech as speechsdk
        print("   ✅ azure-cognitiveservices-speech instalado")
    except ImportError:
        print("   ❌ ERROR: Instala azure-cognitiveservices-speech")
        print("   Ejecuta: poetry add azure-cognitiveservices-speech")
        return False
    
    # 3. Crear servicio Azure
    print("\n3. Creando servicio Azure...")
    try:
        from services.azure_speech_service import AzureSpeechService
        service = AzureSpeechService(azure_key, azure_region)
        print("   ✅ Servicio Azure creado")
    except Exception as e:
        print(f"   ❌ ERROR creando servicio: {e}")
        return False
    
    # 4. Verificar disponibilidad
    print("\n4. Verificando conexión...")
    if service.is_service_available():
        print("   ✅ Servicio disponible")
        
        # Mostrar información
        info = service.get_service_info()
        print(f"   Servicio: {info['service_name']}")
        print(f"   Región: {info['region']}")
        print(f"   Formatos: {', '.join(info['supported_formats'])}")
        
        return True
    else:
        print("   ❌ Servicio no disponible")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_azure_connection())
    
    if success:
        print("\n🎉 ¡CONEXIÓN EXITOSA!")
        print("   Puedes proceder a probar con audio")
    else:
        print("\n💥 HAY PROBLEMAS EN LA CONFIGURACIÓN")
        print("   Revisa los errores anteriores")
```

**Ejecutar el test:**
```bash
python test_azure_connection.py
```

### 5.2 Test Completo con Audio

Si el test anterior es exitoso:

```python
"""
Test completo del agente STT con Azure
"""
import asyncio
import sys
from pathlib import Path

# Agregar src al path
sys.path.append(str(Path(__file__).parent / "src"))

async def test_stt_complete():
    """Test completo de transcripción"""
    
    print("🎯 === TEST COMPLETO STT AGENT ===")
    
    try:
        from voiceflow_stt_agent import VoiceflowSTTAgent
        
        # 1. Crear agente
        print("\n1. Creando agente STT...")
        agent = VoiceflowSTTAgent.create_from_config()
        print(f"   ✅ Agente creado: {agent.agent_id}")
        
        # 2. Health check
        print("\n2. Verificando salud del agente...")
        health = await agent.health_check()
        print(f"   Estado: {health['status']}")
        
        if health['status'] != 'healthy':
            print("   ❌ Agente no está saludable")
            return
        
        # 3. Verificar archivo de audio
        audio_file = "ejemplos/audio_prueba.wav"
        print(f"\n3. Verificando archivo de audio: {audio_file}")
        
        if not Path(audio_file).exists():
            print("   ❌ Archivo de audio no encontrado")
            print("   Crea un archivo de audio en ejemplos/audio_prueba.wav")
            return
        
        print("   ✅ Archivo de audio encontrado")
        
        # 4. Transcribir
        print("\n4. Iniciando transcripción...")
        print("   ⏳ Procesando audio con Azure Speech Services...")
        
        transcription = await agent.transcribe_audio(
            audio_file,
            language="es-ES"  # Español
        )
        
        print(f"\n🎉 ¡TRANSCRIPCIÓN EXITOSA!")
        print(f"📝 Resultado: '{transcription}'")
        
        # 5. Estadísticas
        print("\n5. Estadísticas:")
        history = agent.get_transcription_history()
        info = agent.get_service_info()
        
        print(f"   Transcripciones realizadas: {len(history)}")
        print(f"   Servicio usado: {info['service_info']['service_name']}")
        print(f"   Longitud del texto: {len(transcription)} caracteres")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_stt_complete())
    
    if success:
        print("\n🏆 ¡TODO FUNCIONA CORRECTAMENTE!")
        print("   El agente STT está listo para usar")
    else:
        print("\n🔧 Revisa la configuración y vuelve a intentar")
```

**Guardar como `test_complete.py` y ejecutar:**
```bash
python test_complete.py
```

### 5.3 Usar el Demo Principal

```bash
python main.py
```

## 🔍 Paso 6: Verificar el Consumo

### 6.1 Monitorear Uso en Azure

1. **Ir al portal Azure:**
   - https://portal.azure.com
   - Ir a tu recurso Speech Services

2. **Ver métricas:**
   - En el menú izquierdo: `Supervisión` → `Métricas`
   - Métrica: `Total Calls` o `Total Transactions`
   - Ver las llamadas realizadas

3. **Ver facturación:**
   - Portal Azure → `Administración de costos + facturación`
   - Ver el consumo de tu tier gratuito

### 6.2 Tier Gratuito F0 - Límites

```
🆓 Plan Gratuito F0:
- 5 horas de transcripción por mes
- 20 transacciones por minuto
- 100% gratuito dentro del límite
```

**Para la PoC esto es más que suficiente:**
- Transcripción promedio: 30 segundos por prueba
- 5 horas = 600 pruebas por mes
- Perfecto para desarrollo y testing

## 🚨 Troubleshooting

### Error: "Subscription key is invalid"
```bash
# Verificar que la clave es correcta
# La clave debe tener ~32 caracteres alfanuméricos
# Ejemplo: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

### Error: "Region is not supported"
```bash
# Verificar región en Azure Portal
# Para Azure for Students, regiones válidas: westeurope, westus2, centralus
# Debe coincidir exactamente con la región del recurso
```

### Error: "RequestDisallowedByAzure" al crear recurso
Este error ocurre cuando intentas usar una región no disponible para Azure for Students.

**Solución:**
1. **Eliminar el recurso fallido** (si se creó parcialmente)
2. **Crear nuevo recurso** con una de estas regiones:
   - `West Europe` (recomendada para España)
   - `West US 2`
   - `Central US`
3. **Actualizar tu `.env`** con la región correcta

### Error: "Import azure.cognitiveservices.speech could not be resolved"
```bash
poetry add azure-cognitiveservices-speech
```

### Error: "Audio file not found"
```bash
# Verificar ruta del archivo
ls ejemplos/audio_prueba.wav

# Crear carpeta si no existe
mkdir ejemplos
```

### Error: "Service unavailable"
```bash
# Verificar que el recurso está activo en Azure Portal
# Verificar límites del tier gratuito
# Esperar unos minutos y volver a intentar
```

## ✅ Checklist Final

Antes de considerar la configuración completa, verificar:

- [ ] ✅ Cuenta Azure creada (preferiblemente Azure for Students)
- [ ] ✅ Recurso Speech Services creado con plan F0 (gratuito)
- [ ] ✅ Claves y región obtenidas del portal Azure
- [ ] ✅ Archivo `.env` configurado correctamente
- [ ] ✅ Dependencias instaladas (`poetry install`)
- [ ] ✅ Archivo de audio de prueba creado
- [ ] ✅ Test de conexión exitoso (`python test_azure_connection.py`)
- [ ] ✅ Test completo exitoso (`python test_complete.py`)
- [ ] ✅ Demo principal funciona (`python main.py`)

## 🎯 Próximos Pasos

Una vez que todo funcione:

1. **Experimentar con diferentes audios:**
   - Diferentes idiomas
   - Diferentes calidades de audio
   - Diferentes duraciones

2. **Probar parámetros:**
   ```python
   # Diferentes idiomas
   await agent.transcribe_audio("audio.wav", language="en-US")
   await agent.transcribe_audio("audio.wav", language="fr-FR")
   ```

3. **Integrar en tu sistema multiagente:**
   - El agente está listo para usar
   - Interfaz bien definida
   - Fácil de integrar

¡Ya tienes tu agente STT funcionando con Azure Speech Services! 🚀

## 🚨 SOLUCIÓN RÁPIDA - Error de Región

**¿Tienes el error "RequestDisallowedByAzure" como el usuario?** Sigue estos pasos:

### Paso 1: Limpiar Recursos Fallidos

1. **Ir al Portal Azure:** https://portal.azure.com
2. **Buscar recursos fallidos:**
   - Ir a "Todos los recursos"
   - Buscar `speech-voiceflow-poc-adab` (o tu nombre)
   - Si aparece, eliminarlo
3. **Limpiar grupo de recursos:**
   - Ir a "Grupos de recursos"  
   - Buscar `rg-voiceflow-poc`
   - Si está vacío o con recursos fallidos, eliminarlo

### Paso 2: Crear Recurso con Región Correcta

1. **Crear nuevo recurso Speech Services:**
   ```
   Portal Azure → "Crear un recurso" → Buscar "Speech Services"
   ```

2. **Configurar con región válida:**
   - **Suscripción:** Azure for Students
   - **Grupo de recursos:** Crear nuevo → `rg-voiceflow-poc`
   - **Región:** `West Europe` ← **USAR ESTA**
   - **Nombre:** `speech-poc-[tu-nombre]` (más corto)
   - **Plan de tarifa:** `F0 (Free)`

3. **Si West Europe también falla, probar:**
   - `West US 2`
   - `Central US`
   - `South Central US`

### Paso 3: Actualizar Configuración

Una vez creado exitosamente:

1. **Obtener credenciales:**
   - Ir al recurso → "Claves y punto de conexión"
   - Copiar CLAVE 1 y REGIÓN

2. **Actualizar `.env`:**
   ```env
   AZURE_SPEECH_KEY=tu_clave_real_aqui
   AZURE_SPEECH_REGION=westeurope  # o la región que funcionó
   STT_SERVICE=azure
   ```

### Paso 4: Probar Conexión

```bash
python test_azure_connection.py
```
