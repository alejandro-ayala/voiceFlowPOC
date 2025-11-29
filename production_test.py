#!/usr/bin/env python3
"""
VoiceFlow PoC - Sistema de Testing de Producción con Audio Real
==============================================================

Este módulo proporciona testing completo end-to-end del sistema VoiceFlow PoC
incluyendo grabación de audio real, transcripción STT y procesamiento multi-agente.

Funcionalidades:
- Grabación de audio en tiempo real
- Transcripción con Azure Speech Services
- Procesamiento completo con LangChain Multi-Agent
- Validación end-to-end del flujo completo

Uso:
    python production_test.py              # Test interactivo completo
    python production_test.py --scenarios  # Test con escenarios predefinidos
"""

import asyncio
import os
import sys
import json
import argparse
import wave
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from langchain_agents import TourismMultiAgent

# Load environment variables
load_dotenv()

class Colors:
    """Console colors"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

class ProductionTester:
    """Sistema de testing de producción con audio real"""
    
    def __init__(self):
        self.results = {}
        self.langchain_system = None
        self.setup_audio_config()
        
    def setup_audio_config(self):
        """Configura parámetros de audio"""
        self.audio_config = {
            'sample_rate': int(os.getenv('DEFAULT_SAMPLE_RATE', 16000)),
            'channels': int(os.getenv('DEFAULT_CHANNELS', 1)),
            'format': 'wav',
            'chunk_size': 1024
        }
    
    def print_header(self, title: str, color: str = Colors.CYAN):
        """Imprime header formateado"""
        print(f"\n{color}{'=' * 70}")
        print(f"{color}{title.center(70)}")
        print(f"{color}{'=' * 70}{Colors.END}")
    
    def print_step(self, step: str, status: str = "INFO"):
        """Imprime paso formateado"""
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
        colors = {"INFO": Colors.BLUE, "SUCCESS": Colors.GREEN, "ERROR": Colors.RED, "WARNING": Colors.YELLOW}
        
        icon = icons.get(status, "•")
        color = colors.get(status, Colors.END)
        print(f"{color}{icon} {step}{Colors.END}")
    
    async def initialize_systems(self) -> bool:
        """Inicializa todos los sistemas necesarios"""
        self.print_header("INICIALIZACIÓN DE SISTEMAS", Colors.YELLOW)
        
        try:
            # Verificar variables de entorno
            required_vars = ['OPENAI_API_KEY', 'AZURE_SPEECH_KEY', 'AZURE_SPEECH_REGION']
            for var in required_vars:
                if not os.getenv(var):
                    self.print_step(f"Variable de entorno faltante: {var}", "ERROR")
                    return False
            
            self.print_step("Variables de entorno validadas", "SUCCESS")
            
            # Inicializar LangChain
            self.langchain_system = TourismMultiAgent()
            self.print_step("Sistema LangChain Multi-Agent inicializado", "SUCCESS")
            
            # Verificar sistema de audio
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]
            if not input_devices:
                self.print_step("No hay dispositivos de audio disponibles", "ERROR")
                return False
            
            self.print_step(f"Sistema de audio listo ({len(input_devices)} dispositivos)", "SUCCESS")
            return True
            
        except Exception as e:
            self.print_step(f"Error en inicialización: {str(e)}", "ERROR")
            return False
    
    def record_audio(self, duration: int = 10) -> Optional[str]:
        """Graba audio del micrófono"""
        try:
            import sounddevice as sd
            import numpy as np
            
            self.print_step(f"Iniciando grabación de {duration} segundos...", "INFO")
            self.print_step("🔴 GRABANDO... Habla ahora sobre turismo accesible", "WARNING")
            
            # Grabar audio
            recording = sd.rec(
                int(duration * self.audio_config['sample_rate']),
                samplerate=self.audio_config['sample_rate'],
                channels=self.audio_config['channels'],
                dtype=np.int16
            )
            sd.wait()  # Esperar a que termine la grabación
            
            # Guardar a archivo temporal
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(self.audio_config['channels'])
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.audio_config['sample_rate'])
                wf.writeframes(recording.tobytes())
            
            self.print_step("⏹️ Grabación completada", "SUCCESS")
            return temp_file.name
            
        except Exception as e:
            self.print_step(f"Error en grabación de audio: {str(e)}", "ERROR")
            return None
    
    async def transcribe_audio(self, audio_file: str) -> Optional[str]:
        """Transcribe audio usando Azure Speech Services"""
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            self.print_step("Iniciando transcripción con Azure Speech Services...", "INFO")
            
            # Configurar Azure Speech
            speech_key = os.getenv('AZURE_SPEECH_KEY')
            service_region = os.getenv('AZURE_SPEECH_REGION')
            
            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
            speech_config.speech_language = "es-ES"
            
            # Configurar entrada de audio
            audio_config = speechsdk.audio.AudioConfig(filename=audio_file)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            
            # Realizar transcripción
            result = speech_recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                self.print_step("🎯 Transcripción completada exitosamente", "SUCCESS")
                self.print_step(f"Texto transcrito: '{result.text}'", "INFO")
                return result.text
            else:
                self.print_step(f"Error en transcripción: {result.reason}", "ERROR")
                return None
                
        except Exception as e:
            self.print_step(f"Error en transcripción: {str(e)}", "ERROR")
            return None
        finally:
            # Limpiar archivo temporal
            if os.path.exists(audio_file):
                os.unlink(audio_file)
    
    async def process_with_langchain(self, text: str) -> Optional[str]:
        """Procesa texto con sistema LangChain Multi-Agent"""
        try:
            self.print_step("Procesando con sistema LangChain Multi-Agent...", "INFO")
            
            response = await self.langchain_system.process_request(text)
            
            self.print_step("🤖 Procesamiento multi-agent completado", "SUCCESS")
            return response
            
        except Exception as e:
            self.print_step(f"Error en procesamiento LangChain: {str(e)}", "ERROR")
            return None
    
    async def run_end_to_end_test(self) -> Dict[str, Any]:
        """Ejecuta test completo end-to-end"""
        self.print_header("TEST END-TO-END COMPLETO", Colors.GREEN)
        
        # Inicializar sistemas
        if not await self.initialize_systems():
            return {"success": False, "error": "Falló inicialización de sistemas"}
        
        # Grabar audio
        self.print_step("Preparándose para grabar audio...", "INFO")
        print(f"\n{Colors.YELLOW}🎙️  INSTRUCCIONES PARA GRABACIÓN:{Colors.END}")
        print(f"   1. Habla claramente sobre tus necesidades de turismo accesible")
        print(f"   2. Ejemplos: 'Necesito una ruta al museo en silla de ruedas'")
        print(f"   3. La grabación durará 10 segundos")
        
        input(f"\n{Colors.BOLD}Presiona ENTER cuando estés listo para grabar...{Colors.END}")
        
        audio_file = self.record_audio(duration=10)
        if not audio_file:
            return {"success": False, "error": "Falló grabación de audio"}
        
        # Transcribir
        transcription = await self.transcribe_audio(audio_file)
        if not transcription:
            return {"success": False, "error": "Falló transcripción de audio"}
        
        # Procesar con LangChain
        response = await self.process_with_langchain(transcription)
        if not response:
            return {"success": False, "error": "Falló procesamiento LangChain"}
        
        # Compilar resultados
        results = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "transcription": transcription,
            "response": response,
            "audio_config": self.audio_config
        }
        
        return results
    
    async def run_predefined_scenarios(self) -> Dict[str, Any]:
        """Ejecuta escenarios predefinidos sin grabación de audio"""
        self.print_header("TEST ESCENARIOS PREDEFINIDOS", Colors.BLUE)
        
        if not await self.initialize_systems():
            return {"success": False, "error": "Falló inicialización"}
        
        scenarios = [
            "Necesito ir al Museo del Prado en silla de ruedas, ¿cuál es la mejor ruta?",
            "¿Cómo puedo visitar el Parque del Retiro si tengo problemas de visión?",
            "Necesito restaurantes accesibles cerca de la Gran Vía para cenar",
            "¿Qué líneas de metro son accesibles para personas con muletas?"
        ]
        
        scenario_results = []
        for i, scenario in enumerate(scenarios, 1):
            self.print_step(f"Escenario {i}: {scenario[:50]}...", "INFO")
            
            try:
                response = await self.process_with_langchain(scenario)
                if response:
                    self.print_step(f"Escenario {i} completado exitosamente", "SUCCESS")
                    scenario_results.append({
                        "scenario": scenario,
                        "success": True,
                        "response_length": len(response),
                        "response_preview": response[:150] + "..."
                    })
                else:
                    raise Exception("Respuesta vacía")
                    
            except Exception as e:
                self.print_step(f"Escenario {i} falló: {str(e)}", "ERROR")
                scenario_results.append({
                    "scenario": scenario,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "scenarios": scenario_results,
            "total_scenarios": len(scenarios),
            "successful_scenarios": sum(1 for s in scenario_results if s.get("success"))
        }
    
    def print_results(self, results: Dict[str, Any]):
        """Imprime resultados del testing"""
        self.print_header("RESULTADOS DEL TEST", Colors.CYAN)
        
        if results.get("success"):
            self.print_step("✅ Test completado exitosamente", "SUCCESS")
            
            if "transcription" in results:
                # Resultados end-to-end
                print(f"\n{Colors.BOLD}📝 Transcripción:{Colors.END}")
                print(f"   {results['transcription']}")
                print(f"\n{Colors.BOLD}🤖 Respuesta del Sistema:{Colors.END}")
                print(f"   {results['response'][:300]}...")
                
            elif "scenarios" in results:
                # Resultados de escenarios
                total = results['total_scenarios']
                successful = results['successful_scenarios']
                print(f"\n{Colors.BOLD}📊 Resumen de Escenarios:{Colors.END}")
                print(f"   Total: {total}")
                print(f"   Exitosos: {successful}")
                print(f"   Tasa de éxito: {(successful/total)*100:.1f}%")
        else:
            self.print_step(f"❌ Test falló: {results.get('error')}", "ERROR")
        
        # Guardar resultados
        filename = f"production_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        self.print_step(f"Resultados guardados en: {filename}", "SUCCESS")

def interactive_menu():
    """Menú interactivo"""
    print(f"{Colors.CYAN}{'=' * 70}")
    print(f"{Colors.CYAN}{'VoiceFlow PoC - Testing de Producción'.center(70)}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.END}")
    print(f"\n{Colors.BOLD}Selecciona el tipo de test:{Colors.END}")
    print(f"  {Colors.GREEN}1. Test End-to-End con Audio Real (GRABACIÓN + STT + LangChain){Colors.END}")
    print(f"  {Colors.BLUE}2. Test Escenarios Predefinidos (solo LangChain){Colors.END}")
    print(f"  {Colors.RED}3. Salir{Colors.END}")
    
    while True:
        try:
            choice = input(f"\n{Colors.BOLD}Ingresa tu opción [1]: {Colors.END}") or "1"
            choice = int(choice)
            if choice in [1, 2, 3]:
                return choice
            else:
                print(f"{Colors.RED}Opción inválida.{Colors.END}")
        except ValueError:
            print(f"{Colors.RED}Opción inválida.{Colors.END}")

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='VoiceFlow PoC - Testing de Producción')
    parser.add_argument('--scenarios', action='store_true', help='Ejecutar solo escenarios predefinidos')
    args = parser.parse_args()
    
    tester = ProductionTester()
    
    try:
        if args.scenarios:
            mode = 2
        else:
            mode = interactive_menu()
        
        if mode == 3:
            print(f"{Colors.RED}Saliendo...{Colors.END}")
            return
        
        # Ejecutar test según modo seleccionado
        if mode == 1:
            results = await tester.run_end_to_end_test()
        else:
            results = await tester.run_predefined_scenarios()
        
        # Mostrar resultados
        tester.print_results(results)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Operación cancelada{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Error inesperado: {str(e)}{Colors.END}")

if __name__ == "__main__":
    asyncio.run(main())
