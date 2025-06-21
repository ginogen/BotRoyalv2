#!/usr/bin/env python3
"""
🗄️ CONFIGURACIÓN DE BASE DE DATOS PERSISTENTE
Configuración para PostgreSQL y SQLite con fallback automático
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime
import logging
import pandas as pd

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manager unificado para SQLite y PostgreSQL"""
    
    def __init__(self):
        self.connection = None
        self.db_type = self._detect_database_type()
        self._init_database()
    
    def _detect_database_type(self):
        """Detecta automáticamente el tipo de base de datos"""
        
        logger.info("🔍 DETECTANDO TIPO DE BASE DE DATOS:")
        
        # Verificar variables de entorno
        database_url = os.getenv('DATABASE_URL')
        postgres_url = os.getenv('POSTGRES_URL')
        
        logger.info(f"   DATABASE_URL: {'✅ Configurado' if database_url else '❌ No encontrado'}")
        logger.info(f"   POSTGRES_URL: {'✅ Configurado' if postgres_url else '❌ No encontrado'}")
        
        if database_url or postgres_url:
            logger.info("✅ Usando PostgreSQL")
            return 'postgresql'
        else:
            logger.info("✅ Usando SQLite (desarrollo)")
            return 'sqlite'
    
    def _init_database(self):
        """Inicializa la base de datos según el tipo detectado"""
        
        try:
            if self.db_type == 'postgresql':
                self._init_postgresql()
            else:
                self._init_sqlite()
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")
            if self.db_type == 'postgresql':
                self._fallback_to_sqlite()
            else:
                raise
    
    def _init_postgresql(self):
        """Configuración PostgreSQL"""
        
        try:
            # Railway/Heroku usan DATABASE_URL
            db_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
            
            logger.info(f"🔧 CONFIGURANDO POSTGRESQL:")
            logger.info(f"   URL encontrada: {'✅ Sí' if db_url else '❌ No'}")
            
            if not db_url:
                logger.error("❌ No DATABASE_URL para PostgreSQL")
                self._fallback_to_sqlite()
                return
            
            # Mostrar URL de conexión (censurada)
            safe_url = db_url[:20] + "***" + db_url[-10:] if len(db_url) > 30 else "***"
            logger.info(f"   Conectando a: {safe_url}")
            
            # Conectar a PostgreSQL
            self.connection = psycopg2.connect(db_url)
            self.connection.autocommit = True
            
            logger.info("✅ Conexión a PostgreSQL establecida")
            
            # Crear tablas si no existen
            self._create_postgresql_tables()
            
            logger.info("✅ PostgreSQL configurado completamente")
            
        except Exception as e:
            logger.error(f"❌ Error PostgreSQL: {e}")
            logger.error(f"   Detalles del error: {type(e).__name__}")
            self._fallback_to_sqlite()
    
    def _init_sqlite(self):
        """Configuración SQLite (fallback)"""
        
        # En producción, usar directorio persistente si existe
        if os.getenv('RAILWAY_ENVIRONMENT'):
            db_path = '/app/data/bot_feedback.db'
            os.makedirs('/app/data', exist_ok=True)
        else:
            db_path = 'bot_feedback.db'
        
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row  # Para diccionarios
        
        self._create_sqlite_tables()
        logger.info(f"✅ SQLite conectado: {db_path}")
    
    def _fallback_to_sqlite(self):
        """Fallback a SQLite si PostgreSQL falla"""
        
        logger.warning("⚠️ Fallback a SQLite")
        self.db_type = 'sqlite'
        self._init_sqlite()
    
    def _ensure_tables_exist(self):
        """Asegura que las tablas existan antes de cualquier operación"""
        
        try:
            if self.db_type == 'postgresql':
                # Verificar si las tablas existen
                cursor = self.connection.cursor()
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'conversations'
                """)
                if not cursor.fetchone():
                    logger.info("📋 Creando tablas PostgreSQL...")
                    self._create_postgresql_tables()
                cursor.close()
            else:
                # SQLite - verificar si existe la tabla conversations
                cursor = self.connection.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
                if not cursor.fetchone():
                    logger.info("📋 Creando tablas SQLite...")
                    self._create_sqlite_tables()
                cursor.close()
                
        except Exception as e:
            logger.error(f"❌ Error verificando tablas: {e}")
            # Intentar crear las tablas de todos modos
            if self.db_type == 'postgresql':
                self._create_postgresql_tables()
            else:
                self._create_sqlite_tables()
    
    def _create_postgresql_tables(self):
        """Crear tablas en PostgreSQL"""
        
        cursor = self.connection.cursor()
        
        try:
            # Tabla de conversaciones - ESQUEMA CORRECTO
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id VARCHAR(255) NOT NULL,
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    feedback_text TEXT,
                    category VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de feedback general
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS general_feedback (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255) NOT NULL,
                    feedback_type VARCHAR(100) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    priority VARCHAR(50) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pendiente',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de métricas del bot
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_metrics (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metric_name VARCHAR(100) NOT NULL,
                    metric_value NUMERIC NOT NULL,
                    user_id VARCHAR(255),
                    session_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de feedback detallado
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255) NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    comment TEXT,
                    conversation_id UUID REFERENCES conversations(id),
                    category VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Índices para performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user_timestamp ON conversations(user_id, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_rating ON conversations(rating)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_priority ON general_feedback(priority, status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(rating)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_name ON bot_metrics(metric_name)')
            
            logger.info("✅ Tablas PostgreSQL creadas/verificadas")
            
        except Exception as e:
            logger.error(f"❌ Error creando tablas PostgreSQL: {e}")
            raise
        finally:
            cursor.close()
    
    def _create_sqlite_tables(self):
        """Crear tablas en SQLite"""
        
        cursor = self.connection.cursor()
        
        try:
            # Tabla de conversaciones
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT NOT NULL,
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    feedback_text TEXT,
                    category TEXT
                )
            ''')
            
            # Tabla de feedback general
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS general_feedback (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT DEFAULT 'pendiente',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT NOT NULL
                )
            ''')
            
            # Tabla de métricas del bot
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_metrics (
                    id TEXT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    user_id TEXT,
                    session_id TEXT
                )
            ''')
            
            # Tabla de feedback detallado
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    comment TEXT,
                    conversation_id TEXT,
                    category TEXT
                )
            ''')
            
            self.connection.commit()
            logger.info("✅ Tablas SQLite creadas/verificadas")
            
        except Exception as e:
            logger.error(f"❌ Error creando tablas SQLite: {e}")
            raise
        finally:
            cursor.close()
    
    def save_conversation(self, user_id: str, message: str, bot_response: str, session_id: str):
        """Guarda conversación (unificado para ambas DBs)"""
        
        # Asegurar que las tablas existan
        self._ensure_tables_exist()
        
        conversation_id = str(uuid.uuid4())
        
        try:
            if self.db_type == 'postgresql':
                cursor = self.connection.cursor()
                cursor.execute('''
                    INSERT INTO conversations 
                    (id, user_id, message, bot_response, session_id)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (conversation_id, user_id, message, bot_response, session_id))
                cursor.close()
                
            else:  # SQLite
                cursor = self.connection.cursor()
                cursor.execute('''
                    INSERT INTO conversations 
                    (id, user_id, message, bot_response, timestamp, session_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (conversation_id, user_id, message, bot_response, datetime.now(), session_id))
                self.connection.commit()
                cursor.close()
            
            logger.info(f"✅ Conversación guardada: {conversation_id}")
            return conversation_id
            
        except Exception as e:
            logger.error(f"❌ Error guardando conversación: {e}")
            raise
    
    def save_feedback(self, conversation_id: str, rating: int, feedback_text: str, category: str):
        """Actualiza feedback de conversación"""
        
        # Asegurar que las tablas existan
        self._ensure_tables_exist()
        
        try:
            if self.db_type == 'postgresql':
                cursor = self.connection.cursor()
                cursor.execute('''
                    UPDATE conversations 
                    SET rating = %s, feedback_text = %s, category = %s
                    WHERE id = %s
                ''', (rating, feedback_text, category, conversation_id))
                cursor.close()
                
            else:  # SQLite
                cursor = self.connection.cursor()
                cursor.execute('''
                    UPDATE conversations 
                    SET rating = ?, feedback_text = ?, category = ?
                    WHERE id = ?
                ''', (rating, feedback_text, category, conversation_id))
                self.connection.commit()
                cursor.close()
            
            logger.info(f"✅ Feedback guardado: rating={rating}, conversación={conversation_id}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando feedback: {e}")
            raise
    
    def save_general_feedback(self, user_id: str, feedback_type: str, title: str, description: str, priority: str, session_id: str):
        """Guarda feedback general"""
        
        # Asegurar que las tablas existan
        self._ensure_tables_exist()
        
        feedback_id = str(uuid.uuid4())
        
        try:
            if self.db_type == 'postgresql':
                cursor = self.connection.cursor()
                cursor.execute('''
                    INSERT INTO general_feedback 
                    (id, user_id, feedback_type, title, description, priority, session_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (feedback_id, user_id, feedback_type, title, description, priority, session_id))
                cursor.close()
                
            else:  # SQLite
                cursor = self.connection.cursor()
                cursor.execute('''
                    INSERT INTO general_feedback 
                    (id, user_id, feedback_type, title, description, priority, timestamp, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (feedback_id, user_id, feedback_type, title, description, priority, datetime.now(), session_id))
                self.connection.commit()
                cursor.close()
            
            logger.info(f"✅ Feedback general guardado: {feedback_id}")
            return feedback_id
            
        except Exception as e:
            logger.error(f"❌ Error guardando feedback general: {e}")
            raise
    
    def get_conversations_data(self):
        """Obtiene datos de conversaciones para análisis"""
        
        try:
            if self.db_type == 'postgresql':
                cursor = self.connection.cursor(cursor_factory=RealDictCursor)
                cursor.execute('SELECT * FROM conversations ORDER BY timestamp DESC')
                data = cursor.fetchall()
                cursor.close()
                
                # Convertir a DataFrame-compatible
                return [dict(row) for row in data]
                
            else:  # SQLite
                cursor = self.connection.cursor()
                cursor.execute('SELECT * FROM conversations ORDER BY timestamp DESC')
                data = cursor.fetchall()
                cursor.close()
                
                # Convertir a diccionarios
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in data]
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo conversaciones: {e}")
            return []
    
    def export_data_backup(self):
        """Exporta datos como backup"""
        
        try:
            data = self.get_conversations_data()
            if data:
                df = pd.DataFrame(data)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"backup_conversaciones_{timestamp}.csv"
                df.to_csv(filename, index=False)
                logger.info(f"✅ Backup exportado: {filename}")
                return filename
            else:
                logger.info("⚠️ No hay datos para exportar")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error exportando backup: {e}")
            return None

# Instancia global
db_manager = DatabaseManager()

# Funciones compatibles con la interfaz existente
def save_conversation(user_id: str, message: str, bot_response: str, session_id: str):
    return db_manager.save_conversation(user_id, message, bot_response, session_id)

def save_feedback(conversation_id: str, rating: int, feedback_text: str, category: str):
    return db_manager.save_feedback(conversation_id, rating, feedback_text, category)

def get_conversations_data():
    return db_manager.get_conversations_data()

def export_backup():
    return db_manager.export_data_backup() 