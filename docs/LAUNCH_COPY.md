# Launch Copy — ExoArmur

## Hacker News — Show HN Post

**Title:**
> Show HN: ExoArmur – deterministic execution governance for AI agents (open source)

**Body:**
> AI agents are making real decisions — deleting files, calling APIs, sending messages — and most frameworks give you zero verifiable proof of what actually happened or why.
>
> ExoArmur is an open-source governance substrate that sits between your AI agent and the real world. Every action passes through a policy gate, produces an immutable audit record, and can be cryptographically replayed to prove the decision was correct.
>
> Key properties:
> - **Deterministic replay** — reconstruct any past decision byte-for-byte from its audit trail
> - **Policy enforcement** — actions are DENIED or ALLOWED before execution, not logged after
> - **Proof bundles** — `exoarmur proof` outputs a cryptographically verifiable artifact anyone can validate
> - **Feature-flag gated V2** — Byzantine fault-tolerant consensus, causal counterfactual reasoning, and identity containment scaffolded behind flags
> - **1,027 tests passing**, zero CVEs
>
> Quick start:
> ```
> pip install exoarmur-core
> exoarmur demo     # watch an AI action get blocked by policy
> exoarmur proof    # generate a cryptographic proof bundle
> exoarmur health   # governed runtime health check
> ```
>
> Repo: https://github.com/slucerodev/ExoArmur-Core
>
> Built this because I couldn't find anything that actually *enforces* governance at execution time — most "AI safety" tooling is observability after the fact. Happy to answer questions about the architecture.

---

## Twitter / X — Thread

**Tweet 1 (hook):**
> Your AI agent just deleted a file. Can you prove:
> - Which policy allowed it?
> - What the exact inputs were?
> - That replaying the audit log gives the same decision?
>
> Probably not. That's why I built ExoArmur. 🧵

**Tweet 2 (what it is):**
> ExoArmur is a deterministic execution governance layer for AI agents.
>
> Every action → policy gate → immutable audit record → cryptographic proof.
>
> Not observability after the fact. Enforcement *before* execution.

**Tweet 3 (demo):**
> Three commands from a fresh install:
>
> `exoarmur demo` — AI action hits the governance boundary → DENIED
> `exoarmur proof` — generates a cryptographic proof bundle
> `exoarmur health` — governed runtime health check
>
> The denial is replayable. The proof is verifiable. The audit trail is immutable.

**Tweet 4 (for the LangChain/AutoGen crowd):**
> If you're building with LangChain, LangGraph, or AutoGen — ExoArmur wraps your executor and enforces a governance boundary around every tool call.
>
> Your agent can *propose* an action. ExoArmur decides whether it *executes*.
>
> Open source. 1,027 tests. Zero CVEs.
> → github.com/slucerodev/ExoArmur-Core

**Tweet 5 (CTA):**
> Full architecture: deterministic replay engine, policy decision point, safety gate, identity containment, Byzantine fault-tolerant consensus (gated).
>
> If you're building agents that touch production systems, you need this layer.
>
> ⭐ github.com/slucerodev/ExoArmur-Core

---

## LangChain / AutoGen Community Posts (Discord / Reddit r/LangChain)

**Subject:** Built a governance enforcement layer for LangChain/AutoGen agents — open source

**Body:**
> Been building agents that call real APIs and noticed there's no standard way to:
> 1. Enforce a policy *before* a tool executes (not just log after)
> 2. Produce a cryptographically verifiable proof of every decision
> 3. Replay any past execution deterministically from its audit log
>
> Built ExoArmur to solve this. It's a governance substrate you wrap around your executor:
>
> ```python
> # Instead of calling your tool directly:
> result = my_tool.run(action)
>
> # Route through ExoArmur's governance boundary:
> trace = proxy_pipeline.execute_with_trace(action_intent)
> # → Policy evaluated, safety gate checked, audit record produced
> # → If denied: trace.final_verdict == FinalVerdict.DENY, action never ran
> ```
>
> Open source, 1,027 tests passing, zero CVEs.
> https://github.com/slucerodev/ExoArmur-Core
>
> Happy to answer questions or help with integration.
