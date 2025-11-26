"""
Generador de instrucciones para crear audio WAV para Azure Speech Services
"""

def mostrar_instrucciones():
    print("🎙️  === CREAR AUDIO WAV PARA AZURE ===\n")
    
    print("📋 OPCIÓN 1: Grabadora de Sonidos de Windows")
    print("1. Presiona Windows + R")
    print("2. Escribe: msr")
    print("3. Presiona Enter (se abre Grabadora de Sonidos)")
    print("4. Haz clic en el botón de grabar (círculo rojo)")
    print("5. Graba 10-15 segundos diciendo:")
    print('   "Hola, esta es una prueba del agente de voz a texto')
    print('    para el proyecto de turismo accesible."')
    print("6. Haz clic en parar")
    print("7. Guarda como: audio_prueba.wav")
    print("8. Mueve el archivo a la carpeta: ejemplos/\n")
    
    print("📋 OPCIÓN 2: Usar tu archivo M4A actual")
    print("Si tienes el archivo M4A, puedes intentar:")
    print("1. Renombrar audio_prueba.m4a a audio_prueba.wav")
    print("2. O convertir online en: https://convertio.co/m4a-wav/")
    print("3. Descargar y guardar en ejemplos/\n")
    
    print("📋 OPCIÓN 3: Usar otro software")
    print("- Audacity (gratuito)")
    print("- VLC Media Player (File → Convert)")
    print("- Cualquier editor de audio\n")
    
    print("🎯 FORMATO OBJETIVO:")
    print("   Archivo: ejemplos/audio_prueba.wav")
    print("   Formato: WAV")
    print("   Calidad: Cualquiera (Azure lo procesará)")
    print("   Duración: 10-30 segundos")
    print("   Idioma: Español\n")
    
    print("✅ UNA VEZ QUE TENGAS EL ARCHIVO WAV:")
    print("   py test_complete.py")

if __name__ == "__main__":
    mostrar_instrucciones()
