#!/usr/bin/env python3
"""
🎛️ ROYAL AGENT MANAGER
Sistema de gestión de agentes con feature flags y rollback automático
Permite transición segura entre agentes originales y unificado
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from agents import Agent  # type: ignore
from datetime import datetime

# Importar todos los agentes disponibles
from .royal_agent import create_royal_agent
from .royal_agent_contextual import create_contextual_royal_agent
from .royal_agent_with_mcp import create_enhanced_royal_agent
from .unified_royal_agent import create_unified_royal_agent

logger = logging.getLogger(__name__)

class RoyalAgentManager:
    """
    Gestor inteligente de agentes Royal con feature flags,
    rollback automático y testing A/B
    """
    
    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir or "/Users/gino/BotRoyalv2/royal_config")
        self.feature_flags = {}
        self.current_agent = None
        self.agent_cache = {}
        self.health_status = {}
        self._load_feature_flags()
    
    def _load_feature_flags(self):
        """Carga los feature flags desde la configuración"""
        try:
            agent_config_path = self.config_dir / "agent_config.json"
            with open(agent_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.feature_flags = config.get("feature_flags", {})
                self.rollback_config = config.get("rollback_config", {})
            
            logger.info(f"🎛️ Feature flags loaded: {self.feature_flags}")
            
        except Exception as e:
            logger.error(f"❌ Error loading feature flags: {e}")
            # Feature flags por defecto (modo seguro)
            self.feature_flags = {
                "use_unified_agent": False,
                "preserve_original_agents": True,
                "enable_a_b_testing": False,
                "enable_response_logging": True,
                "enable_performance_metrics": True
            }
            self.rollback_config = {
                "fallback_strategy": "auto_rollback_on_error"
            }
    
    def get_active_agent(self, agent_type: str = "auto") -> Agent:
        """
        Obtiene el agente activo basado en feature flags y configuración
        
        Args:
            agent_type: "auto", "unified", "contextual", "mcp", "base"
        """
        
        # Determinar qué agente usar
        if agent_type == "auto":
            if self.feature_flags.get("use_unified_agent", False):
                selected_type = "unified"
            else:
                # Usar el agente contextual como default (más completo)
                selected_type = "contextual"
        else:
            selected_type = agent_type
        
        # Crear o recuperar agente del cache
        cache_key = f"{selected_type}_{datetime.now().strftime('%Y%m%d')}"
        
        if cache_key in self.agent_cache:
            return self.agent_cache[cache_key]
        
        try:
            agent = self._create_agent(selected_type)
            
            # Verificar salud del agente
            if self._health_check_agent(agent, selected_type):
                self.agent_cache[cache_key] = agent
                self.current_agent = agent
                logger.info(f"✅ Active agent: {selected_type} - {agent.name}")
                return agent
            else:
                # Fallback a agente base si hay problemas
                return self._fallback_agent()
                
        except Exception as e:
            logger.error(f"❌ Error creating {selected_type} agent: {e}")
            return self._fallback_agent()
    
    def _create_agent(self, agent_type: str) -> Agent:
        """Crea el agente del tipo especificado"""
        
        if agent_type == "unified":
            return create_unified_royal_agent(str(self.config_dir))
        
        elif agent_type == "contextual":
            return create_contextual_royal_agent()
        
        elif agent_type == "mcp":
            return create_enhanced_royal_agent()
        
        elif agent_type == "base":
            return create_royal_agent()
        
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
    
    def _health_check_agent(self, agent: Agent, agent_type: str) -> bool:
        """
        Verifica la salud del agente antes de activarlo
        
        Returns:
            True si el agente está saludable, False si necesita rollback
        """
        try:
            health_checks = self.rollback_config.get("health_checks", [])
            
            # Check básico - el agente tiene instrucciones y herramientas
            if not agent.instructions or not agent.tools:
                logger.warning(f"⚠️ {agent_type} agent missing instructions or tools")
                return False
            
            # Check de calidad de respuesta (si está habilitado)
            if "response_quality" in health_checks:
                if len(agent.instructions) < 500:  # Instrucciones muy cortas
                    logger.warning(f"⚠️ {agent_type} agent instructions too short")
                    return False
            
            # Check de herramientas disponibles
            if "tool_availability" in health_checks:
                if len(agent.tools) < 5:  # Muy pocas herramientas
                    logger.warning(f"⚠️ {agent_type} agent has too few tools")
                    return False
            
            # Check de consistencia de personalidad
            if "personality_consistency" in health_checks:
                if "Royalia" not in agent.instructions:
                    logger.warning(f"⚠️ {agent_type} agent missing personality")
                    return False
            
            self.health_status[agent_type] = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "checks_passed": len(health_checks)
            }
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Health check failed for {agent_type}: {e}")
            self.health_status[agent_type] = {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
            return False
    
    def _fallback_agent(self) -> Agent:
        """
        Agente de fallback cuando hay problemas con el agente principal
        Siempre retorna el agente base (más simple y estable)
        """
        try:
            logger.warning("🔄 Falling back to base agent")
            fallback = create_royal_agent()
            self.current_agent = fallback
            return fallback
        except Exception as e:
            logger.error(f"❌ Even fallback agent failed: {e}")
            raise RuntimeError("All agents failed to initialize")
    
    def switch_agent(self, agent_type: str, force: bool = False) -> bool:
        """
        Cambia el agente activo
        
        Args:
            agent_type: Tipo de agente a activar
            force: Si True, fuerza el cambio sin health checks
            
        Returns:
            True si el cambio fue exitoso
        """
        try:
            if not force:
                # Health check antes de cambiar
                test_agent = self._create_agent(agent_type)
                if not self._health_check_agent(test_agent, agent_type):
                    logger.error(f"❌ Cannot switch to {agent_type}: health check failed")
                    return False
            
            # Actualizar feature flags
            if agent_type == "unified":
                self.feature_flags["use_unified_agent"] = True
            else:
                self.feature_flags["use_unified_agent"] = False
            
            # Limpiar cache para forzar recreación
            self.agent_cache.clear()
            
            # Crear nuevo agente activo
            self.current_agent = self.get_active_agent(agent_type)
            
            logger.info(f"🔄 Successfully switched to {agent_type} agent")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to switch to {agent_type}: {e}")
            return False
    
    def get_agent_comparison(self, test_query: str = "¿Cuál es el mínimo de compra?") -> Dict[str, Any]:
        """
        Compara respuestas entre diferentes tipos de agentes
        Útil para testing A/B y validación de equivalencia
        """
        comparison = {
            "test_query": test_query,
            "timestamp": datetime.now().isoformat(),
            "agents": {},
            "summary": {}
        }
        
        agent_types = ["base", "contextual", "mcp"]
        
        # Agregar unified si está habilitado
        if self.feature_flags.get("use_unified_agent", False):
            agent_types.append("unified")
        
        for agent_type in agent_types:
            try:
                agent = self._create_agent(agent_type)
                comparison["agents"][agent_type] = {
                    "name": agent.name,
                    "instructions_length": len(agent.instructions),
                    "tools_count": len(agent.tools),
                    "tools_list": [tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in agent.tools][:10],
                    "status": "created_successfully"
                }
            except Exception as e:
                comparison["agents"][agent_type] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Resumen de comparación
        successful_agents = [k for k, v in comparison["agents"].items() if v.get("status") == "created_successfully"]
        comparison["summary"] = {
            "total_agents_tested": len(agent_types),
            "successful_agents": successful_agents,
            "failed_agents": len(agent_types) - len(successful_agents)
        }
        
        return comparison
    
    def get_health_report(self) -> Dict[str, Any]:
        """Obtiene reporte de salud de todos los agentes"""
        return {
            "current_agent": self.current_agent.name if self.current_agent else "None",
            "feature_flags": self.feature_flags,
            "health_status": self.health_status,
            "agent_cache_size": len(self.agent_cache),
            "timestamp": datetime.now().isoformat()
        }
    
    def enable_unified_agent(self) -> bool:
        """Habilita el agente unificado con verificaciones de seguridad"""
        return self.switch_agent("unified")
    
    def disable_unified_agent(self) -> bool:
        """Deshabilita el agente unificado y vuelve al contextual"""
        return self.switch_agent("contextual")

# Instancia global del manager
agent_manager = RoyalAgentManager()

# Funciones de conveniencia para usar desde otros módulos
def get_royal_agent(agent_type: str = "auto") -> Agent:
    """
    Función principal para obtener el agente Royal activo
    Reemplaza las llamadas directas a create_*_agent()
    """
    return agent_manager.get_active_agent(agent_type)

def run_contextual_conversation_sync_managed(user_id: str, user_message: str) -> str:
    """
    Wrapper que usa AgentManager para ejecutar conversaciones
    Mantiene compatibilidad con royal_server_optimized.py
    """
    try:
        # Usar el contexto original para mantener compatibilidad
        from .conversation_context import context_manager
        context = context_manager.get_or_create_context(user_id)
        
        # Obtener el agente activo a través del manager
        agent = agent_manager.get_active_agent("auto")
        
        # Ejecutar la conversación usando el patrón original
        import asyncio
        import threading
        from concurrent.futures import ThreadPoolExecutor
        
        def run_conversation():
            try:
                from agents import Runner
                with Runner(agent, context) as runner:
                    result = runner.run(user_message)
                    return result.value if hasattr(result, 'value') else str(result)
            except Exception as e:
                logger.error(f"❌ Error in managed conversation: {e}")
                # Fallback al agente contextual original
                from .royal_agent_contextual import run_contextual_conversation_sync
                return run_contextual_conversation_sync(user_id, user_message)
        
        # Ejecutar en thread pool para compatibilidad
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_conversation)
            return future.result(timeout=120)
            
    except Exception as e:
        logger.error(f"❌ Error in agent manager conversation: {e}")
        # Ultimate fallback al método original
        from .royal_agent_contextual import run_contextual_conversation_sync
        return run_contextual_conversation_sync(user_id, user_message)

def switch_to_unified_agent() -> bool:
    """Cambia al agente unificado"""
    return agent_manager.enable_unified_agent()

def switch_to_original_agent() -> bool:
    """Vuelve al agente original (contextual)"""
    return agent_manager.disable_unified_agent()

def get_agent_health() -> Dict[str, Any]:
    """Obtiene el estado de salud de los agentes"""
    return agent_manager.get_health_report()

def compare_agents(test_query: str = None) -> Dict[str, Any]:
    """Compara diferentes tipos de agentes"""
    return agent_manager.get_agent_comparison(test_query)

if __name__ == "__main__":
    # Test del agent manager
    print("🎛️ Testing Royal Agent Manager...")
    
    try:
        # Test agente por defecto
        agent = get_royal_agent()
        print(f"✅ Default agent: {agent.name}")
        
        # Test comparación de agentes
        comparison = compare_agents()
        print(f"📊 Agent comparison: {comparison['summary']}")
        
        # Test reporte de salud
        health = get_agent_health()
        print(f"🏥 Health report: {health['current_agent']}")
        
    except Exception as e:
        print(f"❌ Error testing agent manager: {e}")