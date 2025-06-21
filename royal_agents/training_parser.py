# Training Parser para Royal Bot v2
# Procesa los archivos de entrenamiento y extrae información estructurada

import os
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ConversationExample:
    """Estructura para ejemplos de conversación"""
    scenario: str
    user_message: str
    royalia_response: str
    context: str = ""

@dataclass
class TrainingRule:
    """Estructura para reglas de entrenamiento"""
    category: str
    rule_type: str  # "CRITICO", "IMPORTANTE", "ESPECIFICO"
    description: str
    when_to_apply: str = ""

@dataclass
class FAQ:
    """Estructura para preguntas frecuentes"""
    question: str
    answer: str
    category: str = ""

class TrainingContentParser:
    """Parser para procesar archivos de entrenamiento de Royal"""
    
    def __init__(self):
        self.combo_training = self._parse_combo_training()
        self.product_training = self._parse_product_training()
        self.conversation_examples = self._extract_conversation_examples()
        self.training_rules = self._extract_training_rules()
        self.faqs = self._extract_faqs()
        
        logger.info(f"✅ Training Parser inicializado:")
        logger.info(f"   - {len(self.conversation_examples)} ejemplos de conversación")
        logger.info(f"   - {len(self.training_rules)} reglas de entrenamiento")
        logger.info(f"   - {len(self.faqs)} FAQs procesadas")
        
    def _parse_combo_training(self) -> Dict[str, Any]:
        """Parsea el archivo de entrenamiento de combos"""
        try:
            # Intentar diferentes encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            content = ""
            
            for encoding in encodings:
                try:
                    with open('Entrenamiento/Entrenamiento-Combos.txt', 'r', encoding=encoding) as f:
                        content = f.read()
                    logger.info(f"✅ Archivo de combos leído con encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            
            if not content:
                logger.error("❌ No se pudo leer el archivo con ningún encoding")
                return {}
            
            # Extraer secciones principales
            sections = self._extract_sections(content)
            
            return {
                'raw_content': content,
                'sections': sections,
                'combos_info': self._extract_combos_info(content),
                'benefits': self._extract_benefits(content),
                'links': self._extract_links(content)
            }
        except FileNotFoundError:
            logger.error("❌ Archivo Entrenamiento-Combos.txt no encontrado")
            return {}
        except Exception as e:
            logger.error(f"❌ Error parseando combos training: {str(e)}")
            return {}
    
    def _parse_product_training(self) -> Dict[str, Any]:
        """Parsea el archivo de entrenamiento de productos"""
        try:
            # Intentar diferentes encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            content = ""
            
            for encoding in encodings:
                try:
                    with open('Entrenamiento/Entrenamiento-Productos.txt', 'r', encoding=encoding) as f:
                        content = f.read()
                    logger.info(f"✅ Archivo de productos leído con encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            
            if not content:
                logger.error("❌ No se pudo leer el archivo con ningún encoding")
                return {}
            
            sections = self._extract_sections(content)
            
            return {
                'raw_content': content,
                'sections': sections,
                'mentorship_focus': self._extract_mentorship_content(content),
                'product_categories': self._extract_product_categories(content),
                'important_links': self._extract_links(content)
            }
        except FileNotFoundError:
            logger.error("❌ Archivo Entrenamiento-Productos.txt no encontrado")
            return {}
        except Exception as e:
            logger.error(f"❌ Error parseando products training: {str(e)}")
            return {}
    
    def _extract_sections(self, content: str) -> Dict[str, str]:
        """Extrae secciones marcadas con ============"""
        sections = {}
        current_section = None
        current_content = []
        
        lines = content.split('\n')
        
        for line in lines:
            if '============' in line:
                # Guardar sección anterior si existe
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Nueva sección
                current_section = None
                current_content = []
            elif line.strip().startswith('SECCIÓN') and current_section is None:
                current_section = line.strip()
            elif current_section:
                current_content.append(line)
        
        # Guardar última sección
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()
            
        return sections
    
    def _extract_conversation_examples(self) -> List[ConversationExample]:
        """Extrae ejemplos de conversación de ambos archivos"""
        examples = []
        
        # De archivo de combos - secciones Y contenido completo
        if 'sections' in self.combo_training:
            for section_name, section_content in self.combo_training['sections'].items():
                if 'CONVERSACI' in section_name.upper() or 'EJEMPLO' in section_name.upper() or 'CONVERSACIÓN' in section_name.upper():
                    examples.extend(self._parse_conversation_section(section_content, 'combos'))
        
        # También buscar en contenido completo de combos
        if 'raw_content' in self.combo_training:
            examples.extend(self._parse_conversation_section(self.combo_training['raw_content'], 'combos'))
        
        # De archivo de productos - secciones Y contenido completo
        if 'sections' in self.product_training:
            for section_name, section_content in self.product_training['sections'].items():
                if 'CONVERSACI' in section_name.upper() or 'EJEMPLO' in section_name.upper() or 'CONVERSACIÓN' in section_name.upper():
                    examples.extend(self._parse_conversation_section(section_content, 'productos'))
        
        # También buscar en contenido completo de productos
        if 'raw_content' in self.product_training:
            examples.extend(self._parse_conversation_section(self.product_training['raw_content'], 'productos'))
        
        # Eliminar duplicados
        unique_examples = []
        seen_messages = set()
        for example in examples:
            if example.user_message not in seen_messages:
                unique_examples.append(example)
                seen_messages.add(example.user_message)
        
        return unique_examples
    
    def _parse_conversation_section(self, content: str, source: str) -> List[ConversationExample]:
        """Parsea una sección de conversaciones"""
        examples = []
        
        # Buscar patrones de conversación - versión mejorada
        conversation_blocks = re.split(r'CONVERSACI[ÓO]N EJEMPLO \d+:', content, flags=re.IGNORECASE)
        
        for i, block in enumerate(conversation_blocks[1:], 1):  # Saltar el primer elemento vacío
            lines = block.strip().split('\n')
            user_msg = ""
            royalia_response = ""
            current_speaker = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('Usuario:'):
                    current_speaker = 'usuario'
                    user_msg = line.replace('Usuario:', '').strip()
                elif line.startswith('Royalia:') or line.startswith('Royalía:') or line.startswith('Royal'):
                    current_speaker = 'royalia'
                    # Limpiar múltiples variaciones del nombre
                    clean_line = line.replace('Royalia:', '').replace('Royalía:', '').replace('Royal:', '').strip()
                    royalia_response = clean_line
                elif current_speaker == 'royalia' and line and not line.startswith('Usuario:') and not line.startswith('CONVERSACI'):
                    # Continuar respuesta de Royalia
                    royalia_response += " " + line
            
            if user_msg and royalia_response:
                examples.append(ConversationExample(
                    scenario=f"{source}_ejemplo_{i}",
                    user_message=user_msg,
                    royalia_response=royalia_response,
                    context=source
                ))
        
        return examples
    
    def _extract_training_rules(self) -> List[TrainingRule]:
        """Extrae reglas de entrenamiento de ambos archivos"""
        rules = []
        
        # Combos training rules
        if 'sections' in self.combo_training:
            for section_name, section_content in self.combo_training['sections'].items():
                if 'REGLAS' in section_name.upper() or 'INSTRUCCIONES' in section_name.upper():
                    rules.extend(self._parse_rules_section(section_content, 'combos'))
        
        # Products training rules
        if 'sections' in self.product_training:
            for section_name, section_content in self.product_training['sections'].items():
                if 'REGLAS' in section_name.upper() or 'INSTRUCCIONES' in section_name.upper():
                    rules.extend(self._parse_rules_section(section_content, 'productos'))
        
        return rules
    
    def _parse_rules_section(self, content: str, source: str) -> List[TrainingRule]:
        """Parsea una sección de reglas"""
        rules = []
        lines = content.split('\n')
        
        current_rule_type = "GENERAL"
        
        for line in lines:
            line = line.strip()
            
            # Detectar tipo de regla
            if 'CRÍTICO' in line.upper() or 'CRITICO' in line.upper():
                current_rule_type = "CRITICO"
                if ':' in line:
                    rule_text = line.split(':', 1)[1].strip()
                    if rule_text:
                        rules.append(TrainingRule(
                            category=source,
                            rule_type=current_rule_type,
                            description=rule_text
                        ))
            elif 'IMPORTANTE' in line.upper():
                current_rule_type = "IMPORTANTE"
            elif 'ESPECÍFIC' in line.upper() or 'ESPECIFIC' in line.upper():
                current_rule_type = "ESPECIFICO"
            elif line.startswith('?') or line.startswith('•'):
                # Regla específica
                rule_text = line[1:].strip()
                if rule_text:
                    rules.append(TrainingRule(
                        category=source,
                        rule_type=current_rule_type,
                        description=rule_text
                    ))
            elif 'DEBE' in line or 'NUNCA' in line or 'SIEMPRE' in line:
                rules.append(TrainingRule(
                    category=source,
                    rule_type=current_rule_type,
                    description=line
                ))
        
        return rules
    
    def _extract_faqs(self) -> List[FAQ]:
        """Extrae preguntas frecuentes de ambos archivos"""
        faqs = []
        
        # De combos - buscar en secciones Y en contenido completo
        if 'sections' in self.combo_training:
            for section_name, section_content in self.combo_training['sections'].items():
                if 'PREGUNTA' in section_name.upper() or 'FAQ' in section_name.upper() or 'FRECUENTE' in section_name.upper():
                    faqs.extend(self._parse_faq_section(section_content, 'combos'))
        
        # También buscar en contenido completo de combos
        if 'raw_content' in self.combo_training:
            faqs.extend(self._parse_faq_section(self.combo_training['raw_content'], 'combos'))
        
        # De productos - buscar en secciones Y en contenido completo
        if 'sections' in self.product_training:
            for section_name, section_content in self.product_training['sections'].items():
                if 'PREGUNTA' in section_name.upper() or 'FAQ' in section_name.upper() or 'FRECUENTE' in section_name.upper():
                    faqs.extend(self._parse_faq_section(section_content, 'productos'))
        
        # También buscar en contenido completo de productos
        if 'raw_content' in self.product_training:
            faqs.extend(self._parse_faq_section(self.product_training['raw_content'], 'productos'))
        
        # Eliminar duplicados
        unique_faqs = []
        seen_questions = set()
        for faq in faqs:
            if faq.question not in seen_questions:
                unique_faqs.append(faq)
                seen_questions.add(faq.question)
        
        return unique_faqs
    
    def _parse_faq_section(self, content: str, source: str) -> List[FAQ]:
        """Parsea una sección de FAQs"""
        faqs = []
        lines = content.split('\n')
        
        current_question = ""
        current_answer = ""
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('P:'):
                # Nueva pregunta - guardar la anterior si existe
                if current_question and current_answer:
                    faqs.append(FAQ(
                        question=current_question,
                        answer=current_answer,
                        category=source
                    ))
                
                current_question = line[2:].strip()
                current_answer = ""
                
            elif line.startswith('R:'):
                current_answer = line[2:].strip()
            elif current_answer and line and not line.startswith('P:'):
                # Continuar respuesta
                current_answer += " " + line
        
        # Guardar última FAQ
        if current_question and current_answer:
            faqs.append(FAQ(
                question=current_question,
                answer=current_answer,
                category=source
            ))
        
        return faqs
    
    def _extract_combos_info(self, content: str) -> Dict[str, Any]:
        """Extrae información específica de combos"""
        combos_info = {
            'types': [],
            'benefits': [],
            'when_to_offer': []
        }
        
        # Buscar información de tipos de combos
        if 'bijou' in content.lower():
            combos_info['types'].append('bijou')
        if 'indumentaria' in content.lower():
            combos_info['types'].append('indumentaria')
        if 'makeup' in content.lower():
            combos_info['types'].append('makeup')
        if 'joyas' in content.lower():
            combos_info['types'].append('joyas')
        if 'acero' in content.lower():
            combos_info['types'].append('acero')
        if 'plata' in content.lower():
            combos_info['types'].append('plata')
        
        return combos_info
    
    def _extract_benefits(self, content: str) -> List[str]:
        """Extrae beneficios mencionados en el contenido"""
        benefits = []
        
        # Buscar sección de beneficios
        benefit_patterns = [
            r'BENEFICIOS[^:]*:(.*?)(?=\n\n|\n[A-Z]|$)',
            r'QU[ÉE] SON LOS COMBOS[^:]*:(.*?)(?=\n\n|\n[A-Z]|$)',
            r'VENTAJAS[^:]*:(.*?)(?=\n\n|\n[A-Z]|$)'
        ]
        
        for pattern in benefit_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                lines = match.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('?') or line.startswith('•') or line.startswith('-'):
                        benefits.append(line[1:].strip())
        
        return benefits
    
    def _extract_links(self, content: str) -> List[str]:
        """Extrae enlaces del contenido"""
        # Buscar URLs
        url_pattern = r'https?://[^\s<>"\'{}|\\^`\[\]]+[^\s<>"\'{}|\\^`\[\].,!?:;]'
        links = re.findall(url_pattern, content)
        return list(set(links))  # Eliminar duplicados
    
    def _extract_mentorship_content(self, content: str) -> Dict[str, Any]:
        """Extrae contenido específico de mentoría"""
        return {
            'personality_traits': self._extract_personality_traits(content),
            'forbidden_words': self._extract_forbidden_words(content),
            'approach': self._extract_mentorship_approach(content)
        }
    
    def _extract_personality_traits(self, content: str) -> List[str]:
        """Extrae rasgos de personalidad de Royalía"""
        traits = []
        
        # Buscar sección de personalidad
        if 'personalidad' in content.lower():
            lines = content.split('\n')
            in_personality_section = False
            
            for line in lines:
                line = line.strip()
                if 'personalidad' in line.lower():
                    in_personality_section = True
                elif line.startswith('##') or line.startswith('==='):
                    in_personality_section = False
                elif in_personality_section and (line.startswith('?') or line.startswith('-')):
                    traits.append(line[1:].strip())
        
        return traits
    
    def _extract_forbidden_words(self, content: str) -> List[str]:
        """Extrae palabras prohibidas"""
        forbidden = []
        
        if 'PALABRAS PROHIBIDAS' in content:
            # Buscar la sección de palabras prohibidas
            start = content.find('PALABRAS PROHIBIDAS')
            end = content.find('\n\n', start)
            if end == -1:
                end = content.find('\n#', start)
            
            if start != -1:
                section = content[start:end] if end != -1 else content[start:]
                # Extraer palabras separadas por comas
                words_line = section.split('\n')[1] if '\n' in section else section
                forbidden = [word.strip() for word in words_line.split(',')]
        
        return forbidden
    
    def _extract_mentorship_approach(self, content: str) -> List[str]:
        """Extrae enfoque de mentoría"""
        approaches = []
        
        # Buscar menciones de mentoría y acompañamiento
        mentorship_keywords = ['mentora', 'acompaño', 'asesoramiento', 'ayudo']
        
        lines = content.split('\n')
        for line in lines:
            for keyword in mentorship_keywords:
                if keyword in line.lower() and len(line.strip()) > 20:
                    approaches.append(line.strip())
                    break
        
        return list(set(approaches))  # Eliminar duplicados
    
    def _extract_product_categories(self, content: str) -> Dict[str, str]:
        """Extrae categorías de productos y sus descripciones"""
        categories = {}
        
        # Buscar sección de categorías
        if 'Resumen de categorías' in content:
            lines = content.split('\n')
            current_category = None
            current_description = []
            
            in_categories_section = False
            for line in lines:
                line = line.strip()
                
                if 'Resumen de categorías' in line:
                    in_categories_section = True
                    continue
                elif line.startswith('Ejemplos de conversación'):
                    in_categories_section = False
                    break
                
                if in_categories_section:
                    # Detectar nueva categoría (línea que no empieza con espacio y tiene contenido)
                    if line and not line.startswith(' ') and not line.startswith('?') and not line.startswith('-'):
                        # Guardar categoría anterior
                        if current_category and current_description:
                            categories[current_category] = ' '.join(current_description)
                        
                        current_category = line
                        current_description = []
                    elif current_category and line:
                        current_description.append(line)
            
            # Guardar última categoría
            if current_category and current_description:
                categories[current_category] = ' '.join(current_description)
        
        return categories
    
    # Métodos públicos para acceder a la información procesada
    
    def get_conversation_example_by_scenario(self, scenario: str) -> Optional[ConversationExample]:
        """Obtiene ejemplo de conversación por escenario"""
        scenarios_map = {
            'cliente_indeciso': 'empezando',
            'cliente_experimentado': 'experimentado',
            'dudas_confiabilidad': 'confiable',
            'pregunta_catalogo': 'catalogo',
            'pregunta_minimo': 'minimo',
            'pregunta_envio': 'envio'
        }
        
        search_term = scenarios_map.get(scenario, scenario)
        
        for example in self.conversation_examples:
            if search_term.lower() in example.user_message.lower() or search_term.lower() in example.royalia_response.lower():
                return example
        
        return None
    
    def get_rules_by_category(self, category: str) -> List[TrainingRule]:
        """Obtiene reglas por categoría"""
        return [rule for rule in self.training_rules if rule.category == category]
    
    def get_critical_rules(self) -> List[TrainingRule]:
        """Obtiene todas las reglas críticas"""
        return [rule for rule in self.training_rules if rule.rule_type == "CRITICO"]
    
    def get_faq_by_topic(self, topic: str) -> Optional[FAQ]:
        """Obtiene FAQ por tema"""
        topic_lower = topic.lower()
        
        for faq in self.faqs:
            if topic_lower in faq.question.lower() or topic_lower in faq.answer.lower():
                return faq
        
        return None
    
    def get_combo_benefits(self) -> List[str]:
        """Obtiene beneficios de los combos"""
        if 'benefits' in self.combo_training:
            return self.combo_training['benefits']
        return []
    
    def get_combo_types(self) -> List[str]:
        """Obtiene tipos de combos disponibles"""
        if 'combos_info' in self.combo_training:
            return self.combo_training['combos_info'].get('types', [])
        return []
    
    def get_product_categories_info(self) -> Dict[str, str]:
        """Obtiene información de categorías de productos"""
        if 'product_categories' in self.product_training:
            return self.product_training['product_categories']
        return {}
    
    def get_mentorship_personality(self) -> Dict[str, Any]:
        """Obtiene información de personalidad de mentoría"""
        if 'mentorship_focus' in self.product_training:
            return self.product_training['mentorship_focus']
        return {}
    
    def search_training_content(self, query: str) -> Dict[str, List]:
        """Busca contenido en todo el entrenamiento"""
        query_lower = query.lower()
        results = {
            'examples': [],
            'rules': [],
            'faqs': [],
            'links': []
        }
        
        # Buscar en ejemplos
        for example in self.conversation_examples:
            if (query_lower in example.user_message.lower() or 
                query_lower in example.royalia_response.lower()):
                results['examples'].append(example)
        
        # Buscar en reglas
        for rule in self.training_rules:
            if query_lower in rule.description.lower():
                results['rules'].append(rule)
        
        # Buscar en FAQs
        for faq in self.faqs:
            if (query_lower in faq.question.lower() or 
                query_lower in faq.answer.lower()):
                results['faqs'].append(faq)
        
        # Buscar en enlaces (both combo and product training)
        all_links = []
        if 'links' in self.combo_training:
            all_links.extend(self.combo_training['links'])
        if 'links' in self.product_training:
            all_links.extend(self.product_training['links'])
        
        for link in all_links:
            if query_lower in link.lower():
                results['links'].append(link)
        
        return results

# Instancia global del parser
training_parser = TrainingContentParser() 