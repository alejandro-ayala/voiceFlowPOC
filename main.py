"""
VoiceFlow STT Agent - Proof of Concept for Accessible Tourism Multi-Agent System

This file demonstrates a complete workflow:
1. Audio recording from user microphone
2. Speech-to-text transcription using Azure Speech Services
3. Integration with multi-agent system for accessible tourism route planning
"""

import asyncio
import os
from pathlib import Path
import sys
import time
from typing import Dict, Any, Optional

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from src.voiceflow_stt_agent import VoiceflowSTTAgent
    from src.factory import STTServiceFactory
    from src.interfaces.stt_interface import STTServiceError, AudioFormatError
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure to install dependencies: pip install -r requirements.txt")
    sys.exit(1)


async def record_user_audio() -> Optional[str]:
    """Record audio from user microphone and save as WAV optimized for Azure Speech Services"""
    
    try:
        import sounddevice as sd
        import scipy.io.wavfile as wav
        import numpy as np
        
        print("🎙️  === AUDIO RECORDING FOR ACCESSIBLE TOURISM ===")
        print()
        
        # Optimal configuration for Azure Speech Services
        sample_rate = 16000  # 16kHz recommended by Azure
        channels = 1         # Mono
        
        print("📋 Recording Configuration:")
        print(f"   Sample Rate: {sample_rate} Hz")
        print(f"   Channels: {channels} (Mono)")
        print(f"   Format: WAV")
        print()
        
        # Check available audio devices
        print("🔍 Available audio devices:")
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        
        if not input_devices:
            print("❌ No microphones found")
            return None
        
        for i, device in enumerate(input_devices[:5]):  # Show first 5 devices
            print(f"   {i}: {device['name']}")
        print()
        
        # Prepare recording
        output_file = Path("examples/user_voice_input.wav")
        output_file.parent.mkdir(exist_ok=True)
        
        print("🎯 RECORDING INSTRUCTIONS:")
        print("   1. Speak clearly about your tourism needs (in Spanish)")
        print("   2. Example: 'Necesito una ruta accesible al museo'")
        print("   3. Press ENTER to start recording")
        print("   4. Press ENTER again to stop recording")
        print()
        
        input("✅ Press ENTER when ready to record...")
        print()
        
        print("🔴 RECORDING... (Press ENTER to stop)")
        print("🎙️  Habla ahora sobre tus necesidades de turismo accesible...")
        
        # Prepare arrays to store audio
        audio_data = []
        
        def audio_callback(indata, frames, time, status):
            """Callback to capture audio in real-time"""
            if status:
                print(f"⚠️  Audio status: {status}")
            audio_data.append(indata.copy())
        
        # Start recording
        with sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            callback=audio_callback,
            dtype=np.float32
        ):
            # Wait for user to press ENTER
            input()
        
        if not audio_data:
            print("❌ No audio recorded")
            return None
        
        print("⏹️  Recording completed")
        print("💾 Processing and saving...")
        
        # Concatenate all audio chunks
        recording = np.concatenate(audio_data, axis=0)
        
        # Convert to int16 (standard WAV format)
        recording_int16 = (recording * 32767).astype(np.int16)
        
        # Save as WAV
        wav.write(str(output_file), sample_rate, recording_int16)
        
        # File information
        file_size = output_file.stat().st_size / 1024
        duration_actual = len(recording) / sample_rate
        
        print("✅ Audio saved successfully:")
        print(f"   File: {output_file}")
        print(f"   Size: {file_size:.1f} KB")
        print(f"   Duration: {duration_actual:.1f} seconds")
        print(f"   Format: WAV {sample_rate}Hz Mono")
        print()
        
        return str(output_file)
        
    except ImportError as e:
        missing_module = str(e).split("'")[1] if "'" in str(e) else "unknown module"
        print(f"❌ ERROR: Missing module {missing_module}")
        print()
        print("📦 Install required dependencies:")
        print("   py -m pip install sounddevice scipy numpy")
        print()
        return None
        
    except Exception as e:
        print(f"❌ ERROR during recording: {e}")
        print(f"   Error type: {type(e).__name__}")
        print()
        print("💡 Possible solutions:")
        print("   1. Check that your microphone is connected")
        print("   2. Allow microphone access if Windows requests it")
        print("   3. Close other applications using the microphone")
        print()
        return None


async def transcribe_user_input(audio_file: str) -> Optional[str]:
    """Transcribe user audio input using STT agent"""
    
    print("🤖 === STT AGENT TRANSCRIPTION ===")
    
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
            return None
        
        # Get service information
        info = agent.get_service_info()
        print(f"   STT Service: {info['service_info']['service_name']}")
        print(f"   Supported formats: {', '.join(info['supported_formats'])}")
        
        # Transcribe audio
        print(f"🎵 Transcribing audio: {audio_file}")
        try:
            transcription = await agent.transcribe_audio(
                audio_file,
                language="es-ES"  # Spanish audio input
            )
            print(f"📝 Transcription: '{transcription}'")
            
            # Show statistics
            history = agent.get_transcription_history()
            print(f"📊 Total transcriptions: {len(history)}")
            
            return transcription
            
        except (STTServiceError, AudioFormatError) as e:
            print(f"❌ Transcription error: {e}")
            return None
                
    except Exception as e:
        print(f"❌ Error in STT processing: {e}")
        print("   Check your configuration in .env")
        return None


class AccessibleTourismMultiAgent:
    """Multi-agent system for accessible tourism route planning"""
    
    def __init__(self):
        self.stt_agent = None
        self.agents = {}
        self.conversation_history = []
    
    async def initialize(self):
        """Initialize the multi-agent system"""
        try:
            # Initialize STT agent
            self.stt_agent = VoiceflowSTTAgent.create_from_config("stt_agent")
            self.agents["stt"] = self.stt_agent
            
            print("✅ Multi-agent system initialized")
            return True
            
        except Exception as e:
            print(f"❌ Error initializing multi-agent system: {e}")
            return False
    
    async def process_user_request(self, transcription: str) -> Dict[str, Any]:
        """Process user tourism request through multi-agent system"""
        
        print("\n🏛️  === ACCESSIBLE TOURISM MULTI-AGENT PROCESSING ===")
        
        # Simulate multi-agent processing
        result = {
            "user_input": transcription,
            "timestamp": time.time(),
            "agents_involved": ["stt_agent", "nlu_agent", "planning_agent", "accessibility_agent"],
            "processing_steps": [],
            "recommendations": []
        }
        
        # Step 1: Natural Language Understanding (simulated)
        print("🧠 Step 1: Natural Language Understanding...")
        nlu_result = self._simulate_nlu_processing(transcription)
        result["processing_steps"].append({
            "agent": "nlu_agent",
            "task": "Extract intent and entities from user speech",
            "result": nlu_result
        })
        
        # Step 2: Accessibility Requirements Analysis (simulated)
        print("♿ Step 2: Accessibility Requirements Analysis...")
        accessibility_analysis = self._simulate_accessibility_analysis(nlu_result)
        result["processing_steps"].append({
            "agent": "accessibility_agent", 
            "task": "Analyze accessibility needs",
            "result": accessibility_analysis
        })
        
        # Step 3: Route Planning (simulated)
        print("🗺️  Step 3: Accessible Route Planning...")
        route_plan = self._simulate_route_planning(nlu_result, accessibility_analysis)
        result["processing_steps"].append({
            "agent": "planning_agent",
            "task": "Generate accessible tourism routes",
            "result": route_plan
        })
        
        # Generate final recommendations
        result["recommendations"] = self._generate_recommendations(route_plan)
        
        # Store in conversation history
        self.conversation_history.append(result)
        
        return result
    
    def _simulate_nlu_processing(self, text: str) -> Dict[str, Any]:
        """Simulate Natural Language Understanding processing"""
        
        # Simple keyword-based intent detection (in real system, use ML models)
        intent = "unknown"
        entities = []
        
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["route", "path", "way", "direction"]):
            intent = "route_planning"
        elif any(word in text_lower for word in ["museum", "restaurant", "hotel", "attraction"]):
            intent = "poi_information"
        elif any(word in text_lower for word in ["accessible", "wheelchair", "disability"]):
            intent = "accessibility_request"
        
        # Extract location entities (simplified)
        locations = ["museum", "restaurant", "hotel", "park", "station", "airport"]
        for location in locations:
            if location in text_lower:
                entities.append({"type": "location", "value": location})
        
        return {
            "intent": intent,
            "confidence": 0.85,
            "entities": entities,
            "processed_text": text
        }
    
    def _simulate_accessibility_analysis(self, nlu_result: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate accessibility requirements analysis"""
        
        # Default accessibility features
        accessibility_needs = {
            "wheelchair_accessible": True,
            "audio_guidance": False,
            "visual_assistance": False,
            "cognitive_support": False
        }
        
        # Analyze based on user input
        text = nlu_result.get("processed_text", "").lower()
        
        if "wheelchair" in text or "mobility" in text:
            accessibility_needs["wheelchair_accessible"] = True
        if "blind" in text or "visual" in text:
            accessibility_needs["visual_assistance"] = True
        if "deaf" in text or "hearing" in text:
            accessibility_needs["audio_guidance"] = True
        
        return {
            "accessibility_profile": accessibility_needs,
            "priority_features": ["wheelchair_accessible"],
            "special_requirements": []
        }
    
    def _simulate_route_planning(self, nlu_result: Dict[str, Any], accessibility: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate accessible route planning"""
        
        intent = nlu_result.get("intent", "unknown")
        entities = nlu_result.get("entities", [])
        
        # Generate sample accessible routes
        routes = []
        
        if intent == "route_planning" or intent == "poi_information":
            routes = [
                {
                    "id": "route_001",
                    "name": "Accessible City Center Tour",
                    "duration": "2 hours",
                    "accessibility_score": 9.2,
                    "waypoints": [
                        {"name": "Accessible Metro Station", "type": "transport", "accessibility": "full"},
                        {"name": "Museum of Modern Art", "type": "attraction", "accessibility": "wheelchair_friendly"},
                        {"name": "Inclusive Café", "type": "restaurant", "accessibility": "full"},
                        {"name": "Accessible Park", "type": "recreation", "accessibility": "partial"}
                    ]
                },
                {
                    "id": "route_002", 
                    "name": "Cultural Heritage Accessible Route",
                    "duration": "3 hours",
                    "accessibility_score": 8.7,
                    "waypoints": [
                        {"name": "Historic Cathedral", "type": "attraction", "accessibility": "partial"},
                        {"name": "Accessible Restaurant", "type": "dining", "accessibility": "full"},
                        {"name": "Art Gallery", "type": "culture", "accessibility": "wheelchair_friendly"}
                    ]
                }
            ]
        
        return {
            "routes_found": len(routes),
            "recommended_routes": routes,
            "filters_applied": accessibility["accessibility_profile"]
        }
    
    def _generate_recommendations(self, route_plan: Dict[str, Any]) -> list:
        """Generate final recommendations for the user"""
        
        recommendations = []
        
        for route in route_plan.get("recommended_routes", []):
            recommendation = {
                "type": "accessible_route",
                "title": route["name"],
                "description": f"A {route['duration']} accessible tour with {len(route['waypoints'])} stops",
                "accessibility_score": route["accessibility_score"],
                "highlights": [wp["name"] for wp in route["waypoints"][:3]]
            }
            recommendations.append(recommendation)
        
        # Add general accessibility tips
        recommendations.append({
            "type": "accessibility_tip",
            "title": "Accessibility Information",
            "description": "All recommended routes include wheelchair accessible paths and facilities",
            "additional_info": "Contact venues in advance to confirm current accessibility status"
        })
        
        return recommendations
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get status of all agents in the system"""
        status = {}
        
        for name, agent in self.agents.items():
            if hasattr(agent, 'health_check'):
                health = await agent.health_check()
                status[name] = health["status"]
            else:
                status[name] = "active"
        
        return {
            "system_status": "operational",
            "agents_status": status,
            "total_conversations": len(self.conversation_history)
        }


async def run_complete_workflow():
    """Run the complete accessible tourism workflow: record → transcribe → process"""
    
    print("🌍 === ACCESSIBLE TOURISM VOICE WORKFLOW ===")
    print()
    print("This workflow will:")
    print("1. 🎙️  Record your voice input about tourism needs")
    print("2. 🤖 Transcribe your speech using STT agent")
    print("3. 🏛️  Process your request through multi-agent system")
    print("4. 📋 Provide accessible tourism recommendations")
    print()
    
    # Step 1: Record user audio
    print("STEP 1: Audio Recording")
    print("-" * 30)
    audio_file = await record_user_audio()
    
    if not audio_file:
        print("❌ Could not record audio. Workflow terminated.")
        return False
    
    print()
    
    # Step 2: Transcribe audio
    print("STEP 2: Speech-to-Text Transcription")
    print("-" * 30)
    transcription = await transcribe_user_input(audio_file)
    
    if not transcription:
        print("❌ Could not transcribe audio. Workflow terminated.")
        return False
    
    print()
    
    # Step 3: Process through multi-agent system
    print("STEP 3: Multi-Agent System Processing")
    print("-" * 30)
    
    # Initialize multi-agent system
    multi_agent_system = AccessibleTourismMultiAgent()
    await multi_agent_system.initialize()
    
    # Process user request
    result = await multi_agent_system.process_user_request(transcription)
    
    # Step 4: Display results
    print()
    print("STEP 4: Results and Recommendations")
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
    
    print("✅ WORKFLOW COMPLETED SUCCESSFULLY!")
    print()
    print("💡 Next Steps:")
    print("   • Run the workflow again with different voice inputs")
    print("   • Modify accessibility requirements in your speech")
    print("   • Integrate with real tourism databases")
    print("   • Add more specialized agents (weather, transport, etc.)")
    
    return True


async def demo_service_selection():
    """Demo different STT service options"""
    print("\n🔄 === STT SERVICE SELECTION DEMO ===")
    
    # Get available services
    available_services = STTServiceFactory.get_available_services()
    print(f"📋 Available services: {', '.join(available_services)}")
    
    for service_name in available_services:
        print(f"\n🔧 Testing service: {service_name}")
        
        try:
            # Check service requirements
            if service_name == "azure":
                if not (os.getenv("AZURE_SPEECH_KEY") and os.getenv("AZURE_SPEECH_REGION")):
                    print("   ⚠️  Azure configuration not found, skipping...")
                    continue
                    
            elif service_name == "whisper_api":
                if not os.getenv("OPENAI_API_KEY"):
                    print("   ⚠️  OpenAI API key not found, skipping...")
                    continue
            
            # Create specific service
            if service_name == "azure":
                service = STTServiceFactory.create_service(
                    service_name,
                    subscription_key=os.getenv("AZURE_SPEECH_KEY"),
                    region=os.getenv("AZURE_SPEECH_REGION")
                )
            elif service_name == "whisper_local":
                service = STTServiceFactory.create_service(
                    service_name,
                    model_name="base"
                )
            elif service_name == "whisper_api":
                service = STTServiceFactory.create_service(
                    service_name,
                    api_key=os.getenv("OPENAI_API_KEY")
                )
            
            # Create agent with specific service
            agent = VoiceflowSTTAgent(service, f"agent_{service_name}")
            
            # Check availability
            health = await agent.health_check()
            print(f"   Status: {health['status']}")
            
        except Exception as e:
            print(f"   ❌ Error configuring {service_name}: {e}")


async def demo_configuration_info():
    """Show configuration information"""
    print("\n⚙️  === CONFIGURATION INFO ===")
    
    try:
        agent = VoiceflowSTTAgent.create_from_config()
        
        # Show current configuration
        info = agent.get_service_info()
        print("📋 Current configuration:")
        for key, value in info.items():
            if isinstance(value, dict):
                print(f"   {key}:")
                for subkey, subvalue in value.items():
                    print(f"      {subkey}: {subvalue}")
            else:
                print(f"   {key}: {value}")
        
        # Show customizable transcription parameters
        print("\n🔧 Customizable transcription parameters:")
        print("   - language: audio language (es-ES, en-US, etc.)")
        print("   - task: 'transcribe' or 'translate' (Whisper only)")
        print("   - verbose: detailed logs (Whisper only)")
        
    except Exception as e:
        print(f"❌ Error showing configuration: {e}")


async def main():
    """Main function that runs the accessible tourism voice workflow"""
    print("🚀 VoiceFlow STT Agent - Accessible Tourism PoC")
    print("=" * 55)
    
    # Check configuration file
    if not Path(".env").exists():
        print("⚠️  .env file not found.")
        print("   1. Copy .env.example to .env")
        print("   2. Configure variables according to your preferred service")
        print("   3. Run this script again")
        return
    
    print("Choose an option:")
    print("1. 🌍 Run complete accessible tourism workflow (RECOMMENDED)")
    print("2. 🔧 Demo STT service selection")
    print("3. ⚙️  Show configuration information")
    print()
    
    try:
        choice = input("Enter your choice (1-3) or press Enter for option 1: ").strip()
        if not choice:
            choice = "1"
        
        if choice == "1":
            await run_complete_workflow()
        elif choice == "2":
            await demo_service_selection()
        elif choice == "3":
            await demo_configuration_info()
        else:
            print("Invalid option. Running complete workflow...")
            await run_complete_workflow()
            
    except KeyboardInterrupt:
        print("\n⏹️  Workflow interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    
    print("\n🎯 Next steps:")
    print("   1. Try recording different accessibility requests")
    print("   2. Test with various STT services")
    print("   3. Extend the multi-agent system with real tourism APIs")
    print("   4. Integrate with accessibility databases")


if __name__ == "__main__":
    # Configure basic logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run main workflow
    asyncio.run(main())
