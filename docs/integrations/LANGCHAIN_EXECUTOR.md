# LangChain Executor Integration Guide

**⚠️ IMPORTANT: THIS IS A SCAFFOLD/REFERENCE IMPLEMENTATION**

The LangChainExecutor in Core is a scaffold/reference implementation. It does NOT include real LangChain integration or perform live vendor API calls. Real platform integrations (with actual API calls) belong in optional addon packages (e.g., `exoarmur-langchain-executor`). Core provides the plugin infrastructure and evidence schema for external effects, but does not include vendor SDK integrations.

---

**Version:** 1.0
**Date:** May 28, 2026
**Executor:** LangChainExecutor
**Purpose:** Governance boundary enforcement for LangChain agent operations (scaffold/reference implementation)

---

## Overview

The LangChainExecutor is a scaffold/reference implementation that demonstrates how to integrate ExoArmur's governance boundary with LangChain-based AI systems. This scaffold shows the pattern for:

- **Deterministic audit trails** for all LangChain operations
- **Rollback capabilities** for reversible operations (tool calls, memory operations)
- **State hash verification** for integrity checking
- **Integration with ExoArmur governance boundary** for policy and safety enforcement

**Note:** This scaffold uses mock implementations. For real LangChain integration with live API calls, use the optional addon package `exoarmur-langchain-executor` (when available).

---

## Architecture

### Design Principles

The LangChainExecutor follows ExoArmur's core architectural principles:

1. **Zero network dependencies** in the governance path
2. **Zero ML in the authority path** - all decisions are rule-based
3. **Deterministic execution** through canonical JSON and clock abstraction
4. **Executor isolation** - no direct access to governance internals
5. **DACT compliance** - maintains Levels 1-5 compliance

### Supported Operations

| Operation Type | Description | Reversible |
|----------------|-------------|------------|
| `agent_run` | Execute LangChain agent | No |
| `tool_call` | Execute LangChain tool | Yes |
| `chain_execution` | Execute LangChain chain | No |
| `prompt_execution` | Execute prompt template | No |
| `llm_invoke` | Invoke LLM through LangChain | No |
| `memory_operation` | Memory read/write operations | Yes |

---

## Installation

### Prerequisites

```bash
# Install ExoArmur Core
pip install exoarmur-core

# Install LangChain (separate dependency, not in kernel)
pip install langchain
```

### Import

```python
from exoarmur.executors import LangChainExecutor, LangChainActionType, create_langchain_intent
from exoarmur.kernel.boundary import ActionIntent
```

---

## Quick Start

### Basic Usage

```python
from exoarmur.executors import LangChainExecutor, LangChainActionType, create_langchain_intent
from exoarmur.kernel.boundary import ActionIntent

# Initialize executor
executor = LangChainExecutor()

# Create LangChain intent
langchain_intent = create_langchain_intent(
    actor_id="my_agent",
    action_type=LangChainActionType.AGENT_RUN,
    target="my_agent",
    payload={"input": "What is the capital of France?"}
)

# Convert to ActionIntent for governance boundary
intent = ActionIntent(
    intent_id=langchain_intent.intent_id,
    actor_id=langchain_intent.actor_id,
    actor_type=langchain_intent.actor_type,
    action_type=langchain_intent.action_type,
    target=langchain_intent.target,
    parameters=langchain_intent.payload,
    safety_context={},
    timestamp=langchain_intent.timestamp
)

# Execute with governance
result = executor.execute(intent)

# Check result
if result.success:
    print(f"Execution successful: {result.output}")
    print(f"State hash: {result.evidence['state_hash']}")
    print(f"Rollback available: {result.evidence['rollback_available']}")
else:
    print(f"Execution failed: {result.error}")
```

### Tool Call with Rollback

```python
# Create tool call intent
tool_intent = create_langchain_intent(
    actor_id="my_agent",
    action_type=LangChainActionType.TOOL_CALL,
    target="search_tool",
    payload={"query": "ExoArmur governance"}
)

intent = ActionIntent(
    intent_id=tool_intent.intent_id,
    actor_id=tool_intent.actor_id,
    actor_type=tool_intent.actor_type,
    action_type=tool_intent.action_type,
    target=tool_intent.target,
    parameters=tool_intent.payload,
    safety_context={},
    timestamp=tool_intent.timestamp
)

# Execute
result = executor.execute(intent)

# Rollback if needed
if result.evidence["rollback_available"]:
    rollback_result = executor.rollback(result.execution_id)
    if rollback_result.success:
        print("Rollback successful")
```

---

## Integration Patterns

### Pattern 1: Agent Governance

```python
from exoarmur.executors import LangChainExecutor
from langchain.agents import initialize_agent, Tool

# Initialize executor
executor = LangChainExecutor()

# Create LangChain agent
tools = [Tool(name="search", func=my_search_func)]
agent = initialize_agent(tools)

# Wrap agent execution with governance
def governed_agent_run(input_text):
    intent = create_langchain_intent(
        actor_id="agent",
        action_type=LangChainActionType.AGENT_RUN,
        target="agent",
        payload={"input": input_text}
    )
    
    action_intent = ActionIntent(
        intent_id=intent.intent_id,
        actor_id=intent.actor_id,
        actor_type=intent.actor_type,
        action_type=intent.action_type,
        target=intent.target,
        parameters=intent.payload,
        safety_context={},
        timestamp=intent.timestamp
    )
    
    result = executor.execute(action_intent)
    
    if result.success:
        return result.output
    else:
        raise Exception(f"Governance failure: {result.error}")

# Use governed agent
response = governed_agent_run("What is ExoArmur?")
```

### Pattern 2: Chain Execution

```python
from exoarmur.executors import LangChainExecutor
from langchain.chains import SimpleSequentialChain

# Initialize executor
executor = LangChainExecutor()

# Create chain
chain = SimpleSequentialChain.from_prompts([
    ("question", "Answer: {answer}")
])

# Govern chain execution
def governed_chain_run(input_text):
    intent = create_langchain_intent(
        actor_id="chain",
        action_type=LangChainActionType.CHAIN_EXECUTION,
        target="my_chain",
        payload={"input": input_text}
    )
    
    action_intent = ActionIntent(
        intent_id=intent.intent_id,
        actor_id=intent.actor_id,
        actor_type=intent.actor_type,
        action_type=intent.action_type,
        target=intent.target,
        parameters=intent.payload,
        safety_context={},
        timestamp=intent.timestamp
    )
    
    result = executor.execute(action_intent)
    
    if result.success:
        return result.output
    else:
        raise Exception(f"Governance failure: {result.error}")

# Use governed chain
response = governed_chain_run("Tell me about AI safety")
```

### Pattern 3: Memory Operations with Rollback

```python
from exoarmur.executors import LangChainExecutor
from langchain.memory import ConversationBufferMemory

# Initialize executor
executor = LangChainExecutor()
memory = ConversationBufferMemory()

# Governed memory write
def governed_memory_write(key, value):
    intent = create_langchain_intent(
        actor_id="memory",
        action_type=LangChainActionType.MEMORY_OPERATION,
        target="conversation_memory",
        payload={"operation": "write", "key": key, "value": value}
    )
    
    action_intent = ActionIntent(
        intent_id=intent.intent_id,
        actor_id=intent.actor_id,
        actor_type=intent.actor_type,
        action_type=intent.action_type,
        target=intent.target,
        parameters=intent.payload,
        safety_context={},
        timestamp=intent.timestamp
    )
    
    result = executor.execute(action_intent)
    
    if result.success:
        memory.save_context({key: value})
        return result.execution_id
    else:
        raise Exception(f"Governance failure: {result.error}")

# Write to memory
execution_id = governed_memory_write("user_input", "Hello")

# Rollback if needed
rollback_result = executor.rollback(execution_id)
if rollback_result.success:
    print("Memory operation rolled back")
```

---

## Determinism Guarantees

### Canonical JSON Encoding

All intents are encoded using canonical JSON for deterministic hashing:

```python
intent = create_langchain_intent(
    actor_id="test",
    action_type=LangChainActionType.AGENT_RUN,
    target="agent",
    payload={"z": 1, "a": 2}
)

# Canonical JSON has sorted keys
canonical = intent.to_canonical()
# Keys appear in sorted order: "a" before "z"
```

### Deterministic ID Generation

Intent IDs are generated deterministically using kernel ID factory:

```python
# Same inputs produce same IDs
intent1 = create_langchain_intent("actor", "agent_run", "target", {"data": "test"})
intent2 = create_langchain_intent("actor", "agent_run", "target", {"data": "test"})

assert intent1.intent_id == intent2.intent_id
```

### State Hash Verification

Each execution produces a verifiable state hash:

```python
result = executor.execute(intent)
state_hash = result.evidence["state_hash"]

# Same execution produces same hash
result2 = executor.execute(intent)
assert result.evidence["state_hash"] == result2.evidence["state_hash"]
```

---

## Rollback Capabilities

### Reversible Operations

The following operations support rollback:

- **Tool calls** - Can be rolled back to pre-execution state
- **Memory operations** - Can be rolled back to previous memory state

### Non-Reversible Operations

The following operations do not support rollback:

- **Agent runs** - Generative operations are irreversible
- **LLM invokes** - LLM calls are irreversible
- **Chain executions** - Chain operations are irreversible
- **Prompt executions** - Prompt operations are irreversible

### Rollback Example

```python
# Execute reversible operation
result = executor.execute(tool_intent)

# Check if rollback is available
if result.evidence["rollback_available"]:
    # Perform rollback
    rollback_result = executor.rollback(result.execution_id)
    
    if rollback_result.success:
        print("Rollback successful")
        print(f"New state hash: {rollback_result.evidence['state_hash']}")
    else:
        print(f"Rollback failed: {rollback_result.error}")
```

---

## Compliance Verification

### Air-Gap Integrity

The LangChainExecutor maintains air-gap integrity:

```bash
# Verify no network dependencies in executor
grep -r "import urllib\|import requests\|import socket" \
    src/exoarmur/executors/langchain_executor.py
# Expected: No matches
```

### ML Isolation

The LangChainExecutor maintains ML isolation:

```bash
# Verify no ML dependencies in executor
grep -r "import torch\|import transformers\|import sklearn" \
    src/exoarmur/executors/langchain_executor.py
# Expected: No matches
```

### DACT Compliance

The LangChainExecutor maintains DACT Levels 1-5 compliance:

- **Level 1 (Deterministic Replay)**: ✅ Verified through canonical JSON and deterministic IDs
- **Level 2 (Cryptographic Attestation)**: ✅ Verified through state hash verification
- **Level 3 (Counterfactual Analysis)**: ✅ Verified through rollback capabilities
- **Level 4 (ML Isolation)**: ✅ Verified through dependency audit
- **Level 5 (Air-Gap Integrity)**: ✅ Verified through network dependency audit

---

## Testing

### Run Tests

```bash
# Run LangChain executor tests
python -m pytest tests/executors/test_langchain_executor.py -v

# Run all executor tests
python -m pytest tests/executors/ -v
```

### Test Coverage

The LangChainExecutor has comprehensive test coverage:

- **Basic functionality**: Initialization, intent creation
- **Execution**: All operation types
- **Determinism**: Intent hashing, state hashing, executor state hashing
- **Canonical JSON**: Determinism, sorted keys
- **Rollback**: Reversible operations, non-reversible operations
- **Isolation**: No governance access, state encapsulation

---

## Advanced Usage

### Custom Action Types

```python
# Define custom action type
class CustomLangChainActionType:
    CUSTOM_OPERATION = "custom_operation"

# Use in executor
intent = create_langchain_intent(
    actor_id="custom_actor",
    action_type=CustomLangChainActionType.CUSTOM_OPERATION,
    target="custom_target",
    payload={"custom_data": "value"}
)
```

### Execution History Tracking

```python
# Get execution history
history = executor.get_execution_history()

# Analyze execution patterns
for execution in history:
    print(f"Intent ID: {execution.intent_id}")
    print(f"Status: {execution.status}")
    print(f"State Hash: {execution.state_hash}")
```

### State Hash Verification

```python
# Get current executor state hash
current_hash = executor.get_state_hash()

# Verify integrity after operations
expected_hash = "known_good_hash"
if current_hash != expected_hash:
    raise Exception("State hash mismatch - possible corruption")
```

---

## Troubleshooting

### Common Issues

**Issue**: Import errors
```python
# Solution: Ensure ExoArmur is installed
pip install exoarmur-core
```

**Issue**: Determinism failures
```python
# Solution: Use deterministic clock
from exoarmur.kernel.clock import DeterministicClock, set_clock
clock = DeterministicClock()
set_clock(clock)
```

**Issue**: Rollback failures
```python
# Solution: Check if operation is reversible
if not result.evidence["rollback_available"]:
    print("Operation is not reversible")
```

---

## Best Practices

1. **Always use ActionIntent** for governance boundary integration
2. **Check rollback availability** before attempting rollback
3. **Verify state hashes** for integrity checking
4. **Use deterministic clock** for reproducible testing
5. **Monitor execution history** for debugging and auditing
6. **Handle errors gracefully** with proper error messages
7. **Log execution results** for audit trail maintenance

---

## Security Considerations

1. **API Keys**: Store API keys securely, never in code
2. **Input Validation**: Validate all inputs before execution
3. **Output Sanitization**: Sanitize outputs to prevent injection
4. **Rate Limiting**: Implement rate limiting for API calls
5. **Audit Logging**: Maintain comprehensive audit logs
6. **Access Control**: Implement proper access controls

---

## Performance Considerations

1. **State Hash Computation**: O(n) where n is state size
2. **Execution History**: Grows with each execution, consider cleanup
3. **Rollback Stack**: Grows with reversible operations, consider cleanup
4. **Canonical JSON**: O(n) where n is payload size
5. **Deterministic IDs**: O(1) using kernel ID factory

---

## Future Enhancements

Planned enhancements for the LangChainExecutor:

1. **Real LangChain Integration**: Replace mock implementation with actual LangChain API calls
2. **Advanced Rollback**: Implement actual rollback for LangChain operations
3. **State Persistence**: Add state persistence for recovery
4. **Performance Optimization**: Optimize state hash computation
5. **Additional Operations**: Support more LangChain operation types

---

## Support

For issues, questions, or contributions:

- **Documentation**: See [ExoArmur Documentation](../README.md)
- **Architecture**: See [Architecture](../ARCHITECTURE.md)
- **DACT Standard**: See [DACT Standard](../DACT_STANDARD_v0.2.md)
- **Issues**: Open an issue on GitHub

---

## License

ExoArmur-Core is licensed under the Apache License 2.0 — see [LICENSE](../../LICENSE) for the full terms. This executor file is a scaffold/reference implementation; real LangChain integrations belong in optional addon packages.
