-- ExoArmur pilot — authentication, governed actions, pauses (2.2.0)

CREATE TABLE IF NOT EXISTS api_keys (
    key_hash        TEXT PRIMARY KEY,          -- SHA-256 of raw key; raw key never stored
    principal_id    TEXT NOT NULL,
    tenant_ids      TEXT[] NOT NULL DEFAULT '{}',
    permissions     TEXT[] NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    revoked         BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS operator_sessions (
    token_hash      TEXT PRIMARY KEY,          -- SHA-256 of session token
    principal_id    TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON operator_sessions(expires_at);

CREATE TABLE IF NOT EXISTS execution_pauses (
    scope           TEXT NOT NULL CHECK (scope IN ('global', 'tenant')),
    scope_key       TEXT NOT NULL DEFAULT '',  -- '' for global
    paused          BOOLEAN NOT NULL,
    updated_by      TEXT NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (scope, scope_key)
);

CREATE TABLE IF NOT EXISTS governed_actions (
    action_id       TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    principal_id    TEXT NOT NULL,
    operation       TEXT NOT NULL,
    target_path     TEXT NOT NULL,
    parameters      JSONB NOT NULL,
    params_sha256   TEXT NOT NULL,             -- hash recorded at proposal time
    action_class    TEXT NOT NULL,
    policy_version  TEXT,
    status          TEXT NOT NULL CHECK (status IN
        ('PENDING_APPROVAL','APPROVED','EXECUTING','EXECUTED','FAILED','DENIED','EXPIRED','BLOCKED')),
    approval_id     TEXT,
    approved_by     TEXT,
    approved_at     TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    result          JSONB,
    evidence        JSONB,
    evidence_sha256 TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_actions_tenant ON governed_actions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_actions_status ON governed_actions(status);
CREATE INDEX IF NOT EXISTS idx_actions_principal ON governed_actions(principal_id);
