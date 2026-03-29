# ExoArmur Roadmap

## Current Stable Scope

ExoArmur Core v0.3.0 provides deterministic governance and replayable audit capabilities for autonomous systems.

**Currently Verified Repository Scope:**
- Deterministic execution pipeline with ProxyPipeline boundary
- V1 core cognition loop with immutable contracts
- Source installation via `pip install .`
- Editable installation support for `pip install -e .` and `pip install -e ".[v2]"`
- V2 restrained autonomy deny/replay demonstration path
- Feature-flagged V2 capabilities (disabled by default)

Current validation details should be taken from live CI and the current `README.md` / `VALIDATE.md` guidance rather than from hardcoded test counts in this roadmap.

## Near-Term Improvements

### Enhanced Operator Experience
**Status: Design Phase**
- Web-based operator approval interface
- Real-time audit stream monitoring
- Improved alerting and notification systems
- Mobile operator access capabilities

### Policy Management
**Status: Design Phase**
- Dynamic policy rule configuration
- Policy template system for common scenarios
- Policy conflict detection and resolution
- Policy audit trails and versioning

### Integration Ecosystem
**Status: Research Phase**
- Standardized executor interfaces
- Third-party executor registry
- Integration adapters for common systems
- SDK and client library improvements

### Performance Optimization
**Status: Research Phase**
- Execution pipeline performance improvements
- Reduced latency for real-time applications
- Optimized audit trail storage
- Batch processing capabilities

## Future Exploration

### Multi-Cell Federation
**Status: Conceptual**
- Byzantine fault tolerance for multi-cell coordination
- Cross-cell audit trail consolidation
- Federated policy enforcement
- Inter-cell communication protocols

### Advanced Analytics
**Status: Conceptual**
- Causal analysis of decision patterns
- Anomaly detection in autonomous behavior
- Predictive safety analysis
- Performance metrics and reporting

### AI/ML Integration
**Status: Conceptual**
- Machine learning-based threat detection
- Adaptive policy learning
- Natural language operator interfaces
- Predictive maintenance requirements

## Implementation Principles

### Feature Flags Required
All new capabilities beyond V1 core must be:
- Feature-flagged with default OFF
- Additive and non-invasive to existing functionality
- Fully backward compatible
- Independently testable

### Architecture Compliance
All development must respect:
- ProxyPipeline as sole execution boundary
- Executor isolation and untrusted model
- Deterministic execution requirements
- Invariant enforcement through CI gates
- Immutable V1 contracts

### Quality Standards
- Comprehensive test coverage for new features
- Documentation updates for all user-facing changes
- Security review for architectural modifications
- Performance benchmarking and optimization

## Timeline Estimates

### Near-Term (6-12 months)
- Operator experience improvements
- Policy management system
- Integration ecosystem foundation
- Performance optimization

### Future Exploration (12-24 months)
- Multi-cell federation research
- Advanced analytics capabilities
- AI/ML integration exploration

## Dependencies and Blockers

### Technical Dependencies
- NATS JetStream scalability improvements
- Advanced cryptographic primitives for federation
- Web framework for operator interfaces
- Database systems for audit trail management

### Resource Requirements
- Development team expansion for parallel workstreams
- Security review bandwidth for new features
- Documentation maintenance and updates

### External Dependencies
- Third-party executor ecosystem development
- Community feedback and contribution processing
- Integration testing with external systems

## Contribution Opportunities

We welcome community contributions in all roadmap areas, particularly:

- **Documentation improvements** and examples
- **Test coverage expansion** for edge cases
- **Performance optimization** and profiling
- **Security review** and vulnerability research
- **Integration development** for external systems
- **Community building** and ecosystem development

All roadmap items are subject to change based on community feedback, security requirements, and technical discovery. Priority will be adjusted based on user needs and resource availability.
