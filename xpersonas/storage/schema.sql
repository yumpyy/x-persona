-- xpersonas SQLite Schema

-- Tenants
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'brand',
    config JSON NOT NULL DEFAULT '{}',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Personas
CREATE TABLE IF NOT EXISTS personas (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    platform TEXT NOT NULL,
    handle TEXT NOT NULL,
    display_name TEXT,
    persona_config JSON NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(tenant_id, platform, handle)
);

-- Browser sessions
CREATE TABLE IF NOT EXISTS browser_sessions (
    id TEXT PRIMARY KEY,
    persona_id TEXT NOT NULL REFERENCES personas(id),
    platform TEXT NOT NULL,
    auth_state_path TEXT NOT NULL,
    last_verified_at TEXT,
    is_valid INTEGER NOT NULL DEFAULT 1
);

-- Activity log
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id TEXT NOT NULL REFERENCES personas(id),
    timestamp TEXT NOT NULL,
    platform TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target_post_id TEXT NOT NULL,
    target_author TEXT,
    content TEXT,
    score REAL,
    reason TEXT,
    success INTEGER NOT NULL DEFAULT 1,
    error TEXT,
    is_promo INTEGER NOT NULL DEFAULT 0,
    product_id TEXT,
    metadata JSON
);
CREATE INDEX IF NOT EXISTS idx_activity_persona_time ON activity_log(persona_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_target ON activity_log(target_post_id);

-- Rate limits
CREATE TABLE IF NOT EXISTS rate_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id TEXT NOT NULL REFERENCES personas(id),
    action_type TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rate_limits_persona_action ON rate_limits(persona_id, action_type, timestamp);

-- Escalations
CREATE TABLE IF NOT EXISTS escalations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id TEXT NOT NULL REFERENCES personas(id),
    post_id TEXT,
    platform TEXT NOT NULL,
    reason TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    webhook_sent INTEGER NOT NULL DEFAULT 0,
    acknowledged INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Agent runs
CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    persona_id TEXT NOT NULL REFERENCES personas(id),
    status TEXT NOT NULL DEFAULT 'stopped',
    strategy TEXT NOT NULL,
    config JSON,
    pid INTEGER,
    started_at TEXT,
    stopped_at TEXT,
    last_cycle_at TEXT,
    cycles_completed INTEGER DEFAULT 0,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_persona ON agent_runs(persona_id);

-- Metrics
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id TEXT NOT NULL REFERENCES personas(id),
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_metrics_persona_time ON metrics(persona_id, recorded_at);

-- Products (brand mode)
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    name TEXT NOT NULL,
    description TEXT,
    features JSON,
    pricing TEXT,
    buy_url TEXT,
    pain_points JSON,
    disclosure_rules JSON,
    frequency_cap_per_week INTEGER DEFAULT 3,
    cooldown_days INTEGER DEFAULT 90,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Contacts (personal mode)
CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    persona_id TEXT NOT NULL REFERENCES personas(id),
    platform TEXT NOT NULL,
    handle TEXT NOT NULL,
    display_name TEXT,
    bio TEXT,
    research_interests JSON,
    institution TEXT,
    interaction_count INTEGER DEFAULT 0,
    last_interaction_at TEXT,
    stage TEXT NOT NULL DEFAULT 'stranger',
    rapport_score REAL DEFAULT 0.0,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_contacts_persona ON contacts(persona_id);
CREATE INDEX IF NOT EXISTS idx_contacts_stage ON contacts(persona_id, stage);

-- Contact interactions
CREATE TABLE IF NOT EXISTS contact_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id TEXT NOT NULL REFERENCES contacts(id),
    interaction_type TEXT NOT NULL,
    topic TEXT,
    content TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_interactions_contact ON contact_interactions(contact_id);

-- API Keys
CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    key_hash TEXT NOT NULL,
    name TEXT,
    scopes JSON NOT NULL DEFAULT '[]',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_used_at TEXT,
    UNIQUE(tenant_id, key_hash)
);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id);
