"""
Sistema de Knowledge Base Centralizado para Royal Bot v2
Gestiona todo el conocimiento estático y dinámico del bot
"""

import json
import os
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import logging
from datetime import datetime, timedelta
from functools import lru_cache

logger = logging.getLogger(__name__)


class RoyalKnowledgeBase:
    """
    Sistema centralizado de conocimiento para Royal Bot.
    Carga y gestiona toda la información desde archivos JSON.
    """
    
    def __init__(self, knowledge_dir: Optional[str] = None):
        """
        Inicializa el Knowledge Base.
        
        Args:
            knowledge_dir: Directorio con los archivos JSON de conocimiento
        """
        # Determinar directorio de conocimiento
        if knowledge_dir:
            self.knowledge_dir = Path(knowledge_dir)
        else:
            # Por defecto: knowledge/ en la raíz del proyecto
            self.knowledge_dir = Path(__file__).parent.parent.parent / "knowledge"
        
        # Directorios específicos
        self.static_dir = self.knowledge_dir / "static"
        self.dynamic_dir = self.knowledge_dir / "dynamic"
        
        # Cache de datos cargados
        self._company_data: Optional[Dict] = None
        self._faq_data: Optional[Dict] = None
        self._personality_data: Optional[Dict] = None
        self._policies_data: Optional[Dict] = None
        
        # Cache dinámico con TTL
        self._dynamic_cache: Dict[str, Dict] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=30)  # TTL de 30 minutos
        
        # Cargar datos al inicializar
        self._load_all_data()
        
    def _load_all_data(self) -> None:
        """Carga todos los datos estáticos al inicializar."""
        try:
            # Cargar company.json
            company_path = self.static_dir / "company.json"
            if company_path.exists():
                with open(company_path, 'r', encoding='utf-8') as f:
                    self._company_data = json.load(f)
                logger.info("✅ Company data cargada")
            else:
                logger.warning(f"⚠️ No se encontró {company_path}")
                
            # Cargar faq.json
            faq_path = self.static_dir / "faq.json"
            if faq_path.exists():
                with open(faq_path, 'r', encoding='utf-8') as f:
                    self._faq_data = json.load(f)
                logger.info("✅ FAQ data cargada")
            else:
                logger.warning(f"⚠️ No se encontró {faq_path}")
                
            # Cargar personality.json
            personality_path = self.static_dir / "personality.json"
            if personality_path.exists():
                with open(personality_path, 'r', encoding='utf-8') as f:
                    self._personality_data = json.load(f)
                logger.info("✅ Personality data cargada")
            else:
                logger.warning(f"⚠️ No se encontró {personality_path}")
                
            # Cargar policies.json
            policies_path = self.static_dir / "policies.json"
            if policies_path.exists():
                with open(policies_path, 'r', encoding='utf-8') as f:
                    self._policies_data = json.load(f)
                logger.info("✅ Policies data cargada")
            else:
                logger.warning(f"⚠️ No se encontró {policies_path}")
                
        except Exception as e:
            logger.error(f"❌ Error cargando datos: {e}")
            
    def reload_data(self) -> None:
        """Recarga todos los datos desde los archivos."""
        logger.info("🔄 Recargando Knowledge Base...")
        self._load_all_data()
        self._clear_dynamic_cache()
        
    def _clear_dynamic_cache(self) -> None:
        """Limpia el cache dinámico."""
        self._dynamic_cache.clear()
        self._cache_timestamps.clear()
        logger.info("🧹 Cache dinámico limpiado")
        
    # === Métodos de acceso a Company Info ===
    
    def get_company_info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene información de la empresa.
        
        Args:
            section: Sección específica (general, locations, schedule, etc.)
            
        Returns:
            Información solicitada
        """
        if not self._company_data:
            return {}
            
        if section:
            return self._company_data.get(section, {})
        return self._company_data
    
    def get_locations(self) -> List[Dict[str, str]]:
        """Obtiene las ubicaciones de los locales."""
        locations = self.get_company_info("locations")
        return locations.get("stores", [])
    
    def get_schedule(self) -> Dict[str, str]:
        """Obtiene los horarios de atención."""
        return self.get_company_info("schedule")
    
    def get_social_media(self) -> Dict[str, Any]:
        """Obtiene las redes sociales."""
        return self.get_company_info("social_media")
    
    def get_shipping_info(self) -> Dict[str, Any]:
        """Obtiene información de envíos."""
        return self.get_company_info("shipping")
    
    def get_payment_methods(self) -> Dict[str, Any]:
        """Obtiene métodos de pago."""
        return self.get_company_info("payment_methods")
    
    def get_minimum_purchase(self, purchase_type: str = "wholesale") -> int:
        """
        Obtiene el mínimo de compra.
        
        Args:
            purchase_type: "wholesale" o "retail"
        """
        purchase_types = self.get_company_info("purchase_types")
        if purchase_type in purchase_types:
            return purchase_types[purchase_type].get("minimum", 0)
        return 0
    
    # === Métodos de acceso a FAQs ===
    
    def get_faq(self, faq_id: Optional[str] = None) -> Union[Dict, List[Dict]]:
        """
        Obtiene preguntas frecuentes.
        
        Args:
            faq_id: ID específico de FAQ
            
        Returns:
            FAQ solicitada o lista de todas
        """
        if not self._faq_data:
            return [] if not faq_id else {}
            
        faqs = self._faq_data.get("faqs", [])
        
        if faq_id:
            for faq in faqs:
                if faq.get("id") == faq_id:
                    return faq
            return {}
            
        return faqs
    
    def get_faq_by_category(self, category: str) -> List[Dict]:
        """Obtiene FAQs de una categoría específica."""
        faqs = self.get_faq()
        if isinstance(faqs, list):
            return [faq for faq in faqs if faq.get("category") == category]
        return []
    
    def search_faq(self, query: str) -> List[Dict]:
        """
        Busca FAQs que contengan el query.
        
        Args:
            query: Texto a buscar
            
        Returns:
            Lista de FAQs relevantes
        """
        query_lower = query.lower()
        faqs = self.get_faq()
        results = []
        
        if isinstance(faqs, list):
            for faq in faqs:
                question = faq.get("question", "").lower()
                answer = faq.get("answer", "").lower()
                if query_lower in question or query_lower in answer:
                    results.append(faq)
                    
        return results
    
    # === Métodos de acceso a Personality ===
    
    def get_personality(self, aspect: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene configuración de personalidad.
        
        Args:
            aspect: Aspecto específico (tone, forbidden_words, etc.)
        """
        if not self._personality_data:
            return {}
            
        if aspect:
            return self._personality_data.get(aspect, {})
        return self._personality_data
    
    def get_forbidden_words(self) -> List[str]:
        """Obtiene lista de palabras prohibidas."""
        return self.get_personality("forbidden_words") or []
    
    def get_conversation_approach(self, user_type: str) -> Dict[str, Any]:
        """
        Obtiene enfoque de conversación según tipo de usuario.
        
        Args:
            user_type: "new_entrepreneurs", "experienced_sellers", "retail_customers"
        """
        approaches = self.get_personality("conversation_approach")
        return approaches.get(user_type, {})
    
    def get_error_message(self, error_type: str) -> str:
        """
        Obtiene mensaje de error apropiado.
        
        Args:
            error_type: "unknown_info", "technical_issue", "need_clarification"
        """
        error_handling = self.get_personality("error_handling")
        return error_handling.get(error_type, "Hubo un problema, intentemos de nuevo.")
    
    # === Métodos de acceso a Policies ===
    
    def get_policy(self, policy_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene políticas de la empresa.
        
        Args:
            policy_type: Tipo de política (sales, shipping, return, etc.)
        """
        if not self._policies_data:
            return {}
            
        if policy_type:
            return self._policies_data.get(f"{policy_type}_policies", {})
        return self._policies_data
    
    def get_wholesale_requirements(self) -> Dict[str, Any]:
        """Obtiene requisitos para compra mayorista."""
        sales_policies = self.get_policy("sales")
        return sales_policies.get("wholesale", {}).get("requirements", {})
    
    def get_shipping_costs(self) -> Dict[str, int]:
        """Obtiene costos de envío."""
        shipping = self.get_company_info("shipping")
        return shipping.get("costs", {})
    
    # === Métodos de URLs ===
    
    def get_url(self, url_type: str) -> str:
        """
        Obtiene URL específica.
        
        Args:
            url_type: Tipo de URL (main_store, jewelry, etc.)
        """
        urls = self.get_company_info("urls")
        return urls.get(url_type, "")
    
    def get_all_urls(self) -> Dict[str, str]:
        """Obtiene todas las URLs disponibles."""
        return self.get_company_info("urls")
    
    # === Métodos de cache dinámico ===
    
    def set_dynamic_data(self, key: str, data: Dict, ttl_minutes: Optional[int] = None) -> None:
        """
        Guarda datos dinámicos en cache.
        
        Args:
            key: Clave del cache
            data: Datos a guardar
            ttl_minutes: TTL personalizado en minutos
        """
        self._dynamic_cache[key] = data
        self._cache_timestamps[key] = datetime.now()
        
        if ttl_minutes:
            # Guardar TTL personalizado si se especifica
            self._dynamic_cache[f"{key}_ttl"] = timedelta(minutes=ttl_minutes)
            
        logger.info(f"💾 Datos dinámicos guardados en cache: {key}")
    
    def get_dynamic_data(self, key: str) -> Optional[Dict]:
        """
        Obtiene datos dinámicos del cache.
        
        Args:
            key: Clave del cache
            
        Returns:
            Datos si están en cache y no expiraron
        """
        if key not in self._dynamic_cache:
            return None
            
        # Verificar TTL
        timestamp = self._cache_timestamps.get(key)
        if timestamp:
            # Usar TTL personalizado si existe
            ttl = self._dynamic_cache.get(f"{key}_ttl", self._cache_ttl)
            if datetime.now() - timestamp > ttl:
                # Cache expirado
                del self._dynamic_cache[key]
                del self._cache_timestamps[key]
                logger.info(f"🗑️ Cache expirado y eliminado: {key}")
                return None
                
        return self._dynamic_cache.get(key)
    
    # === Métodos de búsqueda general ===
    
    @lru_cache(maxsize=128)
    def search_knowledge(self, query: str) -> Dict[str, List[Any]]:
        """
        Busca en todo el knowledge base.
        Usa LRU cache para queries frecuentes.
        
        Args:
            query: Texto a buscar
            
        Returns:
            Diccionario con resultados por categoría
        """
        query_lower = query.lower()
        results = {
            "faqs": [],
            "policies": [],
            "company": [],
            "urls": []
        }
        
        # Buscar en FAQs
        results["faqs"] = self.search_faq(query)
        
        # Buscar en company info
        if self._company_data:
            company_str = json.dumps(self._company_data, ensure_ascii=False).lower()
            if query_lower in company_str:
                # Encontrar sección específica
                for section, content in self._company_data.items():
                    content_str = json.dumps(content, ensure_ascii=False).lower()
                    if query_lower in content_str:
                        results["company"].append({
                            "section": section,
                            "content": content
                        })
        
        # Buscar en políticas
        if self._policies_data:
            for policy_type, content in self._policies_data.items():
                content_str = json.dumps(content, ensure_ascii=False).lower()
                if query_lower in content_str:
                    results["policies"].append({
                        "type": policy_type,
                        "content": content
                    })
        
        # Buscar en URLs
        urls = self.get_all_urls()
        for url_type, url in urls.items():
            if query_lower in url_type.lower() or query_lower in url.lower():
                results["urls"].append({
                    "type": url_type,
                    "url": url
                })
                
        return results
    
    # === Métodos de utilidad ===
    
    def get_formatted_info(self, info_type: str) -> str:
        """
        Obtiene información formateada para respuestas.
        
        Args:
            info_type: Tipo de información a formatear
        """
        formatters = {
            "locations": self._format_locations,
            "schedule": self._format_schedule,
            "shipping": self._format_shipping,
            "payment": self._format_payment,
            "minimum": self._format_minimum
        }
        
        formatter = formatters.get(info_type)
        if formatter:
            return formatter()
        return ""
    
    def _format_locations(self) -> str:
        """Formatea ubicaciones para respuesta."""
        locations = self.get_locations()
        if not locations:
            return "No hay información de ubicaciones disponible."
            
        result = "📍 **Nuestros locales en Córdoba Capital:**\n"
        for loc in locations:
            result += f"• {loc['name']}: {loc['address']}\n"
        return result
    
    def _format_schedule(self) -> str:
        """Formatea horarios para respuesta."""
        schedule = self.get_schedule()
        if not schedule:
            return "No hay información de horarios disponible."
            
        result = "🕐 **Horarios de atención:**\n"
        result += f"• Lunes a viernes: {schedule.get('weekdays', 'N/A')}\n"
        result += f"• Sábados: {schedule.get('saturdays', 'N/A')}\n"
        result += f"• Tienda online: {schedule.get('online_store', 'N/A')}"
        return result
    
    def _format_shipping(self) -> str:
        """Formatea información de envíos para respuesta."""
        shipping = self.get_shipping_info()
        if not shipping:
            return "No hay información de envíos disponible."
            
        costs = shipping.get("costs", {})
        times = shipping.get("delivery_times", {})
        
        result = "📦 **Información de envíos:**\n"
        result += f"• Córdoba Capital: ${costs.get('cordoba_capital', 'N/A')}\n"
        result += f"• Resto del país: ${costs.get('rest_of_country', 'N/A')}\n"
        result += f"• Envío gratis: Compras desde ${costs.get('free_shipping_threshold', 'N/A')}\n"
        result += f"• Empresa: {shipping.get('provider', 'N/A')} ({shipping.get('insurance', 'N/A')})"
        return result
    
    def _format_payment(self) -> str:
        """Formatea métodos de pago para respuesta."""
        payment = self.get_payment_methods()
        if not payment:
            return "No hay información de pagos disponible."
            
        result = "💳 **Métodos de pago:**\n"
        
        if payment.get("credit_card", {}).get("enabled"):
            installments = payment["credit_card"].get("installments", "N/A")
            result += f"• Tarjeta de crédito (hasta {installments} cuotas sin interés)\n"
            
        if payment.get("bank_transfer", {}).get("enabled"):
            result += f"• Transferencia bancaria\n"
            result += f"  - CBU: {payment['bank_transfer'].get('cbu', 'N/A')}\n"
            result += f"  - Alias: {payment['bank_transfer'].get('alias', 'N/A')}\n"
            
        if payment.get("cash", {}).get("enabled"):
            result += f"• Efectivo en locales\n"
            
        if payment.get("deposit_system", {}).get("enabled"):
            deposit = payment["deposit_system"].get("amount", "N/A")
            result += f"• Sistema de seña: ${deposit}"
            
        return result
    
    def _format_minimum(self) -> str:
        """Formatea información de mínimos de compra."""
        wholesale_min = self.get_minimum_purchase("wholesale")
        retail_min = self.get_minimum_purchase("retail")
        
        result = "💰 **Mínimos de compra:**\n"
        result += f"• Mayorista: ${wholesale_min:,}".replace(",", ".")
        result += " (precios especiales)\n"
        result += f"• Minorista: Sin mínimo (precios regulares)"
        return result
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen del knowledge base cargado.
        
        Returns:
            Estadísticas del knowledge base
        """
        try:
            cache_size = len(json.dumps(self._dynamic_cache, default=str))
        except:
            cache_size = 0
            
        return {
            "company_sections": len(self._company_data) if self._company_data else 0,
            "faqs_count": len(self.get_faq()) if isinstance(self.get_faq(), list) else 0,
            "personality_aspects": len(self._personality_data) if self._personality_data else 0,
            "policy_types": len(self._policies_data) if self._policies_data else 0,
            "dynamic_cache_items": len(self._dynamic_cache),
            "cache_size_bytes": cache_size
        }


# Instancia singleton para uso global
_kb_instance: Optional[RoyalKnowledgeBase] = None

def get_knowledge_base() -> RoyalKnowledgeBase:
    """
    Obtiene la instancia singleton del Knowledge Base.
    
    Returns:
        Instancia de RoyalKnowledgeBase
    """
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = RoyalKnowledgeBase()
    return _kb_instance