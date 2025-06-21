#!/usr/bin/env python3
"""
Script de pruebas automatizadas para el Royal Bot
Ejecuta una serie de tests para verificar el funcionamiento del agente
"""

import asyncio
import sys
import os
from dotenv import load_dotenv
from agents import Runner
from royal_agents.royal_agent import royal_consultation_agent

# Cargar variables de entorno
load_dotenv(".env")

class RoyalBotTester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_results = []
        
    def print_header(self):
        print("🧪 ROYAL BOT - PRUEBAS AUTOMATIZADAS")
        print("=" * 50)
        
    def print_test_result(self, test_name, passed, response="", expected=""):
        """Imprime el resultado de un test"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        
        if not passed and expected:
            print(f"   Esperado: {expected}")
        if response:
            print(f"   Respuesta: {response[:100]}...")
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
            
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "response": response
        })
        print("-" * 40)
    
    async def test_basic_greeting(self):
        """Test: Saludo básico"""
        try:
            result = await Runner.run(
                royal_consultation_agent,
                "Hola",
                context={"client_id": "test_greeting"}
            )
            response = result.final_output.lower()
            
            # Verificar que se presente como Pablo
            has_pablo = "pablo" in response
            # Verificar tono argentino
            has_argentine_tone = any(word in response for word in ["dale", "che", "posta", "mirá"])
            # Verificar que no use palabras prohibidas
            no_forbidden = not any(word in response for word in ["aquí", "puedes", "tienes", "debes"])
            
            passed = has_pablo and no_forbidden
            self.print_test_result(
                "Saludo básico y presentación",
                passed,
                response,
                "Debe presentarse como Pablo con tono argentino"
            )
            
        except Exception as e:
            self.print_test_result("Saludo básico", False, str(e))
    
    async def test_company_info(self):
        """Test: Información de la empresa"""
        try:
            result = await Runner.run(
                royal_consultation_agent,
                "¿Cómo funciona Royal?",
                context={"client_id": "test_company"}
            )
            response = result.final_output.lower()
            
            # Verificar que mencione información clave
            has_mayorista = "mayorista" in response
            has_minimum = "40" in response or "40000" in response
            has_minorista = "minorista" in response
            
            passed = has_mayorista and has_minimum and has_minorista
            self.print_test_result(
                "Información de la empresa",
                passed,
                response,
                "Debe mencionar mayorista, mínimo y minorista"
            )
            
        except Exception as e:
            self.print_test_result("Información de la empresa", False, str(e))
    
    async def test_shipping_info(self):
        """Test: Información de envíos"""
        try:
            result = await Runner.run(
                royal_consultation_agent,
                "¿Cuánto cuesta el envío?",
                context={"client_id": "test_shipping"}
            )
            response = result.final_output.lower()
            
            # Verificar información de envíos
            has_andreani = "andreani" in response
            has_cordoba_price = "4999" in response or "4.999" in response
            has_national_price = "7499" in response or "7.499" in response
            has_free_shipping = "80" in response and "gratis" in response
            
            passed = has_andreani and (has_cordoba_price or has_national_price)
            self.print_test_result(
                "Información de envíos",
                passed,
                response,
                "Debe mencionar Andreani y precios de envío"
            )
            
        except Exception as e:
            self.print_test_result("Información de envíos", False, str(e))
    
    async def test_jewelry_repairs(self):
        """Test: Arreglos de joyas"""
        try:
            result = await Runner.run(
                royal_consultation_agent,
                "¿Hacen arreglos de joyas?",
                context={"client_id": "test_repairs"}
            )
            response = result.final_output.lower()
            
            # Verificar información de arreglos
            has_repairs = "arreglo" in response or "reparacion" in response
            has_silver = "plata" in response and "925" in response
            has_gold = "oro" in response and "18k" in response
            has_process = "foto" in response or "whatsapp" in response
            
            passed = has_repairs and has_silver and has_gold
            self.print_test_result(
                "Arreglos de joyas",
                passed,
                response,
                "Debe mencionar arreglos, plata 925 y oro 18K"
            )
            
        except Exception as e:
            self.print_test_result("Arreglos de joyas", False, str(e))
    
    async def test_payment_info(self):
        """Test: Información de pagos"""
        try:
            result = await Runner.run(
                royal_consultation_agent,
                "¿Cómo puedo pagar?",
                context={"client_id": "test_payment"}
            )
            response = result.final_output
            
            # Verificar información de pagos
            has_card = "tarjeta" in response.lower()
            has_transfer = "transferencia" in response.lower()
            has_cash = "efectivo" in response.lower()
            has_cbu = "4530000800014232361716" in response
            
            passed = has_card and has_transfer and has_cbu
            self.print_test_result(
                "Información de pagos",
                passed,
                response,
                "Debe mencionar métodos de pago y CBU"
            )
            
        except Exception as e:
            self.print_test_result("Información de pagos", False, str(e))
    
    async def test_forbidden_words(self):
        """Test: Palabras prohibidas"""
        try:
            result = await Runner.run(
                royal_consultation_agent,
                "¿Dónde están ubicados?",
                context={"client_id": "test_forbidden"}
            )
            response = result.final_output.lower()
            
            # Verificar que no use palabras prohibidas
            forbidden_words = ["aquí", "puedes", "quieres", "tienes", "debes", "tú", "tu"]
            used_forbidden = [word for word in forbidden_words if word in response]
            
            passed = len(used_forbidden) == 0
            self.print_test_result(
                "Evitar palabras prohibidas",
                passed,
                response,
                f"No debe usar: {', '.join(used_forbidden) if used_forbidden else 'ninguna'}"
            )
            
        except Exception as e:
            self.print_test_result("Evitar palabras prohibidas", False, str(e))
    
    async def test_argentine_tone(self):
        """Test: Tono argentino"""
        try:
            result = await Runner.run(
                royal_consultation_agent,
                "¿Qué productos tienen?",
                context={"client_id": "test_tone"}
            )
            response = result.final_output.lower()
            
            # Verificar palabras argentinas
            argentine_words = ["dale", "che", "posta", "mirá", "ojo", "bárbaro", "genial", "joya"]
            used_argentine = [word for word in argentine_words if word in response]
            
            # Verificar conjugaciones argentinas
            has_vos = "podés" in response or "querés" in response or "tenés" in response
            
            passed = len(used_argentine) > 0 or has_vos
            self.print_test_result(
                "Tono argentino",
                passed,
                response,
                f"Debe usar palabras argentinas. Usó: {', '.join(used_argentine)}"
            )
            
        except Exception as e:
            self.print_test_result("Tono argentino", False, str(e))
    
    async def test_no_repeated_greetings(self):
        """Test: No saludos repetidos"""
        try:
            client_id = "test_no_repeat"
            
            # Primer mensaje
            result1 = await Runner.run(
                royal_consultation_agent,
                "Hola",
                context={"client_id": client_id}
            )
            response1 = result1.final_output.lower()
            
            # Segundo mensaje del mismo cliente
            result2 = await Runner.run(
                royal_consultation_agent,
                "¿Tienen relojes?",
                context={"client_id": client_id}
            )
            response2 = result2.final_output.lower()
            
            # El segundo mensaje no debería saludar
            has_greeting_first = "hola" in response1 or "pablo" in response1
            has_greeting_second = "hola" in response2 or "pablo" in response2
            
            passed = has_greeting_first and not has_greeting_second
            self.print_test_result(
                "No saludos repetidos",
                passed,
                f"1er msg tienen saludo: {has_greeting_first}, 2do msg: {has_greeting_second}"
            )
            
        except Exception as e:
            self.print_test_result("No saludos repetidos", False, str(e))
    
    async def run_all_tests(self):
        """Ejecuta todos los tests"""
        self.print_header()
        
        tests = [
            ("Saludo básico", self.test_basic_greeting),
            ("Información empresa", self.test_company_info),
            ("Información envíos", self.test_shipping_info),
            ("Arreglos de joyas", self.test_jewelry_repairs),
            ("Información pagos", self.test_payment_info),
            ("Palabras prohibidas", self.test_forbidden_words),
            ("Tono argentino", self.test_argentine_tone),
            ("No saludos repetidos", self.test_no_repeated_greetings)
        ]
        
        for test_name, test_func in tests:
            print(f"\n🧪 Ejecutando: {test_name}")
            await test_func()
            
        self.print_summary()
    
    def print_summary(self):
        """Imprime el resumen de resultados"""
        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0
        
        print("\n" + "=" * 50)
        print("📊 RESUMEN DE PRUEBAS")
        print("=" * 50)
        print(f"✅ Pasaron: {self.passed}")
        print(f"❌ Fallaron: {self.failed}")
        print(f"📈 Porcentaje: {percentage:.1f}%")
        
        if self.failed > 0:
            print("\n🔍 TESTS FALLIDOS:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"   - {result['test']}")
        
        print("\n" + "=" * 50)
        
        if percentage >= 80:
            print("🎉 ¡Excelente! El bot está funcionando correctamente")
        elif percentage >= 60:
            print("⚠️  El bot funciona pero necesita algunas mejoras")
        else:
            print("❌ El bot necesita revisión urgente")
            
        return percentage >= 80

def check_environment():
    """Verifica la configuración del entorno"""
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY no configurada")
        print("   Configurá la variable de entorno o archivo .env")
        return False
    
    print("✅ Configuración del entorno verificada")
    return True

async def main():
    """Función principal"""
    if not check_environment():
        sys.exit(1)
    
    print("🚀 Iniciando pruebas del Royal Bot...")
    print("   Esto puede tomar unos minutos...\n")
    
    tester = RoyalBotTester()
    
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error fatal ejecutando pruebas: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 