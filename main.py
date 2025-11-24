"""
Ejemplo de uso del VoiceflowSTTAgent - Prueba de Concepto

Este archivo demuestra cómo inicializar y usar el agente STT en diferentes escenarios.
"""

import asyncio
import os
from pathlib import Path
import sys

# Agregar el directorio src al path para los imports
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from voiceflow_stt_agent import VoiceflowSTTAgent
    from factory import STTServiceFactory
    from interfaces.stt_interface import STTServiceError, AudioFormatError
except ImportError as e:
    print(f"Error importando módulos: {e}")
    print("Asegúrate de haber instalado las dependencias: pip install -r requirements.txt")
    sys.exit(1)


async def demo_basic_usage():
    """Demostración básica del uso del agente STT."""
    print("🎯 === DEMO: Uso Básico del Agente STT ===")
    
    try:
        # Crear agente desde configuración (lee .env automáticamente)
        print("📋 Creando agente desde configuración...")
        agent = VoiceflowSTTAgent.create_from_config()
        
        # Verificar estado del agente
        print("🔍 Verificando estado del agente...")
        health = await agent.health_check()
        print(f"   Estado: {health['status']}")
        print(f"   Servicio disponible: {health['service_available']}")
        
        # Obtener información del servicio
        info = agent.get_service_info()
        print(f"   Servicio STT: {info['service_info']['service_name']}")
        print(f"   Formatos soportados: {', '.join(info['supported_formats'])}")
        
        # Simular transcripción (archivo de ejemplo)
        # NOTA: Reemplaza con la ruta a tu archivo de audio real
        audio_file = "ejemplos/audio_prueba.wav"  # Cambia por tu archivo
        
        if Path(audio_file).exists():
            print(f"🎵 Transcribiendo audio: {audio_file}")
            try:
                transcription = await agent.transcribe_audio(
                    audio_file,
                    language="es-ES"  # Español de España
                )
                print(f"📝 Transcripción: '{transcription}'")
                
                # Mostrar estadísticas
                history = agent.get_transcription_history()
                print(f"📊 Total transcripciones: {len(history)}")
                
            except (STTServiceError, AudioFormatError) as e:
                print(f"❌ Error en transcripción: {e}")
                
        else:
            print(f"⚠️  Archivo de audio no encontrado: {audio_file}")
            print("   Para probar con audio real, coloca un archivo WAV en esa ruta")
            
            # Simular transcripción fallida para mostrar manejo de errores
            try:
                await agent.transcribe_audio("archivo_inexistente.wav")
            except STTServiceError as e:
                print(f"✅ Manejo de errores funciona correctamente: {e}")
    
    except Exception as e:
        print(f"❌ Error en demo básico: {e}")
        print("   Verifica tu configuración en .env")


async def demo_multiple_services():
    """Demostración de múltiples servicios STT."""
    print("\n🔄 === DEMO: Múltiples Servicios STT ===")
    
    # Obtener servicios disponibles
    available_services = STTServiceFactory.get_available_services()
    print(f"📋 Servicios disponibles: {', '.join(available_services)}")
    
    for service_name in available_services:
        print(f"\n🔧 Probando servicio: {service_name}")
        
        try:
            # Intentar crear cada servicio
            if service_name == "azure":
                if not (os.getenv("AZURE_SPEECH_KEY") and os.getenv("AZURE_SPEECH_REGION")):
                    print("   ⚠️  Configuración Azure no encontrada, saltando...")
                    continue
                    
            elif service_name == "whisper_api":
                if not os.getenv("OPENAI_API_KEY"):
                    print("   ⚠️  API Key de OpenAI no encontrada, saltando...")
                    continue
            
            # Crear servicio específico
            if service_name == "azure":
                service = STTServiceFactory.create_service(
                    service_name,
                    subscription_key=os.getenv("AZURE_SPEECH_KEY"),
                    region=os.getenv("AZURE_SPEECH_REGION")
                )
            elif service_name == "whisper_local":
                service = STTServiceFactory.create_service(
                    service_name,
                    model_name="base"
                )
            elif service_name == "whisper_api":
                service = STTServiceFactory.create_service(
                    service_name,
                    api_key=os.getenv("OPENAI_API_KEY")
                )
            
            # Crear agente con servicio específico
            agent = VoiceflowSTTAgent(service, f"agent_{service_name}")
            
            # Verificar disponibilidad
            health = await agent.health_check()
            print(f"   Estado: {health['status']}")
            
        except Exception as e:
            print(f"   ❌ Error configurando {service_name}: {e}")


async def demo_configuration_options():
    """Demostración de opciones de configuración."""
    print("\n⚙️  === DEMO: Opciones de Configuración ===")
    
    try:
        agent = VoiceflowSTTAgent.create_from_config()
        
        # Mostrar configuración actual
        info = agent.get_service_info()
        print("📋 Configuración actual:")
        for key, value in info.items():
            if isinstance(value, dict):
                print(f"   {key}:")
                for subkey, subvalue in value.items():
                    print(f"      {subkey}: {subvalue}")
            else:
                print(f"   {key}: {value}")
        
        # Demostrar parámetros de transcripción personalizados
        print("\n🔧 Parámetros de transcripción personalizables:")
        print("   - language: idioma del audio (es-ES, en-US, etc.)")
        print("   - task: 'transcribe' o 'translate' (solo Whisper)")
        print("   - verbose: logs detallados (solo Whisper)")
        
    except Exception as e:
        print(f"❌ Error mostrando configuración: {e}")


async def main():
    """Función principal que ejecuta todas las demostraciones."""
    print("🚀 VoiceFlow STT Agent - Prueba de Concepto")
    print("=" * 50)
    
    # Verificar archivo de configuración
    if not Path(".env").exists():
        print("⚠️  Archivo .env no encontrado.")
        print("   1. Copia .env.example a .env")
        print("   2. Configura las variables según tu servicio preferido")
        print("   3. Vuelve a ejecutar este script")
        return
    
    # Ejecutar demostraciones
    await demo_basic_usage()
    await demo_multiple_services()
    await demo_configuration_options()
    
    print("\n✅ Demos completadas!")
    print("\n🎯 Próximos pasos:")
    print("   1. Coloca archivos de audio en la carpeta 'ejemplos/'")
    print("   2. Modifica las rutas en este script")
    print("   3. Ejecuta transcripciones reales")
    print("   4. Integra el agente en tu sistema multiagente")


if __name__ == "__main__":
    # Configurar logging básico para la demo
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Ejecutar demo
    asyncio.run(main())
