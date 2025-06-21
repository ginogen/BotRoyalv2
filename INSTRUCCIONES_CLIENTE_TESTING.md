# 🎯 INSTRUCCIONES PARA EL CLIENTE - Interface de Testing Bot Royal

## 📱 ¿QUÉ VAS A HACER?

Vas a probar el bot de Royal Company de manera **profesional** y **sistemática** para ayudar a mejorarlo al máximo. Todo lo que hagas quedará registrado para implementar las mejoras.

## 🚀 CÓMO EMPEZAR (MUY FÁCIL)

### Paso 1: Abrir la interface
```bash
# Solo copiar y pegar en la terminal:
python install_testing_interface.py
```

### Paso 2: Iniciar la aplicación
```bash
# En Mac/Linux:
./start_testing_interface.sh

# En Windows:
start_testing_interface.bat
```

### Paso 3: Se abre automáticamente
Se abrirá una página web en tu navegador en: `http://localhost:8501`

## 📋 QUÉ VAS A ENCONTRAR

### 💬 **Chat de Pruebas** (LO MÁS IMPORTANTE)

**🎯 Tu trabajo principal:**
1. **Chatea normalmente** con el bot como si fueras un cliente real
2. **Después de cada respuesta** aparece un panel de feedback
3. **Califica la respuesta** del 1 al 5 (5 = perfecta)
4. **Marca la categoría** del problema si lo hay
5. **Escribe específicamente** qué está mal y cómo debería mejorar

**💡 Botones de prueba rápida:**
- 🚀 Emprendimiento
- 📦 Productos  
- 🚚 Envíos

### 🔍 **Transparencia del Bot**

**📝 Aquí puedes ver:**
- El "cerebro" del bot (system prompt)
- Qué herramientas usa internamente
- Por qué responde de cierta manera

**🎯 Tu trabajo:**
- Lee el system prompt
- Sugiere mejoras específicas
- Di si falta algo importante

### 📊 **Dashboard de Feedback**

**📈 Aquí verás:**
- Gráficos de tus calificaciones
- Estadísticas de problemas encontrados
- Timeline de tu actividad de testing

### 📝 **Feedback General**

**🎯 Para reportar:**
- Bugs o errores importantes
- Sugerencias de nuevas funcionalidades
- Mejoras de experiencia de usuario

## 🎯 ESCENARIOS IMPORTANTES A PROBAR

### 🚀 **Emprendimiento (CRÍTICO)**
```
"Quiero empezar a vender"
"Soy nueva en esto" 
"¿Qué me recomendás para empezar?"
"¿Cuánto necesito de inversión inicial?"
```

### 📦 **Consultas de Productos**
```
"¿Tenés anillos de plata?"
"Busco relojes Casio"
"Mostrame maquillaje"
"¿Qué combos hay disponibles?"
```

### 🚚 **Información Comercial**
```
"¿Cómo son los envíos?"
"¿Cuál es el mínimo de compra?"
"¿Dónde están ubicados?"
"¿Qué formas de pago aceptan?"
```

### 😤 **Situaciones Problemáticas**
```
"No me gusta nada de lo que me mostraste"
"Esto es un desastre"
"No funciona nada"
"Me está confundiendo"
```

### 💳 **Intención de Compra**
```
Después de ver productos, di:
"Quiero el segundo"
"Me interesa el anillo ese"
"¿Cómo compro?"
```

## ✅ QUÉ FEEDBACK ES MÁS VALIOSO

### **🎯 FEEDBACK ESPECÍFICO:**
❌ **Malo:** "No me gusta"
✅ **Bueno:** "Debería preguntar mi presupuesto antes de mostrar productos caros"

❌ **Malo:** "Está mal"  
✅ **Bueno:** "Usa demasiados emojis, parece poco profesional"

❌ **Malo:** "No entiende"
✅ **Bueno:** "Cuando digo 'quiero el segundo' no recuerda qué productos me mostró antes"

### **🚨 ERRORES CRÍTICOS A BUSCAR:**
- No recuerda productos mostrados anteriormente
- Inventa precios o información falsa
- No detecta cuando estoy frustrado
- Responde cosas que no corresponden a Royal Company
- No escala a humano cuando debería

### **💡 MEJORAS A SUGERIR:**
- Palabras o frases que debería usar
- Información que debería preguntar
- Orden diferente de respuestas
- Tono de comunicación más apropiado

## 🏆 OBJETIVOS DE TU TESTING

### **🎯 Objetivo Principal:**
Que el bot sea **indistinguible de un vendedor humano experto** de Royal Company

### **📊 Métricas de Éxito:**
- 90%+ de respuestas calificadas con 4-5 estrellas
- 0 información inventada o incorrecta
- Detección perfecta de frustración
- Escalación apropiada a humanos cuando sea necesario

### **🧠 Memoria Perfecta:**
- Recuerda productos mostrados
- Usa esa memoria para referencias ("el segundo", "ese anillo")
- Mantiene contexto de la conversación completa

## 💡 CONSEJOS PARA TESTING EFECTIVO

1. **🎭 Actúa como diferentes tipos de clientes:**
   - Emprendedora nueva nerviosa
   - Cliente experimentado exigente  
   - Persona confundida que no entiende
   - Cliente impaciente y apurado

2. **📱 Simula conversaciones reales:**
   - No hagas preguntas técnicas raras
   - Habla como hablarías normalmente
   - Interrumpe, cambia de tema, sé impredecible

3. **🔍 Prueba los límites:**
   - Pregunta cosas que no debe saber
   - Ve si inventa información
   - Prueba si mantiene el rol de Pablo

4. **⭐ Califica honestamente:**
   - 5 estrellas = respuesta perfecta, no cambiarías nada
   - 4 estrellas = muy buena, mejoras menores
   - 3 estrellas = aceptable pero mejorable
   - 2 estrellas = problemas evidentes
   - 1 estrella = respuesta mala o incorrecta

## 🚨 PROBLEMAS COMUNES Y SOLUCIONES

### **🤖 "El bot no responde"**
- Verificar que esté configurado OPENAI_API_KEY
- Probar reiniciar la sesión (botón "Nueva Sesión")

### **💾 "No se guarda mi feedback"**
- Hacer clic en "Guardar Feedback" después de escribir
- Verificar que aparezca "✅ Feedback guardado"

### **🔄 "Se colgó la interface"**
- Refrescar la página (F5)
- O cerrar y volver a ejecutar start_testing_interface

### **📊 "No aparecen gráficos"**
- Ir a "Dashboard de Feedback"
- Asegurate de haber dado feedback a varias conversaciones

---

## 🎯 RESULTADO ESPERADO

Al final de tu testing, tendremos:
- **Conversaciones reales** probadas exhaustivamente
- **Feedback específico** para cada tipo de problema
- **Métricas claras** de qué funciona y qué no
- **Roadmap de mejoras** basado en datos reales

¡Tu trabajo será **fundamental** para que el bot sea un éxito total! 🚀 