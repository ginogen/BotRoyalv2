# 🚀 Instalación y Prueba del Royal Bot

## ⚡ Instalación Rápida

### 1. **Automatizada (Recomendada)**
```bash
# Ejecutar script de setup automático
python setup_dev.py
```

### 2. **Manual**
```bash
# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp config.env.example .env
# Editar .env con tu OPENAI_API_KEY
```

## 🔑 Configuración Requerida

### OpenAI API Key (OBLIGATORIO)
1. Ir a https://platform.openai.com/api-keys
2. Crear una nueva API key
3. Configurar de una de estas formas:

**Opción A: Variable de entorno**
```bash
export OPENAI_API_KEY=sk-tu-clave-aqui
```

**Opción B: Archivo .env**
```env
OPENAI_API_KEY=sk-tu-clave-aqui
```

## 🧪 Pruebas

### 1. **Chat Interactivo (Entorno de Prueba)**
```bash
python test_chat.py
```

**Comandos de prueba:**
- "Hola" - Verificar saludo de Pablo
- "¿Cómo funciona Royal?" - Info de la empresa
- "¿Hacen arreglos de joyas?" - Servicios
- "¿Cuánto cuesta el envío?" - Información de envíos
- "¿Cómo puedo pagar?" - Métodos de pago
- "salir" - Terminar sesión

### 2. **Pruebas Automatizadas**
```bash
python run_tests.py
```

Ejecuta 8 tests automáticos:
- ✅ Saludo y presentación como Pablo
- ✅ Información de la empresa
- ✅ Datos de envíos
- ✅ Servicios de arreglos
- ✅ Métodos de pago
- ✅ Evitar palabras prohibidas
- ✅ Tono argentino
- ✅ No saludos repetidos

### 3. **Servidor Web**
```bash
python server.py
```

Endpoints disponibles:
- GET http://localhost:8000 - Status
- GET http://localhost:8000/health - Health check
- POST http://localhost:8000/test/message - Test directo

**Test con curl:**
```bash
curl -X POST "http://localhost:8000/test/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola, ¿cómo funciona Royal?", "client_id": "test123"}'
```

## 📋 Verificación del Bot

### ✅ Debe Hacer:
- ✅ Presentarse como Pablo solo en el primer mensaje
- ✅ Usar tono argentino ("dale", "posta", "mirá", "ojo")
- ✅ Conjugar con "vos" (podés, querés, tenés)
- ✅ Proporcionar información completa sobre Royal
- ✅ Responder sobre productos, envíos, pagos y servicios

### ❌ NO Debe Hacer:
- ❌ Usar palabras prohibidas: "aquí", "puedes", "tienes", "debes", "tú"
- ❌ Saludar repetidamente al mismo cliente
- ❌ Inventar información que no conoce
- ❌ Ser formal o neutro en el tono

## 🏆 Información Clave que Maneja

### Productos
- Joyas: Plata 925, oro 18K, personalizadas
- Relojes: Casio y otras marcas
- Maquillaje y belleza
- Indumentaria y accesorios

### Compras
- **Mayorista**: Mínimo $40,000, precios especiales
- **Minorista**: Sin mínimo, precios regulares

### Envíos
- Empresa: Andreani (100% asegurado)
- Córdoba Capital: $4,999
- Resto del país: $7,499
- **GRATIS** en pedidos +$80,000

### Pagos
- Tarjeta (hasta 3 cuotas sin interés)
- Transferencia: CBU 4530000800014232361716
- Efectivo en locales
- Sistema de seña: $10,000

### Ubicaciones (Córdoba Capital)
- Royal Joyas: 9 de Julio 472
- Royal Joyas: General Paz 159, Galería Planeta, Local 18
- Royal Bijou: San Martín 48, Galería San Martín, Local 23A

## 🔧 Troubleshooting

### Error: "OpenAI API Key not found"
```bash
# Verificar configuración
echo $OPENAI_API_KEY
# O revisar archivo .env
```

### Error: "No module named 'agents'"
```bash
# Reinstalar dependencias
pip install -r requirements.txt
```

### Bot responde en inglés
- Verificar que el prompt tenga instrucciones en español
- Revisar que no use palabras prohibidas

### Error: "Redis connection failed"
```bash
# Redis es opcional para desarrollo
# El bot funciona sin Redis (sin persistencia)
```

## 📦 Próximos Pasos

Una vez que las pruebas locales funcionen:

1. **Deploy en Railway**
   - Subir código a GitHub
   - Conectar repo en Railway
   - Configurar variables de entorno
   - Agregar Redis add-on

2. **Integrar con Chatwoot**
   - Configurar webhook: https://tu-bot.railway.app/webhook/chatwoot
   - Agregar CHATWOOT_WEBHOOK_SECRET

3. **Integrar con Evolution API**
   - Configurar webhook: https://tu-bot.railway.app/webhook/evolution
   - Agregar EVOLUTION_API_URL y EVOLUTION_API_TOKEN

## 📞 Soporte

Si tenés problemas:
1. Revisar logs en la consola
2. Verificar configuración de API keys
3. Probar con `python run_tests.py`
4. Contactar al equipo de desarrollo

---
**🏆 Royal Company 2024 - ¡Listo para atender clientes!** 