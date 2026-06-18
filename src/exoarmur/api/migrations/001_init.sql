-- ExoArmur API Phase 6 — PostgreSQL schema
-- Tables mirror the Pydantic models in api/models.py

CREATE TABLE IF NOT EXISTS observations (
    observation_id    TEXT PRIMARY KEY,
    source_federate_id TEXT NOT NULL,
    timestamp_utc     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    correlation_id    TEXT,
    observation_type TEXT NOT NULL,
    confidence        NUMERIC(5,4) NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    evidence_refs     TEXT[] NOT NULL DEFAULT '{}',
    payload_type      TEXT NOT NULL DEFAULT 'json',
    payload_data      JSONB NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_obs_correlation ON observations(correlation_id);
CREATE INDEX IF NOT EXISTS idx_obs_timestamp ON observations(timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_obs_source ON observations(source_federate_id);

CREATE TABLE IF NOT EXISTS beliefs (
    belief_id         TEXT PRIMARY KEY,
    belief_type       TEXT NOT NULL,
    confidence        NUMERIC(5,4) NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source_observations TEXT[] NOT NULL DEFAULT '{}',
    derived_at        TIMESTAMPTZ NOT NULL,
    correlation_id    TEXT,
    evidence_summary  TEXT NOT NULL DEFAULT '',
    conflicts         TEXT[] NOT NULL DEFAULT '{}',
    metadata          JSONB NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_belief_correlation ON beliefs(correlation_id);
CREATE INDEX IF NOT EXISTS idx_belief_type ON beliefs(belief_type);

CREATE TABLE IF NOT EXISTS audit_records (
    audit_id          TEXT PRIMARY KEY,
    event_kind        TEXT NOT NULL,
    payload_ref       JSONB NOT NULL DEFAULT '{}',
    correlation_id    TEXT NOT NULL,
    trace_id          TEXT NOT NULL DEFAULT '',
    tenant_id         TEXT NOT NULL DEFAULT 'default',
    cell_id           TEXT NOT NULL DEFAULT 'default',
    idempotency_key   TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_records(correlation_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_records(created_at DESC);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id       TEXT PRIMARY KEY,
    status            TEXT NOT NULL CHECK (status IN ('PENDING', 'APPROVED', 'DENIED')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    requested_action_class TEXT NOT NULL,
    correlation_id    TEXT NOT NULL,
    operator_id       TEXT,
    reason            TEXT,
    resolved_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_approval_status ON approvals(status);
CREATE INDEX IF NOT EXISTS idx_approval_correlation ON approvals(correlation_id);

CREATE TABLE IF NOT EXISTS federates (
    federate_id       TEXT PRIMARY KEY,
    federation_role   TEXT NOT NULL,
    cell_status       TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    public_key        TEXT
);

CREATE TABLE IF NOT EXISTS arbitrations (
    arbitration_id    TEXT PRIMARY KEY,
    created_at_utc    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status            TEXT NOT NULL,
    conflict_type     TEXT NOT NULL,
    subject_key       TEXT NOT NULL,
    conflict_key      TEXT NOT NULL,
    claims            JSONB NOT NULL DEFAULT '[]',
    evidence_refs     TEXT[] NOT NULL DEFAULT '{}',
    correlation_id    TEXT,
    proposed_resolution JSONB,
    decision          JSONB,
    approval_id       TEXT
);

CREATE INDEX IF NOT EXISTS idx_arbitration_status ON arbitrations(status);

CREATE TABLE IF NOT EXISTS benchmark_runs (
    run_id            TEXT PRIMARY KEY,
    core_version      TEXT NOT NULL,
    started_at        TIMESTAMPTZ NOT NULL,
    finished_at       TIMESTAMPTZ NOT NULL,
    mode              TEXT NOT NULL CHECK (mode IN ('determinism', 'throughput', 'replay', 'noise')),
    data              JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_benchmark_started ON benchmark_runs(started_at DESC);
