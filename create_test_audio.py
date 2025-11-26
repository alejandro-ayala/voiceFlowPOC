"""
Script para crear un archivo de audio de prueba usando Windows SAPI (síntesis de voz)
"""
import os
import sys
from pathlib import Path

def create_test_audio():
    """Crear archivo de audio de prueba usando Windows SAPI"""
    
    print("🎵 === CREANDO AUDIO DE PRUEBA ===")
    
    # Texto para sintetizar
    text = "Hola, esta es una prueba del agente de voz a texto para el proyecto de turismo accesible."
    
    # Crear carpeta ejemplos si no existe
    ejemplos_dir = Path("ejemplos")
    ejemplos_dir.mkdir(exist_ok=True)
    
    audio_file = ejemplos_dir / "audio_prueba.wav"
    
    print(f"📝 Texto a sintetizar: '{text}'")
    print(f"💾 Guardando en: {audio_file}")
    
    try:
        # Usar Windows SAPI para crear audio
        import win32com.client
        
        # Crear objeto de síntesis de voz
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        
        # Crear objeto de archivo de audio
        file_stream = win32com.client.Dispatch("SAPI.SpFileStream")
        
        # Configurar archivo de salida
        file_stream.Open(str(audio_file), 3)  # 3 = SSFMCreateForWrite
        speaker.AudioOutputStream = file_stream
        
        # Sintetizar y guardar
        speaker.Speak(text)
        
        # Cerrar archivo
        file_stream.Close()
        
        print("✅ Audio de prueba creado exitosamente!")
        print(f"📂 Archivo: {audio_file}")
        print(f"📊 Tamaño: {audio_file.stat().st_size / 1024:.1f} KB")
        
        return True
        
    except ImportError:
        print("❌ No se puede usar SAPI (falta pywin32)")
        print("\n💡 ALTERNATIVAS:")
        print("1. Instalar pywin32: pip install pywin32")
        print("2. O grabar manualmente con Grabadora de Windows:")
        print("   - Abrir 'Grabadora de sonidos' de Windows")
        print("   - Grabar 10-15 segundos diciendo el texto de arriba")
        print(f"   - Guardar como: {audio_file}")
        return False
        
    except Exception as e:
        print(f"❌ Error creando audio: {e}")
        print("\n💡 SOLUCIÓN MANUAL:")
        print("1. Abrir 'Grabadora de sonidos' de Windows")
        print("2. Grabar diciendo:")
        print(f"   '{text}'")
        print(f"3. Guardar como: {audio_file}")
        return False

if __name__ == "__main__":
    success = create_test_audio()
    
    if success:
        print("\n🎯 ¡Listo! Ahora puedes ejecutar:")
        print("   py test_complete.py")
    else:
        print("\n🔧 Crea el audio manualmente y luego ejecuta:")
        print("   py test_complete.py")
