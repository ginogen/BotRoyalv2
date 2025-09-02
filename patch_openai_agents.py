"""
Parche para manejar el error de importación de WebSearchToolFilters
Este archivo debe ejecutarse antes de importar agents
"""

import sys
import logging
from unittest.mock import MagicMock

logger = logging.getLogger(__name__)

# Primero verificar si openai está instalado
try:
    import openai
except ImportError:
    logger.warning("⚠️ OpenAI no está instalado aún, parche se aplicará después")
    sys.exit(0)

# Crear la estructura completa de módulos si no existe
if not hasattr(openai, 'types'):
    openai.types = type(sys)('openai.types')
    sys.modules['openai.types'] = openai.types

if not hasattr(openai.types, 'responses'):
    openai.types.responses = type(sys)('openai.types.responses')
    sys.modules['openai.types.responses'] = openai.types.responses

if not hasattr(openai.types.responses, 'tool'):
    openai.types.responses.tool = type(sys)('openai.types.responses.tool')
    sys.modules['openai.types.responses.tool'] = openai.types.responses.tool

# Intentar importar WebSearchToolFilters
try:
    from openai.types.responses.tool import WebSearchToolFilters
    logger.info("✅ WebSearchToolFilters ya existe, no se necesita parche")
except (ImportError, AttributeError):
    # Crear el mock de WebSearchToolFilters
    class WebSearchToolFilters:
        """Mock de WebSearchToolFilters para compatibilidad"""
        def __init__(self, *args, **kwargs):
            pass
    
    # Asignar al módulo
    openai.types.responses.tool.WebSearchToolFilters = WebSearchToolFilters
    sys.modules['openai.types.responses.tool'].WebSearchToolFilters = WebSearchToolFilters
    
    logger.info("✅ Parche aplicado: WebSearchToolFilters creado como mock")

# También crear otros mocks que puedan faltar
mock_classes = ['WebSearchTool', 'WebSearchResult', 'WebSearchQuery']
for class_name in mock_classes:
    if not hasattr(openai.types.responses.tool, class_name):
        mock_class = type(class_name, (), {})
        setattr(openai.types.responses.tool, class_name, mock_class)
        logger.info(f"✅ Mock creado para {class_name}")