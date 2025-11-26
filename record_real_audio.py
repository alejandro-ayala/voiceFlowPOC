"""
Real-time audio recorder for Azure Speech Services
Records from your microphone and saves directly in optimized WAV format
"""
import sys
from pathlib import Path
import time

def grabar_audio_real():
    """Graba audio real desde el micrófono y lo guarda como WAV"""
    
    try:
        import sounddevice as sd
        import scipy.io.wavfile as wav
        import numpy as np
        
        print("🎙️  === GRABADOR DE AUDIO PARA AZURE ===")
        print()
        
        # Configuración optimizada para Azure Speech Services
        sample_rate = 16000  # 16kHz recomendado por Azure
        channels = 1         # Mono
        
        print("📋 Configuración:")
        print(f"   Sample Rate: {sample_rate} Hz")
        print(f"   Canales: {channels} (Mono)")
        print(f"   Formato: WAV")
        print()
        
        # Verificar dispositivos de audio disponibles
        print("🔍 Dispositivos de audio disponibles:")
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        
        if not input_devices:
            print("❌ No se encontraron micrófonos disponibles")
            return False
        
        for i, device in enumerate(input_devices):
            print(f"   {i}: {device['name']}")
        print()
        
        # Prepare recording
        output_file = Path("examples/audio_test.wav")
        output_file.parent.mkdir(exist_ok=True)
        
        print("🎯 INSTRUCCIONES:")
        print("   1. Habla claramente hacia tu micrófono")
        print("   2. Di algo como:")
        print('      "Hola, esta es una prueba del agente de voz a texto')
        print('       para el proyecto de turismo accesible."')
        print("   3. Presiona ENTER para empezar a grabar")
        print("   4. Presiona ENTER otra vez para parar")
        print()
        
        input("✅ Presiona ENTER cuando estés listo para grabar...")
        print()
        
        print("🔴 GRABANDO... (Presiona ENTER para parar)")
        print("🎙️  Habla ahora...")
        
        # Preparar arrays para almacenar audio
        audio_data = []
        
        def audio_callback(indata, frames, time, status):
            """Callback para capturar audio en tiempo real"""
            if status:
                print(f"⚠️  Estado del audio: {status}")
            audio_data.append(indata.copy())
        
        # Iniciar grabación
        with sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            callback=audio_callback,
            dtype=np.float32
        ):
            # Esperar a que el usuario presione ENTER
            input()
        
        if not audio_data:
            print("❌ No se grabó audio")
            return False
        
        print("⏹️  Grabación completada")
        print("💾 Procesando y guardando...")
        
        # Concatenar todos los chunks de audio
        recording = np.concatenate(audio_data, axis=0)
        
        # Convertir a int16 (formato estándar para WAV)
        recording_int16 = (recording * 32767).astype(np.int16)
        
        # Guardar como WAV
        wav.write(str(output_file), sample_rate, recording_int16)
        
        # Información del archivo creado
        file_size = output_file.stat().st_size / 1024
        duration_actual = len(recording) / sample_rate
        
        print("✅ Audio guardado exitosamente:")
        print(f"   Archivo: {output_file}")
        print(f"   Tamaño: {file_size:.1f} KB")
        print(f"   Duración: {duration_actual:.1f} segundos")
        print(f"   Formato: WAV {sample_rate}Hz Mono")
        print()
        
        return True
        
    except ImportError as e:
        missing_module = str(e).split("'")[1] if "'" in str(e) else "módulo desconocido"
        print(f"❌ ERROR: Falta el módulo {missing_module}")
        print()
        print("📦 Instala las dependencias necesarias:")
        print("   py -m pip install sounddevice scipy numpy")
        print()
        return False
        
    except Exception as e:
        print(f"❌ ERROR durante la grabación: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        print()
        print("💡 Posibles soluciones:")
        print("   1. Verifica que tu micrófono esté conectado")
        print("   2. Permite acceso al micrófono si Windows lo solicita")
        print("   3. Cierra otras aplicaciones que usen el micrófono")
        print()
        return False

def verificar_archivo_creado():
    """Verifica que el archivo se creó correctamente"""
    output_file = Path("ejemplos/audio_prueba.wav")
    
    if output_file.exists():
        file_size = output_file.stat().st_size
        if file_size > 1000:  # Al menos 1KB
            print("🎯 ¡Archivo listo para Azure Speech Services!")
            print("   Ejecuta: py test_complete.py")
            return True
        else:
            print("⚠️  El archivo es muy pequeño, puede estar corrupto")
            return False
    else:
        print("❌ No se pudo crear el archivo de audio")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando grabador de audio en tiempo real...")
    print()
    
    success = grabar_audio_real()
    
    print("-" * 60)
    if success:
        if verificar_archivo_creado():
            print("🏆 ¡GRABACIÓN EXITOSA!")
            print("   El archivo WAV está listo para Azure")
        else:
            print("🔧 Hubo problemas con el archivo creado")
    else:
        print("🔧 No se pudo completar la grabación")
        print("   Alternativa: Usa la Grabadora de Windows (msr)")
