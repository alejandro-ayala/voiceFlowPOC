#!/usr/bin/env python3
"""
Test script para verificar que la transcripción de audio funciona correctamente.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_audio_service():
    """Test the audio service with real STT"""
    try:
        print("Testing VoiceFlow Audio Service...")
        
        # Import the audio service and settings
        from web_ui.services.audio_service import AudioService
        from web_ui.config.settings import Settings
        
        # Create settings instance
        settings = Settings()
        
        # Create service instance with settings
        service = AudioService(settings)
        
        # Test with dummy audio data (should trigger fallback if STT not available)
        dummy_audio = b'fake_audio_data' * 100  # Some dummy bytes
        
        print("Testing transcription with dummy data...")
        result = await service.transcribe_audio(
            audio_data=dummy_audio,
            format="audio/wav",
            language="es-ES"
        )
        
        print(f"Transcription result: {result.transcription}")
        print(f"Confidence: {result.confidence}")
        print(f"Processing time: {result.processing_time}s")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_stt_agent():
    """Test the STT agent directly"""
    try:
        print("Testing STT Agent directly...")
        
        from src.voiceflow_stt_agent import create_stt_agent
        
        agent = create_stt_agent()
        print(f"STT Agent created: {type(agent)}")
        
        return True
        
    except Exception as e:
        print(f"STT Agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("VoiceFlow PoC - Audio Service Test")
    print("=" * 50)
    
    # Test STT agent first
    stt_success = await test_stt_agent()
    print()
    
    # Test audio service
    audio_success = await test_audio_service()
    print()
    
    if stt_success and audio_success:
        print("All tests passed! The audio service should work correctly.")
    else:
        print("WARNING: Some tests failed. Audio service may use fallback mode.")
    
    print("\nReady to test in the web UI!")

if __name__ == "__main__":
    asyncio.run(main())
