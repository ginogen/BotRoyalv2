# Plantillas de Mensajes para Sistema de Seguimiento de 14 Etapas
# Cada mensaje mantiene la personalidad de Royalia con enfoque de ventas

import random
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FollowUpMessageTemplates:
    """Gestiona todas las plantillas de mensajes para el sistema de seguimiento"""
    
    def __init__(self):
        # Plantillas por etapa con múltiples variaciones
        self.templates = {
            0: self._get_stage_0_templates(),   # 1 hora después
            1: self._get_stage_1_templates(),   # Día 1
            2: self._get_stage_2_templates(),   # Día 2
            4: self._get_stage_4_templates(),   # Día 4
            7: self._get_stage_7_templates(),   # Día 7
            10: self._get_stage_10_templates(), # Día 10
            14: self._get_stage_14_templates(), # Día 14
            18: self._get_stage_18_templates(), # Día 18
            26: self._get_stage_26_templates(), # Día 26
            36: self._get_stage_36_templates(), # Día 36
            46: self._get_stage_46_templates(), # Día 46
            56: self._get_stage_56_templates(), # Día 56
            66: self._get_stage_66_templates(), # Día 66
            999: self._get_maintenance_templates() # Mantenimiento (cada 15 días)
        }
        
        # Variables de personalización
        self.user_variables = [
            "emprendedora", "revendedora", "clienta", "amiga"
        ]
        
        # Productos destacados por tipo
        self.product_highlights = {
            "joyas": ["anillos de plata 925", "aros con cristales", "pulseras ajustables"],
            "maquillaje": ["labiales de larga duración", "bases líquidas", "paletas de sombras"],
            "indumentaria": ["remeras oversized", "jeans de moda", "accesorios trendy"],
            "general": ["combos emprendedores", "productos más vendidos", "novedades de temporada"]
        }
    
    def _get_stage_0_templates(self) -> List[Dict[str, Any]]:
        """Plantillas para Stage 0 - 1 hora después de la conversación"""
        return [
            {
                "message": """¡Hola de nuevo! 👋

{conversation_opener} y quería seguir ayudándote con tu emprendimiento. {questions_reference}

¿Ya tuviste oportunidad de pensar en qué rubro te gustaría arrancar? 

**Recordá que tenemos:**
• Combos emprendedores listos para vender
• Mínimo desde $40.000 
• Margen de ganancia hasta 150%

{budget_reference}, podés arrancar con productos que incluyen justo {specific_products}.

{personalized_cta}

¡Estoy acá para acompañarte en este paso!{objection_response}""",
                "cta": "¿Con qué rubro arrancamos?",
                "urgency": "low"
            },
            {
                "message": """¿Todo bien? 😊

Te escribo rapidito porque me encanta ayudar a emprendedoras como vos que están decididas a crecer.

**¿Sabías que nuestras emprendedoras que arrancan esta semana ya están vendiendo en 2-3 días?**

Es porque empezamos con los productos que más se mueven:
✨ Joyas que no se oxidan
💄 Maquillaje de calidad
👕 Ropa que está de moda

**¿Te animo a dar el paso hoy?** En menos de una semana podés estar generando tus primeras ventas.

Contame, ¿qué es lo que más te tienta para arrancar? 💎""",
                "cta": "¡Vamos a armarte tu primer kit!",
                "urgency": "medium"
            },
            {
                "message": """¡Hola! Me alegra que hayamos charlado 💛

Quería contarte algo que me parece súper importante:

**Las emprendedoras que arrancan ESTA semana tienen una ventaja:** están llegando justo para la temporada más fuerte de ventas.

En Royal tenemos todo listo para que puedas:
🚀 Empezar con productos probados
📈 Tener margen de ganancia real (150%)
💪 Recuperar tu inversión rápido

**¿Te copa que armemos tu kit de arranque ahora?** 

Con $40.000 ya podés empezar y en 2 semanas estar facturando el doble 📊""",
                "cta": "¡Quiero mi kit de arranque!",
                "urgency": "high"
            }
        ]
    
    def _get_stage_1_templates(self) -> List[Dict[str, Any]]:
        """Plantillas para Stage 1 - Día 1"""
        return [
            {
                "message": """Buenos días! ☀️

{conversation_opener} y me quedé con muchas ganas de ayudarte a arrancarlo. {questions_reference}

**¿Sabés qué me pasa seguido?** Muchas emprendedoras me dicen "ay, ojalá hubiera empezado antes" cuando ven lo bien que les va.

**La diferencia entre empezar HOY o el mes que viene son $50.000+ en ventas que te perdés.**

Tengo algunos combos que se están agotando rapidísimo porque son los favoritos con {specific_products}:

🔥 Combo Joyas Trendy - $45.000 (recuperás $110.000 en ventas)
💄 Combo Maquillaje Esencial - $42.000 (recuperás $105.000 en ventas)  
👑 Combo Emprendedora Total - $65.000 (recuperás $165.000 en ventas)

{budget_reference}, cualquiera de estos combos te permite arrancar con todo lo que necesitás.{objection_response}

{personalized_cta}""",
                "cta": "¡Quiero empezar ya!",
                "urgency": "high"
            },
            {
                "message": """¡Hola! ¿Cómo estás? 😊

Te escribo porque ayer me contaste que querías emprender y hoy tengo una propuesta que te va a encantar.

**¿Viste que muchas veces postergamos cosas importantes?** Con el emprendimiento pasa lo mismo, pero cada día que pasa es dinero que no ganamos.

**Calculá esto:** Si arrancás hoy con $40.000, en un mes podés estar facturando $100.000+. Si esperás un mes más... perdés esos $100.000.

**Los combos que más se venden esta semana:**
• Anillos ajustables (se venden solos)
• Labiales de larga duración (toda mujer los compra)  
• Aros con cristales (regalo perfecto)

¿Te copa que te arme un mix con esos productos que SÉ que se van a vender?""",
                "cta": "¡Sí, armámelo!",
                "urgency": "medium"
            }
        ]
    
    def _get_stage_2_templates(self) -> List[Dict[str, Any]]:
        """Plantillas para Stage 2 - Día 2"""
        return [
            {
                "message": """¡Hola! 💛

Ya hace 2 días que charlamos sobre tu emprendimiento y quería compartirte algo que me motiva un montón.

**Ayer una clienta que empezó hace 3 semanas me escribió:** "Royalia, no puedo creer que en 20 días ya recuperé toda mi inversión y encima gané $30.000 extra"

**¿Sabés por qué le fue tan bien?** 
✅ Empezó con productos de alta rotación
✅ No se complicó eligiendo, confió en nuestra experiencia
✅ Arrancó SIN miedo

**Vos tenés el mismo potencial.** 

Los productos que más están funcionando ahora:
🔥 Conjuntos de aros (se venden de a pares)
💋 Kits de maquillaje (alta ganancia)
💍 Anillos trendy (los más pedidos)

¿Te animo a dar el paso hoy? Te juro que en 3 semanas me vas a agradecer 🚀""",
                "cta": "¡Sí, quiero empezar!",
                "urgency": "high"
            },
            {
                "message": """¿Qué tal? 😊

**Pregunta honesta:** ¿Qué es lo que más te frena para arrancar tu emprendimiento?

Porque en estos años hablé con miles de emprendedoras y las excusas siempre son las mismas:
❌ "No sé qué elegir" → Te armamos el combo perfecto
❌ "Y si no se vende" → Elegimos productos de alta rotación
❌ "Es mucha plata" → Empezás con $40.000 y lo multiplicás
❌ "No tengo experiencia" → Te acompañamos en todo

**La verdad:** TODAS las excusas tienen solución. El único riesgo real es NO empezar.

¿Te parece que charlemos 5 minutos y resolvemos juntas todas tus dudas? 💪""",
                "cta": "¡Sí, charlemos!",
                "urgency": "low"
            }
        ]
    
    def _get_stage_4_templates(self) -> List[Dict[str, Any]]:
        """Plantillas para Stage 4 - Día 4"""
        return [
            {
                "message": """¡Hola! ¿Cómo venís? 👋

**4 días charlamos sobre tu emprendimiento** y quería contarte algo que me pasó recién.

Una emprendedora me escribió: *"Royalia, pensé 2 semanas si arrancar o no. Cuando finalmente me decidí, en la primera semana vendí $80.000. Me arrepiento de haber dudado tanto tiempo"*

**¿Te suena conocido esto de dudar?** Es súper normal, pero cada día que pasa perdés oportunidades de venta.

**Mirá lo que está pasando ahora:**
🔥 Las fiestas de fin de año se acercan (más ventas)
💍 Los regalos de cumpleaños aumentan
💄 El maquillaje para eventos se dispara

**¿No es el momento perfecto para arrancar?**

Te tengo 3 combos que están funcionando de 10:
• Combo Fiestas ($48.000 → vendes $125.000)
• Combo Regalos Ideales ($45.000 → vendes $115.000)  
• Combo Todo en Uno ($65.000 → vendes $170.000)

¿Cuál te copa más para empezar YA?""",
                "cta": "¡Elijo mi combo!",
                "urgency": "high"
            }
        ]
    
    def _get_stage_7_templates(self) -> List[Dict[str, Any]]:
        """Plantillas para Stage 7 - Día 7 (semana después)"""
        return [
            {
                "message": """¡Una semana! ⏰

{time_reference} que charlamos sobre tu emprendimiento y me quedé con la duda... {questions_reference}

**¿Seguís con la idea de arrancar o ya te desanimaste?**

Porque te voy a ser súper honesta: la mayoría de las personas habla, habla, habla sobre emprender, pero nunca DA EL PASO.

**Las que SÍ lo dan, después de 6 meses me escriben:** "Gracias Royalia, cambié mi vida económica"

**¿Sabés cuál es la diferencia entre las que lo logran y las que se quedan hablando?**

**Las que lo logran ACTÚAN. Punto.**

No esperan el momento perfecto. No buscan más excusas. No postergan más.

**ACTÚAN.**

{objection_response}

**¿Vos sos de las que ACTÚAN o de las que hablan?**

Si sos de las que actúan, escribime ahora y en 30 minutos tenés tu combo con {specific_products} listo.

{budget_reference} podés arrancar HOY MISMO.

Si sos de las que hablan... nos vemos en unos meses cuando te vuelva a tentar la idea 🤷‍♀️

**¿Cuál elegís?**""",
                "cta": "SOY DE LAS QUE ACTÚAN",
                "urgency": "high"
            }
        ]
    
    def _get_stage_10_templates(self) -> List[Dict[str, Any]]:
        """Plantillas para Stage 10 - Día 10"""
        return [
            {
                "message": """10 días... 🤔

**¿Te digo algo que me llama la atención?**

Hace 10 días me escribiste interesada en emprender. Charlamos, te dije todo lo que necesitabas saber...

**¿Y después? Silencio.**

**Fijate esta foto que me mandó una clienta ayer** → [SIMULACIÓN: foto de ventas exitosas]

Ella empezó hace exactamente 10 días. SÍ, 10 días.

**¿Sabés cuánto facturó en estos 10 días? $95.000**

Con una inversión inicial de $45.000.

**Mientras vos pensás, ella factura.**

**No te juzgo, eh.** Cada una tiene sus tiempos. Pero quería que supieras que:

• Los productos siguen estando disponibles
• Los precios siguen siendo los mismos  
• La oportunidad sigue ahí

**La única diferencia es que cada día vale plata.**

¿Seguís interesada o ya cambió tu situación?""",
                "cta": "Sí, sigo interesada",
                "urgency": "medium"
            }
        ]
    
    def _get_stage_14_templates(self) -> List[Dict[str, Any]]:
        """Plantillas para Stage 14 - Día 14 (2 semanas)"""
        return [
            {
                "message": """2 semanas exactas. 📅

**¿Sabés qué me pregunto?** Si en estas 2 semanas hubieras empezado tu emprendimiento, ¿cuánto estarías facturando hoy?

Te voy a ser súper directa porque me importás:

**Una emprendedora que empiece hoy, en 2 semanas ya recuperó su inversión.**

**Una que empezó hace 2 semanas, hoy está ganando $50.000+ por mes extra.**

**¿Y una que sigue pensándolo?** Sigue donde mismo.

**No te escribo para presionarte.** Te escribo porque genuinamente creo que tenés potencial y me da bronca ver potencial desperdiciado.

**¿Quiere decir que es tarde?** Para nada.

Pero quiere decir que **CADA DÍA que pasa es plata que no entra a tu bolsillo.**

Si realmente querés emprender:
✅ Te ayudo ahora
✅ Elegimos productos juntas  
✅ En 3 días tenés tu stock
✅ En 1 semana empezás a vender

Si no querés emprender:
❌ Te dejo de escribir
❌ Nos despedimos como amigas
❌ Sin drama

**¿Qué elegís? ¿Emprendemos juntas o nos despedimos?**""",
                "cta": "Emprendemos juntas",
                "urgency": "high"
            }
        ]
    
    def _get_stage_18_templates(self) -> List[Dict[str, Any]]:
        """Plantillas para Stage 18 - Día 18"""
        return [
            {
                "message": """18 días pensándolo... 💭

**¿Te cuento qué hizo una clienta en estos 18 días?**

Día 1: Me escribió como vos
Día 2: Hizo su primer pedido ($42.000)
Día 5: Recibió su stock
Día 7: Vendió los primeros productos ($25.000)
Día 10: Hizo su segundo pedido ($65.000) 
Día 14: Vendió $50.000 más
**Día 18 (hoy): Me escribió que ya ganó $85.000 limpios**

**Mientras vos pensás, ella ganó $85.000.**

**Sin juzgarte,** pero quería que vieras la diferencia entre pensar y hacer.

**La buena noticia:** Podés empezar mañana mismo si querés.
**La mala noticia:** Cada día que pasa, otra emprendedora toma tu lugar en el mercado.

**¿Seguimos con el emprendimiento o ya no te interesa más?**

Contestame con sinceridad para saber si te sigo acompañando o no 😊""",
                "cta": "Sí, quiero empezar",
                "urgency": "medium"
            }
        ]
    
    def _get_stage_26_templates(self) -> List[Dict[str, Any]]:
        """Plantillas para Stage 26 - Día 26"""
        return [
            {
                "message": """¡Un mes! 📆

Hace casi un mes que hablamos de tu emprendimiento por primera vez.

**¿Sabés qué me da curiosidad?** Qué pasó en tu cabeza durante este mes.

**Porque han pasado 3 cosas:**

1️⃣ Te decidiste emprender con otra empresa
2️⃣ Seguís con la idea pero algo te frena
3️⃣ Ya no te interesa el tema

**Si es la opción 1:** Te felicito sinceramente 👏 Lo importante es que hayas dado el paso.

**Si es la opción 2:** Entiendo perfectamente. A veces necesitamos más tiempo. ¿Querés que charlemos qué es lo que específicamente te frena?

**Si es la opción 3:** Todo bien, cambiar de idea es válido. Solo avisame para no seguir escribiéndote 😊

**¿Cuál es tu situación?**

**PD:** Por si te sirve, tengo 3 clientas que empezaron este mes pasando POR LA MISMA DUDA que vos. Hoy todas están súper contentas con los resultados.

A veces solo necesitamos el empujoncito correcto 💪""",
                "cta": "Contame tu situación",
                "urgency": "low"
            }
        ]
    
    def _get_stage_36_templates(self) -> List[Dict[str, Any]]:
        """Plantillas para Stage 36 - Día 36"""
        return [
            {
                "message": """Más de un mes... 🤯

**¿Te digo algo loco?** 

En el tiempo que llevamos "en contacto" (36 días), una de mis clientas ya recuperó su inversión inicial 3 VECES.

**Empezó con $45.000. Hoy ya facturó $180.000.**

**No te lo digo para hacerte sentir mal.** Te lo digo porque quizás no te das cuenta del POTENCIAL que estás dejando pasar.

**Pero bueno...** quizás el emprendimiento no es para vos en este momento de tu vida.

**Y está PERFECTO.** No todo el mundo está listo para emprender en cualquier momento.

**Capaz ahora tenés otras prioridades:**
• Trabajo full time muy demandante
• Situación personal compleja
• Otros proyectos que te consumen tiempo

**Si es así, solo avisame para dejar de escribirte** y que no sientas que te "persigo" 😅

**Pero si AÚN tenés ganas y algo específico te frena...**

**Escribime una sola palabra: "GANAS"**

Y charlamos puntualmente qué es lo que pasa.

¿Dale?""",
                "cta": "GANAS",
                "urgency": "low"
            }
        ]
    
    def _get_stage_46_templates(self) -> List[Dict[str, Any]]:
        """Plantillas para Stage 46 - Día 46"""
        return [
            {
                "message": """46 días de seguimiento... ⏳

**¿Sabés qué?** Respeto tu tiempo y tus decisiones.

**46 días es suficiente tiempo** para que una persona se decida sobre algo que le interesa de verdad.

**Si fuera TAN importante para vos, ya hubieras empezado.**

**Y está súper bien así.** Cada una tiene sus prioridades y sus momentos.

**Te voy a hacer la última pregunta directa:**

**¿Querés que te deje de escribir sobre el emprendimiento?**

Si me decís que SÍ, te dejo tranquila y nos despedimos como amigas.

Si me decís que NO, seguimos charlando pero necesito saber QUÉ específicamente te frena para poder ayudarte de verdad.

**No hay respuesta incorrecta,** pero necesito una respuesta honesta.

¿Dale? 😊""",
                "cta": "Dame tu respuesta honesta",
                "urgency": "low"
            }
        ]
    
    def _get_stage_56_templates(self) -> List[Dict[str, Any]]:
        """Plantillas para Stage 56 - Día 56"""
        return [
            {
                "message": """2 meses charlando... 📊

**Está bueno hacer un balance, ¿no te parece?**

**Hace 2 meses:** Te interesaba emprender, hiciste consultas, te pasé info completa.

**Hoy:** Seguimos en el mismo lugar.

**No está mal, eh.** A veces las cosas no se dan y punto.

**Pero quería preguntarte algo importante:**

**¿Cambió algo en tu situación que haga que ahora SÍ puedas/quieras emprender?**

**Por ejemplo:**
✅ Te organizaste mejor con los tiempos
✅ Mejoraste tu situación económica  
✅ Se resolvieron temas personales
✅ Encontraste la motivación que te faltaba

**Si cambió algo y querés intentarlo → Escribime "CAMBIÓ"**

**Si todo sigue igual → Escribime "IGUAL"**

**De acuerdo a tu respuesta veo cómo seguimos** 😊

Sin presiones, solo quiero saber cómo estás.""",
                "cta": "CAMBIÓ o IGUAL",
                "urgency": "low"
            }
        ]
    
    def _get_stage_66_templates(self) -> List[Dict[str, Any]]:
        """Plantillas para Stage 66 - Día 66 (final de secuencia)"""
        return [
            {
                "message": """66 días... El último mensaje de la serie 📮

**¿Sabés qué me pasa?** Que realmente me importa que te vaya bien.

**En estos 66 días te acompañé** con info, propuestas, seguimiento... porque creí (y sigo creyendo) que tenés potencial.

**Pero también entiendo** que a veces las cosas no se dan. Y está perfecto.

**Este es mi último mensaje "activo" sobre el emprendimiento.**

**A partir de acá:**
• Te voy a escribir cada tanto (cada 15 días aprox) solo para mantener el contacto
• Te voy a contar novedades, productos nuevos, promos especiales  
• PERO no te voy a insistir más con el emprendimiento

**Si en algún momento TE NACE emprender, escribime.**
**Si nunca te nace, también está perfecto.**

**¿Te parece bien así?**

**PD:** Fue un placer conocerte y charlar con vos estos días. Genuinamente te deseo lo mejor en todos tus proyectos 💛

**PD2:** La puerta de Royal siempre está abierta para vos 🚪✨""",
                "cta": "¡Gracias por todo!",
                "urgency": "low"
            }
        ]
    
    def _get_maintenance_templates(self) -> List[Dict[str, Any]]:
        """Plantillas para modo mantenimiento (cada 15 días después del día 66)"""
        return [
            {
                "message": """¡Hola! ¿Cómo andás? 😊

**Solo un saludito rápido** para contarte las novedades de Royal.

**Productos que están pegando fuerte:**
🔥 Nueva línea de {specific_products} (salen como pan caliente)
💄 Labiales matte que duran TODO el día
👑 Conjuntos de aros que están súper trendy

**Promo del mes:** Combos con 15% extra de descuento

**¿Todo bien con vos?** ¿Algún proyecto nuevo en puerta?

**PD:** Si algún día te pinta arrancar con el emprendimiento, recordá que {time_reference} hablamos sobre {interest} y me quedé con ganas de ayudarte 😉""",
                "cta": "¡Hola! Todo bien",
                "urgency": "low"
            },
            {
                "message": """¡Holaa! Saludito de Royalia 👋

**¿Viste las nuevas tendencias?** Están entrando productos súper innovadores.

**Lo que más se está vendiendo:**
✨ Joyería minimalista (súper trendy)
💫 Maquillaje vegano (boom total)
🌟 Accesorios sustentables

**Si querés te mando el catálogo actualizado** para que veas las novedades, ¡sin compromiso!

**¿Te copa?**

**PD:** ¿Cómo viene tu año? ¡Espero que súper bien!""",
                "cta": "¡Sí, mandame el catálogo!",
                "urgency": "low"
            },
            {
                "message": """¿Qué tal? 🌟

**Te acordás que hace un tiempo charlamos sobre emprendimiento?**

**No te escribo para insistir,** solo para contarte que seguimos creciendo y ayudando a emprendedoras.

**Esta semana:** 3 clientas nuevas empezaron y ya están súper contentas con sus primeras ventas.

**¿Sabés qué me pone contenta?** Ver cómo cambian sus vidas. Posta.

**Si algún día te nace la idea de nuevo, acá estoy** para acompañarte como a ellas.

**¿Todo bien con vos?** 💛""",
                "cta": "¡Sí, todo bien!",
                "urgency": "low"
            }
        ]

# SISTEMA DE PERSONALIZACIÓN AVANZADA
class MessagePersonalizer:
    """Sistema de personalización avanzada para mensajes de follow-up"""
    
    @staticmethod
    def get_time_reference(stage: int) -> str:
        """Obtiene referencia temporal según la etapa"""
        time_references = {
            0: "hace una hora",
            1: "ayer",
            2: "hace dos días", 
            4: "hace unos días",
            7: "la semana pasada",
            10: "hace una semana y media",
            14: "hace dos semanas",
            18: "hace casi tres semanas",
            26: "el mes pasado",
            36: "hace más de un mes",
            46: "hace un mes y medio",
            56: "hace dos meses",
            66: "hace más de dos meses",
            999: "hace un tiempo"
        }
        return time_references.get(stage, "hace un tiempo")
    
    @staticmethod
    def get_conversation_opener(user_profile: Dict, stage: int) -> str:
        """Genera opening personalizado basado en el perfil"""
        time_ref = MessagePersonalizer.get_time_reference(stage)
        
        # Usar temas específicos de conversación si están disponibles
        topics = user_profile.get("conversation_topics", [])
        if topics:
            main_topic = topics[0].replace("_", " ")
            return f"Me quedé pensando en nuestra charla {time_ref} sobre {main_topic}"
        
        # Fallback con interés general
        interest = user_profile.get("interest", "emprendimiento")
        if interest != "general":
            return f"Me quedé pensando en nuestra charla {time_ref} sobre {interest}"
        
        return f"Me quedé pensando en nuestra charla {time_ref}"
    
    @staticmethod
    def get_specific_products_text(user_profile: Dict) -> str:
        """Genera texto sobre productos específicos mencionados"""
        specific_products = user_profile.get("specific_products", [])
        
        if len(specific_products) >= 2:
            return f"los {specific_products[0]} y {specific_products[1]}"
        elif len(specific_products) == 1:
            return f"los {specific_products[0]}"
        else:
            # Fallback según interés general
            interest = user_profile.get("interest", "general")
            fallbacks = {
                "joyas": "anillos y aros",
                "maquillaje": "labiales y bases",
                "indumentaria": "remeras y jeans",
                "relojes": "relojes de moda",
                "general": "productos más vendidos"
            }
            return fallbacks.get(interest, "productos que te interesan")
    
    @staticmethod
    def get_budget_reference(user_profile: Dict) -> str:
        """Obtiene referencia al presupuesto mencionado"""
        budget = user_profile.get("budget_mentioned")
        if budget:
            return f"Con el presupuesto de {budget} que mencionaste"
        else:
            return "Con el mínimo de $40.000"
    
    @staticmethod
    def get_personalized_cta(user_profile: Dict) -> str:
        """Genera CTA personalizado según perfil"""
        engagement = user_profile.get("engagement_level", "medio")
        experience = user_profile.get("experience_level", "intermedio")
        
        if engagement == "alto" and experience == "empezando":
            return "¿Te animo a dar el paso hoy mismo? 🚀"
        elif engagement == "alto":
            return "¿Arrancamos con tu pedido ahora? 💪"
        elif experience == "empezando":
            return "¿Te parece que charlemos y armamos algo juntas? 😊"
        else:
            return "¿Seguís interesada en emprender? 💛"
    
    @staticmethod  
    def get_objection_response(user_profile: Dict) -> str:
        """Genera respuesta a objeciones específicas mencionadas"""
        objections = user_profile.get("objections", [])
        
        if not objections:
            return ""
        
        objection_responses = {
            "no sé qué elegir": "Por eso armamos los combos emprendedores, para que no tengas que elegir uno por uno.",
            "es mucha inversión": "Te entiendo, pero pensá que con $40.000 podés generar $100.000+ en ventas.",  
            "no tengo experiencia": "¡Perfecto! Eso significa que te vamos a acompañar desde cero hasta que seas una genia vendiendo.",
            "no sé si se vende": "Te doy un dato: el 95% de las emprendedoras que empiezan con nosotros recuperan su inversión en el primer mes.",
            "tengo miedo de perder": "Es normal tener esa sensación. Por eso empezás con productos que SÍ o SÍ se venden.",
        }
        
        main_objection = objections[0]
        response = objection_responses.get(main_objection, "")
        
        if response:
            return f"\n\n{response}"
        
        return ""
    
    @staticmethod
    def get_questions_reference(user_profile: Dict) -> str:
        """Referencia a preguntas específicas que hizo el usuario"""
        questions = user_profile.get("questions_asked", [])
        
        if not questions:
            return ""
        
        question_references = {
            "cuánto necesito para empezar": "cuando me preguntaste cuánto necesitás para arrancar",
            "qué productos se venden más": "cuando me consultaste qué productos tienen mejor salida",
            "cuánto gano por producto": "cuando me preguntaste sobre la rentabilidad",
            "cómo funciona el envío": "cuando me preguntaste sobre los envíos",
            "tienen local físico": "cuando me preguntaste por nuestros locales",
        }
        
        main_question = questions[0]
        reference = question_references.get(main_question, "")
        
        if reference:
            return f"Especialmente {reference}."
        
        return ""

def get_followup_message_for_stage(stage: int, user_profile: Optional[Dict] = None, 
                                 interaction_count: int = 0) -> Optional[str]:
    """
    Obtiene un mensaje personalizado para una etapa específica con personalización avanzada
    
    Args:
        stage: Número de etapa (0, 1, 2, 4, 7, etc.)
        user_profile: Perfil del usuario para personalización
        interaction_count: Número de interacciones previas
    
    Returns:
        Mensaje personalizado o None si no hay plantilla para esa etapa
    """
    try:
        templates = FollowUpMessageTemplates()
        personalizer = MessagePersonalizer()
        
        if stage not in templates.templates:
            logger.warning(f"⚠️ No hay plantilla para etapa {stage}")
            return None
        
        # Obtener plantillas de la etapa
        stage_templates = templates.templates[stage]
        
        # Seleccionar plantilla (con variación según interacciones)
        if interaction_count > 0:
            # Para usuarios con interacciones previas, usar variaciones diferentes
            template_index = interaction_count % len(stage_templates)
        else:
            template_index = 0
        
        selected_template = stage_templates[template_index]
        message = selected_template["message"]
        
        # PERSONALIZACIÓN AVANZADA si hay perfil disponible
        if user_profile:
            # Variables de reemplazo dinámico
            replacements = {
                "{time_reference}": personalizer.get_time_reference(stage),
                "{conversation_opener}": personalizer.get_conversation_opener(user_profile, stage),
                "{specific_products}": personalizer.get_specific_products_text(user_profile),
                "{budget_reference}": personalizer.get_budget_reference(user_profile),
                "{personalized_cta}": personalizer.get_personalized_cta(user_profile),
                "{objection_response}": personalizer.get_objection_response(user_profile),
                "{questions_reference}": personalizer.get_questions_reference(user_profile),
                "{user_type}": user_profile.get("user_type", "emprendedora"),
                "{interest}": user_profile.get("interest", "productos"),
                "{experience_level}": user_profile.get("experience_level", "empezando"),
            }
            
            # Aplicar reemplazos si las variables existen en el mensaje
            for variable, value in replacements.items():
                if variable in message and value:
                    message = message.replace(variable, value)
            
            # Personalización básica según perfil (mantenemos la lógica existente)
            if user_profile.get("interest") == "joyas":
                message = message.replace("productos más vendidos", "anillos y aros que se venden solos")
            elif user_profile.get("interest") == "maquillaje":  
                message = message.replace("productos más vendidos", "labiales y bases que todas quieren")
            elif user_profile.get("interest") == "indumentaria":
                message = message.replace("productos más vendidos", "ropa trendy que está súper de moda")
            
            # Personalizar trato según experiencia
            if user_profile.get("experience_level") == "empezando":
                message = message.replace("emprendedora", "futura emprendedora")
            
        logger.info(f"✅ Mensaje personalizado generado para etapa {stage}, interacciones: {interaction_count}")
        return message
        
    except Exception as e:
        logger.error(f"❌ Error generando mensaje para etapa {stage}: {e}")
        return None

def get_message_preview_for_stage(stage: int) -> Optional[str]:
    """Obtiene una vista previa del mensaje para una etapa (para testing)"""
    message = get_followup_message_for_stage(stage)
    if message:
        return message[:150] + "..." if len(message) > 150 else message
    return None

def get_all_available_stages() -> List[int]:
    """Retorna todas las etapas disponibles"""
    templates = FollowUpMessageTemplates()
    return list(templates.templates.keys())

if __name__ == "__main__":
    # Test de las plantillas
    logger.info("🧪 Test de plantillas de follow-up")
    
    stages = get_all_available_stages()
    logger.info(f"📋 Etapas disponibles: {stages}")
    
    # Test de algunos mensajes
    for stage in [0, 1, 7, 14, 66, 999]:
        if stage in stages:
            preview = get_message_preview_for_stage(stage)
            logger.info(f"📝 Etapa {stage}: {preview}")
    
    # Test con perfil de usuario
    test_profile = {"interest": "joyas", "experience_level": "empezando"}
    message = get_followup_message_for_stage(1, user_profile=test_profile, interaction_count=2)
    
    if message:
        logger.info(f"📄 Mensaje personalizado: {message[:100]}...")
    
    logger.info("✅ Test de plantillas completado")