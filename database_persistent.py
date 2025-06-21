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

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manager unificado para SQLite y PostgreSQL"""
    
    def __init__(self):
        self.db_type = self._detect_database_type()
        self.connection = None
        self._init_database()
    
    def _detect_database_type(self):
        """Detecta qué tipo de base de datos usar"""
        
        # PostgreSQL si hay URL de conexión
        if os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL'):
            return 'postgresql'
        
        # SQLite como fallback
        return 'sqlite'
    
    def _init_database(self):
        """Inicializa la base de datos según el tipo"""
        
        if self.db_type == 'postgresql':
            self._init_postgresql()
        else:
            self._init_sqlite()
    
    def _init_postgresql(self):
        """Configuración PostgreSQL"""
        
        try:
            # Railway/Heroku usan DATABASE_URL
            db_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
            
            if not db_url:
                logger.error("❌ No DATABASE_URL para PostgreSQL")
                self._fallback_to_sqlite()
                return
            
            # Conectar a PostgreSQL
            self.connection = psycopg2.connect(db_url)
            self.connection.autocommit = True
            
            # Crear tablas si no existen
            self._create_postgresql_tables()
            
            logger.info("✅ PostgreSQL conectado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error PostgreSQL: {e}")
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
    
    def _create_postgresql_tables(self):
        """Crear tablas en PostgreSQL"""
        
        cursor = self.connection.cursor()
        
        # Tabla de conversaciones
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
        
        # Índices para performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user_timestamp ON conversations(user_id, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_rating ON conversations(rating)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_feedback_priority ON general_feedback(priority, status)')
        
        cursor.close()
    
    def _create_sqlite_tables(self):
        """Crear tablas en SQLite"""
        
        cursor = self.connection.cursor()
        
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
        
        self.connection.commit()
        cursor.close()
    
    def save_conversation(self, user_id: str, message: str, bot_response: str, session_id: str):
        """Guarda conversación (unificado para ambas DBs)"""
        
        conversation_id = str(uuid.uuid4())
        
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
        
        return conversation_id
    
    def save_feedback(self, conversation_id: str, rating: int, feedback_text: str, category: str):
        """Actualiza feedback de conversación"""
        
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
    
    def get_conversations_data(self):
        """Obtiene datos de conversaciones para análisis"""
        
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
            columns = [description[0] for description in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            
            return data
    
    def export_data_backup(self):
        """Exporta datos como backup JSON"""
        
        import json
        
        conversations = self.get_conversations_data()
        
        backup = {
            'export_date': datetime.now().isoformat(),
            'database_type': self.db_type,
            'conversations_count': len(conversations),
            'conversations': conversations
        }
        
        filename = f"backup_feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(backup, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"📁 Backup exportado: {filename}")
        return filename

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