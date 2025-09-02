"""
Parche para manejar el error de importación de WebSearchToolFilters
Este archivo debe ejecutarse antes de importar agents
"""

import sys
from unittest.mock import MagicMock

# Crear un mock para WebSearchToolFilters si no existe
try:
    from openai.types.responses.tool import WebSearchToolFilters
except ImportError:
    # Crear la estructura de módulos necesaria
    if 'openai.types.responses.tool' not in sys.modules:
        # Asegurarse de que todos los módulos padre existan
        import openai
        if not hasattr(openai, 'types'):
            openai.types = MagicMock()
        if not hasattr(openai.types, 'responses'):
            openai.types.responses = MagicMock()
        if not hasattr(openai.types.responses, 'tool'):
            openai.types.responses.tool = MagicMock()
        
        # Registrar en sys.modules
        sys.modules['openai.types'] = openai.types
        sys.modules['openai.types.responses'] = openai.types.responses
        sys.modules['openai.types.responses.tool'] = openai.types.responses.tool
    
    # Crear el mock de WebSearchToolFilters
    WebSearchToolFilters = MagicMock()
    WebSearchToolFilters.__name__ = 'WebSearchToolFilters'
    
    # Asignar al módulo
    sys.modules['openai.types.responses.tool'].WebSearchToolFilters = WebSearchToolFilters
    
    print("✅ Parche aplicado: WebSearchToolFilters creado como mock")