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
        print("   Ejecuta: pip install azure-cognitiveservices-speech")
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
        print("   Ejecuta: python test_complete.py")
    else:
        print("\n💥 HAY PROBLEMAS EN LA CONFIGURACIÓN")
        print("   Revisa los errores anteriores")
        print("   Consulta: AZURE_SETUP_GUIDE.md")
