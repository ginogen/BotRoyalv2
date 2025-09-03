#!/usr/bin/env python3
"""
🔍 CATEGORY MATCHER - SISTEMA DE BÚSQUEDA INTELIGENTE DE CATEGORÍAS
Busca categorías relevantes en el JSON y mapea consultas de usuarios a URLs específicas.
Usado por la IA para responder con links directos a categorías de productos.
"""

import os
import json
import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher
import unicodedata

logger = logging.getLogger(__name__)

# =====================================================
# MODELOS DE DATOS
# =====================================================

@dataclass
class Category:
    """Categoría de producto con información completa"""
    name: str
    slug: str
    url: str
    keywords: Set[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = set()

@dataclass
class CategoryMatch:
    """Resultado de búsqueda de categoría"""
    category: Category
    relevance_score: float
    matched_keywords: List[str]
    match_type: str  # 'exact', 'partial', 'keyword', 'fuzzy'

# =====================================================
# CATEGORY MATCHER PRINCIPAL
# =====================================================

class CategoryMatcher:
    """
    Sistema inteligente de búsqueda de categorías.
    Carga el JSON y crea mapeos semánticos para búsquedas eficientes.
    """
    
    def __init__(self, json_path: str = None):
        self.json_path = json_path or "/Users/gino/BotRoyalv2/Entrenamiento/todas-las-categorias.json"
        self.categories: List[Category] = []
        self.keyword_to_categories: Dict[str, List[Category]] = {}
        
        # Configuración
        self.min_relevance_score = 0.3
        self.max_results = 8
        
        # Cargar categorías
        self._load_categories()
        self._build_keyword_mappings()
        
        logger.info(f"🔍 CategoryMatcher inicializado: {len(self.categories)} categorías cargadas")
    
    def _load_categories(self) -> None:
        """Cargar categorías desde el JSON"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.categories = []
            for item in data:
                if isinstance(item, dict) and all(key in item for key in ['name', 'slug', 'url']):
                    category = Category(
                        name=item['name'],
                        slug=item['slug'], 
                        url=item['url']
                    )
                    self.categories.append(category)
            
            logger.info(f"✅ {len(self.categories)} categorías cargadas desde JSON")
            
        except Exception as e:
            logger.error(f"❌ Error cargando categorías: {e}")
            self.categories = []
    
    def _build_keyword_mappings(self) -> None:
        """Construir mapeos de keywords a categorías"""
        self.keyword_to_categories = {}
        
        # Mapeos de sinónimos y variaciones
        keyword_mappings = {
            # Lentes y gafas
            'lentes': ['lentes', 'gafas', 'anteojos', 'lentes de sol', 'gafas de sol'],
            'polarizados': ['polarizados', 'polarizado', 'anti reflejante'],
            'uv': ['uv', 'uv400', 'protección solar', 'proteccion solar'],
            
            # Joyas y accesorios
            'anillos': ['anillos', 'sortijas', 'sortija', 'anillo'],
            'aros': ['aros', 'pendientes', 'aretes'],
            'collares': ['collares', 'collar', 'cadenas', 'cadena'],
            'pulseras': ['pulseras', 'pulsera', 'brazaletes', 'brazalete'],
            
            # Materiales
            'plata': ['plata', 'plata 925', '925', 'silver'],
            'acero': ['acero', 'acero quirúrgico', 'quirurgico', 'steel'],
            'oro': ['oro', 'dorado', 'gold'],
            
            # Ropa y accesorios
            'relojes': ['relojes', 'reloj'],
            'casio': ['casio'],
            'ropa': ['ropa', 'indumentaria', 'vestimenta'],
            'remeras': ['remeras', 'remera', 'camisetas', 'camiseta'],
            'pantalones': ['pantalones', 'pantalón', 'jeans'],
            
            # Maquillaje
            'maquillaje': ['maquillaje', 'makeup', 'cosmeticos', 'cosméticos'],
            'labial': ['labial', 'labiales', 'lipstick'],
            'base': ['base', 'base de maquillaje', 'foundation'],
            'sombras': ['sombras', 'sombra', 'eyeshadow'],
            
            # Bijouterie
            'bijou': ['bijou', 'bijouterie', 'bijoutería', 'accesorios']
        }
        
        # Crear mapeo inverso
        for main_keyword, variants in keyword_mappings.items():
            for variant in variants:
                variant_clean = self._normalize_text(variant)
                if variant_clean not in self.keyword_to_categories:
                    self.keyword_to_categories[variant_clean] = []
        
        # Mapear cada categoría a sus keywords
        for category in self.categories:
            category_keywords = self._extract_keywords_from_category(category)
            category.keywords = category_keywords
            
            # Agregar a mapeo inverso
            for keyword in category_keywords:
                keyword_clean = self._normalize_text(keyword)
                if keyword_clean not in self.keyword_to_categories:
                    self.keyword_to_categories[keyword_clean] = []
                self.keyword_to_categories[keyword_clean].append(category)
        
        logger.info(f"✅ Keyword mapping creado: {len(self.keyword_to_categories)} keywords mapeadas")
    
    def _extract_keywords_from_category(self, category: Category) -> Set[str]:
        """Extraer keywords de una categoría"""
        keywords = set()
        
        # Keywords del nombre
        name_words = re.findall(r'\w+', category.name.lower())
        keywords.update(name_words)
        
        # Keywords del slug  
        slug_words = category.slug.replace('-', ' ').split()
        keywords.update(slug_words)
        
        # Remover palabras muy cortas o comunes
        stop_words = {'de', 'la', 'el', 'y', 'con', 'para', 'cm', 'amp'}
        keywords = {kw for kw in keywords if len(kw) >= 3 and kw not in stop_words}
        
        return keywords
    
    def _normalize_text(self, text: str) -> str:
        """Normalizar texto para búsqueda"""
        # Remover acentos
        text = unicodedata.normalize('NFD', text)
        text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
        
        # Lowercase y limpiar
        text = text.lower().strip()
        
        # Remover caracteres especiales
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def find_categories(self, query: str, max_results: int = None) -> List[CategoryMatch]:
        """
        Buscar categorías relevantes para una consulta de usuario.
        
        Args:
            query: Consulta del usuario (ej: "tienen lentes de sol")
            max_results: Máximo número de resultados
            
        Returns:
            Lista de CategoryMatch ordenada por relevancia
        """
        if not query.strip():
            return []
        
        max_results = max_results or self.max_results
        query_normalized = self._normalize_text(query)
        query_words = query_normalized.split()
        
        matches = []
        
        # 1. Búsqueda por keywords exactas
        for word in query_words:
            if word in self.keyword_to_categories:
                for category in self.keyword_to_categories[word]:
                    match = CategoryMatch(
                        category=category,
                        relevance_score=1.0,
                        matched_keywords=[word],
                        match_type='exact'
                    )
                    matches.append(match)
        
        # 2. Búsqueda parcial en nombres
        for category in self.categories:
            name_normalized = self._normalize_text(category.name)
            
            # Coincidencia completa en nombre
            if query_normalized in name_normalized:
                match = CategoryMatch(
                    category=category,
                    relevance_score=0.9,
                    matched_keywords=[query_normalized],
                    match_type='partial'
                )
                if not self._already_matched(matches, category):
                    matches.append(match)
            
            # Coincidencia de palabras individuales
            matched_words = []
            for word in query_words:
                if len(word) >= 3 and word in name_normalized:
                    matched_words.append(word)
            
            if matched_words:
                score = len(matched_words) / len(query_words) * 0.7
                if score >= self.min_relevance_score:
                    match = CategoryMatch(
                        category=category,
                        relevance_score=score,
                        matched_keywords=matched_words,
                        match_type='keyword'
                    )
                    if not self._already_matched(matches, category):
                        matches.append(match)
        
        # 3. Búsqueda fuzzy en categorías con nombres similares
        for category in self.categories:
            name_normalized = self._normalize_text(category.name)
            
            # Solo para nombres no muy largos
            if len(name_normalized.split()) <= 4:
                similarity = SequenceMatcher(None, query_normalized, name_normalized).ratio()
                
                if similarity >= 0.6 and similarity < 0.9:  # Evitar duplicados exactos
                    match = CategoryMatch(
                        category=category,
                        relevance_score=similarity * 0.5,
                        matched_keywords=[],
                        match_type='fuzzy'
                    )
                    if not self._already_matched(matches, category):
                        matches.append(match)
        
        # Ordenar por relevancia y remover duplicados
        matches = self._deduplicate_matches(matches)
        matches.sort(key=lambda m: m.relevance_score, reverse=True)
        
        # Filtrar por score mínimo y limitar resultados
        filtered_matches = [m for m in matches if m.relevance_score >= self.min_relevance_score]
        
        logger.info(f"🔍 Búsqueda '{query}': {len(filtered_matches)} coincidencias encontradas")
        
        return filtered_matches[:max_results]
    
    def _already_matched(self, matches: List[CategoryMatch], category: Category) -> bool:
        """Verificar si una categoría ya está en los resultados"""
        return any(match.category.url == category.url for match in matches)
    
    def _deduplicate_matches(self, matches: List[CategoryMatch]) -> List[CategoryMatch]:
        """Remover duplicados manteniendo el mejor score"""
        seen_urls = {}
        
        for match in matches:
            url = match.category.url
            if url not in seen_urls or match.relevance_score > seen_urls[url].relevance_score:
                seen_urls[url] = match
        
        return list(seen_urls.values())
    
    def find_categories_by_keywords(self, keywords: List[str]) -> List[CategoryMatch]:
        """Buscar categorías usando lista específica de keywords"""
        matches = []
        
        for keyword in keywords:
            keyword_clean = self._normalize_text(keyword)
            if keyword_clean in self.keyword_to_categories:
                for category in self.keyword_to_categories[keyword_clean]:
                    match = CategoryMatch(
                        category=category,
                        relevance_score=1.0,
                        matched_keywords=[keyword],
                        match_type='exact'
                    )
                    if not self._already_matched(matches, category):
                        matches.append(match)
        
        return matches
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del matcher"""
        return {
            'total_categories': len(self.categories),
            'total_keywords': len(self.keyword_to_categories),
            'unique_domains': len(set(cat.url.split('/')[2] for cat in self.categories if cat.url)),
            'config': {
                'min_relevance_score': self.min_relevance_score,
                'max_results': self.max_results,
                'json_path': self.json_path
            }
        }

# =====================================================
# INSTANCIA GLOBAL
# =====================================================

# Instancia global del matcher
category_matcher = None

def get_category_matcher() -> CategoryMatcher:
    """Obtener instancia global del CategoryMatcher"""
    global category_matcher
    
    if category_matcher is None:
        category_matcher = CategoryMatcher()
    
    return category_matcher

# Funciones de conveniencia
def find_categories(query: str, max_results: int = None) -> List[CategoryMatch]:
    """Función de conveniencia para buscar categorías"""
    matcher = get_category_matcher()
    return matcher.find_categories(query, max_results)

def search_categories_by_keywords(keywords: List[str]) -> List[CategoryMatch]:
    """Función de conveniencia para buscar por keywords específicas"""
    matcher = get_category_matcher()
    return matcher.find_categories_by_keywords(keywords)

def format_categories_for_user(matches: List[CategoryMatch], max_display: int = 5) -> str:
    """Formatear categorías para mostrar al usuario"""
    if not matches:
        return "No encontré categorías específicas para tu consulta."
    
    result_parts = []
    
    if len(matches) == 1:
        match = matches[0]
        result_parts.append(f"✅ **Encontré esta categoría:**")
        result_parts.append(f"🔗 **{match.category.name}**")
        result_parts.append(f"   👉 {match.category.url}")
    else:
        result_parts.append(f"✅ **Encontré {len(matches[:max_display])} categorías relacionadas:**")
        
        for i, match in enumerate(matches[:max_display], 1):
            result_parts.append(f"{i}. 🔗 **{match.category.name}**")
            result_parts.append(f"   👉 {match.category.url}")
        
        if len(matches) > max_display:
            result_parts.append(f"\n💡 Y {len(matches) - max_display} categorías más disponibles...")
    
    result_parts.append(f"\n🛒 **¿Te interesa alguna de estas categorías?** Puedo ayudarte a encontrar productos específicos.")
    
    return "\n".join(result_parts)

# =====================================================
# FUNCIONES DE UTILIDAD
# =====================================================

def extract_product_keywords(query: str) -> List[str]:
    """Extraer keywords de productos de una consulta de usuario"""
    
    # Patterns comunes de consulta
    patterns = [
        r'\b(tienen|hay|tenés|venden|vendés|buscó|busco)\s+(.+?)(?:\s|$)',
        r'\b(quiero|necesito|me interesa)\s+(.+?)(?:\s|$)',
        r'\b(categoría|categoria|sección|seccion).*?(\w+)',
        r'\b(\w+(?:\s+\w+)*?)(?:\s+(?:baratos?|buenos?|mejores?|disponibles?))?$'
    ]
    
    keywords = []
    query_lower = query.lower()
    
    for pattern in patterns:
        matches = re.findall(pattern, query_lower)
        for match in matches:
            if isinstance(match, tuple):
                for part in match:
                    if len(part.strip()) >= 3:
                        keywords.append(part.strip())
            else:
                if len(match.strip()) >= 3:
                    keywords.append(match.strip())
    
    # Si no encontramos patterns, usar palabras significativas
    if not keywords:
        words = re.findall(r'\w+', query_lower)
        stop_words = {'tienen', 'hay', 'venden', 'quiero', 'necesito', 'me', 'interesa', 'de', 'la', 'el', 'y', 'con'}
        keywords = [word for word in words if len(word) >= 3 and word not in stop_words]
    
    return keywords[:5]  # Máximo 5 keywords

if __name__ == "__main__":
    # Test del sistema
    import asyncio
    
    async def test_category_matcher():
        print("🧪 Testing CategoryMatcher...")
        
        matcher = get_category_matcher()
        
        test_queries = [
            "tienen lentes de sol",
            "anillos de plata",
            "relojes casio", 
            "maquillaje labial",
            "cadenas de oro",
            "ropa de mujer",
            "bijouterie"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Consulta: '{query}'")
            matches = find_categories(query, max_results=3)
            
            if matches:
                for match in matches:
                    print(f"  ✅ {match.category.name} (score: {match.relevance_score:.2f}) - {match.match_type}")
                    print(f"      {match.category.url}")
            else:
                print("  ❌ Sin coincidencias")
        
        # Test de formateo
        print(f"\n📝 Ejemplo de respuesta formateada:")
        matches = find_categories("lentes de sol", max_results=3)
        formatted = format_categories_for_user(matches)
        print(formatted)
        
        # Estadísticas
        stats = matcher.get_stats()
        print(f"\n📊 Estadísticas:")
        print(f"  Categorías: {stats['total_categories']}")
        print(f"  Keywords: {stats['total_keywords']}")
    
    asyncio.run(test_category_matcher())