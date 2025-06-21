# Chat Interactivo Royal Bot v2
# Permite chatear directamente con Pablo usando el sistema contextual

import os
import sys
from royal_agents import run_contextual_conversation_sync, cleanup_old_contexts
from royal_agents.conversation_context import context_manager
import logging

# Configurar logging mínimo para evitar spam
logging.basicConfig(level=logging.ERROR)

def mostrar_bienvenida():
    """Muestra la bienvenida del chat"""
    print("\n" + "🎉" + "="*60 + "🎉")
    print("    💎 ROYAL COMPANY CHAT BOT v2.0 💎")
    print("    🤖 Pablo - Tu asistente personal")
    print("    🧠 Con memoria y contexto completo")
    print("🎉" + "="*60 + "🎉")
    print()
    print("💬 COMANDOS ESPECIALES:")
    print("   • 'salir' → Terminar chat")
    print("   • 'contexto' → Ver tu contexto actual")  
    print("   • 'limpiar' → Reiniciar conversación")
    print("   • 'ayuda' → Mostrar ejemplos")
    print("   • 'debug' → Ver información técnica")
    print()

def mostrar_ayuda():
    """Muestra ejemplos de preguntas"""
    print("\n💡 **EJEMPLOS DE PREGUNTAS:**")
    print()
    print("🚀 **Para Emprendedores:**")
    print("   • 'Quiero empezar a vender'")
    print("   • '¿Qué combos me recomendás?'")
    print("   • 'Soy nueva en esto'")
    print("   • 'Quiero ser revendedora'")
    print()
    print("🛍️ **Para Productos:**")
    print("   • '¿Tenés anillos de plata?'")
    print("   • 'Busco relojes Casio'")
    print("   • 'Mostrame maquillaje'")
    print("   • 'Quiero ver cadenas'")
    print()
    print("🧠 **Para Probar Memoria:**")
    print("   • Primero busca productos")
    print("   • Luego di 'quiero el segundo'")
    print("   • O 'me gusta el primero'")
    print()
    print("📞 **Para Info General:**")
    print("   • '¿Dónde están ubicados?'")
    print("   • '¿Cómo son los envíos?'")
    print("   • '¿Cuál es el mínimo?'")
    print()

def mostrar_contexto(user_id):
    """Muestra el contexto actual del usuario"""
    try:
        context = context_manager.get_or_create_context(user_id)
        conv = context.conversation
        
        print("\n🧠 **TU CONTEXTO ACTUAL:**")
        print(f"   👤 Usuario: {user_id}")
        print(f"   🔄 Estado: {conv.current_state}")
        print(f"   🚀 Emprendedor: {conv.is_entrepreneur} ({conv.experience_level})")
        print(f"   📦 Productos en memoria: {len(conv.recent_products)}")
        print(f"   💬 Conversaciones: {len(conv.interaction_history)}")
        
        if conv.product_interests:
            print(f"   💡 Intereses: {', '.join(conv.product_interests[-3:])}")
            
        if conv.budget_range:
            print(f"   💰 Presupuesto: {conv.budget_range}")
        
        if conv.recent_products:
            print("\n   📦 **Últimos productos vistos:**")
            for i, product in enumerate(conv.recent_products[-5:], 1):
                print(f"      {i}. {product.name} - ${product.price}")
                
        if conv.interaction_history:
            print(f"\n   💬 **Últimas {min(3, len(conv.interaction_history))} interacciones:**")
            for interaction in conv.interaction_history[-3:]:
                role = "👤" if interaction["role"] == "user" else "🤖"
                message = interaction["message"][:60] + "..." if len(interaction["message"]) > 60 else interaction["message"]
                print(f"      {role} {message}")
                
    except Exception as e:
        print(f"❌ Error mostrando contexto: {e}")

def mostrar_debug():
    """Muestra información de debug del sistema"""
    print("\n🔧 **INFORMACIÓN DE DEBUG:**")
    print(f"   📊 Contextos activos: {len(context_manager.active_contexts)}")
    print(f"   🐍 Python: {sys.version}")
    
    # Verificar variables de entorno
    print("\n   🌍 **Variables de Entorno:**")
    print(f"      OPENAI_API_KEY: {'✅ Configurado' if os.getenv('OPENAI_API_KEY') else '❌ NO CONFIGURADO'}")
    print(f"      WOOCOMMERCE_CONSUMER_KEY: {'✅ Configurado' if os.getenv('WOOCOMMERCE_CONSUMER_KEY') else '❌ NO CONFIGURADO'}")
    print(f"      WOOCOMMERCE_CONSUMER_SECRET: {'✅ Configurado' if os.getenv('WOOCOMMERCE_CONSUMER_SECRET') else '❌ NO CONFIGURADO'}")
    
    # Estados de contextos
    if context_manager.active_contexts:
        print("\n   👥 **Usuarios activos:**")
        for user_id, context in context_manager.active_contexts.items():
            conv = context.conversation
            print(f"      • {user_id}: {conv.current_state} ({len(conv.recent_products)} productos)")

def verificar_configuracion():
    """Verifica que la configuración esté correcta"""
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ **ERROR CRÍTICO:**")
        print("   OPENAI_API_KEY no está configurado")
        print()
        print("💡 **Para solucionarlo:**")
        print("   1. Conseguí tu API key en: https://platform.openai.com/api-keys")
        print("   2. Configurala con: export OPENAI_API_KEY=sk-tu_key_aqui")
        print("   3. O creá un archivo .env con: OPENAI_API_KEY=sk-tu_key_aqui")
        print()
        return False
    
    return True

def chat_principal():
    """Función principal del chat"""
    
    # Verificar configuración
    if not verificar_configuracion():
        return
    
    # Mostrar bienvenida
    mostrar_bienvenida()
    
    # Pedir nombre del usuario
    user_id = input("👤 ¿Cómo te llamás? (o presiona Enter para usar 'usuario'): ").strip()
    if not user_id:
        user_id = "usuario_chat"
    
    print(f"\n¡Perfecto {user_id}! Ya podemos charlar 🚀")
    print("💡 Tip: Probá preguntar sobre emprender o productos específicos")
    print("-" * 60)
    
    # Loop principal del chat
    while True:
        try:
            # Pedir mensaje del usuario
            user_message = input(f"\n👤 {user_id}: ").strip()
            
            # Comandos especiales
            if user_message.lower() in ['salir', 'exit', 'quit', 'chau', 'bye']:
                print(f"\n🤖 Pablo: ¡Hasta luego {user_id}! Fue un placer ayudarte 👋")
                print("🧹 Limpiando contextos antiguos...")
                cleanup_old_contexts()
                break
                
            elif user_message.lower() in ['contexto', 'context', 'info']:
                mostrar_contexto(user_id)
                continue
                
            elif user_message.lower() in ['limpiar', 'reset', 'reiniciar']:
                if user_id in context_manager.active_contexts:
                    del context_manager.active_contexts[user_id]
                print("🧹 Contexto limpiado. ¡Empezamos de nuevo!")
                continue
                
            elif user_message.lower() in ['ayuda', 'help', 'ejemplos']:
                mostrar_ayuda()
                continue
                
            elif user_message.lower() in ['debug', 'info_debug', 'sistema']:
                mostrar_debug()
                continue
            
            # Evitar mensajes vacíos
            if not user_message:
                print("💭 Escribe algo para charlar, o 'ayuda' para ver ejemplos")
                continue
            
            # Obtener respuesta del bot
            print(f"\n🤖 Pablo: ", end="", flush=True)
            
            # Usar función contextual
            response = run_contextual_conversation_sync(user_id, user_message)
            print(response)
            
        except KeyboardInterrupt:
            print(f"\n\n🤖 Pablo: ¡Hasta luego {user_id}! Nos vemos pronto 👋")
            break
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("\n💡 Posibles soluciones:")
            print("   • Verificá tu conexión a internet")
            print("   • Revisá que OPENAI_API_KEY esté bien configurado")
            print("   • Probá con un mensaje más simple")
            print("   • Escribí 'debug' para ver más información")

def main():
    """Función principal"""
    try:
        chat_principal()
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        print("\n🆘 **AYUDA:**")
        print("   1. Verificá que tengas instaladas las dependencias:")
        print("      pip install -r requirements.txt")
        print("   2. Asegurate de estar en el directorio correcto:")
        print("      cd /Users/gino/BotRoyalv2")
        print("   3. Configurá tu API key:")
        print("      export OPENAI_API_KEY=sk-tu_key")

if __name__ == "__main__":
    main() 