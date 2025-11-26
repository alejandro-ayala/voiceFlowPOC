"""
Interactive Real Audio Test for Accessible Tourism Voice Workflow
This script allows you to test the complete workflow with real voice input
"""

import asyncio
import sys
import time
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

record_user_audio = main_module.record_user_audio
transcribe_user_input = main_module.transcribe_user_input
AccessibleTourismMultiAgent = main_module.AccessibleTourismMultiAgent


async def test_with_real_audio():
    """Test the complete workflow with real audio recording"""
    
    print("🎤 === REAL AUDIO TEST FOR ACCESSIBLE TOURISM ===")
    print()
    print("This test will:")
    print("1. 🎙️  Record your voice talking about accessibility needs")
    print("2. 🤖 Transcribe your speech using Azure Speech Services")
    print("3. 🏛️  Process through the multi-agent tourism system")
    print("4. 📋 Generate accessible tourism recommendations")
    print()
    
    print("📝 SUGGESTED PHRASES TO TEST:")
    print("   • 'I need an accessible route to the museum'")
    print("   • 'Find me wheelchair accessible restaurants near the park'")
    print("   • 'I want to visit tourist attractions with audio guidance'")
    print("   • 'Show me accessible hotels in the city center'")
    print()
    
    input("🚀 Press ENTER when ready to start the test...")
    print()
    
    # Step 1: Record real audio
    print("=" * 50)
    print("STEP 1: RECORDING YOUR VOICE")
    print("=" * 50)
    
    audio_file = await record_user_audio()
    
    if not audio_file:
        print("❌ Recording failed. Test terminated.")
        return False
    
    print(f"✅ Audio recorded successfully: {audio_file}")
    print()
    
    # Step 2: Transcribe the audio
    print("=" * 50)
    print("STEP 2: SPEECH-TO-TEXT TRANSCRIPTION")
    print("=" * 50)
    
    transcription = await transcribe_user_input(audio_file)
    
    if not transcription:
        print("❌ Transcription failed or was empty.")
        print("💡 Tips for better recognition:")
        print("   • Speak clearly and at normal pace")
        print("   • Ensure microphone is close enough")
        print("   • Reduce background noise")
        print("   • Try speaking in English")
        return False
    
    print(f"🎯 TRANSCRIPTION SUCCESS: '{transcription}'")
    print()
    
    # Step 3: Process through multi-agent system
    print("=" * 50)
    print("STEP 3: MULTI-AGENT SYSTEM PROCESSING")
    print("=" * 50)
    
    # Initialize multi-agent system
    multi_agent_system = AccessibleTourismMultiAgent()
    await multi_agent_system.initialize()
    
    # Process the transcribed request
    result = await multi_agent_system.process_user_request(transcription)
    
    # Step 4: Show detailed results
    print()
    print("=" * 50)
    print("STEP 4: RESULTS & RECOMMENDATIONS")
    print("=" * 50)
    print()
    
    print("🎯 ANALYSIS OF YOUR REQUEST:")
    print(f"   Original Speech: '{result['user_input']}'")
    print(f"   Processing Time: {time.strftime('%H:%M:%S', time.localtime(result['timestamp']))}")
    print()
    
    print("🧠 INTELLIGENT PROCESSING:")
    for i, step in enumerate(result['processing_steps'], 1):
        agent_name = step['agent'].replace('_', ' ').title()
        print(f"   {i}. {agent_name}")
        print(f"      Task: {step['task']}")
        
        # Show specific results for each agent
        if step['agent'] == 'nlu_agent':
            nlu = step['result']
            print(f"      → Detected Intent: {nlu['intent']} (confidence: {nlu['confidence']*100:.1f}%)")
            if nlu['entities']:
                entities_str = ', '.join([f"{e['value']} ({e['type']})" for e in nlu['entities']])
                print(f"      → Found Entities: {entities_str}")
            else:
                print(f"      → Found Entities: None")
                
        elif step['agent'] == 'accessibility_agent':
            acc = step['result']
            active_features = [k.replace('_', ' ').title() for k, v in acc['accessibility_profile'].items() if v]
            print(f"      → Accessibility Needs: {', '.join(active_features)}")
            
        elif step['agent'] == 'planning_agent':
            plan = step['result']
            print(f"      → Generated Routes: {plan['routes_found']}")
        
        print()
    
    print("🏆 YOUR PERSONALIZED RECOMMENDATIONS:")
    for i, rec in enumerate(result['recommendations'], 1):
        print(f"   {i}. 🎯 {rec['title']}")
        print(f"      📄 {rec['description']}")
        if 'accessibility_score' in rec:
            print(f"      ♿ Accessibility Score: {rec['accessibility_score']}/10")
        if 'highlights' in rec:
            print(f"      🌟 Highlights: {', '.join(rec['highlights'])}")
        if 'additional_info' in rec:
            print(f"      💡 Note: {rec['additional_info']}")
        print()
    
    # System performance info
    status = await multi_agent_system.get_system_status()
    print("🔧 SYSTEM PERFORMANCE:")
    print(f"   Overall Status: {status['system_status'].upper()}")
    print(f"   Conversations Processed: {status['total_conversations']}")
    print(f"   Active Agents: {len(status['agents_status'])}")
    print()
    
    print("🎉 TEST COMPLETED SUCCESSFULLY!")
    print()
    print("💡 What happened:")
    print("   ✓ Your voice was recorded and saved as WAV audio")
    print("   ✓ Azure Speech Services transcribed your speech")
    print("   ✓ NLU agent understood your intent and extracted entities")
    print("   ✓ Accessibility agent analyzed your accessibility needs")
    print("   ✓ Planning agent generated personalized accessible routes")
    print("   ✓ System provided tailored tourism recommendations")
    
    return True


async def quick_voice_test():
    """Quick test just for voice recording and transcription"""
    
    print("🎤 === QUICK VOICE & STT TEST ===")
    print()
    print("This is a quick test to verify:")
    print("• Voice recording works")
    print("• Audio quality is good")
    print("• Speech-to-text transcription works")
    print()
    
    # Record audio
    audio_file = await record_user_audio()
    if not audio_file:
        return False
    
    # Transcribe
    transcription = await transcribe_user_input(audio_file)
    if transcription:
        print(f"🎯 SUCCESS! Transcribed: '{transcription}'")
        return True
    else:
        print("❌ Transcription failed")
        return False


async def main():
    """Main test menu"""
    import time
    
    print("🚀 REAL AUDIO TESTING FOR ACCESSIBLE TOURISM")
    print("=" * 55)
    
    # Check configuration
    if not Path(".env").exists():
        print("⚠️  .env file not found.")
        print("   1. Copy .env.example to .env")
        print("   2. Configure your Azure Speech Services credentials")
        print("   3. Run this script again")
        return
    
    print()
    print("Choose a test:")
    print("1. 🌍 Complete workflow test with real audio (RECOMMENDED)")
    print("2. 🎤 Quick voice recording & transcription test")
    print("3. ❌ Exit")
    print()
    
    try:
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == "1":
            success = await test_with_real_audio()
            if success:
                print("\n🏆 COMPLETE TEST PASSED!")
            else:
                print("\n⚠️  Test completed with issues - check output above")
                
        elif choice == "2":
            success = await quick_voice_test()
            if success:
                print("\n✅ Quick test passed!")
            else:
                print("\n❌ Quick test failed")
                
        elif choice == "3":
            print("👋 Goodbye!")
            return
            
        else:
            print("Invalid choice. Exiting...")
            
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    
    print("\n🎯 Next Steps:")
    print("   • Try different voice inputs and accents")
    print("   • Test various accessibility requirements")
    print("   • Experiment with different tourism requests")


if __name__ == "__main__":
    # Configure logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    asyncio.run(main())
