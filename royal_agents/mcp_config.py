import os
from typing import Dict, Any

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv no instalado. Instalar con: pip install python-dotenv")

def get_mcp_config() -> Dict[str, Any]:
    """Configuración para el MCP Server de WooCommerce"""
    
    return {
        # Configuración WooCommerce
        'woocommerce': {
            'site_url': os.getenv('WOOCOMMERCE_SITE_URL', 'https://royal-company.com'),
            'consumer_key': os.getenv('WOOCOMMERCE_CONSUMER_KEY'),
            'consumer_secret': os.getenv('WOOCOMMERCE_CONSUMER_SECRET'),
            'version': 'wc/v3'  # Versión de la API
        },
        
        # Configuración MCP Server
        'mcp_server': {
            'url': os.getenv('MCP_SERVER_URL', 'http://localhost:3000'),
            'timeout': 30,
            'log_level': os.getenv('MCP_LOG_LEVEL', 'info')
        },
        
        # Mapeo de categorías Royal -> WooCommerce
        'category_mapping': {
            'joyas': ['jewelry', 'joyas', 'plata', 'oro'],
            'relojes': ['watches', 'relojes', 'casio'],
            'maquillaje': ['makeup', 'cosmetics', 'belleza'],
            'indumentaria': ['clothing', 'ropa', 'apparel'],
            'accesorios': ['accessories', 'accesorios']
        },
        
        # Configuración de respuestas
        'response_limits': {
            'max_products_per_search': 8,
            'max_orders_per_customer': 5,
            'max_categories_display': 10
        }
    }

def validate_mcp_config() -> bool:
    """Valida que la configuración MCP esté completa"""
    
    required_vars = [
        'WOOCOMMERCE_CONSUMER_KEY',
        'WOOCOMMERCE_CONSUMER_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️ Variables de entorno faltantes para MCP: {', '.join(missing_vars)}")
        return False
    
    print("✅ Configuración MCP completa - Conectando con WooCommerce real")
    return True

def get_mcp_server_config():
    """Configuración específica para MCP Server usando la sintaxis oficial"""
    from agents.mcp import MCPServerStdio, MCPServerSse, MCPServerStreamableHttp
    
    # Ejemplo de configuración para diferentes tipos de MCP Server
    configs = {
        'stdio': {
            'class': MCPServerStdio,
            'params': {
                'command': 'node',
                'args': ['path/to/woocommerce-mcp-server.js'],
                'env': {
                    'WOOCOMMERCE_SITE_URL': os.getenv('WOOCOMMERCE_SITE_URL'),
                    'WOOCOMMERCE_CONSUMER_KEY': os.getenv('WOOCOMMERCE_CONSUMER_KEY'),
                    'WOOCOMMERCE_CONSUMER_SECRET': os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
                }
            }
        },
        'sse': {
            'class': MCPServerSse,
            'params': {
                'url': os.getenv('MCP_SERVER_URL', 'http://localhost:3000'),
                'cache_tools_list': True  # Cache para mejor performance
            }
        },
        'http': {
            'class': MCPServerStreamableHttp,
            'params': {
                'url': os.getenv('MCP_SERVER_URL', 'http://localhost:3000'),
                'cache_tools_list': True
            }
        }
    }
    
    return configs 