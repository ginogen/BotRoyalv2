import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from agents import function_tool  # type: ignore
import httpx
from datetime import datetime
import logging

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

async def infer_category_from_query(query: str) -> Dict[str, Any]:
    """
    Infiere categoría y términos de búsqueda de la consulta del usuario.
    Analiza el query para extraer tipo de producto, material y categoría probable.
    """
    query_lower = query.lower()
    
    # Diccionario de términos clave → categorías y materiales
    product_types = {
        'joyas': ['anillo', 'anillos', 'aro', 'aros', 'cadena', 'cadenas', 'pulsera', 'pulseras', 
                  'dije', 'dijes', 'collar', 'collares', 'medalla', 'medallon', 'abretiros'],
        'bijou': ['bijouterie', 'bijou', 'insumos', 'armar', 'bases', 'piedras'],
        'relojes': ['reloj', 'relojes', 'casio', 'smartwatch', 'pulsera hora'],
        'maquillaje': ['labial', 'labiales', 'sombra', 'sombras', 'maquillaje', 'makeup', 
                       'brocha', 'brochas', 'esmalte', 'esmaltes', 'rimel', 'delineador'],
        'belleza': ['crema', 'cremas', 'aceite', 'aceites', 'mascarilla', 'serum', 'perfume'],
        'indumentaria': ['ropa', 'remera', 'remeras', 'pantalon', 'pantalones', 'vestido', 
                         'vestidos', 'campera', 'camperas', 'buzo', 'buzos', 'jean', 'jeans'],
        'accesorios': ['lentes', 'anteojos', 'gafas', 'cinturon', 'cinturones', 'billetera',
                       'cartera', 'mochila', 'bolso', 'llavero', 'vincha', 'hebilla'],
        'calzados': ['zapato', 'zapatos', 'sandalia', 'sandalias', 'zapatilla', 'zapatillas',
                     'bota', 'botas', 'ojotas', 'calzado'],
        'electronica': ['auricular', 'auriculares', 'cargador', 'cable', 'power bank', 'parlante']
    }
    
    materials = {
        'plata': ['plata', '925', 'plata 925', 'plata ley'],
        'oro': ['oro', '18k', '18 kilates', 'dorado', 'gold', 'enchapado'],
        'acero': ['acero', 'quirurgico', 'quirúrgico', 'inoxidable', 'steel']
    }
    
    # Detectar categoría principal
    detected_category = None
    detected_product_type = None
    detected_material = None
    
    # Buscar tipo de producto
    for category, keywords in product_types.items():
        for keyword in keywords:
            if keyword in query_lower:
                detected_category = category
                detected_product_type = keyword
                logger.info(f"   Detectado tipo de producto: {keyword} → categoría: {category}")
                break
        if detected_category:
            break
    
    # Buscar material
    for material, keywords in materials.items():
        for keyword in keywords:
            if keyword in query_lower:
                detected_material = material
                logger.info(f"   Detectado material: {material}")
                break
        if detected_material:
            break
    
    # Si detectamos material de joyería pero no categoría, asumir joyas
    if detected_material and not detected_category:
        detected_category = 'joyas'
        logger.info(f"   Material {detected_material} detectado → asumiendo categoría: joyas")
    
    # Extraer términos de búsqueda más específicos
    search_terms = query
    
    # Si encontramos categoría y material, buscar más específicamente
    if detected_product_type and detected_material:
        search_terms = f"{detected_product_type} {detected_material}"
    elif detected_product_type:
        search_terms = detected_product_type
    
    result = {
        'category': detected_category,
        'material': detected_material,
        'product_type': detected_product_type,
        'search_terms': search_terms,
        'original_query': query,
        'requires_clarification': detected_category is None
    }
    
    logger.info(f"   Inferencia completa: {result}")
    return result

@function_tool
async def get_product_info(product_name: str = "", product_id: str = "", category: str = "") -> str:
    """
    Obtiene información de productos de WooCommerce con búsqueda inteligente.
    
    Args:
        product_name: Nombre del producto a buscar (puede incluir tipo y material)
        product_id: ID específico del producto
        category: Categoría de productos (opcional, se infiere si no se proporciona)
    """
    
    logger.info(f"🔍 GET_PRODUCT_INFO llamada:")
    logger.info(f"   product_name: '{product_name}'")
    logger.info(f"   product_id: '{product_id}'")
    logger.info(f"   category: '{category}'")
    
    # Si hay un ID específico, buscar directamente
    if product_id:
        params = {'include': product_id}
    else:
        # Usar inferencia inteligente si tenemos product_name
        if product_name and not category:
            inference = await infer_category_from_query(product_name)
            
            # Usar los términos de búsqueda inferidos
            params = {'search': inference['search_terms']}
            
            # Si se detectó una categoría, agregarla
            if inference['category']:
                category = inference['category']
                logger.info(f"   Categoría inferida: {category}")
                
                # Si detectamos material específico, refinar la búsqueda
                if inference['material']:
                    # Para joyas, buscar con material específico
                    if category == 'joyas':
                        params['search'] = f"{inference['product_type'] or 'joya'} {inference['material']}"
                        logger.info(f"   Búsqueda refinada: {params['search']}")
        else:
            params = {}
            if product_name:
                params['search'] = product_name
            if category:
                params['category'] = category
    
    # Mapeo de categorías Royal a WooCommerce
    category_mapping = {
        'joyas': 'jewelry',
        'relojes': 'watches', 
        'maquillaje': 'makeup',
        'indumentaria': 'clothing',
        'accesorios': 'accessories',
        'bijou': 'bijouterie',
        'belleza': 'beauty',
        'calzados': 'shoes',
        'electronica': 'electronics'
    }
    
    if category and category.lower() in category_mapping:
        params['category'] = category_mapping[category.lower()]
        logger.info(f"   Categoría mapeada: {category} -> {category_mapping[category.lower()]}")
    
    result = await wc_client.make_request('products', params)
    
    if 'error' in result:
        logger.error(f"❌ Error en get_product_info: {result['error']}")
        return f"No pude obtener info de productos: {result['error']}"
    
    # La respuesta de WooCommerce es directamente una lista, no un dict con 'products'
    products = result if isinstance(result, list) else result.get('products', [])
    
    logger.info(f"📦 Productos encontrados: {len(products)}")
    
    # Si no encontramos productos con búsqueda específica, intentar búsqueda más amplia
    if not products and product_name:
        logger.info("   No se encontraron productos, intentando búsqueda ampliada...")
        
        # Si habíamos inferido una categoría, intentar sin ella
        if 'category' in params:
            params_broad = {'search': product_name}
            result_broad = await wc_client.make_request('products', params_broad)
            
            if not isinstance(result_broad, dict) or 'error' not in result_broad:
                products = result_broad if isinstance(result_broad, list) else result_broad.get('products', [])
                logger.info(f"   Búsqueda ampliada encontró: {len(products)} productos")
        
        # Si aún no hay resultados, intentar con términos parciales
        if not products and ' ' in product_name:
            # Buscar por la palabra más relevante (generalmente el tipo de producto)
            main_term = product_name.split()[0]
            params_partial = {'search': main_term}
            result_partial = await wc_client.make_request('products', params_partial)
            
            if not isinstance(result_partial, dict) or 'error' not in result_partial:
                products = result_partial if isinstance(result_partial, list) else result_partial.get('products', [])
                logger.info(f"   Búsqueda parcial con '{main_term}' encontró: {len(products)} productos")
    
    if not products:
        # Mensaje más útil basado en lo que buscábamos
        if product_name and 'plata' in product_name.lower():
            return f"❌ No encontré productos de plata que coincidan con '{product_name}'.\n\n💡 **Te puedo ayudar con:**\n• Ver todo el catálogo de joyas de plata\n• Buscar un tipo específico (anillos, aros, cadenas)\n• Mostrarte los combos para emprendedores\n\n¿Qué preferís?"
        elif product_name:
            return f"❌ No encontré productos que coincidan exactamente con '{product_name}'.\n\n💡 **Probá especificando:**\n• El tipo exacto de producto\n• El material o categoría\n• O decime 'mostrame todo de [categoría]'\n\n¿Cómo te puedo ayudar?"
        else:
            return f"No encontré productos en la categoría '{category}'"
    
    # Log del primer producto para debug
    if len(products) > 0:
        logger.info(f"   Primer producto keys: {list(products[0].keys())}")
        logger.info(f"   Primer producto name: {products[0].get('name', 'Sin nombre')}")
    
    # Formatear respuesta para Royalia
    products_info = []
    for product in products[:5]:  # Máximo 5 productos
        # Adaptarse a la estructura real de WooCommerce
        name = product.get('name', 'Sin nombre')
        price = product.get('price', product.get('regular_price', 'Consultar'))
        stock_status = product.get('stock_status', 'instock') == 'instock'
        permalink = product.get('permalink', '')
        
        # Manejar categorías
        categories = product.get('categories', [])
        category_name = categories[0].get('name', 'General') if categories else 'General'
        
        info = f"""
📦 **{name}**
💰 Precio: ${price}
📊 Stock: {'✅ Disponible' if stock_status else '❌ Sin stock'}
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
    
    products_list = []
    for product in products[:8]:  # Máximo 8 productos
        name = product.get('name', 'Sin nombre')
        price = product.get('price', 0)
        permalink = product.get('permalink', '')
        
        product_info = f"• {name} - ${price}"
        if permalink:
            product_info += f" 🔗 {permalink}"
        
        products_list.append(product_info)
    
    return f"💰 **Productos entre ${min_price} y ${max_price}:**\n" + "\n".join(products_list)

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
            name = product.get('name', 'Sin nombre')
            price = product.get('price', product.get('regular_price', 'Consultar'))
            stock_status = product.get('stock_status', 'instock') == 'instock'
            permalink = product.get('permalink', '')
            
            info = f"""
🎁 **{name}**
💰 Precio: ${price}
📊 Stock: {'✅ Disponible' if stock_status else '❌ Sin stock'}"""
            
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
                price = product.get('price', product.get('regular_price', 'Consultar'))
                stock_status = product.get('stock_status', 'instock') == 'instock'
                permalink = product.get('permalink', '')
                
                info = f"""
💎 **{name}**
💰 Precio: ${price}
📊 Stock: {'✅ Disponible' if stock_status else '❌ Sin stock'}"""
                
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
    stock_quantity = product.get('stock_quantity', 'No especificado')
    permalink = product.get('permalink', '')
    sku = product.get('sku', 'No disponible')
    
    # Descripción corta
    short_description = product.get('short_description', '')
    
    # Categorías
    categories = product.get('categories', [])
    category_names = [cat.get('name', '') for cat in categories]
    
    # Formatear respuesta detallada
    details = f"""
📦 **{name}**
🆔 SKU: {sku}
💰 Precio: ${price}"""
    
    if sale_price and regular_price and sale_price != regular_price:
        details += f"\n🔥 OFERTA: ${sale_price} (antes ${regular_price})"
    
    details += f"""
📊 Stock: {'✅ Disponible' if stock_status else '❌ Sin stock'}"""
    
    if stock_quantity != 'No especificado' and stock_quantity is not None:
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

def create_woocommerce_tools():
    """Retorna lista de tools de WooCommerce para usar en el agente"""
    return [
        get_product_info,
        check_stock_availability, 
        get_product_categories,
        search_products_by_price_range,
        get_combo_emprendedor_products,
        get_product_details_with_link
    ] 