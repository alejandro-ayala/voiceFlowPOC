"""
Convertir archivo M4A a WAV para Azure Speech Services
"""
import sys
from pathlib import Path

# Agregar src al path
sys.path.append(str(Path(__file__).parent / "src"))

def convert_audio_to_wav():
    """Convierte el archivo M4A a WAV optimizado para Azure"""
    
    try:
        from pydub import AudioSegment
        print("📁 Convirtiendo M4A a WAV para Azure Speech Services...")
        
        # Cargar archivo M4A
        input_file = "ejemplos/audio_prueba.m4a"
        output_file = "ejemplos/audio_prueba.wav"
        
        if not Path(input_file).exists():
            print(f"❌ Archivo no encontrado: {input_file}")
            return False
        
        print(f"🔄 Cargando: {input_file}")
        audio = AudioSegment.from_file(input_file, format="m4a")
        
        # Convertir a formato óptimo para Azure Speech:
        # - 16kHz sample rate (recomendado para speech recognition)
        # - Mono (1 canal)
        # - WAV format
        print("🔧 Optimizando para Azure Speech Services...")
        audio_optimized = audio.set_frame_rate(16000).set_channels(1)
        
        # Exportar como WAV
        print(f"💾 Guardando: {output_file}")
        audio_optimized.export(output_file, format="wav")
        
        # Mostrar información
        original_size = Path(input_file).stat().st_size / 1024
        new_size = Path(output_file).stat().st_size / 1024
        duration = len(audio) / 1000  # segundos
        
        print("✅ Conversión completada:")
        print(f"   Original: {original_size:.1f} KB (M4A)")
        print(f"   Nuevo: {new_size:.1f} KB (WAV 16kHz mono)")
        print(f"   Duración: {duration:.1f} segundos")
        print(f"   Archivo listo: {output_file}")
        
        return True
        
    except ImportError:
        print("❌ ERROR: pydub no está instalado")
        print("   Instala con: py -m pip install pydub")
        return False
        
    except Exception as e:
        print(f"❌ ERROR convirtiendo audio: {e}")
        print("   Tipo de error:", type(e).__name__)
        return False

if __name__ == "__main__":
    print("🎵 === CONVERTIDOR DE AUDIO PARA AZURE ===")
    
    success = convert_audio_to_wav()
    
    if success:
        print("\n🎯 ¡CONVERSIÓN EXITOSA!")
        print("   Ahora puedes ejecutar: py test_complete.py")
        print("   El test usará el archivo WAV optimizado")
    else:
        print("\n🔧 Hay problemas en la conversión")
        print("   Alternativa: Graba directamente en formato WAV")
