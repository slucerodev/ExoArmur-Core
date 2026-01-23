# FEDERATION_IDENTITY.md

## Purpose
Defines the federation identity handshake protocol, cryptographic verification, and secure inter-cell communication capabilities that enable ExoArmur to operate as a trusted mesh of autonomous defensive cells.

## Definitions

**Federation Identity**: The cryptographic identity and trust relationship established between cells in the ExoArmur mesh, enabling secure communication and coordinated defense without centralized control.

**Handshake Protocol**: The multi-step cryptographic process by which cells establish trust relationships, exchange capabilities, and verify each other's authenticity using Ed25519 signatures.

**Cryptographic Verification**: The process of verifying message signatures, key authenticity, nonce uniqueness, and timestamp freshness to prevent replay attacks and ensure message integrity.

**Replay Protection**: Security mechanisms that prevent the reuse of nonces, timestamps, or signatures to protect against replay attacks in federation communications.

**FederateKeyPair**: Ed25519 key pair used by a cell for signing and verifying federation messages, with stable key_id derived from the public key hash.

**Nonce**: Cryptographically random value used once per message to prevent replay attacks, with TTL-based expiration and tracking.

**Handshake Session**: Temporary session state maintained during the identity handshake process, tracking protocol state and security parameters.

## Federation Identity Handshake Protocol

### Phase 1: Identity Exchange
- **Purpose**: Initial cell identification and key exchange
- **Message**: IdentityExchangeMessage signed with cell's private key
- **Verification**: Ed25519 signature verification over canonical bytes
- **Contents**: Cell public key, certificate chain, federation role, capabilities
- **Security**: Nonce-based replay protection, timestamp freshness validation

### Phase 2: Capability Negotiation
- **Purpose**: Exchange supported capabilities and requirements
- **Message**: CapabilityNegotiateMessage with capability lists
- **Verification**: Signature verification and capability compatibility checking
- **Contents**: Supported capabilities, required capabilities, priority constraints
- **Security**: Continuation of nonce tracking and timestamp validation

### Phase 3: Trust Establishment
- **Purpose**: Establish trust scores and federation parameters
- **Message**: TrustEstablishMessage with trust assessment
- **Verification**: Signature verification and trust score validation
- **Contents**: Trust score, trust reasons, expiration, policy references
- **Security**: Final cryptographic verification before federation confirmation

### Phase 4: Federation Confirmation
- **Purpose**: Confirm successful federation establishment
- **Message**: FederationConfirmMessage acknowledging completion
- **Verification**: Signature verification of confirmation
- **Contents**: Session summary, federation parameters, next steps
- **Security**: Completion of cryptographic verification and session finalization

## Cryptographic Security Model

### Ed25519 Signature Scheme
- **Algorithm**: Ed25519 for high-performance, secure digital signatures
- **Key Generation**: Cryptographically secure random key pair generation
- **Key ID**: Stable SHA-256 hash of base64-encoded public key
- **Signature**: Base64-encoded Ed25519 signature over canonical bytes
- **Verification**: Deterministic signature verification with public key

### Canonical Serialization
- **Purpose**: Ensure consistent hash generation across all cells
- **Method**: JSON with sorted keys, normalized types, compact separators
- **Scope**: All signed messages and audit records
- **Verification**: Canonical bytes used for all signature operations
- **Integrity**: Prevents ambiguous serialization that could affect signatures

### Replay Protection Mechanisms
- **Nonce Tracking**: Per-federate nonce storage with TTL expiration
- **Timestamp Validation**: Bounded timestamp skew checking (default 5 minutes)
- **Signature Freshness**: Verification of signature creation time
- **Session Isolation**: Handshake session state with cryptographic binding

## Protocol Enforcement

### Verification Pipeline
1. **Schema Validation**: Pydantic model validation of message structure
2. **Signature Verification**: Ed25519 signature verification over canonical bytes
3. **Key ID Matching**: Verify signature key_id matches expected federate key
4. **Nonce Uniqueness**: Prevent reuse of previously used nonces
5. **Timestamp Freshness**: Reject messages with excessive timestamp skew
6. **Audit Event Emission**: Record all verification outcomes with metadata

### Failure Handling
- **Invalid Signature**: Reject message, emit audit event, transition to failed state
- **Key Mismatch**: Reject message, emit audit event, transition to failed state
- **Nonce Reuse**: Reject message, emit audit event, transition to failed state
- **Timestamp Out of Bounds**: Reject message, emit audit event, transition to failed state
- **Unknown Key ID**: Reject message, emit audit event, transition to failed state

### Audit Trail
- **Success Events**: Record successful verification with federate_id, key_id, message_type
- **Failure Events**: Record failure reasons with detailed error information
- **Correlation Tracking**: Link all events to handshake session and correlation_id
- **Timestamp Logging**: Record all verification timestamps for replay analysis
- **Cryptographic Evidence**: Include signature verification results and key material

## Federation Identity Store

### Identity Management
- **Storage**: Deterministic storage of federate identities with cryptographic keys
- **Retrieval**: Fast lookup of federate identities by federate_id or key_id
- **Validation**: Schema validation and cryptographic key verification
- **Expiration**: Optional identity expiration with graceful renewal
- **Revocation**: Secure identity revocation with federation notification

### Nonce Management
- **Generation**: Cryptographically secure nonce generation using secrets.token_urlsafe()
- **Tracking**: Per-federate nonce storage with TTL and usage state
- **Expiration**: Automatic cleanup of expired nonces
- **Rejection**: Deterministic rejection of reused or expired nonces
- **Isolation**: Nonce isolation between federates to prevent cross-contamination

### Session Management
- **Creation**: Handshake session creation with unique session identifiers
- **State Tracking**: Protocol state machine with deterministic transitions
- **Expiration**: Session expiration with automatic cleanup
- **Completion**: Session finalization with federation confirmation
- **Error Handling**: Graceful failure handling with audit trail preservation

## Security Guarantees

### Cryptographic Guarantees
- **Message Integrity**: All messages protected by Ed25519 signatures
- **Authentication**: Strong cryptographic authentication of cell identities
- **Non-Repudiation**: Digital signatures provide non-repudiation evidence
- **Forward Secrecy**: Compromise of private keys does not affect past signatures

### Replay Protection Guarantees
- **Nonce Uniqueness**: Each nonce used at most once per federate
- **Timestamp Freshness**: Messages rejected if timestamps are outside acceptable bounds
- **Session Isolation**: Handshake sessions isolated with cryptographic binding
- **Deterministic Behavior**: Same inputs always produce same verification results

### Audit Guarantees
- **Complete Trail**: All verification steps recorded with full metadata
- **Integrity Evidence**: Cryptographic evidence preserved for all decisions
- **Replay Capability**: Complete replay of federation handshakes for verification
- **Compliance Support**: Audit trail supports regulatory compliance requirements

## Implementation Status

### Completed Components ✅
- **FederateKeyPair**: Ed25519 key generation and management
- **Message Signing**: Cryptographic signing of federation messages
- **Signature Verification**: Deterministic signature verification
- **Protocol Enforcer**: Complete protocol boundary enforcement
- **Federation Identity Store**: Deterministic storage with replay protection
- **Audit Events**: Comprehensive audit trail for all operations
- **Test Coverage**: 24/24 tests passing with deterministic time and isolated state

### Security Features ✅
- **Ed25519 Cryptography**: Industry-standard elliptic curve cryptography
- **Canonical Serialization**: Deterministic JSON serialization for consistent hashing
- **Replay Protection**: Comprehensive nonce and timestamp-based replay protection
- **Protocol Enforcement**: Strict enforcement of all protocol boundaries
- **Audit Trail**: Complete audit evidence for all verification outcomes
- **Test Isolation**: Fresh contexts and deterministic clocks for testing

### Integration Points ✅
- **Feature Flag Integration**: V2 federation capabilities properly gated
- **Dependency Injection**: Clean separation of concerns with injected dependencies
- **Deterministic Time**: Fixed clock implementation for test stability
- **V1 Compatibility**: No impact on existing V1 functionality
- **Production Ready**: All components production-ready with proper error handling

## Usage Examples

### Basic Federation Setup
```python
from src.federation.crypto import FederateKeyPair
from src.federation.federate_identity_store import FederateIdentityStore
from src.federation.protocol_enforcer import ProtocolEnforcer
from src.federation.clock import SystemClock

# Create cell identity
key_pair = FederateKeyPair()

# Create federation components
identity_store = FederateIdentityStore()
protocol_enforcer = ProtocolEnforcer(identity_store, SystemClock())

# Store cell identity
identity = FederateIdentityV1(
    federate_id="cell-us-east-1-cluster-01-node-01",
    public_key=key_pair.public_key_b64,
    key_id=key_pair.key_id,
    federation_role=FederationRole.MEMBER,
    capabilities=["belief_aggregation", "policy_distribution"],
    trust_score=0.8
)
identity_store.store_identity(identity)
```

### Message Verification
```python
from src.federation.messages import create_identity_exchange_message
from src.federation.crypto import sign_message

# Create and sign message
message = create_identity_exchange_message(
    federate_id="cell-us-east-1-cluster-01-node-01",
    nonce="unique-nonce-12345",
    correlation_id="correlation-67890",
    cell_public_key=key_pair.public_key_b64,
    federation_role="member",
    capabilities=["belief_aggregation"]
)

signed_message = sign_message(message, key_pair.private_key)

# Verify message
success, failure_reason, audit_event = protocol_enforcer.verify_handshake_message(signed_message)
```

This federation identity system provides the cryptographic foundation for secure ExoArmur mesh operations while maintaining complete auditability and deterministic replay capability.
