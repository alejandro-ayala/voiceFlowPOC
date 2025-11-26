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
        from src.voiceflow_stt_agent import VoiceflowSTTAgent
        
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
            print("   Verifica tu configuración en .env")
            return
        
        # 3. Verificar archivo de audio
        audio_file = "ejemplos/audio_prueba.wav"
        print(f"\n3. Verificando archivo de audio: {audio_file}")
        
        if not Path(audio_file).exists():
            print("   ❌ Archivo de audio no encontrado")
            print("   INSTRUCCIONES:")
            print("   1. Crea la carpeta 'ejemplos' si no existe")
            print("   2. Graba un audio de 10-15 segundos en español")
            print("   3. Guárdalo como 'ejemplos/audio_prueba.wav'")
            print("   4. O usa cualquier archivo WAV/MP3 que tengas")
            
            # Listar archivos disponibles
            ejemplos_dir = Path("ejemplos")
            if ejemplos_dir.exists():
                archivos = list(ejemplos_dir.glob("*.*"))
                if archivos:
                    print(f"\n   Archivos encontrados en ejemplos/:")
                    for archivo in archivos:
                        print(f"      - {archivo.name}")
                    print("   Cambia el nombre a 'audio_prueba.wav' o modifica el código")
            
            return False
        
        print("   ✅ Archivo de audio encontrado")
        
        # Mostrar info del archivo
        file_size = Path(audio_file).stat().st_size / 1024  # KB
        print(f"   Tamaño: {file_size:.1f} KB")
        
        # 4. Transcribir
        print("\n4. Iniciando transcripción...")
        print("   ⏳ Procesando audio con Azure Speech Services...")
        print("   (Esto puede tomar unos segundos...)")
        
        transcription = await agent.transcribe_audio(
            audio_file,
            language="es-ES"  # Español de España
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
        print(f"   Formatos soportados: {', '.join(info['supported_formats'])}")
        
        # 6. Probar con diferentes idiomas (opcional)
        print("\n6. ¿Probar con inglés? (y/n):", end=" ")
        try:
            respuesta = input().lower().strip()
            if respuesta in ['y', 'yes', 'sí', 's']:
                print("   ⏳ Transcribiendo en inglés...")
                transcription_en = await agent.transcribe_audio(
                    audio_file,
                    language="en-US"
                )
                print(f"   📝 En inglés: '{transcription_en}'")
        except:
            pass  # Skip si hay problema con input
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nDEBUG INFO:")
        print(f"   Error type: {type(e).__name__}")
        
        # Ayuda específica según el error
        if "could not be resolved" in str(e) or "No module named" in str(e):
            print("   💡 Solución: Instala las dependencias")
            print("      pip install -r requirements.txt")
            print("      pip install azure-cognitiveservices-speech")
        elif "AZURE_SPEECH_KEY" in str(e) or "No encontrada" in str(e):
            print("   💡 Solución: Configura tu archivo .env")
            print("      Copia .env.example a .env")
            print("      Agrega tu AZURE_SPEECH_KEY")
        elif "Audio file not found" in str(e):
            print("   💡 Solución: Crea un archivo de audio")
            print("      Graba audio en ejemplos/audio_prueba.wav")
        
        return False

if __name__ == "__main__":
    print("🚀 Iniciando test completo del agente STT...")
    print("📋 Verificando configuración Azure y transcripción de audio")
    print("-" * 60)
    
    success = asyncio.run(test_stt_complete())
    
    print("-" * 60)
    if success:
        print("🏆 ¡TODO FUNCIONA CORRECTAMENTE!")
        print("   ✅ Azure Speech Services conectado")
        print("   ✅ Agente STT operativo") 
        print("   ✅ Transcripción de audio exitosa")
        print("\n🎯 El agente está listo para integrar en tu sistema multiagente")
        print("   Usa: agent = VoiceflowSTTAgent.create_from_config()")
        print("   Transcribe: await agent.transcribe_audio('audio.wav')")
    else:
        print("🔧 NECESITA CONFIGURACIÓN")
        print("   📖 Consulta: AZURE_SETUP_GUIDE.md")
        print("   🔍 Ejecuta primero: python test_azure_connection.py")
