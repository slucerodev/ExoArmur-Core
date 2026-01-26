# EXOARMUR EXECUTION SURFACE INVENTORY
## WORKFLOW 5A - SAFETY SURFACE INVENTORY

**Generated:** 2026-01-25T20:39:00Z  
**Scope:** All identified execution paths that can cause side effects  
**Classification:** READ-ONLY / SIDE-EFFECT / UNKNOWN (treat as unsafe)

---

## EXECUTION PATHS CLASSIFIED AS SIDE-EFFECT (UNSAFE)

### 1. Identity Containment Execution
**File:** `src/identity_containment/execution.py`  
**Lines:** 59-124, 126-166, 168-183, 220-256

**Methods:**
- `execute_containment_apply()` - Applies identity containment (SIDE-EFFECT)
- `execute_containment_revert()` - Reverts identity containment (SIDE-EFFECT)  
- `process_expirations()` - Processes expired containments (SIDE-EFFECT)
- `tick()` - Background tick service for expirations (SIDE-EFFECT)

**Side Effects:** 
- Modifies external state via effector operations
- Emits audit events
- Changes containment status

### 2. Execution Kernel
**File:** `src/execution/execution_kernel.py`  
**Lines:** 75-109

**Methods:**
- `execute_intent()` - Executes ADMO intents (SIDE-EFFECT)

**Side Effects:**
- Executes containment actions (A0/A1/A2/A3)
- Modifies system state based on decisions
- Records execution state

### 3. Control Plane API (Phase 2 Scaffolding)
**File:** `src/control_plane/control_api.py`  
**Lines:** 102-112, 138-148, 150-160

**Methods:**
- `join_federation()` - Federation join operation (SIDE-EFFECT)
- `approve_request()` - Approval operation (SIDE-EFFECT)
- `deny_request()` - Denial operation (SIDE-EFFECT)

**Side Effects:**
- Federation state changes
- Approval state changes
- Audit trail modifications

**Note:** Currently scaffolding (enabled=False), but designed for side effects

---

## EXECUTION PATHS CLASSIFIED AS READ-ONLY (SAFE)

### 1. Control Plane API Query Operations
**File:** `src/control_plane/control_api.py`  
**Lines:** 72-84, 86-100, 114-124, 126-136, 162-172, 174-185, 187-201

**Methods:**
- `get_federation_status()` - Status query (READ-ONLY)
- `get_federation_members()` - Member list (READ-ONLY)
- `get_pending_approvals()` - Approval queue (READ-ONLY)
- `get_approval_details()` - Approval details (READ-ONLY)
- `get_audit_events()` - Audit query (READ-ONLY)
- `get_health_metrics()` - Health status (READ-ONLY)
- `get_available_endpoints()` - Endpoint list (READ-ONLY)

**Side Effects:** None (pure queries)

---

## EXECUTION PATHS CLASSIFIED AS UNKNOWN (TREAT AS UNSAFE)

### 1. Replay Engine
**File:** `src/replay/replay_engine.py`  
**Lines:** TBD - requires analysis

**Classification Rationale:** Replay engine may have side effects when replaying events

### 2. Mock Executor (V2 Testing)
**File:** `src/v2_restrained_autonomy/mock_executor.py`  
**Lines:** TBD - requires analysis

**Classification Rationale:** Mock executor designed for testing but may have execution paths

---

## BACKGROUND WORKERS / TICK SERVICES

### 1. Identity Containment Tick Service
**File:** `src/identity_containment/execution.py`  
**Lines:** 186-256

**Behavior:** Periodic expiration processing (SIDE-EFFECT)
**Trigger:** Time-based tick interval
**Side Effects:** Processes expirations, emits audit events

### 2. Federation Coordination Manager
**File:** `src/federation/coordination/federation_coordination_manager.py`  
**Lines:** TBD - requires analysis

**Classification Rationale:** Background coordination may cause side effects

---

## API ENDPOINTS (POTENTIAL EXECUTION TRIGGERS)

### REST API Endpoints (Phase 2 Scaffolding)
**Base Path:** `/api/v2/`

**Execution-Triggering Endpoints:**
- `POST /api/v2/federation/join` - Federation join (SIDE-EFFECT)
- `POST /api/v2/approvals/{approval_id}/approve` - Approval (SIDE-EFFECT)
- `POST /api/v2/approvals/{approval_id}/deny` - Denial (SIDE-EFFECT)

**Query-Only Endpoints (Safe):**
- `GET /api/v2/federation/status` - Status query
- `GET /api/v2/federation/members` - Member list
- `GET /api/v2/approvals/pending` - Approval queue
- `GET /api/v2/approvals/{approval_id}` - Approval details
- `GET /api/v2/audit/federation` - Audit query
- `GET /api/v2/monitoring/health` - Health status

---

## SUMMARY

**Total Execution Paths Identified:** 12
- **SIDE-EFFECT (Unsafe):** 7 paths requiring kill switch protection
- **READ-ONLY (Safe):** 5 paths (queries only)
- **UNKNOWN (Treat as Unsafe):** 2 paths requiring analysis

**Critical Enforcement Points:**
1. Identity containment operations (apply/revert/expire)
2. Execution kernel intent execution
3. Control plane approval operations
4. Background tick services
5. Federation join operations

**Next Steps:**
1. Analyze UNKNOWN paths to determine true classification
2. Implement single authoritative gate function for all SIDE-EFFECT paths
3. Add kill switch enforcement before any side effect execution
4. Ensure all SIDE-EFFECT paths emit audit events when blocked
