-- 🏗️ ROYAL BOT V2 - OPTIMIZED DATABASE SCHEMA
-- PostgreSQL schema for maximum efficiency
-- Compatible with Railway PostgreSQL

-- =====================================================
-- 1. CONVERSATION CONTEXTS (Multi-layer system)
-- =====================================================

CREATE TABLE IF NOT EXISTS conversation_contexts (
    user_id VARCHAR(255) PRIMARY KEY,
    
    -- Context data (JSONB for flexibility and performance)
    context_data JSONB NOT NULL DEFAULT '{}',
    
    -- User profile data
    user_profile JSONB DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    
    -- Conversation state
    current_state VARCHAR(50) DEFAULT 'browsing',
    user_intent VARCHAR(100) DEFAULT '',
    is_entrepreneur BOOLEAN DEFAULT FALSE,
    experience_level VARCHAR(50) DEFAULT '',
    
    -- Product interactions
    recent_products JSONB DEFAULT '[]',
    product_interests TEXT[] DEFAULT '{}',
    budget_range VARCHAR(100),
    
    -- Timestamps
    conversation_started TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_contexts_last_interaction ON conversation_contexts(last_interaction);
CREATE INDEX IF NOT EXISTS idx_contexts_user_intent ON conversation_contexts(user_intent);
CREATE INDEX IF NOT EXISTS idx_contexts_is_entrepreneur ON conversation_contexts(is_entrepreneur);
CREATE INDEX IF NOT EXISTS idx_contexts_current_state ON conversation_contexts(current_state);

-- JSONB indexes for context_data queries
CREATE INDEX IF NOT EXISTS idx_contexts_context_data_gin ON conversation_contexts USING GIN (context_data);

-- =====================================================
-- 2. ADVANCED MESSAGE QUEUE (Persistent + Priority)
-- =====================================================

CREATE TYPE message_priority AS ENUM ('urgent', 'high', 'normal', 'low');
CREATE TYPE message_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'dead_letter');

CREATE TABLE IF NOT EXISTS message_queue (
    id SERIAL PRIMARY KEY,
    queue_id UUID DEFAULT gen_random_uuid() UNIQUE,
    
    -- Message data
    user_id VARCHAR(255) NOT NULL,
    message_content TEXT NOT NULL,
    message_hash VARCHAR(64) NOT NULL, -- For deduplication
    
    -- Routing and priority
    source VARCHAR(50) NOT NULL, -- chatwoot, evolution, test
    priority message_priority DEFAULT 'normal',
    
    -- Processing data
    status message_status DEFAULT 'pending',
    worker_id VARCHAR(100),
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    
    -- Metadata
    conversation_id VARCHAR(255),
    phone VARCHAR(50),
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scheduled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Error handling
    last_error TEXT,
    error_details JSONB
);

-- Indexes for queue performance
CREATE INDEX IF NOT EXISTS idx_queue_status_priority ON message_queue(status, priority, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_queue_user_id ON message_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_queue_message_hash ON message_queue(message_hash);
CREATE INDEX IF NOT EXISTS idx_queue_created_at ON message_queue(created_at);
CREATE INDEX IF NOT EXISTS idx_queue_worker_id ON message_queue(worker_id);

-- =====================================================
-- 3. SYSTEM METRICS (Real-time monitoring)
-- =====================================================

CREATE TYPE metric_type AS ENUM (
    'queue_depth', 'response_time', 'worker_utilization', 
    'cache_hit_rate', 'error_rate', 'user_satisfaction',
    'memory_usage', 'cpu_usage', 'database_performance'
);

CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    
    -- Metric info
    metric_type metric_type NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,4) NOT NULL,
    
    -- Context
    user_id VARCHAR(255),
    worker_id VARCHAR(100),
    
    -- Additional data
    metadata JSONB DEFAULT '{}',
    
    -- Timestamp
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Partitioning for metrics (optional, for high volume)
CREATE INDEX IF NOT EXISTS idx_metrics_type_time ON system_metrics(metric_type, recorded_at);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at ON system_metrics(recorded_at);

-- =====================================================
-- 4. USER INTERACTIONS LOG (Comprehensive tracking)
-- =====================================================

CREATE TABLE IF NOT EXISTS user_interactions (
    id SERIAL PRIMARY KEY,
    
    -- User info
    user_id VARCHAR(255) NOT NULL,
    session_id UUID DEFAULT gen_random_uuid(),
    
    -- Interaction data
    role VARCHAR(20) NOT NULL, -- user, assistant, system
    message TEXT NOT NULL,
    message_type VARCHAR(50), -- text, product_query, purchase_intent
    
    -- Context at time of interaction
    user_state VARCHAR(50),
    products_shown JSONB DEFAULT '[]',
    
    -- Processing info
    response_time_ms INTEGER,
    ai_model VARCHAR(50),
    confidence_score DECIMAL(3,2),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for interaction queries
CREATE INDEX IF NOT EXISTS idx_interactions_user_id_time ON user_interactions(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_interactions_session_id ON user_interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_interactions_message_type ON user_interactions(message_type);

-- =====================================================
-- 5. RATE LIMITING (Smart multi-window)
-- =====================================================

CREATE TABLE IF NOT EXISTS rate_limits (
    id SERIAL PRIMARY KEY,
    
    -- Target identification
    user_id VARCHAR(255),
    ip_address INET,
    identifier_type VARCHAR(20) NOT NULL, -- user, ip, global
    
    -- Rate limiting windows
    window_size INTEGER NOT NULL, -- seconds
    max_requests INTEGER NOT NULL,
    current_requests INTEGER DEFAULT 0,
    
    -- Time tracking
    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_request TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Metadata
    is_vip BOOLEAN DEFAULT FALSE,
    bypass_reason VARCHAR(100),
    
    -- Reset tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for rate limiting performance
CREATE UNIQUE INDEX IF NOT EXISTS idx_rate_limits_unique ON rate_limits(
    COALESCE(user_id, ''), 
    COALESCE(host(ip_address), ''), 
    identifier_type, 
    window_size
);
CREATE INDEX IF NOT EXISTS idx_rate_limits_window_start ON rate_limits(window_start);

-- =====================================================
-- 6. PERFORMANCE CACHE TABLE (Query result caching)
-- =====================================================

CREATE TABLE IF NOT EXISTS query_cache (
    cache_key VARCHAR(255) PRIMARY KEY,
    
    -- Cache data
    cache_data JSONB NOT NULL,
    cache_type VARCHAR(50) NOT NULL, -- product_search, user_context, ai_response
    
    -- Cache metadata
    user_id VARCHAR(255),
    query_hash VARCHAR(64),
    
    -- TTL and invalidation
    ttl_seconds INTEGER DEFAULT 3600,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour'),
    
    -- Hit tracking
    hit_count INTEGER DEFAULT 0,
    last_hit TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for cache performance
CREATE INDEX IF NOT EXISTS idx_cache_expires_at ON query_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_cache_type_created ON query_cache(cache_type, created_at);
CREATE INDEX IF NOT EXISTS idx_cache_user_id ON query_cache(user_id);

-- =====================================================
-- 7. TRIGGERS AND FUNCTIONS (Automation)
-- =====================================================

-- Auto-update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to context table
CREATE TRIGGER update_contexts_updated_at 
    BEFORE UPDATE ON conversation_contexts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Auto-cleanup expired cache
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM query_cache WHERE expires_at < CURRENT_TIMESTAMP;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE 'plpgsql';

-- Auto-cleanup old interactions (keep 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_interactions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_interactions 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE 'plpgsql';

-- Auto-cleanup old metrics (keep 7 days)
CREATE OR REPLACE FUNCTION cleanup_old_metrics()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM system_metrics 
    WHERE recorded_at < CURRENT_TIMESTAMP - INTERVAL '7 days';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE 'plpgsql';

-- =====================================================
-- 8. VIEWS FOR MONITORING (Performance insights)
-- =====================================================

-- Queue health view
CREATE OR REPLACE VIEW queue_health AS
SELECT 
    priority,
    status,
    COUNT(*) as message_count,
    AVG(EXTRACT(EPOCH FROM (COALESCE(completed_at, CURRENT_TIMESTAMP) - created_at))) as avg_processing_time,
    MIN(created_at) as oldest_message
FROM message_queue 
GROUP BY priority, status;

-- User activity summary
CREATE OR REPLACE VIEW user_activity_summary AS
SELECT 
    user_id,
    COUNT(*) as total_interactions,
    MAX(last_interaction) as last_seen,
    current_state,
    is_entrepreneur,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - MAX(last_interaction)))/3600 as hours_since_last_interaction
FROM conversation_contexts
GROUP BY user_id, current_state, is_entrepreneur
ORDER BY last_seen DESC;

-- System performance view
CREATE OR REPLACE VIEW system_performance AS
SELECT 
    metric_type,
    AVG(metric_value) as avg_value,
    MAX(metric_value) as max_value,
    MIN(metric_value) as min_value,
    COUNT(*) as sample_count,
    MAX(recorded_at) as last_recorded
FROM system_metrics 
WHERE recorded_at > CURRENT_TIMESTAMP - INTERVAL '1 hour'
GROUP BY metric_type;

-- =====================================================
-- 9. INITIAL DATA AND CONFIGURATION
-- =====================================================

-- Create default rate limit entries
INSERT INTO rate_limits (identifier_type, window_size, max_requests) 
VALUES 
    ('global', 60, 1000),  -- 1000 requests per minute globally
    ('user', 60, 10),      -- 10 requests per minute per user
    ('ip', 60, 50)         -- 50 requests per minute per IP
ON CONFLICT DO NOTHING;

-- =====================================================
-- COMMENTS AND DOCUMENTATION
-- =====================================================

COMMENT ON TABLE conversation_contexts IS 'Persistent conversation context and user profiles';
COMMENT ON TABLE message_queue IS 'Advanced message queue with priority and error handling';
COMMENT ON TABLE system_metrics IS 'Real-time system performance metrics';
COMMENT ON TABLE user_interactions IS 'Complete log of user interactions for analysis';
COMMENT ON TABLE rate_limits IS 'Smart rate limiting with multiple windows';
COMMENT ON TABLE query_cache IS 'Performance cache for expensive queries';

-- Schema version for migrations
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description) 
VALUES (1, 'Initial optimized schema for Royal Bot v2 - Maximum efficiency')
ON CONFLICT (version) DO NOTHING;