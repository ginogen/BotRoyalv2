import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from agents import function_tool  # type: ignore
import httpx
from datetime import datetime
import logging
import sys

# Importar función de fallback para categorías locales
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from category_matcher import find_categories

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("✅ Variables de entorno cargadas con python-dotenv")
except ImportError:
    logger.warning("⚠️ python-dotenv no instalado. Instalar con: pip install python-dotenv")

class WooCommerceMCPClient:
    """Cliente para conectar con MCP Server de WooCommerce"""
    
    def __init__(self):
        # Cargar configuración con logging detallado
        self.base_url = os.getenv('WOOCOMMERCE_SITE_URL', 'https://royal-company.com')
        self.consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
        self.consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
        self.mcp_server_url = os.getenv('MCP_SERVER_URL', 'http://localhost:3000')
        
        # Log de configuración (sin mostrar secrets completos)
        logger.info("🔧 CONFIGURACIÓN WOOCOMMERCE:")
        logger.info(f"   URL: {self.base_url}")
        logger.info(f"   Consumer Key: {'✅ Configurado' if self.consumer_key else '❌ NO CONFIGURADO'}")
        logger.info(f"   Consumer Secret: {'✅ Configurado' if self.consumer_secret else '❌ NO CONFIGURADO'}")
        logger.info(f"   MCP Server: {self.mcp_server_url}")
        
        if not self.consumer_key or not self.consumer_secret:
            logger.error("❌ CRÍTICO: Variables WooCommerce no configuradas!")
            logger.error("   Verificar: WOOCOMMERCE_CONSUMER_KEY y WOOCOMMERCE_CONSUMER_SECRET")
            
    async def make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Hace request directo a la API REST de WooCommerce con logging detallado"""
        
        # Log de inicio de request
        logger.info(f"🌐 REQUEST WooCommerce: {endpoint}")
        logger.info(f"   Parámetros: {params}")
        
        try:
            # Validar configuración antes del request
            if not self.consumer_key or not self.consumer_secret:
                error_msg = "Variables de WooCommerce no configuradas"
                logger.error(f"❌ {error_msg}")
                return {"error": error_msg}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # URL directa a la API REST de WooCommerce
                url = f"{self.base_url}/wp-json/wc/v3/{endpoint}"
                logger.info(f"   URL completa: {url}")
                
                # Autenticación básica con consumer key y secret
                auth = (self.consumer_key, self.consumer_secret)
                
                # Hacer el request
                logger.info("   Enviando request...")
                response = await client.get(url, params=params, auth=auth)
                
                # Log de respuesta
                logger.info(f"   Status Code: {response.status_code}")
                logger.info(f"   Headers: {dict(response.headers)}")
                
                # Verificar status code
                if response.status_code == 401:
                    error_msg = "Error de autenticación - Verificar Consumer Key/Secret"
                    logger.error(f"❌ {error_msg}")
                    return {"error": error_msg}
                elif response.status_code == 404:
                    error_msg = f"Endpoint no encontrado: {endpoint}"
                    logger.error(f"❌ {error_msg}")
                    return {"error": error_msg}
                elif response.status_code != 200:
                    error_msg = f"Error HTTP {response.status_code}: {response.text}"
                    logger.error(f"❌ {error_msg}")
                    return {"error": error_msg}
                
                # Parsear respuesta JSON
                try:
                    json_data = response.json()
                    logger.info(f"✅ Respuesta exitosa: {len(json_data) if isinstance(json_data, list) else 'object'} elementos")
                    
                    # Log detallado de la estructura de respuesta
                    if isinstance(json_data, list) and len(json_data) > 0:
                        logger.info(f"   Primer elemento keys: {list(json_data[0].keys())}")
                    elif isinstance(json_data, dict):
                        logger.info(f"   Respuesta keys: {list(json_data.keys())}")
                    
                    return json_data
                    
                except json.JSONDecodeError as e:
                    error_msg = f"Error parseando JSON: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    logger.error(f"   Respuesta raw: {response.text[:500]}")
                    return {"error": error_msg}
                
        except httpx.TimeoutException:
            error_msg = f"Timeout conectando con {self.base_url}"
            logger.error(f"❌ {error_msg}")
            return {"error": error_msg}
        except httpx.ConnectError:
            error_msg = f"Error de conexión con {self.base_url}"
            logger.error(f"❌ {error_msg}")
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"error": error_msg}

# Instancia global del cliente
wc_client = WooCommerceMCPClient()

@function_tool
async def get_product_info(product_name: str = "", product_id: str = "", category: str = "") -> str:
    """
    Obtiene información de productos de WooCommerce.
    
    Args:
        product_name: Nombre del producto a buscar
        product_id: ID específico del producto
        category: Categoría de productos (joyas, relojes, maquillaje, etc.)
    """
    
    logger.info(f"🔍 GET_PRODUCT_INFO llamada:")
    logger.info(f"   product_name: '{product_name}'")
    logger.info(f"   product_id: '{product_id}'")
    logger.info(f"   category: '{category}'")
    
    params = {}
    if product_name:
        params['search'] = product_name
    if product_id:
        params['include'] = product_id
    if category:
        params['category'] = category
    
    # Mapeo de categorías Royal a WooCommerce
    category_mapping = {
        'joyas': 'jewelry',
        'relojes': 'watches', 
        'maquillaje': 'makeup',
        'indumentaria': 'clothing',
        'accesorios': 'accessories'
    }
    
    if category.lower() in category_mapping:
        params['category'] = category_mapping[category.lower()]
        logger.info(f"   Categoría mapeada: {category} -> {category_mapping[category.lower()]}")
    
    result = await wc_client.make_request('products', params)
    
    if 'error' in result:
        logger.error(f"❌ Error en get_product_info: {result['error']}")
        return f"No pude obtener info de productos: {result['error']}"
    
    # La respuesta de WooCommerce es directamente una lista, no un dict con 'products'
    products = result if isinstance(result, list) else result.get('products', [])
    
    logger.info(f"📦 Productos encontrados: {len(products)}")
    
    if not products:
        logger.info(f"   No se encontraron productos para: {product_name or category}")
        return f"No encontré productos que coincidan con '{product_name or category}'"
    
    # Log del primer producto para debug
    if len(products) > 0:
        logger.info(f"   Primer producto keys: {list(products[0].keys())}")
        logger.info(f"   Primer producto name: {products[0].get('name', 'Sin nombre')}")
    
    # Filtrar solo productos EN STOCK
    in_stock_products = []
    for product in products:
        # Verificar stock usando múltiples campos de WooCommerce
        stock_status = product.get('stock_status', 'instock') == 'instock'
        in_stock = product.get('in_stock', True)  # Default True para compatibilidad
        stock_quantity = product.get('stock_quantity')
        
        # Producto está en stock si stock_status es 'instock'
        is_available = stock_status and in_stock
        if stock_quantity is not None and stock_quantity == 0:
            is_available = False
            
        if is_available:
            in_stock_products.append(product)
    
    logger.info(f"📦 Productos EN STOCK: {len(in_stock_products)} de {len(products)} total")
    
    # Si NO hay productos en stock, activar fallback con categorías
    if not in_stock_products:
        logger.warning(f"⚠️ Productos encontrados pero SIN STOCK para: {product_name or category}")
        logger.info(f"🔄 Activando fallback con categorías locales")
        
        search_term = product_name or category or "productos"
        try:
            matches = find_categories(search_term, max_results=6)
            
            if matches:
                logger.info(f"✅ Fallback exitoso: {len(matches)} categorías encontradas")
                
                categories_info = []
                for match in matches[:5]:
                    category_info = f"""
📦 **{match.category.name}**
🔗 Ver productos: {match.category.url}
"""
                    categories_info.append(category_info)
                
                response = f"📦 **Los productos están agotados, pero encontré estas categorías relacionadas:**\n"
                response += "\n".join(categories_info)
                
                return response
            else:
                return f"Los productos están agotados temporalmente. Dejame consultar con el equipo para opciones alternativas."
                
        except Exception as e:
            logger.error(f"❌ Error en fallback: {str(e)}")
            return f"Los productos están agotados temporalmente. Dejame consultar con el equipo para opciones alternativas."
    
    # Formatear solo productos EN STOCK
    products_info = []
    for product in in_stock_products[:5]:  # Máximo 5 productos
        # Adaptarse a la estructura real de WooCommerce
        name = product.get('name', 'Sin nombre')
        price = product.get('price', product.get('regular_price', 'Consultar'))
        permalink = product.get('permalink', '')
        
        # Manejar categorías
        categories = product.get('categories', [])
        category_name = categories[0].get('name', 'General') if categories else 'General'
        
        info = f"""
📦 **{name}**
💰 Precio: ${price}
📊 Stock: ✅ Disponible
🏷️ Categoría: {category_name}"""
        
        if product.get('sale_price'):
            info += f"\n🔥 Oferta: ${product.get('sale_price')} (antes ${product.get('regular_price')})"
            
        if permalink:
            info += f"\n🔗 Ver producto: {permalink}"
        
        info += "\n"
        products_info.append(info)
    
    logger.info(f"✅ Respuesta formateada para {len(products_info)} productos")
    return "\n".join(products_info)

@function_tool
async def check_stock_availability(product_ids: List[str]) -> str:
    """
    Verifica disponibilidad de stock para productos específicos.
    
    Args:
        product_ids: Lista de IDs de productos a verificar
    """
    
    results = []
    for product_id in product_ids:
        result = await wc_client.make_request(f'products/{product_id}')
        
        if 'error' not in result:
            product = result.get('product', {})
            stock_status = "✅ Disponible" if product.get('in_stock') else "❌ Sin stock"
            stock_quantity = product.get('stock_quantity', 'No especificado')
            
            results.append(f"""
{product.get('name', f'Producto {product_id}')}:
Stock: {stock_status}
Cantidad: {stock_quantity}
""")
    
    return "\n".join(results) if results else "No se pudo verificar el stock"


@function_tool
async def get_product_categories() -> str:
    """Obtiene las categorías de productos disponibles en WooCommerce."""
    
    logger.info("🏷️ GET_PRODUCT_CATEGORIES llamada")
    
    result = await wc_client.make_request('products/categories')
    
    if 'error' in result:
        logger.error(f"❌ Error en get_product_categories: {result['error']}")
        return "No pude obtener las categorías en este momento"
    
    # La respuesta de WooCommerce es directamente una lista, no un dict con 'categories'
    categories_data = result if isinstance(result, list) else result.get('categories', [])
    
    logger.info(f"📂 Categorías encontradas: {len(categories_data)}")
    
    # Log del primer elemento para debug
    if len(categories_data) > 0:
        logger.info(f"   Primera categoría keys: {list(categories_data[0].keys())}")
        logger.info(f"   Primera categoría: {categories_data[0].get('name', 'Sin nombre')}")
    
    categories = []
    for cat in categories_data:
        count = cat.get('count', 0)
        if count > 0:  # Solo categorías con productos
            categories.append(f"🏷️ {cat.get('name')} ({count} productos)")
    
    logger.info(f"✅ Categorías con productos: {len(categories)}")
    
    if not categories:
        return "📂 **No encontré categorías con productos disponibles en este momento**"
    
    return "📂 **Categorías disponibles:**\n" + "\n".join(categories[:10])

@function_tool
async def search_products_by_price_range(min_price: float, max_price: float, category: str = "") -> str:
    """
    Busca productos dentro de un rango de precios.
    
    Args:
        min_price: Precio mínimo
        max_price: Precio máximo  
        category: Categoría opcional para filtrar
    """
    
    params = {
        'min_price': min_price,
        'max_price': max_price,
        'per_page': 10
    }
    
    if category:
        params['category'] = category
    
    result = await wc_client.make_request('products', params)
    
    if 'error' in result:
        return f"Error buscando productos: {result['error']}"
    
    products = result.get('products', [])
    if not products:
        return f"No encontré productos entre ${min_price} y ${max_price}"
    
    # Filtrar solo productos EN STOCK
    in_stock_products = []
    for product in products:
        stock_status = product.get('stock_status', 'instock') == 'instock'
        in_stock = product.get('in_stock', True)
        stock_quantity = product.get('stock_quantity')
        
        is_available = stock_status and in_stock
        if stock_quantity is not None and stock_quantity == 0:
            is_available = False
            
        if is_available:
            in_stock_products.append(product)
    
    if not in_stock_products:
        return f"No hay productos disponibles en stock entre ${min_price} y ${max_price} en este momento"
    
    products_list = []
    for product in in_stock_products[:8]:  # Máximo 8 productos
        name = product.get('name', 'Sin nombre')
        price = product.get('price', 0)
        permalink = product.get('permalink', '')
        
        product_info = f"• {name} - ${price} ✅ Disponible"
        if permalink:
            product_info += f" 🔗 {permalink}"
        
        products_list.append(product_info)
    
    return f"💰 **Productos disponibles entre ${min_price} y ${max_price}:**\n" + "\n".join(products_list)

@function_tool
async def get_combo_emprendedor_products() -> str:
    """Obtiene combos específicos para emprendedores de WooCommerce."""
    
    logger.info("🚀 GET_COMBO_EMPRENDEDOR_PRODUCTS llamada")
    
    # Buscar productos por categoría "Combos Emprendedores" (ID 91)
    combo_result = await wc_client.make_request('products', {'category': 91, 'per_page': 8})
    
    # También buscar por término "combo"
    search_result = await wc_client.make_request('products', {'search': 'combo', 'per_page': 5})
    
    products_info = []
    
    # Procesar combos de la categoría específica
    if isinstance(combo_result, list) and len(combo_result) > 0:
        logger.info(f"📦 Combos de categoría encontrados: {len(combo_result)}")
        
        for product in combo_result[:5]:
            # Verificar stock antes de agregar
            stock_status = product.get('stock_status', 'instock') == 'instock'
            in_stock = product.get('in_stock', True)
            stock_quantity = product.get('stock_quantity')
            
            is_available = stock_status and in_stock
            if stock_quantity is not None and stock_quantity == 0:
                is_available = False
            
            # Solo agregar productos EN STOCK
            if is_available:
                name = product.get('name', 'Sin nombre')
                price = product.get('price', product.get('regular_price', 'Consultar'))
                permalink = product.get('permalink', '')
                
                info = f"""
🎁 **{name}**
💰 Precio: ${price}
📊 Stock: ✅ Disponible"""
                
                if permalink:
                    info += f"\n🔗 Ver combo: {permalink}"
                
                info += "\n"
                products_info.append(info)
    
    # Procesar resultados de búsqueda adicionales
    if isinstance(search_result, list) and len(search_result) > 0:
        logger.info(f"🔍 Combos de búsqueda encontrados: {len(search_result)}")
        
        for product in search_result[:3]:
            name = product.get('name', 'Sin nombre')
            # Evitar duplicados
            if not any(name in info for info in products_info):
                # Verificar stock antes de agregar
                stock_status = product.get('stock_status', 'instock') == 'instock'
                in_stock = product.get('in_stock', True)
                stock_quantity = product.get('stock_quantity')
                
                is_available = stock_status and in_stock
                if stock_quantity is not None and stock_quantity == 0:
                    is_available = False
                
                # Solo agregar productos EN STOCK
                if is_available:
                    price = product.get('price', product.get('regular_price', 'Consultar'))
                    permalink = product.get('permalink', '')
                    
                    info = f"""
💎 **{name}**
💰 Precio: ${price}
📊 Stock: ✅ Disponible"""
                    
                    if permalink:
                        info += f"\n🔗 Ver combo: {permalink}"
                    
                    info += "\n"
                    products_info.append(info)
    
    logger.info(f"✅ Total combos formateados: {len(products_info)}")
    
    if not products_info:
        return "📦 **No encontré combos emprendedores disponibles en este momento**"
    
    header = "🚀 **COMBOS EMPRENDEDORES DISPONIBLES:**\n"
    footer = "\n💡 *Estos son combos especiales con precios mayoristas para emprendedores*"
    
    return header + "\n".join(products_info) + footer

@function_tool
async def get_product_details_with_link(product_name: str) -> str:
    """
    Obtiene información detallada de un producto específico incluyendo enlace directo.
    
    Args:
        product_name: Nombre específico del producto a buscar
    """
    
    logger.info(f"🔍 GET_PRODUCT_DETAILS_WITH_LINK llamada para: '{product_name}'")
    
    # Buscar producto específico
    result = await wc_client.make_request('products', {'search': product_name, 'per_page': 3})
    
    if 'error' in result:
        logger.error(f"❌ Error en get_product_details_with_link: {result['error']}")
        return f"No pude obtener detalles del producto: {result['error']}"
    
    products = result if isinstance(result, list) else []
    
    if not products:
        return f"❌ No encontré el producto '{product_name}' en nuestro catálogo"
    
    # Tomar el primer producto (más relevante)
    product = products[0]
    
    name = product.get('name', 'Sin nombre')
    price = product.get('price', product.get('regular_price', 'Consultar'))
    regular_price = product.get('regular_price', '')
    sale_price = product.get('sale_price', '')
    stock_status = product.get('stock_status', 'instock') == 'instock'
    in_stock = product.get('in_stock', True)
    stock_quantity = product.get('stock_quantity', 'No especificado')
    permalink = product.get('permalink', '')
    sku = product.get('sku', 'No disponible')
    
    # Verificar disponibilidad
    is_available = stock_status and in_stock
    if stock_quantity is not None and stock_quantity == 0:
        is_available = False
    
    # Si el producto específico NO está en stock, ofrecer categorías relacionadas
    if not is_available:
        logger.warning(f"⚠️ Producto '{name}' SIN STOCK")
        logger.info(f"🔄 Activando fallback con categorías locales para: '{product_name}'")
        
        try:
            matches = find_categories(product_name, max_results=6)
            
            if matches:
                logger.info(f"✅ Fallback exitoso: {len(matches)} categorías encontradas")
                
                categories_info = []
                for match in matches[:5]:
                    category_info = f"""
📦 **{match.category.name}**
🔗 Ver productos: {match.category.url}
"""
                    categories_info.append(category_info)
                
                response = f"😔 **'{name}' está agotado temporalmente**\n\n"
                response += f"📦 **Pero encontré estas categorías relacionadas con '{product_name}':**\n"
                response += "\n".join(categories_info)
                response += "\n💬 **¡Explorá estas opciones para encontrar productos similares disponibles!**"
                
                return response
            else:
                return f"😔 **'{name}' está agotado temporalmente**\n\n💬 Dejame consultar con el equipo para opciones alternativas similares."
                
        except Exception as e:
            logger.error(f"❌ Error en fallback: {str(e)}")
            return f"😔 **'{name}' está agotado temporalmente**\n\n💬 Dejame consultar con el equipo para opciones alternativas similares."
    
    # Descripción corta
    short_description = product.get('short_description', '')
    
    # Categorías
    categories = product.get('categories', [])
    category_names = [cat.get('name', '') for cat in categories]
    
    # Formatear respuesta detallada para productos EN STOCK
    details = f"""
📦 **{name}**
🆔 SKU: {sku}
💰 Precio: ${price}"""
    
    if sale_price and regular_price and sale_price != regular_price:
        details += f"\n🔥 OFERTA: ${sale_price} (antes ${regular_price})"
    
    details += f"""
📊 Stock: ✅ Disponible"""
    
    if stock_quantity != 'No especificado' and stock_quantity is not None and stock_quantity != 0:
        details += f" ({stock_quantity} unidades)"
    
    if category_names:
        details += f"\n🏷️ Categorías: {', '.join(category_names)}"
    
    if short_description:
        # Limpiar HTML básico
        clean_description = short_description.replace('<p>', '').replace('</p>', '').replace('<br>', ' ').strip()
        if clean_description:
            details += f"\n📝 Descripción: {clean_description[:200]}..."
    
    if permalink:
        details += f"\n\n🔗 **Ver en la tienda: {permalink}**"
    else:
        details += f"\n\n💬 **Consultá disponibilidad y hacé tu pedido por WhatsApp**"
    
    logger.info(f"✅ Detalles obtenidos para: {name}")
    return details

@function_tool
async def search_products(search_term: str) -> str:
    """
    Busca productos en WooCommerce por término general.
    Útil para búsquedas amplias como "esmaltes", "perfumes", "cremas", etc.
    
    Args:
        search_term: Término de búsqueda general
    """
    
    logger.info(f"🔍 SEARCH_PRODUCTS llamada con término: '{search_term}'")
    
    # Buscar productos con el término
    result = await wc_client.make_request('products', {
        'search': search_term,
        'per_page': 10,
        'orderby': 'popularity'
    })
    
    if 'error' in result:
        logger.error(f"❌ Error en search_products: {result['error']}")
        logger.info(f"🔄 Activando fallback con categorías locales para: '{search_term}'")
        
        # FALLBACK: Usar búsqueda local de categorías
        try:
            matches = find_categories(search_term, max_results=6)
            
            if matches:
                logger.info(f"✅ Fallback exitoso: {len(matches)} categorías encontradas")
                
                # Formatear respuesta usando categorías locales
                categories_info = []
                for match in matches[:5]:  # Máximo 5 categorías
                    category_info = f"• **{match.category.name}** 🔗 [Ver productos]({match.category.url})"
                    categories_info.append(category_info)
                
                response = f"🔍 **Encontré estas categorías para '{search_term}':**\n\n"
                response += "\n".join(categories_info)
                response += "\n\n💬 **¡Hacé clic en cualquier categoría para ver todos los productos disponibles!**"
                
                return response
            else:
                logger.warning(f"⚠️ Fallback: No se encontraron categorías para '{search_term}'")
                return f"No encontré productos específicos de '{search_term}' en el sistema. Dejame consultar con el equipo para darte información precisa."
                
        except Exception as e:
            logger.error(f"❌ Error en fallback: {str(e)}")
            return "No pude realizar la búsqueda en este momento. El equipo técnico está trabajando en ello."
    
    products = result if isinstance(result, list) else []
    
    logger.info(f"📦 Productos encontrados: {len(products)}")
    
    if not products:
        # Si no encontramos productos, activar fallback con categorías
        logger.warning(f"⚠️ No se encontraron productos para: {search_term}")
        logger.info(f"🔄 Activando fallback con categorías locales para: '{search_term}'")
        
        try:
            matches = find_categories(search_term, max_results=6)
            
            if matches:
                logger.info(f"✅ Fallback exitoso: {len(matches)} categorías encontradas")
                
                categories_info = []
                for match in matches[:5]:
                    category_info = f"• **{match.category.name}** 🔗 [Ver productos]({match.category.url})"
                    categories_info.append(category_info)
                
                response = f"🔍 **No encontré productos específicos de '{search_term}' en stock, pero encontré estas categorías relacionadas:**\n\n"
                response += "\n".join(categories_info)
                response += "\n\n💬 **¡Hacé clic en cualquier categoría para ver todos los productos disponibles!**"
                
                return response
            else:
                return f"No encontré productos específicos de '{search_term}' en el sistema. Dejame consultar con el equipo para darte información precisa."
                
        except Exception as e:
            logger.error(f"❌ Error en fallback: {str(e)}")
            return f"No encontré productos específicos de '{search_term}' en el sistema. Dejame consultar con el equipo para darte información precisa."
    
    # Filtrar solo productos EN STOCK
    in_stock_products = []
    for product in products:
        # Verificar stock usando múltiples campos de WooCommerce
        stock_status = product.get('stock_status', 'instock') == 'instock'
        in_stock = product.get('in_stock', True)  # Default True para compatibilidad
        stock_quantity = product.get('stock_quantity')
        
        # Producto está en stock si:
        # - stock_status es 'instock' Y
        # - in_stock es True Y  
        # - stock_quantity no es 0 (si está definido)
        is_available = stock_status and in_stock
        if stock_quantity is not None and stock_quantity == 0:
            is_available = False
            
        if is_available:
            in_stock_products.append(product)
    
    logger.info(f"📦 Productos EN STOCK: {len(in_stock_products)} de {len(products)} total")
    
    # Si NO hay productos en stock, activar fallback con categorías
    if not in_stock_products:
        logger.warning(f"⚠️ Productos encontrados pero SIN STOCK para: {search_term}")
        logger.info(f"🔄 Activando fallback con categorías locales para: '{search_term}'")
        
        try:
            matches = find_categories(search_term, max_results=6)
            
            if matches:
                logger.info(f"✅ Fallback exitoso: {len(matches)} categorías encontradas")
                
                categories_info = []
                for match in matches[:5]:
                    category_info = f"• **{match.category.name}** 🔗 [Ver productos]({match.category.url})"
                    categories_info.append(category_info)
                
                response = f"🔍 **Los productos de '{search_term}' están agotados, pero encontré estas categorías relacionadas:**\n\n"
                response += "\n".join(categories_info)
                response += "\n\n💬 **¡Hacé clic en cualquier categoría para ver productos disponibles!**"
                
                return response
            else:
                return f"Los productos de '{search_term}' están agotados temporalmente. Dejame consultar con el equipo para opciones alternativas."
                
        except Exception as e:
            logger.error(f"❌ Error en fallback: {str(e)}")
            return f"Los productos de '{search_term}' están agotados temporalmente. Dejame consultar con el equipo para opciones alternativas."
    
    # Formatear solo productos EN STOCK
    products_info = []
    
    for product in in_stock_products[:5]:  # Máximo 5 productos
        name = product.get('name', 'Sin nombre')
        price = product.get('price', product.get('regular_price', 'Consultar'))
        
        # Formatear precio
        if price and price != 'Consultar':
            try:
                price = f"${float(price):,.0f}".replace(',', '.')
            except:
                price = f"${price}"
        
        products_info.append(f"• **{name}** - {price} ✅ Disponible")
    
    response = f"🔍 **Productos disponibles para '{search_term}':**\n\n"
    response += "\n".join(products_info)
    response += "\n\n💬 **¿Te interesa alguno en particular? Contame cuál para darte más detalles!**"
    
    return response

def create_woocommerce_tools():
    """Retorna lista de tools de WooCommerce para usar en el agente"""
    return [
        get_product_info,
        check_stock_availability, 
        get_product_categories,
        search_products_by_price_range,
        get_combo_emprendedor_products,
        get_product_details_with_link,
        search_products  # Nueva herramienta de búsqueda general
    ] 