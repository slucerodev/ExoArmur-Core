# The Counterfactual Gap: How ExoArmur Answers the Question AI Governance Has Been Avoiding

## SECTION 1: THE QUESTION NOBODY CAN ANSWER

When an AI system denies someone healthcare, flags a loan application as fraudulent, or makes a decision that causes harm — investigators, lawyers, and the people affected all ask the same question:

"Would the AI have decided differently if the input had been different?"

This is the counterfactual question. It is the question that determines liability. It determines fairness. It determines whether a policy change would have prevented the harm.

No AI governance system in production can answer it today.

While major players like Microsoft and well-funded startups like Fiddler are building AI governance toolkits, none have solved the counterfactual problem. The focus has been on monitoring, logging, and explainable AI — important capabilities that stop short of answering "what if" questions with mathematical rigor.

Consider three real incidents. In 2023, UnitedHealth's nH Predict AI system was used by a Medicare Advantage insurer to override doctor recommendations with an alleged 90% error rate. Families whose care was denied could not answer the fundamental question: would the AI have approved care if it had seen additional medical data? The result was that the insurer is now required to retain detailed records of all inputs and decisions.

In 2025, the Massachusetts Attorney General reached a settlement with a student loan company whose AI underwriting model had disparate impact based on race and immigration status. No effective process existed to test the model before deployment. The company is now required to document every algorithmic decision and retain that documentation.

From 2016 to 2020, Australia's Robodebt system sent false debt notices to thousands of welfare recipients. The Royal Commission found it lacked contestability in decision-making. Citizens had no way to ask "would this debt exist if my income had been calculated differently?"

These are not edge cases. They are the rule. And in every case, the inability to answer the counterfactual question meant that accountability was impossible.

## SECTION 2: WHY THIS HAS NEVER BEEN SOLVED

This problem exists for three fundamental reasons. First, AI systems are built for forward prediction, not backward reconstruction. They log outputs, not the complete execution state needed to replay a decision under different conditions. When an AI makes a decision, it typically records the input and the result, but not the intermediate states, the version of the model used, or the random seeds that led to that specific outcome.

Second, non-determinism. Most AI systems introduce randomness. The same input on Tuesday may produce a different output than it did on Monday. You cannot replay what you cannot reproduce. This randomness is often intentional — it helps models generalize and avoid overfitting — but it makes counterfactual analysis impossible without careful architectural design.

Third, no separation between policy and execution. When the rule that governs a decision is entangled with the system that executes it, there is no clean way to ask "what if the rule had seen different data?" The policy and the execution are woven together in a way that makes it impossible to modify one without affecting the other.

Field research from Arize revealed this fundamental tension: "Traditional software used to be deterministic... Given the same input, the same outcome follows. Agents introduce variability into systems built for repeatability."

Researchers have known this gap exists for years. Pearl's causal hierarchy — published in the 1990s — describes exactly what is needed. The theory has been there for thirty years. The infrastructure has not.

## SECTION 3: WHAT A SOLUTION ACTUALLY REQUIRES

The academic literature identifies five architectural prerequisites for genuine counterfactual replay. These are not aspirational requirements. They are the minimum viable architecture for answering the counterfactual question with mathematical rigor.

First, deterministic execution traces. Every step of every decision must be logged — not just inputs and outputs, but the complete execution state. Every version, every intermediate value, every external call. Without this comprehensive logging, replay is impossible.

Second, separation of policy from execution. The rules that govern a decision must be cleanly separated from the system that carries it out. Without this separation, you cannot modify one without affecting the other. The policy evaluation must be a distinct component from the execution engine.

Third, re-execution capability. The system must be able to replay a past decision with a modified input and produce a new result under identical conditions. This requires that the execution environment be perfectly reproducible.

Fourth, a formal intervention model. The architecture must encode how inputs affect outcomes — what Pearl calls the "do-operator." Without this, changing an input without modeling its downstream effects produces unrealistic scenarios that do not reflect how the system would actually behave.

Fifth, outcome comparison. After replaying under the counterfactual, the system must produce a verifiable comparison — did the decision change? By how much? What does that mean? The comparison must be mathematically rigorous and explainable.

## SECTION 4: WHAT EXOARMUR BUILT

ExoArmur-Core is an open-source deterministic governance runtime built by a solo developer over nine months. It was not designed to solve the counterfactual problem. Its architecture — built for audit integrity and policy enforcement — turns out to satisfy every prerequisite researchers identify as necessary.

For deterministic execution traces, ExoArmur's replay engine captures complete execution traces as AuditRecordV1 objects with hash-chained audit trails. The same correlation ID always produces the same replay result. This can be verified by running `python examples/quickstart_replay.py`.

For separation of policy from execution, ExoArmur's ProxyPipeline enforces a clean boundary between policy evaluation (PolicyDecisionPoint) and execution (ExecutorPlugin). These are not the same component. This can be verified by running `python examples/demo_standalone.py`, which shows policy denial before any execution side effect occurs.

For re-execution capability, the ReplayEngine can replay any recorded correlation ID deterministically. The same inputs always produce the same result, making counterfactual analysis possible.

For a formal intervention model, ExoArmur's counterfactual module implements Pearl's interventional level directly. An Intervention object specifies a field, its original value, and its counterfactual value. The apply_intervention() function produces a modified AuditRecordV1 without touching the original.

For outcome comparison, CounterfactualReport compares original and counterfactual replay results, produces a verdict (SAME_OUTCOME / DIFFERENT_OUTCOME / INCONCLUSIVE), and generates a human-readable explanation.

Running ExoArmur's counterfactual engine today produces output like this:

```
ORIGINAL EXECUTION:
  Actor: agent-001
  Result: SUCCESS

COUNTERFACTUAL EXECUTION:
  Actor: unauthorized-actor
  Result: SUCCESS

VERDICT: SAME_OUTCOME
```

The policy decision was the same even with an unauthorized actor. This suggests the current policy may not be checking actor authorization.

This is not just a replay. It is a finding. The system automatically identified a policy gap that no human had spotted.

## SECTION 5: WHAT THIS UNLOCKS

Five capabilities become possible with genuine counterfactual reasoning. First, genuine liability determination. Courts can now get a technically rigorous answer to the question "Was the AI decision the cause of the harm, or would the same decision have been made regardless of the disputed input?"

Second, causal fairness auditing. Not just "does this model produce disparate outcomes?" but "would this specific decision have been different if the applicant's race had been different?" This is counterfactual fairness as defined by Kusner et al. (NIPS 2017).

Third, algorithmic recourse. "What would need to change for this person to receive a different decision?" Not an approximation. An exact answer from a replayed execution.

Fourth, policy improvement. "If we changed this rule, how many past decisions would have been different?" Run counterfactuals across an entire audit history to understand the impact of policy changes before implementing them.

Fifth, regulatory compliance. EU AI Act Articles 12-13 require logging sufficient to trace AI system actions. ExoArmur's audit trail satisfies this requirement and goes further — it enables the counterfactual queries regulators will eventually demand.

## SECTION 6: CURRENT STATE AND ROADMAP

What works today is substantial. The policy enforcement pipeline is verified working. Deterministic replay is verified working. The counterfactual engine is a working prototype. The system has a clean install with zero dependencies beyond Python and a core test suite that passes without external infrastructure dependencies.

What is being built includes Structural Causal Model construction from audit trails, do-calculus implementation for multi-variable interventions, integration with LangChain and OpenAI Agents SDK, and counterfactual certificates as first-class audit artifacts.

The counterfactual engine today implements Pearl's interventional level — Rung 2 of the causal ladder. Full Rung 3 (genuine structural counterfactuals) requires learning causal structure from audit trails. That work is underway.

## SECTION 7: CLOSING

ExoArmur did not set out to solve the counterfactual problem. It set out to make AI decisions auditable and replayable. The counterfactual capability emerged from the architecture.

That is how it usually works. The infrastructure comes first. The capabilities follow.

The counterfactual gap in AI governance is not a research problem. It is an infrastructure problem. The theory has existed for thirty years. What was missing was a system built with the right architectural primitives.

ExoArmur is open source. The code is real. The demo runs in under two minutes.

GitHub: https://github.com/slucerodev/ExoArmur-Core
