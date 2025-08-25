"""
Core modules for Royal Bot v2
Sistema centralizado de conocimiento y agente unificado
"""

from .knowledge_system import RoyalKnowledgeBase, get_knowledge_base
from .instruction_builder import InstructionBuilder, get_instruction_builder
from .unified_agent import UnifiedRoyalAgent, get_unified_agent, process_message_sync

__all__ = [
    'RoyalKnowledgeBase',
    'get_knowledge_base',
    'InstructionBuilder', 
    'get_instruction_builder',
    'UnifiedRoyalAgent',
    'get_unified_agent',
    'process_message_sync'
]

# Versión del sistema core
__version__ = '2.0.0'