"""
Test script for the complete accessible tourism workflow using pre-recorded audio
This bypasses audio recording and uses a known working audio file to test STT and multi-agent processing
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from src.voiceflow_stt_agent import VoiceflowSTTAgent
    from src.interfaces.stt_interface import STTServiceError, AudioFormatError
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure to install dependencies: pip install -r requirements.txt")
    sys.exit(1)

# Import the multi-agent system from main.py
import importlib.util
spec = importlib.util.spec_from_file_location("main", "main.py")
main_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_module)

AccessibleTourismMultiAgent = main_module.AccessibleTourismMultiAgent


async def test_complete_workflow_with_file():
    """Test the complete workflow using a pre-recorded audio file"""
    
    print("🧪 === TESTING COMPLETE WORKFLOW WITH PRE-RECORDED AUDIO ===")
    print()
    
    # Use the known working audio file
    audio_file = "examples/test_audio.wav"
    
    if not Path(audio_file).exists():
        print(f"❌ Test audio file not found: {audio_file}")
        print("Make sure the audio file exists from previous tests.")
        return False
    
    print(f"🎵 Using test audio file: {audio_file}")
    print()
    
    # Step 1: Transcribe audio
    print("STEP 1: Speech-to-Text Transcription")
    print("-" * 30)
    
    try:
        # Create STT agent from configuration
        print("📋 Creating STT agent from configuration...")
        agent = VoiceflowSTTAgent.create_from_config()
        
        # Check agent health
        print("🔍 Checking agent health...")
        health = await agent.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Service available: {health['service_available']}")
        
        if health['status'] != 'healthy':
            print("❌ STT agent is not healthy")
            return False
        
        # Get service information
        info = agent.get_service_info()
        print(f"   STT Service: {info['service_info']['service_name']}")
        print(f"   Supported formats: {', '.join(info['supported_formats'])}")
        
        # Transcribe audio
        print(f"🎵 Transcribing audio: {audio_file}")
        transcription = await agent.transcribe_audio(
            audio_file,
            language="en-US"  # English for international accessibility
        )
        
        if not transcription:
            print("❌ No transcription received")
            return False
            
        print(f"📝 Transcription: '{transcription}'")
        
        # Show statistics
        history = agent.get_transcription_history()
        print(f"📊 Total transcriptions: {len(history)}")
        print()
        
    except (STTServiceError, AudioFormatError) as e:
        print(f"❌ Transcription error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error in STT processing: {e}")
        return False
    
    # Step 2: Process through multi-agent system
    print("STEP 2: Multi-Agent System Processing")
    print("-" * 30)
    
    try:
        # Initialize multi-agent system
        multi_agent_system = AccessibleTourismMultiAgent()
        await multi_agent_system.initialize()
        
        # Process user request
        result = await multi_agent_system.process_user_request(transcription)
        
        # Step 3: Display results
        print()
        print("STEP 3: Results and Recommendations")
        print("-" * 30)
        print()
        print("🎯 PROCESSING RESULTS:")
        print(f"   User Input: '{result['user_input']}'")
        print(f"   Agents Involved: {', '.join(result['agents_involved'])}")
        print()
        
        print("📋 PROCESSING STEPS:")
        for i, step in enumerate(result['processing_steps'], 1):
            print(f"   {i}. {step['agent']}: {step['task']}")
            if step['agent'] == 'nlu_agent':
                nlu = step['result']
                print(f"      → Intent: {nlu['intent']} (confidence: {nlu['confidence']})")
                print(f"      → Entities: {len(nlu['entities'])} found")
            elif step['agent'] == 'accessibility_agent':
                acc = step['result']
                features = [k for k, v in acc['accessibility_profile'].items() if v]
                print(f"      → Accessibility needs: {', '.join(features)}")
            elif step['agent'] == 'planning_agent':
                plan = step['result']
                print(f"      → Routes found: {plan['routes_found']}")
        print()
        
        print("🏆 RECOMMENDATIONS:")
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"   {i}. {rec['title']}")
            print(f"      {rec['description']}")
            if 'accessibility_score' in rec:
                print(f"      Accessibility Score: {rec['accessibility_score']}/10")
            if 'highlights' in rec:
                print(f"      Highlights: {', '.join(rec['highlights'])}")
            print()
        
        # System status
        status = await multi_agent_system.get_system_status()
        print("🔧 SYSTEM STATUS:")
        print(f"   Overall: {status['system_status']}")
        print(f"   Total conversations: {status['total_conversations']}")
        print()
        
        print("✅ COMPLETE WORKFLOW TEST SUCCESSFUL!")
        print()
        print("🎯 What was tested:")
        print("   ✓ STT agent initialization and health check")
        print("   ✓ Audio transcription with Azure Speech Services")
        print("   ✓ Multi-agent system initialization")
        print("   ✓ Natural Language Understanding (simulated)")
        print("   ✓ Accessibility requirements analysis")
        print("   ✓ Accessible route planning")
        print("   ✓ Recommendation generation")
        print("   ✓ System status reporting")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in multi-agent processing: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Testing Complete Accessible Tourism Workflow")
    print("=" * 50)
    
    # Check configuration file
    if not Path(".env").exists():
        print("⚠️  .env file not found.")
        print("   1. Copy .env.example to .env")
        print("   2. Configure variables according to your preferred service")
        print("   3. Run this script again")
        sys.exit(1)
    
    # Run test
    success = asyncio.run(test_complete_workflow_with_file())
    
    if success:
        print("\n🏆 All tests passed! The complete workflow is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
