#!/usr/bin/env python3
"""
🚀 MIGRATION AND DEPLOYMENT SCRIPT
Handles migration from old system to optimized system for Railway
"""

import os
import sys
import json
import logging
import asyncio
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
import time

# Database imports
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MigrationManager:
    """Manages migration from old Royal Bot to optimized version"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.redis_url = os.getenv('REDIS_URL')
        self.environment = os.getenv('RAILWAY_ENVIRONMENT', 'development')
        
        self.pg_pool = None
        self.migration_log = []
        
    async def initialize(self):
        """Initialize database connection"""
        if not self.database_url:
            logger.error("❌ DATABASE_URL not found")
            return False
        
        try:
            self.pg_pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=5,
                dsn=self.database_url
            )
            
            # Test connection
            conn = self.pg_pool.getconn()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                logger.info(f"✅ Connected to PostgreSQL: {version.split(',')[0]}")
            finally:
                self.pg_pool.putconn(conn)
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def log_migration_step(self, step: str, status: str, details: str = ""):
        """Log migration step"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'step': step,
            'status': status,
            'details': details
        }
        self.migration_log.append(entry)
        
        status_emoji = "✅" if status == "success" else "❌" if status == "error" else "⚠️"
        logger.info(f"{status_emoji} {step}: {status} {details}")
    
    async def check_existing_schema(self) -> Dict[str, bool]:
        """Check what tables already exist"""
        if not self.pg_pool:
            return {}
        
        existing_tables = {}
        required_tables = [
            'conversation_contexts',
            'message_queue', 
            'system_metrics',
            'user_interactions',
            'rate_limits',
            'query_cache'
        ]
        
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            
            for table in required_tables:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = %s
                    )
                """, (table,))
                
                exists = cursor.fetchone()[0]
                existing_tables[table] = exists
            
        except Exception as e:
            logger.error(f"❌ Error checking existing schema: {e}")
        finally:
            if conn:
                self.pg_pool.putconn(conn)
        
        return existing_tables
    
    async def backup_existing_data(self) -> bool:
        """Backup existing data before migration"""
        logger.info("💾 Starting data backup...")
        
        try:
            # Check if old tables exist
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            
            # Check for old conversation_contexts table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'conversation_contexts'
                )
            """)
            
            if cursor.fetchone()[0]:
                # Backup existing conversation contexts
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_table = f"conversation_contexts_backup_{timestamp}"
                
                cursor.execute(f"""
                    CREATE TABLE {backup_table} AS 
                    SELECT * FROM conversation_contexts
                """)
                
                cursor.execute(f"SELECT COUNT(*) FROM {backup_table}")
                count = cursor.fetchone()[0]
                
                conn.commit()
                self.log_migration_step("backup_data", "success", f"Backed up {count} context records")
            else:
                self.log_migration_step("backup_data", "info", "No existing data to backup")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            self.log_migration_step("backup_data", "error", str(e))
            return False
        finally:
            if conn:
                self.pg_pool.putconn(conn)
    
    async def apply_schema(self) -> bool:
        """Apply the new optimized schema"""
        logger.info("📋 Applying new schema...")
        
        try:
            # Read schema file
            schema_path = os.path.join(os.path.dirname(__file__), 'database_schema.sql')
            if not os.path.exists(schema_path):
                self.log_migration_step("apply_schema", "error", "Schema file not found")
                return False
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # Apply schema
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            
            # Execute schema (it's designed to be idempotent)
            cursor.execute(schema_sql)
            conn.commit()
            
            # Verify tables were created
            existing_tables = await self.check_existing_schema()
            missing_tables = [table for table, exists in existing_tables.items() if not exists]
            
            if missing_tables:
                self.log_migration_step("apply_schema", "error", f"Missing tables: {missing_tables}")
                return False
            else:
                self.log_migration_step("apply_schema", "success", "All tables created successfully")
                return True
            
        except Exception as e:
            logger.error(f"❌ Schema application failed: {e}")
            self.log_migration_step("apply_schema", "error", str(e))
            return False
        finally:
            if conn:
                self.pg_pool.putconn(conn)
    
    async def migrate_existing_data(self) -> bool:
        """Migrate data from old format to new format"""
        logger.info("🔄 Migrating existing data...")
        
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Look for backup tables to migrate from
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'conversation_contexts_backup_%'
                ORDER BY table_name DESC
                LIMIT 1
            """)
            
            backup_table = cursor.fetchone()
            if not backup_table:
                self.log_migration_step("migrate_data", "info", "No backup data to migrate")
                return True
            
            backup_table_name = backup_table['table_name']
            logger.info(f"🔄 Migrating from {backup_table_name}")
            
            # Get old data
            cursor.execute(f"SELECT * FROM {backup_table_name}")
            old_records = cursor.fetchall()
            
            migrated_count = 0
            
            for record in old_records:
                try:
                    # Transform old record to new format
                    new_record = self._transform_context_record(dict(record))
                    
                    # Insert into new table
                    cursor.execute("""
                        INSERT INTO conversation_contexts (
                            user_id, context_data, user_profile, preferences,
                            current_state, user_intent, is_entrepreneur, experience_level,
                            recent_products, product_interests, budget_range,
                            conversation_started, last_interaction
                        ) VALUES (
                            %(user_id)s, %(context_data)s, %(user_profile)s, %(preferences)s,
                            %(current_state)s, %(user_intent)s, %(is_entrepreneur)s, %(experience_level)s,
                            %(recent_products)s, %(product_interests)s, %(budget_range)s,
                            %(conversation_started)s, %(last_interaction)s
                        ) ON CONFLICT (user_id) DO NOTHING
                    """, new_record)
                    
                    migrated_count += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to migrate record {record.get('user_id', 'unknown')}: {e}")
            
            conn.commit()
            self.log_migration_step("migrate_data", "success", f"Migrated {migrated_count} records")
            return True
            
        except Exception as e:
            logger.error(f"❌ Data migration failed: {e}")
            self.log_migration_step("migrate_data", "error", str(e))
            return False
        finally:
            if conn:
                self.pg_pool.putconn(conn)
    
    def _transform_context_record(self, old_record: Dict) -> Dict:
        """Transform old context record to new format"""
        
        # Default values for new schema
        transformed = {
            'user_id': old_record.get('user_id', ''),
            'context_data': old_record.get('context_data', {}) if isinstance(old_record.get('context_data'), dict) else {},
            'user_profile': old_record.get('user_profile', {}) if isinstance(old_record.get('user_profile'), dict) else {},
            'preferences': old_record.get('preferences', {}) if isinstance(old_record.get('preferences'), dict) else {},
            'current_state': old_record.get('current_state', 'browsing'),
            'user_intent': old_record.get('user_intent', ''),
            'is_entrepreneur': old_record.get('is_entrepreneur', False),
            'experience_level': old_record.get('experience_level', ''),
            'recent_products': json.dumps(old_record.get('recent_products', [])),
            'product_interests': old_record.get('product_interests', []) or [],
            'budget_range': old_record.get('budget_range'),
            'conversation_started': old_record.get('conversation_started', old_record.get('created_at', datetime.now())),
            'last_interaction': old_record.get('last_interaction', old_record.get('updated_at', datetime.now()))
        }
        
        return transformed
    
    async def verify_migration(self) -> bool:
        """Verify the migration was successful"""
        logger.info("🔍 Verifying migration...")
        
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            
            # Check all required tables exist and have expected structure
            tables_to_check = {
                'conversation_contexts': ['user_id', 'context_data', 'last_interaction'],
                'message_queue': ['queue_id', 'user_id', 'message_content', 'status'],
                'system_metrics': ['metric_type', 'metric_value', 'recorded_at'],
                'user_interactions': ['user_id', 'message', 'created_at'],
                'rate_limits': ['identifier_type', 'max_requests', 'window_size'],
                'query_cache': ['cache_key', 'cache_data', 'expires_at']
            }
            
            for table, required_columns in tables_to_check.items():
                # Check table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = %s
                    )
                """, (table,))
                
                if not cursor.fetchone()[0]:
                    self.log_migration_step("verify_migration", "error", f"Table {table} missing")
                    return False
                
                # Check required columns exist
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = %s
                """, (table,))
                
                existing_columns = [row[0] for row in cursor.fetchall()]
                missing_columns = set(required_columns) - set(existing_columns)
                
                if missing_columns:
                    self.log_migration_step("verify_migration", "error", 
                                          f"Table {table} missing columns: {missing_columns}")
                    return False
            
            # Check data integrity
            cursor.execute("SELECT COUNT(*) FROM conversation_contexts")
            context_count = cursor.fetchone()[0]
            
            self.log_migration_step("verify_migration", "success", 
                                  f"All tables verified. {context_count} context records ready.")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration verification failed: {e}")
            self.log_migration_step("verify_migration", "error", str(e))
            return False
        finally:
            if conn:
                self.pg_pool.putconn(conn)
    
    async def run_full_migration(self) -> bool:
        """Run complete migration process"""
        logger.info("🚀 Starting full migration process...")
        
        if not await self.initialize():
            return False
        
        steps = [
            ("check_schema", self.check_existing_schema),
            ("backup_data", self.backup_existing_data),
            ("apply_schema", self.apply_schema),
            ("migrate_data", self.migrate_existing_data),
            ("verify_migration", self.verify_migration)
        ]
        
        for step_name, step_func in steps:
            try:
                if step_name == "check_schema":
                    # Special handling for schema check
                    existing = await step_func()
                    logger.info(f"📋 Existing tables: {existing}")
                    continue
                
                success = await step_func()
                if not success:
                    logger.error(f"❌ Migration failed at step: {step_name}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Migration step {step_name} failed: {e}")
                self.log_migration_step(step_name, "error", str(e))
                return False
        
        # Save migration log
        await self.save_migration_log()
        
        logger.info("✅ Migration completed successfully!")
        return True
    
    async def save_migration_log(self):
        """Save migration log to database"""
        try:
            conn = self.pg_pool.getconn()
            cursor = conn.cursor()
            
            # Create migration log table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS migration_logs (
                    id SERIAL PRIMARY KEY,
                    migration_id VARCHAR(100),
                    log_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            migration_id = f"optimization_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            cursor.execute("""
                INSERT INTO migration_logs (migration_id, log_data)
                VALUES (%s, %s)
            """, (migration_id, json.dumps(self.migration_log)))
            
            conn.commit()
            logger.info(f"📝 Migration log saved with ID: {migration_id}")
            
        except Exception as e:
            logger.error(f"⚠️ Failed to save migration log: {e}")
        finally:
            if conn:
                self.pg_pool.putconn(conn)

class DeploymentManager:
    """Manages deployment to Railway"""
    
    def __init__(self):
        self.environment = os.getenv('RAILWAY_ENVIRONMENT', 'development')
        
    def check_railway_environment(self) -> Dict[str, Any]:
        """Check Railway environment configuration"""
        logger.info("🔍 Checking Railway environment...")
        
        required_vars = [
            'DATABASE_URL',
            'OPENAI_API_KEY'
        ]
        
        optional_vars = [
            'REDIS_URL',
            'CHATWOOT_API_URL',
            'CHATWOOT_API_TOKEN',
            'CHATWOOT_ACCOUNT_ID',
            'EVOLUTION_API_URL',
            'EVOLUTION_API_TOKEN',
            'INSTANCE_NAME'
        ]
        
        env_status = {
            'required': {},
            'optional': {},
            'railway_specific': {}
        }
        
        # Check required variables
        for var in required_vars:
            value = os.getenv(var)
            env_status['required'][var] = {
                'present': value is not None,
                'value_preview': value[:20] + "..." if value and len(value) > 20 else value
            }
        
        # Check optional variables
        for var in optional_vars:
            value = os.getenv(var)
            env_status['optional'][var] = {
                'present': value is not None,
                'value_preview': value[:20] + "..." if value and len(value) > 20 else None
            }
        
        # Check Railway-specific variables
        railway_vars = ['RAILWAY_ENVIRONMENT', 'PORT', 'RAILWAY_PROJECT_ID']
        for var in railway_vars:
            env_status['railway_specific'][var] = os.getenv(var)
        
        return env_status
    
    def generate_railway_config(self) -> Dict[str, Any]:
        """Generate optimized Railway configuration"""
        
        config = {
            'nixpacks.toml': {
                '[phases.setup]': {
                    'nixPkgs': ['python310', 'postgresql', 'redis'],
                    'aptPkgs': ['build-essential', 'libpq-dev']
                },
                '[phases.install]': {
                    'cmds': [
                        'pip install --upgrade pip',
                        'pip install -r requirements.txt'
                    ]
                },
                '[start]': {
                    'cmd': 'python royal_server_optimized.py'
                }
            },
            'railway.toml': {
                '[build]': {
                    'builder': 'nixpacks'
                },
                '[deploy]': {
                    'numReplicas': 1,
                    'sleepApplication': False,
                    'restartPolicyType': 'ON_FAILURE'
                }
            },
            'Procfile': 'web: python royal_server_optimized.py'
        }
        
        return config
    
    def create_deployment_files(self):
        """Create necessary deployment files"""
        logger.info("📄 Creating deployment files...")
        
        config = self.generate_railway_config()
        
        # Create nixpacks.toml
        nixpacks_content = """[phases.setup]
nixPkgs = ["python310", "postgresql", "redis"]
aptPkgs = ["build-essential", "libpq-dev"]

[phases.install]
cmds = [
    "pip install --upgrade pip",
    "pip install -r requirements.txt"
]

[start]
cmd = "python royal_server_optimized.py"
"""
        
        with open('nixpacks.toml', 'w') as f:
            f.write(nixpacks_content)
        
        # Create/update Procfile
        with open('Procfile', 'w') as f:
            f.write('web: python royal_server_optimized.py\n')
        
        logger.info("✅ Deployment files created")
    
    async def run_deployment_check(self) -> bool:
        """Run pre-deployment checks"""
        logger.info("🔍 Running deployment checks...")
        
        # Check environment
        env_status = self.check_railway_environment()
        
        # Check required variables
        missing_required = [
            var for var, status in env_status['required'].items() 
            if not status['present']
        ]
        
        if missing_required:
            logger.error(f"❌ Missing required environment variables: {missing_required}")
            return False
        
        # Check files exist
        required_files = [
            'royal_server_optimized.py',
            'hybrid_context_manager.py',
            'advanced_message_queue.py',
            'dynamic_worker_pool.py',
            'database_schema.sql',
            'requirements.txt'
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        if missing_files:
            logger.error(f"❌ Missing required files: {missing_files}")
            return False
        
        # Create deployment files
        self.create_deployment_files()
        
        logger.info("✅ Deployment checks passed")
        return True

async def main():
    """Main migration and deployment process"""
    print("🚀 ROYAL BOT OPTIMIZATION - MIGRATION & DEPLOYMENT")
    print("=" * 60)
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python migrate_and_deploy.py [migrate|deploy|full]")
        print("  migrate: Run database migration only")
        print("  deploy:  Run deployment checks only") 
        print("  full:    Run complete migration and deployment")
        return
    
    command = sys.argv[1].lower()
    
    if command in ['migrate', 'full']:
        print("\n📋 RUNNING DATABASE MIGRATION")
        print("-" * 40)
        
        migration_manager = MigrationManager()
        migration_success = await migration_manager.run_full_migration()
        
        if not migration_success:
            print("❌ Migration failed!")
            return
        
        print("✅ Migration completed successfully!")
    
    if command in ['deploy', 'full']:
        print("\n🚀 RUNNING DEPLOYMENT CHECKS")  
        print("-" * 40)
        
        deployment_manager = DeploymentManager()
        deployment_success = await deployment_manager.run_deployment_check()
        
        if not deployment_success:
            print("❌ Deployment checks failed!")
            return
        
        print("✅ Deployment checks passed!")
        print("\n📋 NEXT STEPS:")
        print("1. Commit all changes to git")
        print("2. Push to Railway (automatic deploy)")
        print("3. Verify deployment with: curl https://your-app.railway.app/health")
        print("4. Monitor metrics at: https://your-app.railway.app/metrics")
    
    print("\n🎉 OPTIMIZATION COMPLETE!")
    print("Your Royal Bot is now running with maximum efficiency!")

if __name__ == "__main__":
    asyncio.run(main())