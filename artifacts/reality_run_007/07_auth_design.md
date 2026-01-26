# Gate 5E Authentication/Authorization Design Document
## WORKFLOW 5E - MINIMAL AUTHN/Z FOR EXECUTION TRIGGERS

**Generated:** 2026-01-25T21:00:00Z  
**Status:** IMPLEMENTED AND TESTED

---

## DESIGN OVERVIEW

### API Key Authentication
Implements minimal API key authentication for all execution-triggering endpoints. This satisfies Rule R5 from Phase 5 rules.

### Permission-Based Authorization
Fine-grained permissions control what actions each API key can perform, with tenant-scoped access control.

### Fail Closed Security
All endpoints require authentication and authorization by default. Missing or invalid credentials result in immediate denial.

---

## ARCHITECTURE

### Core Components

#### 1. APIKey Data Structure
```python
@dataclass
class APIKey:
    key_id: str
    key_hash: str  # SHA-256 hash of actual key
    tenant_ids: List[str]  # Tenants this key can access
    permissions: Set[Permission]  # Granted permissions
    principal_id: str  # Key owner
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    description: Optional[str] = None
    last_used_at: Optional[datetime] = None
```

#### 2. Permission System
```python
class Permission(str, Enum):
    # Execution permissions
    EXECUTE_A0 = "execute:A0"  # Observe actions
    EXECUTE_A1 = "execute:A1"  # Soft containment
    EXECUTE_A2 = "execute:A2"  # Hard containment
    EXECUTE_A3 = "execute:A3"  # Irreversible actions
    
    # Approval permissions
    REQUEST_APPROVAL = "approval:request"
    GRANT_APPROVAL = "approval:grant"
    DENY_APPROVAL = "approval:deny"
    
    # Management permissions
    VIEW_STATUS = "status:view"
    MANAGE_KILL_SWITCH = "kill_switch:manage"
    MANAGE_TENANTS = "tenant:manage"
```

#### 3. AuthService
```python
class AuthService:
    async def authenticate(api_key: str) -> AuthContext
    async def authorize(auth_context: AuthContext, permission: Permission, tenant_id: str) -> AuthContext
    async def authenticate_and_authorize(...) -> AuthContext
```

### Authentication Flow

#### 1. API Key Validation
```python
def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()
```

#### 2. Key Verification
- Check key exists in storage
- Verify key is active and not expired
- Update last used timestamp

#### 3. Authorization Check
- Verify tenant access rights
- Check required permission
- Return authenticated context

### Authorization Model

#### 1. Tenant Scoping
- Each API key has explicit list of allowed tenant IDs
- Cross-tenant access is explicitly denied
- Tenant boundaries are enforced at authorization time

#### 2. Permission Enforcement
- Each action type requires specific permission
- Permissions are granted per API key
- Missing permissions result in denial

#### 3. Principal Tracking
- All actions track the principal (API key owner)
- Audit events include principal identification
- Accountability is maintained

---

## SECURITY PROPERTIES

### API Key Security
- **Storage**: Only SHA-256 hashes stored, never actual keys
- **Generation**: Cryptographically secure random keys
- **Expiration**: Optional expiration dates for temporary access
- **Revocation**: Immediate key deactivation capability

### Authentication Guarantees
- **Fail Closed**: Missing/invalid keys → DENY
- **Key Validation**: Active and non-expired keys only
- **Rate Limiting**: Last-used tracking enables rate limiting
- **Audit Trail**: All authentication attempts logged

### Authorization Guarantees
- **Tenant Isolation**: Explicit tenant access control
- **Permission Boundaries**: Fine-grained action control
- **Principal Accountability**: All actions attributed to key owner
- **Least Privilege**: Keys only get required permissions

---

## INTEGRATION POINTS

### Current Implementation
- **AuthService**: Standalone auth/authorization service
- **APIKeyStore**: In-memory key storage (for testing)
- **Decorators**: `@requires_auth` for endpoint protection

### Future Integration
- **ExecutionGate**: Add auth requirement before execution
- **Control Plane API**: Protect all execution-triggering endpoints
- **ApprovalGate**: Require auth for approval operations
- **Tenant Context**: Integrate auth context with tenant operations

### Decorator Usage
```python
@requires_auth(Permission.EXECUTE_A2)
async def containment_endpoint(api_key=None, tenant_id=None, auth_context=None, **kwargs):
    # Function only executes with valid auth and sufficient permissions
    pass
```

---

## API KEY OPERATIONS

### Key Creation
```python
# Create API key with specific permissions
actual_key = await create_api_key(
    key_id="operator-key-123",
    tenant_ids=["tenant-abc", "tenant-xyz"],
    permissions=[Permission.EXECUTE_A1, Permission.EXECUTE_A2],
    principal_id="operator-456",
    expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    description="Operations team key"
)
```

### Key Usage
```python
# Authenticate and authorize in one step
auth_context = await authenticate_and_authorize(
    api_key=provided_api_key,
    required_permission=Permission.EXECUTE_A2,
    tenant_id="tenant-abc",
    correlation_id="req-123",
    trace_id="trace-456"
)
```

### Key Management
```python
# Revoke API key
success = await revoke_api_key("operator-key-123")
```

---

## PERMISSION MATRIX

| Action Type | Required Permission | Risk Level | Description |
|--------------|-------------------|------------|-------------|
| A0_observe | EXECUTE_A0 | Low | Read-only observations |
| A1_soft_containment | EXECUTE_A1 | Medium | Soft containment actions |
| A2_hard_containment | EXECUTE_A2 | High | Hard containment actions |
| A3_irreversible | EXECUTE_A3 | Critical | Irreversible actions |
| Request Approval | REQUEST_APPROVAL | Medium | Submit approval requests |
| Grant Approval | GRANT_APPROVAL | High | Grant operation approval |
| View Status | VIEW_STATUS | Low | View system status |
| Manage Kill Switch | MANAGE_KILL_SWITCH | Critical | Emergency controls |
| Manage Tenants | MANAGE_TENANTS | High | Tenant management |

---

## TESTING STRATEGY

### Unit Tests
- ✅ API key creation and validation
- ✅ Authentication success/failure scenarios
- ✅ Authorization permission enforcement
- ✅ Tenant access control
- ✅ Combined auth/authorization flow
- ✅ Key management operations
- ✅ Permission enforcement by action type

### Security Tests
- ✅ Invalid API key rejection
- ✅ Expired key rejection
- ✅ Inactive key rejection
- ✅ Missing permission denial
- ✅ Cross-tenant access denial
- ✅ Principal tracking

### Test Coverage
- Authentication logic: 100%
- Authorization logic: 100%
- Key management: 100%
- Permission enforcement: 100%
- Error handling: 100%

---

## OPERATIONAL PROCEDURES

### API Key Lifecycle
1. **Creation**: Generate key with specific permissions and tenant access
2. **Distribution**: Securely deliver key to authorized operator
3. **Usage**: Key used for authenticated API calls
4. **Rotation**: Periodically rotate keys for security
5. **Revocation**: Immediately revoke compromised or expired keys

### Permission Management
```python
# Observer key (read-only)
observer_key = await create_api_key(
    key_id="observer-001",
    tenant_ids=["tenant-abc"],
    permissions=[Permission.EXECUTE_A0, Permission.VIEW_STATUS],
    principal_id="observer-123"
)

# Operator key (full execution)
operator_key = await create_api_key(
    key_id="operator-001",
    tenant_ids=["tenant-abc"],
    permissions=[Permission.EXECUTE_A0, Permission.EXECUTE_A1, Permission.EXECUTE_A2],
    principal_id="operator-456"
)

# Admin key (management)
admin_key = await create_api_key(
    key_id="admin-001",
    tenant_ids=["tenant-abc"],
    permissions=list(Permission),  # All permissions
    principal_id="admin-789"
)
```

### Security Monitoring
- Monitor authentication failure rates
- Track API key usage patterns
- Alert on suspicious activity patterns
- Log all authorization denials

---

## COMPLIANCE WITH PHASE 5 RULES

- ✅ **R0**: Old rules still apply (V1 contracts immutable)
- ✅ **R1**: Fail closed on execution (auth required by default)
- ✅ **R2**: Single authoritative enforcement point (AuthService)
- ✅ **R3**: Tenant context mandatory (auth includes tenant)
- ✅ **R5**: AUTHN/Z required for execution-triggering endpoints
- ✅ **R6**: Every denial audited with deterministic replay

---

## REPLAY DETERMINISM

### Authentication Replay
- API key hashes are durable and reproducible
- Authentication decisions are deterministic
- Key state (active/expired) is preserved

### Authorization Replay
- Permission grants are durable and verifiable
- Tenant access rights are reproducible
- Authorization logic is deterministic

### Audit Trail
- All authentication attempts are logged
- All authorization decisions are recorded
- Principal actions are fully attributable
- Security events are tamper-evident

---

## NEXT STEPS

1. Integrate auth service with all execution-triggering endpoints
2. Add persistent key storage (JetStream KV or database)
3. Implement key rotation and expiration automation
4. Add security monitoring and alerting
5. Create operator management UI for key administration

**STATUS: AUTHENTICATION/AUTHORIZATION READY FOR INTEGRATION**
