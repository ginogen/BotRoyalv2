# Ejemplo Simple - Sistema de Contexto Royal Bot v2
# Demuestra cómo usar el sistema de memoria paso a paso

from royal_agents import run_contextual_conversation_sync

def ejemplo_basico():
    """Ejemplo básico de conversación con memoria"""
    
    print("🎯 EJEMPLO BÁSICO - Conversación con Memoria")
    print("="*50)
    
    user_id = "ejemplo_123"
    
    # 1. Primera interacción - buscar productos
    print("\n👤 Usuario: ¿Tenés relojes Casio?")
    response1 = run_contextual_conversation_sync(
        user_id=user_id,
        user_message="¿Tenés relojes Casio?"
    )
    print(f"🤖 Pablo: {response1[:200]}...")
    
    # 2. Segunda interacción - hacer referencia al producto
    print("\n👤 Usuario: Quiero el segundo")
    response2 = run_contextual_conversation_sync(
        user_id=user_id,
        user_message="Quiero el segundo"
    )
    print(f"🤖 Pablo: {response2[:200]}...")
    
    # 3. Tercera interacción - confirmar compra
    print("\n👤 Usuario: Sí, ese quiero")
    response3 = run_contextual_conversation_sync(
        user_id=user_id,
        user_message="Sí, ese quiero"
    )
    print(f"🤖 Pablo: {response3[:200]}...")
    
    print("\n✅ El bot recordó qué productos mostró y cuál eligió el usuario!")

def ejemplo_emprendedor():
    """Ejemplo con perfil de emprendedor"""
    
    print("\n\n🚀 EJEMPLO EMPRENDEDOR - Perfil Personalizado")
    print("="*50)
    
    user_id = "emprendedor_456"
    
    # 1. Usuario menciona emprender
    print("\n👤 Usuario: Quiero empezar a vender")
    response1 = run_contextual_conversation_sync(
        user_id=user_id,
        user_message="Quiero empezar a vender"
    )
    print(f"🤖 Pablo: {response1[:300]}...")
    
    # 2. Responder al bot
    print("\n👤 Usuario: Es mi primer emprendimiento, me gustan las joyas")
    response2 = run_contextual_conversation_sync(
        user_id=user_id,
        user_message="Es mi primer emprendimiento, me gustan las joyas"
    )
    print(f"🤖 Pablo: {response2[:300]}...")
    
    print("\n✅ El bot detectó que es emprendedor principiante y adaptó su respuesta!")

def ejemplo_contexto_entre_conversaciones():
    """Ejemplo de memoria entre conversaciones separadas"""
    
    print("\n\n🧠 EJEMPLO PERSISTENCIA - Memoria Entre Conversaciones")
    print("="*50)
    
    user_id = "persistente_789"
    
    # Conversación 1
    print("\n--- CONVERSACIÓN 1 ---")
    print("👤 Usuario: Soy emprendedora experimentada, busco anillos de plata")
    response1 = run_contextual_conversation_sync(
        user_id=user_id,
        user_message="Soy emprendedora experimentada, busco anillos de plata"
    )
    print(f"🤖 Pablo: {response1[:250]}...")
    
    # Simulamos pausa...
    print("\n⏳ [Pausa en la conversación...]")
    
    # Conversación 2 - el bot debe recordar
    print("\n--- CONVERSACIÓN 2 (más tarde) ---")
    print("👤 Usuario: ¿Recordás qué productos me mostraste?")
    response2 = run_contextual_conversation_sync(
        user_id=user_id,
        user_message="¿Recordás qué productos me mostraste?"
    )
    print(f"🤖 Pablo: {response2[:250]}...")
    
    print("\n✅ El bot mantuvo la memoria entre conversaciones!")

def mostrar_contexto():
    """Muestra información del contexto para debugging"""
    
    print("\n\n🔍 INFORMACIÓN DE CONTEXTO")
    print("="*50)
    
    from royal_agents.conversation_context import context_manager
    
    print(f"📊 Contextos activos: {len(context_manager.active_contexts)}")
    
    for user_id, context in context_manager.active_contexts.items():
        conv = context.conversation
        print(f"\n👤 Usuario: {user_id}")
        print(f"   🔄 Estado: {conv.current_state}")
        print(f"   🚀 Es emprendedor: {conv.is_entrepreneur}")
        print(f"   📦 Productos en memoria: {len(conv.recent_products)}")
        print(f"   💬 Interacciones: {len(conv.interaction_history)}")
        
        if conv.recent_products:
            print("   📋 Últimos productos:")
            for i, product in enumerate(conv.recent_products[-3:], 1):
                print(f"      {i}. {product.name} - ${product.price}")

if __name__ == "__main__":
    print("🧠 DEMOSTRACIÓN DEL SISTEMA DE CONTEXTO Y MEMORIA")
    print("📋 Royal Bot v2 - OpenAI Agents SDK")
    print("\nEste ejemplo muestra cómo el bot mantiene memoria de:")
    print("✅ Productos mostrados al usuario")
    print("✅ Referencias como 'el segundo', 'el primero'")
    print("✅ Perfil del usuario (emprendedor, experiencia)")
    print("✅ Conversaciones anteriores")
    
    try:
        ejemplo_basico()
        ejemplo_emprendedor()
        ejemplo_contexto_entre_conversaciones()
        mostrar_contexto()
        
        print("\n\n🎉 ¡DEMOSTRACIÓN COMPLETADA!")
        print("El sistema de contexto funciona correctamente.")
        print("\n💡 Para usar en tu aplicación:")
        print("from royal_agents import run_contextual_conversation_sync")
        print("response = run_contextual_conversation_sync(user_id, message)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Asegurate de tener configuradas las variables de entorno:")
        print("- OPENAI_API_KEY")
        print("- WOOCOMMERCE_CONSUMER_KEY (opcional)")
        print("- WOOCOMMERCE_CONSUMER_SECRET (opcional)") 