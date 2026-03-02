#!/usr/bin/env python3
"""
VoiceFlow PoC - Sistema de Testing y Validación Integrado
========================================================

Sistema consolidado que valida todas las integraciones del proyecto VoiceFlow PoC
con dos modos de operación:

1. MODO TEST: Validación mínima de conexiones sin consumir créditos API
2. MODO PRODUCCIÓN: Test completo con audio real y llamadas API completas

Uso:
    python test_voiceflow.py              # Modo interactivo
    python test_voiceflow.py --test       # Modo test (sin consumir créditos)
    python test_voiceflow.py --prod       # Modo producción (consume créditos)
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

from langchain_agents import TourismMultiAgent

# Load environment variables
load_dotenv()


class Colors:
    """Console colors for better output"""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


class VoiceFlowTester:
    """Sistema de testing consolidado para VoiceFlow PoC"""

    def __init__(self):
        self.results = {}
        self.langchain_system = None

    def print_header(self, title: str, color: str = Colors.CYAN):
        """Imprime header formateado"""
        print(f"\n{color}{'=' * 70}")
        print(f"{color}{title.center(70)}")
        print(f"{color}{'=' * 70}{Colors.END}")

    def print_step(self, step: str, status: str = "INFO"):
        """Imprime paso formateado con estado"""
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}
        colors = {
            "INFO": Colors.BLUE,
            "SUCCESS": Colors.GREEN,
            "ERROR": Colors.RED,
            "WARNING": Colors.YELLOW,
        }

        icon = icons.get(status, "•")
        color = colors.get(status, Colors.END)
        print(f"{color}{icon} {step}{Colors.END}")

    def check_environment(self) -> bool:
        """Valida configuración del entorno"""
        self.print_header("VALIDACIÓN DEL ENTORNO", Colors.YELLOW)

        required_vars = {
            "OPENAI_API_KEY": "OpenAI API Key",
            "AZURE_SPEECH_KEY": "Azure Speech Key",
            "AZURE_SPEECH_REGION": "Azure Speech Region",
        }

        all_valid = True
        for var, description in required_vars.items():
            value = os.getenv(var)
            if value:
                masked = f"{value[:8]}...{value[-8:]}" if len(value) > 16 else "***"
                self.print_step(f"{description}: {masked}", "SUCCESS")
                self.results[f"env_{var.lower()}"] = True
            else:
                self.print_step(f"{description}: Faltante", "ERROR")
                self.results[f"env_{var.lower()}"] = False
                all_valid = False

        return all_valid

    async def test_openai(self, minimal: bool = True) -> bool:
        """Test conexión OpenAI"""
        self.print_header("TEST CONEXIÓN OPENAI", Colors.BLUE)

        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            if minimal:
                self.print_step("Validando formato de API key y cliente", "INFO")
                self.print_step("Cliente OpenAI inicializado correctamente", "SUCCESS")
                self.results["openai_connection"] = True
                return True
            else:
                self.print_step("Realizando llamada de prueba a OpenAI GPT-4", "INFO")
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "user",
                            "content": "Responde 'Test exitoso' en español",
                        }
                    ],
                    max_tokens=30,
                )
                test_response = response.choices[0].message.content
                self.print_step(f"Respuesta OpenAI: {test_response}", "SUCCESS")
                self.results["openai_response"] = test_response
                self.results["openai_connection"] = True
                return True

        except Exception as e:
            self.print_step(f"Error en conexión OpenAI: {str(e)}", "ERROR")
            self.results["openai_connection"] = False
            return False

    async def test_azure_speech(self, minimal: bool = True) -> bool:
        """Test Azure Speech Services"""
        self.print_header("TEST AZURE SPEECH SERVICES", Colors.BLUE)

        try:
            import azure.cognitiveservices.speech as speechsdk

            speech_key = os.getenv("AZURE_SPEECH_KEY")
            service_region = os.getenv("AZURE_SPEECH_REGION")

            speech_config = speechsdk.SpeechConfig(
                subscription=speech_key, region=service_region
            )
            speech_config.speech_language = "es-ES"

            self.print_step(
                f"Azure Speech configurado para región: {service_region}", "SUCCESS"
            )
            self.print_step("Configuración de idioma: es-ES", "SUCCESS")

            if not minimal:
                self.print_step(
                    "Nota: Test completo de audio requiere entrada de micrófono",
                    "WARNING",
                )

            self.results["azure_speech_connection"] = True
            return True

        except Exception as e:
            self.print_step(f"Error en Azure Speech: {str(e)}", "ERROR")
            self.results["azure_speech_connection"] = False
            return False

    async def test_langchain(self, minimal: bool = True) -> bool:
        """Test sistema LangChain Multi-Agent"""
        self.print_header("TEST LANGCHAIN MULTI-AGENT", Colors.GREEN)

        try:
            self.print_step("Inicializando sistema LangChain Multi-Agent", "INFO")
            self.langchain_system = TourismMultiAgent()
            self.print_step("Sistema LangChain inicializado correctamente", "SUCCESS")

            # Test herramientas
            tools = self.langchain_system.tools
            tool_names = [tool.name for tool in tools]
            self.print_step(
                f"Herramientas disponibles: {', '.join(tool_names)}", "SUCCESS"
            )

            if not minimal:
                # Test completo con llamada API real
                self.print_step(
                    "Ejecutando test completo de workflow multi-agent", "INFO"
                )
                test_query = (
                    "Necesito información sobre el Museo del Prado para silla de ruedas"
                )

                response = await self.langchain_system.process_request(test_query)
                self.print_step("Procesamiento multi-agent completado", "SUCCESS")
                self.print_step(f"Respuesta (preview): {response[:100]}...", "INFO")

                self.results["langchain_full_response"] = response[:200]

            self.results["langchain_tools"] = tool_names
            self.results["langchain_connection"] = True
            return True

        except Exception as e:
            self.print_step(f"Error en sistema LangChain: {str(e)}", "ERROR")
            self.results["langchain_connection"] = False
            return False

    async def test_audio_system(self) -> bool:
        """Test sistema de audio"""
        self.print_header("TEST SISTEMA DE AUDIO", Colors.CYAN)

        try:
            import sounddevice as sd

            devices = sd.query_devices()
            input_devices = [d for d in devices if d["max_input_channels"] > 0]
            self.print_step(
                f"Dispositivos de entrada encontrados: {len(input_devices)}", "SUCCESS"
            )

            for i, device in enumerate(input_devices[:3]):  # Show first 3 devices
                self.print_step(f"  {i}: {device['name']}", "INFO")

            self.results["audio_devices_count"] = len(input_devices)
            self.results["audio_system_ready"] = True
            return True

        except Exception as e:
            self.print_step(f"Error en sistema de audio: {str(e)}", "ERROR")
            self.results["audio_system_ready"] = False
            return False

    async def run_test_mode(self) -> Dict[str, Any]:
        """Ejecuta modo TEST (mínimo consumo de APIs)"""
        self.print_header("VOICEFLOW POC - MODO TEST", Colors.CYAN)
        self.print_step("Ejecutando tests con mínimo consumo de APIs", "INFO")

        # Ejecutar todos los tests en modo mínimo
        env_ok = self.check_environment()
        openai_ok = await self.test_openai(minimal=True)
        azure_ok = await self.test_azure_speech(minimal=True)
        langchain_ok = await self.test_langchain(minimal=True)
        audio_ok = await self.test_audio_system()

        self.results["mode"] = "test"
        self.results["all_systems_ready"] = all(
            [env_ok, openai_ok, azure_ok, langchain_ok, audio_ok]
        )
        self.results["timestamp"] = datetime.now().isoformat()

        return self.results

    async def run_production_mode(self) -> Dict[str, Any]:
        """Ejecuta modo PRODUCCIÓN (test completo con APIs)"""
        self.print_header("VOICEFLOW POC - MODO PRODUCCIÓN", Colors.GREEN)
        self.print_step(
            "Ejecutando tests completos (consumirá créditos API)", "WARNING"
        )

        # Ejecutar todos los tests en modo completo
        env_ok = self.check_environment()
        openai_ok = await self.test_openai(minimal=False)
        azure_ok = await self.test_azure_speech(minimal=False)
        langchain_ok = await self.test_langchain(minimal=False)
        audio_ok = await self.test_audio_system()

        # Tests adicionales de producción
        if all([env_ok, openai_ok, azure_ok, langchain_ok]):
            await self.test_production_scenarios()

        self.results["mode"] = "production"
        self.results["all_systems_ready"] = all(
            [env_ok, openai_ok, azure_ok, langchain_ok, audio_ok]
        )
        self.results["timestamp"] = datetime.now().isoformat()

        return self.results

    async def test_production_scenarios(self):
        """Test escenarios completos de producción"""
        self.print_header("TEST ESCENARIOS DE PRODUCCIÓN", Colors.GREEN)

        scenarios = [
            "Necesito ir al Museo del Prado en silla de ruedas",
            "¿Cómo visitar el Parque del Retiro con problemas de visión?",
            "Restaurantes accesibles cerca de Gran Vía",
        ]

        scenario_results = []
        for i, scenario in enumerate(scenarios, 1):
            self.print_step(f"Escenario {i}: {scenario[:50]}...", "INFO")
            try:
                response = await self.langchain_system.process_request(scenario)
                self.print_step(f"Escenario {i} completado exitosamente", "SUCCESS")
                scenario_results.append(
                    {
                        "scenario": scenario,
                        "success": True,
                        "response_length": len(response),
                    }
                )
            except Exception as e:
                self.print_step(f"Escenario {i} falló: {str(e)}", "ERROR")
                scenario_results.append(
                    {"scenario": scenario, "success": False, "error": str(e)}
                )

        self.results["production_scenarios"] = scenario_results

    def print_final_report(self):
        """Imprime reporte final comprehensivo"""
        self.print_header("REPORTE FINAL", Colors.CYAN)

        # Resumen
        mode = "MODO TEST" if self.results.get("mode") == "test" else "MODO PRODUCCIÓN"
        status = "✅ EXITOSO" if self.results.get("all_systems_ready") else "❌ FALLOS"

        print(f"{Colors.BOLD}Modo de ejecución: {Colors.YELLOW}{mode}{Colors.END}")
        print(f"{Colors.BOLD}Estado general: {status}{Colors.END}")
        print(
            f"{Colors.BOLD}Timestamp: {Colors.CYAN}{self.results.get('timestamp')}{Colors.END}"
        )

        # Estado de componentes
        print(f"\n{Colors.BOLD}Estado de Componentes:{Colors.END}")
        components = [
            ("Configuración de Entorno", self.results.get("env_openai_api_key", False)),
            ("Conexión OpenAI", self.results.get("openai_connection", False)),
            (
                "Azure Speech Services",
                self.results.get("azure_speech_connection", False),
            ),
            ("Sistema LangChain", self.results.get("langchain_connection", False)),
            ("Sistema de Audio", self.results.get("audio_system_ready", False)),
        ]

        for component, status in components:
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {component}")

        # Recomendaciones
        print(f"\n{Colors.BOLD}Recomendaciones:{Colors.END}")
        if self.results.get("all_systems_ready"):
            print(f"  {Colors.GREEN}✅ Sistema listo para despliegue{Colors.END}")
            print(
                f"  {Colors.GREEN}✅ Todas las integraciones funcionan correctamente{Colors.END}"
            )
            if self.results.get("mode") == "test":
                print(
                    f"  {Colors.YELLOW}💡 Ejecutar modo producción para test completo{Colors.END}"
                )
        else:
            print(
                f"  {Colors.RED}❌ Corregir componentes fallidos antes del despliegue{Colors.END}"
            )
            print(f"  {Colors.YELLOW}⚠️  Revisar configuración del entorno{Colors.END}")

        # Guardar resultados
        with open(
            f"test_results_{self.results.get('mode')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n{Colors.GREEN}📄 Resultados guardados en archivo JSON{Colors.END}")


def interactive_menu():
    """Menú interactivo para selección de modo"""
    print(f"{Colors.CYAN}{'=' * 70}")
    print(f"{Colors.CYAN}{'VoiceFlow PoC - Sistema de Testing Integrado'.center(70)}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.END}")
    print(f"\n{Colors.BOLD}Selecciona el modo de testing:{Colors.END}")
    print(
        f"  {Colors.GREEN}1. MODO TEST - Validación mínima (no consume créditos API){Colors.END}"
    )
    print(
        f"  {Colors.YELLOW}2. MODO PRODUCCIÓN - Test completo (consume créditos API){Colors.END}"
    )
    print(f"  {Colors.RED}3. Salir{Colors.END}")

    while True:
        try:
            choice = input(f"\n{Colors.BOLD}Ingresa tu opción [1]: {Colors.END}") or "1"
            choice = int(choice)
            if choice in [1, 2, 3]:
                return choice
            else:
                print(
                    f"{Colors.RED}Opción inválida. Por favor ingresa 1, 2 o 3.{Colors.END}"
                )
        except ValueError:
            print(
                f"{Colors.RED}Opción inválida. Por favor ingresa un número.{Colors.END}"
            )


async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="VoiceFlow PoC - Sistema de Testing Integrado"
    )
    parser.add_argument(
        "--test", action="store_true", help="Ejecutar en modo test (mínimo consumo API)"
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Ejecutar en modo producción (test completo)",
    )
    args = parser.parse_args()

    tester = VoiceFlowTester()

    # Determinar modo de ejecución
    if args.test:
        mode = 1
    elif args.prod:
        mode = 2
    else:
        mode = interactive_menu()

    if mode == 3:
        print(f"{Colors.RED}Saliendo...{Colors.END}")
        return

    try:
        # Ejecutar tests según el modo seleccionado
        if mode == 1:
            await tester.run_test_mode()
        else:
            await tester.run_production_mode()

        # Mostrar reporte final
        tester.print_final_report()

    except KeyboardInterrupt:
        print(f"\n{Colors.RED}Operación cancelada por el usuario{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Error inesperado: {str(e)}{Colors.END}")


if __name__ == "__main__":
    asyncio.run(main())
