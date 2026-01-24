#!/usr/bin/env python3
"""
Simple VoiceFlow PoC Web UI starter with real audio transcription
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment for development
os.environ['ENVIRONMENT'] = 'development'
os.environ['DEBUG'] = 'true'

print("VoiceFlow PoC - Real Audio Transcription Demo")
print("=" * 50)

try:
    # Test STT availability
    print("Testing Azure STT availability...")
    from src.voiceflow_stt_agent import create_stt_agent
    stt_agent = create_stt_agent()
    print("Azure STT agent is available!")
except Exception as e:
    print(f"WARNING: Azure STT not available: {e}")
    print("Will use simulation mode")

# Start the web server
print("\nStarting web server...")
print("Open browser to: http://127.0.0.1:8002")
print("Features:")
print("   - Real audio recording from browser microphone")
print("   - Real Azure STT transcription (if configured)")
print("   - Simulated AI responses for demo")
print("   - Complete conversation flow")
print("\n" + "=" * 50)

if __name__ == "__main__":
    import uvicorn
    from web_ui.app import app
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8002,
        reload=True,
        log_level="info"
    )
