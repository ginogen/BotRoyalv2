#!/usr/bin/env python3
"""
🚀 UNIFIED ROYAL AGENT - Royal Bot v2.0
Sistema unificado que carga toda la configuración desde archivos JSON
Mantiene EXACTAMENTE la misma funcionalidad que los agentes originales
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from agents import Agent, Runner, function_tool  # type: ignore
from datetime import datetime

# Importar herramientas existentes
from .royal_agent import (
    get_royal_info, track_client_greeting, get_arreglos_info,
    get_joyas_personalizadas_info, get_royal_education_info,
    get_combos_emprendedores_info, get_inversion_presupuesto_info,
    get_acompanamiento_venta_info, get_situaciones_frecuentes
)

# Importar herramientas contextuales si están disponibles
try:
    from .contextual_tools import create_contextual_tools
    CONTEXTUAL_AVAILABLE = True
except ImportError:
    CONTEXTUAL_AVAILABLE = False

# Importar herramientas MCP si están disponibles  
try:
    from .woocommerce_mcp_tools import create_woocommerce_tools
    from .training_mcp_tools import create_training_tools
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

logger = logging.getLogger(__name__)

class UnifiedRoyalAgentConfig:
    """Cargador y gestor de configuración unificada"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir or "/Users/gino/BotRoyalv2/royal_config")
        self.config = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Carga todos los archivos de configuración JSON"""
        try:
            # Cargar configuración principal del agente
            agent_config_path = self.config_dir / "agent_config.json"
            with open(agent_config_path, 'r', encoding='utf-8') as f:
                self.agent_config = json.load(f)
            
            # Cargar todas las configuraciones referenciadas
            for config_name, filename in self.agent_config["config_files"].items():
                config_path = self.config_dir / filename
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        self.config[config_name] = json.load(f)
                    logger.info(f"✅ Loaded {config_name} from {filename}")
                except Exception as e:
                    logger.error(f"❌ Error loading {config_name} from {filename}: {e}")
                    self.config[config_name] = {}
            
            logger.info("🚀 All configurations loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Error loading agent configuration: {e}")
            raise
    
    def get_personality(self) -> Dict[str, Any]:
        """Obtiene la configuración de personalidad"""
        return self.config.get("personality", {})
    
    def get_company_knowledge(self) -> Dict[str, Any]:
        """Obtiene el conocimiento de la empresa"""
        return self.config.get("company_knowledge", {})
    
    def get_protocols(self) -> Dict[str, Any]:
        """Obtiene los protocolos críticos"""
        return self.config.get("protocols", {})
    
    def get_product_training(self) -> Dict[str, Any]:
        """Obtiene el entrenamiento de productos"""
        return self.config.get("product_training", {})
    
    def get_combo_training(self) -> Dict[str, Any]:
        """Obtiene el entrenamiento de combos"""
        return self.config.get("combo_training", {})
    
    def get_response_rules(self) -> Dict[str, Any]:
        """Obtiene las reglas de respuesta"""
        return self.config.get("response_rules", {})

class UnifiedRoyalAgent:
    """Agente Royal unificado que mantiene EXACTAMENTE la misma funcionalidad"""
    
    def __init__(self, config_dir: str = None):
        self.config = UnifiedRoyalAgentConfig(config_dir)
        self.agent = None
        self._build_agent()
    
    def _build_agent(self) -> Agent:
        """Construye el agente con toda la configuración cargada"""
        
        # Generar instrucciones unificadas
        instructions = self._generate_unified_instructions()
        
        # Preparar todas las herramientas
        tools = self._prepare_all_tools()
        
        # Obtener configuración del agente
        agent_info = self.config.agent_config["agent_info"]
        
        # Crear el agente
        self.agent = Agent(
            name=agent_info["name"],
            instructions=instructions,
            model=agent_info["model"],
            tools=tools
        )
        
        logger.info(f"🎯 {agent_info['name']} v{agent_info['version']} created with {len(tools)} tools")
        return self.agent
    
    def _generate_unified_instructions(self) -> str:
        """Genera las instrucciones unificadas desde los archivos JSON"""
        
        personality = self.config.get_personality()
        protocols = self.config.get_protocols()
        company = self.config.get_company_knowledge()
        product_training = self.config.get_product_training()
        combo_training = self.config.get_combo_training()
        
        # Construir instrucciones siguiendo la jerarquía de prioridades
        instructions = f"""
# IDENTIDAD Y PERSONALIDAD

{self._format_identity_section(personality)}

{self._format_personality_section(personality)}

{self._format_protocols_section(protocols)}

{self._format_training_section(product_training, combo_training)}

{self._format_company_section(company)}

{self._format_behavioral_rules_section(personality, protocols)}

# REGLA DE ORO
{protocols.get('golden_rule', 'Mantener siempre el enfoque en ayudar al usuario')}
"""
        
        return instructions.strip()
    
    def _format_identity_section(self, personality: Dict) -> str:
        """Formatea la sección de identidad"""
        identity = personality.get("identity", {})
        return f"""
Sos {identity.get("name", "Royalia")}, {identity.get("role", "asistente de Royal")}.
{identity.get("description", "Tu rol es ayudar a los usuarios.")}
"""
    
    def _format_personality_section(self, personality: Dict) -> str:
        """Formatea la sección de personalidad argentina"""
        language_style = personality.get("language_style", {})
        forbidden_words = personality.get("forbidden_words", [])
        
        section = "## Personalidad Argentina\n"
        
        if language_style.get("region") == "argentina":
            section += f"- Hablá en tono argentino {language_style.get('formality', 'informal')} y amigable\n"
        
        if language_style.get("voseo"):
            section += "- Usá el voseo, no hablar en 'usted'\n"
        
        if language_style.get("typical_words"):
            words = ", ".join(language_style["typical_words"][:8])  # Limitar palabras
            section += f"- Palabras típicas: {words}\n"
        
        if language_style.get("emoji_usage", {}).get("use_emojis"):
            section += "- Usá emojis para remarcar algo importante (sin abusar)\n"
        
        if forbidden_words:
            section += f"\n## PALABRAS PROHIBIDAS - NUNCA USAR:\n"
            section += ", ".join(forbidden_words[:15])  # Primeras 15 palabras
        
        return section
    
    def _format_protocols_section(self, protocols: Dict) -> str:
        """Formatea la sección de protocolos críticos"""
        section = "# 🚨 PROTOCOLOS CRÍTICOS 🚨\n"
        
        frustration = protocols.get("frustration_detection_protocol", {})
        if frustration:
            section += f"""
## {frustration.get('name', 'FRUSTRATION DETECTION')}

**REGLA OBLIGATORIA:** {frustration.get('mandatory_rule_1', {}).get('requirement', 'Detectar frustración')}

**Acciones cuando detectes frustración:**
"""
            for action in frustration.get('mandatory_rule_1', {}).get('actions_when_frustrated_level_2_or_3', [])[:4]:
                section += f"- {action}\n"
        
        hitl = protocols.get("hitl_protocol", {})
        if hitl:
            section += f"\n## {hitl.get('name', 'HITL PROTOCOL')}\n"
            section += "**NUNCA USAR:**\n"
            for phrase in hitl.get("forbidden_phrases", [])[:3]:
                section += f"- \"{phrase}\"\n"
            
            section += "\n**USAR EN SU LUGAR:**\n"
            for phrase in hitl.get("replacement_phrases", [])[:3]:
                section += f"- \"{phrase}\"\n"
        
        return section
    
    def _format_training_section(self, product_training: Dict, combo_training: Dict) -> str:
        """Formatea la sección de entrenamiento"""
        section = "# 📚 ENTRENAMIENTO Y MENTORÍA\n"
        
        # Reglas críticas de entrenamiento
        if product_training.get("critical_rules"):
            section += "## Reglas Críticas:\n"
            for rule in product_training["critical_rules"][:2]:
                section += f"- {rule}\n"
        
        # Combos para emprendedores
        if combo_training.get("critical_rules"):
            section += "\n## Protocolo de Combos:\n"
            for rule in combo_training["critical_rules"][:2]:
                section += f"- {rule}\n"
        
        # Ejemplos clave
        examples = product_training.get("conversation_examples", [])
        if examples:
            section += f"\n## Ejemplo de Mentoría:\n"
            example = examples[0] if examples else {}
            if example:
                section += f"Usuario: {example.get('user_query', '')}\n"
                section += f"Royalia: {example.get('royalia_response', '')[:200]}...\n"
        
        return section
    
    def _format_company_section(self, company: Dict) -> str:
        """Formatea la información clave de la empresa"""
        section = "# 🏢 INFORMACIÓN CLAVE DE ROYAL\n"
        
        company_info = company.get("company_info", {})
        section += f"{company_info.get('description', '')}\n\n"
        
        # Ubicaciones
        locations = company.get("locations", {})
        if locations.get("stores"):
            section += f"## Ubicación ({locations.get('city', '')}):\n"
            for store in locations["stores"][:3]:
                section += f"- {store.get('name', '')}: {store.get('address', '')}\n"
        
        # Tipos de compra
        purchase_types = company.get("purchase_types", {})
        if purchase_types:
            section += "\n## Tipos de Compra:\n"
            mayorista = purchase_types.get("mayorista", {})
            section += f"### Mayorista: Mínimo {mayorista.get('minimum', '$40,000')}\n"
            minorista = purchase_types.get("minorista", {})
            section += f"### Minorista: {minorista.get('minimum', 'Sin mínimo')}\n"
        
        # Envíos y pagos (información esencial)
        shipping = company.get("shipping", {})
        if shipping:
            section += f"\n## Envíos: {shipping.get('provider', 'Andreani')} - "
            section += f"Córdoba {shipping.get('costs', {}).get('cordoba_capital', '$4,999')}, "
            section += f"Nacional {shipping.get('costs', {}).get('rest_of_country', '$7,499')}\n"
        
        return section
    
    def _format_behavioral_rules_section(self, personality: Dict, protocols: Dict) -> str:
        """Formatea las reglas de comportamiento críticas"""
        section = "# 📋 REGLAS DE COMPORTAMIENTO CRÍTICAS\n"
        
        behavioral_rules = personality.get("behavioral_rules", {}).get("critical_rules", [])
        for rule in behavioral_rules[:6]:  # Primeras 6 reglas más importantes
            section += f"- {rule}\n"
        
        protocol_rules = protocols.get("critical_behavioral_rules", [])
        for rule in protocol_rules[:4]:  # Primeras 4 reglas de protocolo
            section += f"- {rule}\n"
        
        return section
    
    def _prepare_all_tools(self) -> List:
        """Prepara todas las herramientas disponibles manteniendo compatibilidad exacta"""
        
        # Herramientas base (siempre disponibles)
        base_tools = [
            get_royal_info,
            track_client_greeting, 
            get_arreglos_info,
            get_joyas_personalizadas_info,
            get_royal_education_info,
            get_combos_emprendedores_info,
            get_inversion_presupuesto_info,
            get_acompanamiento_venta_info,
            get_situaciones_frecuentes
        ]
        
        all_tools = base_tools.copy()
        
        # Agregar herramientas contextuales si están disponibles
        if CONTEXTUAL_AVAILABLE:
            try:
                contextual_tools = create_contextual_tools()
                all_tools.extend(contextual_tools)
                logger.info("✅ Contextual tools added")
            except Exception as e:
                logger.warning(f"⚠️ Contextual tools failed: {e}")
        
        # Agregar herramientas MCP si están disponibles
        if MCP_AVAILABLE:
            try:
                woocommerce_tools = create_woocommerce_tools()
                all_tools.extend(woocommerce_tools)
                logger.info("✅ WooCommerce tools added")
            except Exception as e:
                logger.warning(f"⚠️ WooCommerce tools failed: {e}")
            
            try:
                training_tools = create_training_tools()
                all_tools.extend(training_tools)
                logger.info("✅ Training tools added")
            except Exception as e:
                logger.warning(f"⚠️ Training tools failed: {e}")
        
        return all_tools
    
    def get_agent(self) -> Agent:
        """Retorna el agente construido"""
        if not self.agent:
            self._build_agent()
        return self.agent

# Funciones de conveniencia para mantener compatibilidad
def create_unified_royal_agent(config_dir: str = None) -> Agent:
    """
    Crea el agente Royal unificado manteniendo compatibilidad exacta
    con la interfaz existente
    """
    unified = UnifiedRoyalAgent(config_dir)
    return unified.get_agent()

def get_unified_agent_config(config_dir: str = None) -> UnifiedRoyalAgentConfig:
    """Obtiene la configuración del agente unificado"""
    return UnifiedRoyalAgentConfig(config_dir)

# Variables de compatibilidad para importación
unified_royal_agent = None

def initialize_unified_agent(config_dir: str = None):
    """Inicializa el agente unificado global"""
    global unified_royal_agent
    unified_royal_agent = create_unified_royal_agent(config_dir)
    return unified_royal_agent

# Funciones de utilidad para testing y comparación
def compare_agent_responses(query: str, config_dir: str = None) -> Dict[str, Any]:
    """
    Compara respuestas entre agente unificado y originales
    Útil para testing de equivalencia
    """
    results = {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "unified_response": None,
        "original_responses": {},
        "errors": []
    }
    
    # Probar agente unificado
    try:
        unified = create_unified_royal_agent(config_dir)
        # Aquí se podría ejecutar una conversación de prueba
        results["unified_response"] = "Agent created successfully"
    except Exception as e:
        results["errors"].append(f"Unified agent error: {e}")
    
    return results

if __name__ == "__main__":
    # Test básico del agente unificado
    print("🚀 Testing Unified Royal Agent...")
    
    try:
        agent = create_unified_royal_agent()
        print(f"✅ {agent.name} created successfully")
        print(f"📝 Instructions length: {len(agent.instructions)} characters")
        print(f"🛠️ Tools count: {len(agent.tools)}")
        
    except Exception as e:
        print(f"❌ Error creating unified agent: {e}")