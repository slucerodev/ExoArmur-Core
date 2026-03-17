# SecurityHardeningReview Skill

## Purpose
Evaluate code for security and governance boundary weaknesses.

## Security Review Categories

### Input Validation
```python
# VULNERABLE: No input validation
def execute_action(user_input: str):
    return subprocess.run(user_input, shell=True)

# SECURE: Proper validation and sanitization
def execute_action(validated_input: str):
    if not re.match(r'^[a-zA-Z0-9_-]+$', validated_input):
        raise ValueError("Invalid input")
    return subprocess.run([validated_input], shell=False)
```

### Secret Management
```python
# VULNERABLE: Hardcoded secrets
credential = "example-value"

# SECURE: Environment variable injection
api_key = os.environ.get('API_KEY')
if not api_key:
    raise ValueError("API_KEY environment variable required")
```

### Privilege Escalation Prevention
```python
# VULNERABLE: Trusting user input for privileges
if user_input.get('trusted', False):
    execute_privileged_operation()

# SECURE: Explicit authorization checks
if user_has_privilege(user_id, 'admin'):
    execute_privileged_operation()
```

## Governance Boundary Security

### Executor Isolation
- Verify executors cannot access governance components
- Check executors receive only ActionIntent
- Ensure executors cannot modify traces
- Validate executor capabilities are declared

### Pipeline Integrity
- Confirm no bypass of policy evaluation
- Verify safety gate always runs
- Check audit trail completeness
- Validate trace immutability

### Gateway Security
- Ensure gateway has no business logic
- Verify gateway routes through pipeline
- Check gateway cannot modify intents
- Validate gateway is stateless

## Security Review Checklist

### Code Security
- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all external inputs
- [ ] Proper error handling without information leakage
- [ ] SQL injection prevention
- [ ] Command injection prevention
- [ ] XSS prevention (if web interface)

### Governance Security
- [ ] No bypass of ProxyPipeline
- [ ] Proper executor isolation
- [ ] Immutable audit trails
- [ ] Tamper-evident evidence chains
- [ ] Proper authorization checks

### Operational Security
- [ ] Secure secret management
- [ ] Proper logging and monitoring
- [ ] Rate limiting and DoS protection
- [ ] Secure communication channels
- [ ] Regular security updates

## Implementation Steps
1. Scan codebase for security vulnerabilities
2. Review governance boundary implementations
3. Check input validation patterns
4. Verify secret management practices
5. Test for common security issues
6. Document security requirements
7. Add security tests where needed

## Common Security Issues
- Hardcoded credentials in code
- Missing input validation
- Overly permissive error messages
- Insufficient logging
- No rate limiting
- Missing authentication/authorization
- Insecure direct object references
- Improper error handling
