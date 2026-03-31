#!/usr/bin/env python3
"""
Production Drift Demo - Final Presentation Script

This is the single end-state demo script for live presentation.
It demonstrates "Same agent. Same prompt. Different execution reality."

SUCCESS CRITERIA:
1. Developer sees divergence without explanation
2. Developer recognizes it as production-relevant
3. Developer maps it to their own agent stack
4. Conclusion: "I cannot debug this class of failure without this layer."
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Ensure deterministic environment
os.environ['PYTHONHASHSEED'] = '0'

from exoarmur_production_drift_demo import ExoArmurDriftVerifier

def main():
    """Run the production drift demo for presentation"""
    print("🎯 PRODUCTION AGENT DRIFT DEMO - LIVE PRESENTATION")
    print("=" * 70)
    print("AI Agent Execution Integrity Verification")
    print("Scenario: Security incident response escalation decision")
    print("Core insight: Same agent. Same prompt. Different execution reality.")
    print()
    
    # Run the complete demo
    verifier = ExoArmurDriftVerifier()
    results = verifier.run_complete_demo()
    
    # Extract key findings for presentation
    execution_verification = results["exoarmur_verification"]["execution_verification"]
    divergence_analysis = execution_verification["divergence_analysis"]
    
    print("📊 KEY FINDINGS FOR DEVELOPER AUDIENCE:")
    print("-" * 50)
    print(f"✅ IDENTICAL INPUT: Same incident report, same agent configuration")
    print(f"🚨 DIVERGENT EXECUTION: {not divergence_analysis['fingerprints_identical']}")
    print(f"⏱️  TIME VARIANCE: {divergence_analysis['execution_variance_ms']}ms")
    print(f"🔐 FINGERPRINT A: {execution_verification['trace_a']['fingerprint'][:16]}...")
    print(f"🔐 FINGERPRINT B: {execution_verification['trace_b']['fingerprint'][:16]}...")
    print(f"🎯 DECISION CONSISTENCY: {divergence_analysis['decisions_identical']}")
    print()
    
    print("🎯 PRODUCTION RELEVANCE:")
    print("-" * 30)
    print("• API latency variance: ±30% with occasional spikes")
    print("• Cache hit/miss behavior divergence")
    print("• Partial tool responses from external APIs")
    print("• Retry behavior in production environments")
    print("• Execution ordering drift in complex pipelines")
    print()
    
    print("🤔 DEVELOPER QUESTIONS:")
    print("-" * 25)
    print("• Have you seen this in your LangGraph agents?")
    print("• How do you debug subtle execution differences?")
    print("• What happens when retries cause different paths?")
    print("• Can you prove your agent behaved consistently?")
    print()
    
    print("💡 THE EXOARMUR ANSWER:")
    print("-" * 25)
    print("✅ Deterministic execution fingerprinting")
    print("✅ Cross-system agreement verification")
    print("✅ Production drift detection")
    print("✅ Execution trace comparison")
    print("✅ Integrity verification without side effects")
    print()
    
    if divergence_analysis['divergence_detected']:
        print("🚨 CONCLUSION FOR DEVELOPERS:")
        print("-" * 35)
        print("Same agent. Same prompt. Different execution reality.")
        print("This occurs in production environments today.")
        print("Without execution trace verification, this failure class is undetectable.")
        print()
        print("🎯 DEVELOPER REALIZATION:")
        print("\"I cannot debug this class of failure without this layer.\"")
    else:
        print("✅ BASELINE SCENARIO:")
        print("-" * 20)
        print("Executions were identical (baseline scenario).")
        print("ExoArmur would detect any divergence if it occurred.")
    
    print()
    print("🔐 EXOARMUR: AI Agent Execution Verification Layer")
    print("https://github.com/exoarmur/ai-agent-verification")

if __name__ == "__main__":
    main()
