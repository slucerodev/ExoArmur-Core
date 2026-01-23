# Federation Coordination v2 Safety Invariants
# 
# These invariants define the absolute safety boundaries of coordination.
# Any violation compromises the safety guarantees of ExoArmur ADMO.

# GLOBAL SAFETY INVARIANTS (Apply to ALL messages)
global_safety_invariants:
  no_executable_content:
    description: "Messages may not contain executable instructions"
    validation: "All fields must be descriptive data only"
    violation_impact: "CRITICAL - Enables remote code execution"
    
  no_conditional_logic:
    description: "Messages may not contain conditional logic"
    validation: "No if/then/else constructs in any field"
    violation_impact: "CRITICAL - Enables decision-making authority"
    
  no_obligation_creation:
    description: "Messages may not imply obligations"
    validation: "Language must be purely descriptive"
    violation_impact: "HIGH - Enables binding commitments"
    
  no_authority_transfer:
    description: "Messages may not transfer decision authority"
    validation: "No delegation or authorization fields"
    violation_impact: "CRITICAL - Breaks cell autonomy"
    
  no_infinite_validity:
    description: "All messages must have finite expiration"
    validation: "expires_at must be present and reasonable"
    violation_impact: "MEDIUM - Enables permanent coordination"
    
  no_global_state_reference:
    description: "Messages may not reference global state"
    validation: "All state must be local to coordination"
    violation_impact: "HIGH - Enables federation brain"

# MESSAGE-SPECIFIC SAFETY INVARIANTS

message_safety_invariants:
  coordination.announcement.v2:
    description: "I am available to coordinate X"
    
    receiver_may_not:
      assume_obligation:
        description: "Assume obligation to participate"
        risk: "Creates binding commitments"
        mitigation: "Treat as informational only"
        
      infer_approval:
        description: "Infer approval of capabilities"
        risk: "Creates false authority"
        mitigation: "Verify independently"
        
      create_dependencies:
        description: "Create dependencies on announcement"
        risk: "Creates coupling"
        mitigation: "Maintain independence"
        
      assume_permanence:
        description: "Assume permanent availability"
        risk: "Creates expectations"
        mitigation: "Respect expiration"
    
    receiver_may:
      observe_availability:
        description: "Observe availability information"
        safety: "Purely observational"
        
      consider_coordination:
        description: "Consider future coordination"
        safety: "No commitment required"
        
      store_for_reference:
        description: "Store for audit and reference"
        safety: "Informational use only"
        
      align_timing:
        description: "Align timing if beneficial"
        safety: "Optional optimization"
    
    sender_constraints:
      capabilities_descriptive_only:
        description: "Capabilities must be descriptive"
        validation: "No executable or prescriptive content"
        
      requirements_non_binding:
        description: "Requirements are preferences only"
        validation: "No obligation language"
        
      scope_limited:
        description: "Scope must be limited and specific"
        validation: "No global or unlimited scope"
        
      expiration_reasonable:
        description: "Expiration must be reasonable"
        validation: "Max 24 hours from issued_at"

  coordination.claim.v2:
    description: "I am coordinating X until T"
    
    receiver_may_not:
      assume_authority:
        description: "Assume authority over claimed resources"
        risk: "Enables unauthorized control"
        mitigation: "Maintain local authority"
        
      infer_permission:
        description: "Infer permission to act"
        risk: "Creates false authorization"
        mitigation: "Verify permissions locally"
        
      create_dependencies:
        description: "Create dependencies on claim"
        risk: "Creates coupling and failure points"
        mitigation: "Maintain independence"
        
      assume_exclusivity:
        description: "Assume exclusive coordination"
        risk: "Creates false monopolies"
        mitigation: "Allow multiple coordinations"
    
    receiver_may:
      observe_coordination:
        description: "Observe coordination activity"
        safety: "Purely observational"
        
      align_timing:
        description: "Align timing if beneficial"
        safety: "Optional coordination"
        
      store_for_audit:
        description: "Store for audit replay"
        safety: "Informational use only"
        
      consider_context:
        description: "Consider as additional context"
        safety: "No action required"
    
    sender_constraints:
      role_descriptive_only:
        description: "Role is descriptive, not authoritative"
        validation: "No enforcement language"
        
      resources_informational:
        description: "Claimed resources are informational"
        validation: "No control language"
        
      expiration_short:
        description: "Claims must be short-lived"
        validation: "Max 1 hour from issued_at"
        
      ownership_explicit:
        description: "Owner must be explicitly stated"
        validation: "owner_cell_id required"

  coordination.release.v2:
    description: "I am no longer coordinating X"
    
    receiver_may_not:
      assume_availability:
        description: "Assume resources are now available"
        risk: "Creates false expectations"
        mitigation: "Verify independently"
        
      infer_success:
        description: "Infer coordination success"
        risk: "Creates false conclusions"
        mitigation: "Observe actual outcomes"
        
      create_new_obligations:
        description: "Create new obligations based on release"
        risk: "Enables unintended commitments"
        mitigation: "Maintain status quo"
        
      assume_cleanup:
        description: "Assume automatic cleanup"
        risk: "Creates expectations"
        mitigation: "Handle cleanup locally"
    
    receiver_may:
      observe_end:
        description: "Observe coordination end"
        safety: "Purely observational"
        
      update_state:
        description: "Update local state accordingly"
        safety: "Local decision only"
        
      store_for_audit:
        description: "Store for audit replay"
        safety: "Informational use only"
        
      plan_next_steps:
        description: "Plan next coordination steps"
        safety: "Local planning only"
    
    sender_constraints:
      reason_descriptive:
        description: "Release reason must be descriptive"
        validation: "No blame or obligation language"
        
      final_state_accurate:
        description: "Final state must be accurate"
        validation: "Must reflect actual outcome"
        
      ownership_verified:
        description: "Only owner may release"
        validation: "owner_cell_id must match claim owner"
        
      immediate_expiration:
        description: "Release should expire quickly"
        validation: "expires_at close to issued_at"

  coordination.observation.v2:
    description: "I observed Y at time T"
    
    receiver_may_not:
      treat_as_authoritative:
        description: "Treat observation as authoritative truth"
        risk: "Creates false authority"
        mitigation: "Verify independently"
        
      base_decisions:
        description: "Base decisions solely on observation"
        risk: "Enables poor decision-making"
        mitigation: "Use multiple sources"
        
      assume_completeness:
        description: "Assume observation completeness"
        risk: "Creates false confidence"
        mitigation: "Consider limitations"
        
      infer_capabilities:
        description: "Infer capabilities from observation"
        risk: "Creates false assumptions"
        mitigation: "Verify capabilities directly"
    
    receiver_may:
      consider_context:
        description: "Consider as additional context"
        safety: "Informational use only"
        
      combine_sources:
        description: "Combine with other information sources"
        safety: "Multi-source validation"
        
      store_for_analysis:
        description: "Store for trend analysis"
        safety: "Historical use only"
        
      verify_independently:
        description: "Verify observation independently"
        safety: "Local validation"
    
    sender_constraints:
      data_non_authoritative:
        description: "Observed data is non-authoritative"
        validation: "No truth claims"
        
      confidence_honest:
        description: "Confidence score must be honest"
        validation: "Must reflect actual uncertainty"
        
      scope_limited:
        description: "Observation scope must be limited"
        validation: "No global claims"
        
      timestamp_accurate:
        description: "Observation timestamp must be accurate"
        validation: "Must reflect actual observation time"

  coordination.intent.broadcast.v2:
    description: "I intend to do Z"
    
    receiver_may_not:
      assume_permission:
        description: "Assume permission to act on intent"
        risk: "Creates false authorization"
        mitigation: "Verify permissions locally"
        
      infer_approval:
        description: "Infer approval of intent"
        risk: "Creates false consensus"
        mitigation: "Maintain independent approval"
        
      create_obligations:
        description: "Create obligations based on intent"
        risk: "Enables unintended commitments"
        mitigation: "Treat as informational"
        
      assume_execution:
        description: "Assume intent will be executed"
        risk: "Creates false expectations"
        mitigation: "Monitor actual actions"
    
    receiver_may:
      consider_planning:
        description: "Consider for planning purposes"
        safety: "Informational planning only"
        
      align_timing:
        description: "Align timing if beneficial"
        safety: "Optional coordination"
        
      store_for_visibility:
        description: "Store for coordination visibility"
        safety: "Informational use only"
        
      anticipate_actions:
        description: "Anticipate potential actions"
        safety: "Preparatory planning only"
    
    sender_constraints:
      intent_non_binding:
        description: "Intent must be non-binding"
        validation: "No commitment language"
        
      priority_descriptive:
        description: "Priority is descriptive only"
        validation: "No enforcement implications"
        
      expiration_reasonable:
        description: "Intent expiration must be reasonable"
        validation: "Max 4 hours from issued_at"
        
      targets_specific:
        description: "Target cells must be specific"
        validation: "No implicit targeting"

# SAFETY ENFORCEMENT RULES
enforcement_rules:
  validation_mandatory:
    description: "All messages must pass safety validation"
    enforcement: "Reject messages that violate invariants"
    
  audit_required:
    description: "All coordination must be audited"
    enforcement: "Generate audit events for all messages"
    
  expiration_enforced:
    description: "Message expiration must be enforced"
    enforcement: "Ignore expired messages automatically"
    
  ownership_verified:
    description: "Message ownership must be verified"
    enforcement: "Reject unauthorized releases/modifications"

# FAILURE MODE ANALYSIS
failure_modes:
  message_tampering:
    description: "Coordination messages are tampered"
    impact: "HIGH - Corrupts coordination visibility"
    mitigation: "Cryptographic signatures, integrity validation"
    
  expiration_bypass:
    description: "Messages bypass expiration"
    impact: "MEDIUM - Enables permanent coordination"
    mitigation: "Strict expiration enforcement, cleanup tasks"
    
  authority_escalation:
    description: "Messages imply authority escalation"
    impact: "CRITICAL - Breaks cell autonomy"
    mitigation: "Strict content validation, authority checks"
    
  observation_corruption:
    description: "Observation data is corrupted"
    impact: "LOW - Poor coordination decisions"
    mitigation: "Confidence scoring, source verification"
    
  intent_manipulation:
    description: "Intent messages are manipulated"
    impact: "MEDIUM - Misaligned coordination"
    mitigation: "Intent validation, source verification"

# SAFETY MONITORING
safety_monitoring:
  invariant_violations:
    description: "Track safety invariant violations"
    alerting: "Immediate alerts for critical violations"
    
  message_patterns:
    description: "Monitor coordination message patterns"
    alerting: "Alert on anomalous patterns"
    
  expiration_drift:
    description: "Monitor message expiration adherence"
    alerting: "Alert on expiration violations"
    
  authority_boundaries:
    description: "Monitor authority boundary crossings"
    alerting: "Critical alerts for boundary violations"
