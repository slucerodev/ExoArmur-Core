# ExoArmur Benchmark Suite

This document describes the performance and determinism benchmark suite for ExoArmur Core.

## Overview

The benchmark suite validates that ExoArmur maintains deterministic execution under load while providing performance metrics for throughput, latency, and replay costs. The system proves that performance scaling does NOT break determinism.

## Key Principles

- **PRIMARY**: Determinism under load - prove that high concurrency does not break hash consistency
- **SECONDARY**: Throughput and latency - measure execution performance
- **CRITICAL**: Replay/verification cost - measure the overhead of deterministic replay
- **OPTIONAL**: Noise resistance impact - verify that irrelevant data does not affect execution

## Running Benchmarks

### Command Line Interface

```bash
# Run all benchmarks
exoarmur benchmark --all

# Run specific benchmark
exoarmur benchmark --determinism-load
exoarmur benchmark --throughput
exoarmur benchmark --replay
exoarmur benchmark --noise

# Customize concurrency levels and runs
exoarmur benchmark --determinism-load --concurrency 10,50,100,500,1000 --runs 100

# Output results in JSON format
exoarmur benchmark --all --json
```

### Available Flags

- `--determinism-load`: Run determinism under load test
- `--throughput`: Run throughput and latency test
- `--replay`: Run replay/verification benchmark
- `--noise`: Run noise resistance benchmark
- `--all`: Run all benchmarks (default if no specific flag is set)
- `--concurrency <list>`: Comma-separated concurrency levels (default: 10,50,100,500,1000)
- `--runs <int>`: Number of runs per level (default: 100)
- `--json`: Output results in JSON format
- `--minimal`: Output minimal high-signal format for demos

## Reproducible Benchmark Proof

The benchmark suite provides reproducible proof artifacts for public-facing validation.

### Commands

Generate reproducible benchmark results:

```bash
# High-concurrency determinism test (primary metric)
exoarmur benchmark --determinism-load --runs 500 --concurrency 1000

# Full benchmark suite (secondary metrics)
exoarmur benchmark --all --runs 200
```

### Interpretation

- **Determinism under load** is the primary metric - proves that hash consistency holds under extreme concurrency
- **Performance metrics** (throughput, latency) are secondary - provide context but do not determine correctness
- A determinism failure (unique hash count > 1) is a critical bug regardless of performance numbers
- Performance variations across hardware are expected; determinism must be invariant

### Demo Mode

For terminal-ready output suitable for screen recording:

```bash
# Minimal output format
exoarmur benchmark --determinism-load --runs 100 --concurrency 500 --minimal
```

Or use the demo script:

```bash
bash scripts/demo_benchmark.sh
```

### Consistency Validation

Validate benchmark consistency across multiple runs:

```bash
bash scripts/validate_benchmark_consistency.sh
```

This runs the determinism benchmark 3 times and verifies identical results. Fails if any run diverges.

### Snapshot Generation

Generate a timestamped benchmark snapshot for archival:

```bash
bash scripts/generate_benchmark_snapshot.sh
```

This writes system information and benchmark results to `docs/BENCHMARK_SNAPSHOT.md`.

## Benchmark Types

### 1. Determinism Under Load (PRIMARY)

**Purpose**: Prove that determinism holds even under high concurrency.

**Method**: Executes the determinism proof harness at increasing concurrency levels (10, 50, 100, 500, 1000) with multiple runs per level. Verifies that all executions produce identical hashes.

**Metrics**:
- Concurrency level
- Total executions
- Unique hash count (must be 1)
- Failures
- Total runtime

**Output Example**:
```
DETERMINISM UNDER LOAD
----------------------
Concurrency: 1000
Executions: 1000
Unique Hashes: 1
Failures: 0
STATUS: DETERMINISTIC
```

**Interpretation**:
- **PASS**: Unique hash count = 1, failures = 0
- **FAIL**: Unique hash count > 1 (determinism violation)
- The benchmark will immediately fail if any hash divergence is detected

### 2. Throughput and Latency (SECONDARY)

**Purpose**: Measure execution performance under load.

**Method**: Executes scenarios at multiple concurrency levels and measures:
- Executions per second
- Latency percentiles (p50, p95, p99)
- Mean latency

**Metrics**:
- Concurrency level
- Total executions
- Executions per second
- p50, p95, p99 latency (ms)
- Mean latency (ms)
- Total runtime

**Output Example**:
```
THROUGHPUT
----------
Throughput: 125.50 exec/sec
p50: 7.25 ms
p95: 12.80 ms
p99: 18.45 ms
```

**Interpretation**:
- Higher throughput = better performance
- Lower latency = better performance
- p99 latency indicates worst-case performance
- Compare across concurrency levels to identify scaling characteristics

### 3. Replay/Verification Cost (CRITICAL)

**Purpose**: Measure the overhead of deterministic replay and verification.

**Method**: Executes scenarios, replays from input hash, and verifies hash consistency. Measures timing for each phase.

**Metrics**:
- Execution time (avg, p50, p95)
- Replay time (avg, p50, p95)
- Verification time (avg, p50, p95)

**Output Example**:
```
REPLAY PERFORMANCE
------------------
Execution: 8.45 ms
Replay: 5.23 ms
Verification: 2.10 ms
```

**Interpretation**:
- Replay time should be close to execution time (efficient replay)
- Verification time should be minimal (efficient hash comparison)
- High replay cost may indicate optimization opportunities

### 4. Noise Resistance (OPTIONAL)

**Purpose**: Verify that irrelevant data does not affect execution or hash.

**Method**: Injects increasing noise payload sizes (1, 10, 100) and measures:
- Hash stability (must remain unchanged)
- Latency impact

**Metrics**:
- Noise level
- Hash stable (YES/NO)
- Latency impact (%)
- Baseline latency
- Noisy latency

**Output Example**:
```
NOISE RESISTANCE
----------------
Noise Level: 100
Hash Stable: YES
Latency Impact: 2.35%
```

**Interpretation**:
- **PASS**: Hash stable = YES (noise does not affect execution)
- **FAIL**: Hash stable = NO (noise affected execution - critical bug)
- Latency impact should be minimal (< 10% acceptable)

## Sample Output

### Text Format

```
============================================================
EXOARMUR BENCHMARK RESULTS
============================================================

DETERMINISM UNDER LOAD
------------------------------------------------------------
Concurrency: 1000
Executions: 1000
Unique Hashes: 1
Failures: 0
STATUS: DETERMINISTIC

THROUGHPUT
------------------------------------------------------------
Throughput: 125.50 exec/sec
p50: 7.25 ms
p95: 12.80 ms
p99: 18.45 ms

REPLAY PERFORMANCE
------------------------------------------------------------
Execution: 8.45 ms
Replay: 5.23 ms
Verification: 2.10 ms

NOISE RESISTANCE
------------------------------------------------------------
Noise Level: 100
Hash Stable: YES
Latency Impact: 2.35%
```

### JSON Format

```json
{
  "determinism": [
    {
      "concurrency_level": 1000,
      "total_executions": 1000,
      "unique_hash_count": 1,
      "failures": 0,
      "total_runtime_ms": 8523.45,
      "status": "DETERMINISTIC"
    }
  ],
  "throughput": [
    {
      "concurrency_level": 100,
      "total_executions": 1000,
      "executions_per_second": 125.5,
      "latency_p50_ms": 7.25,
      "latency_p95_ms": 12.8,
      "latency_p99_ms": 18.45,
      "latency_mean_ms": 9.12,
      "total_runtime_ms": 7968.23
    }
  ],
  "replay": {
    "runs": 100,
    "execution_time_avg_ms": 8.45,
    "execution_time_p50_ms": 7.8,
    "execution_time_p95_ms": 12.3,
    "replay_time_avg_ms": 5.23,
    "replay_time_p50_ms": 4.9,
    "replay_time_p95_ms": 8.1,
    "verification_time_avg_ms": 2.1,
    "verification_time_p50_ms": 1.9,
    "verification_time_p95_ms": 3.2
  },
  "noise": [
    {
      "noise_level": 100,
      "hash_stable": true,
      "latency_impact_percent": 2.35,
      "baseline_latency_ms": 8.45,
      "noisy_latency_ms": 8.65
    }
  ]
}
```

## CI/CD Integration

The benchmark suite is integrated into `scripts/check_determinism.sh` as a non-blocking step:

```bash
# Step 9: Optional determinism load benchmark (NON-BLOCKING)
exoarmur benchmark --determinism-load --concurrency 10,50 --runs 50
```

**Important**: The CI step does NOT fail on performance numbers. It only fails if determinism breaks (hash divergence). This ensures CI remains fast while still catching critical determinism violations.

## Testing

The benchmark suite includes comprehensive tests in `tests/test_benchmark.py`:

- Test determinism load test produces single hash
- Test throughput test runs without error
- Test replay benchmark returns valid metrics
- Test noise benchmark does not alter hash
- Test all benchmarks can run together

Run tests:
```bash
pytest tests/test_benchmark.py -v
```

## Architecture

The benchmark suite is additive and isolated from core logic:

- **Location**: `src/exoarmur/benchmark/`
- **Components**:
  - `benchmark_runner.py`: Main benchmark execution logic
  - `metrics.py`: Measurement utilities (latency, percentiles, resource tracking)
  - Uses existing `DeterminismHarness` for determinism testing
  - Leverages canonical payloads and stable_hash for consistency

**Key Constraint**: All benchmarking uses canonical payload + stable_hash only. No modifications to V1 behavior or contracts.

## Performance Expectations

### Determinism
- **Requirement**: Unique hash count must equal 1 at all concurrency levels
- **Target**: Determinism holds at concurrency ≥ 1000
- **Failure**: Any hash divergence is a critical bug

### Throughput
- **Expected**: Varies by hardware and workload
- **Target**: > 100 exec/sec at concurrency 100 (typical hardware)
- **Monitoring**: Track p99 latency for worst-case performance

### Replay Cost
- **Expected**: Replay time should be ≤ execution time
- **Target**: Replay overhead < 50% of execution time
- **Monitoring**: High replay cost may indicate optimization opportunities

### Noise Resistance
- **Requirement**: Hash must remain stable at all noise levels
- **Target**: Latency impact < 10% at noise level 100
- **Failure**: Any hash change is a critical bug

## Troubleshooting

### Determinism Violation

If the determinism load test fails with hash divergence:

1. Check for nondeterministic code paths (datetime.now(), random, unordered iteration)
2. Verify determinism guards are enabled
3. Review the specific concurrency level that failed
4. Check for race conditions or shared mutable state

### Poor Performance

If throughput or latency metrics are unexpectedly poor:

1. Verify system resources (CPU, memory)
2. Check for external dependencies (NATS, database)
3. Profile the execution to identify bottlenecks
4. Consider if the workload is representative of production

### Replay Verification Failure

If replay verification fails:

1. Check input hash consistency
2. Verify payload storage is working correctly
3. Check for environment differences between execution and replay
4. Verify deterministic ordering is enforced

## Future Enhancements

Potential additions to the benchmark suite:

- Memory usage tracking under load
- Network I/O metrics (if applicable)
- Long-running stability tests (hours/days)
- Multi-node federation benchmarks
- Custom workload simulation

## References

- Determinism Proof Harness: `src/exoarmur/proof/determinism_harness.py`
- Scenario Builder: `src/exoarmur/proof/scenario_builder.py`
- Hash Extraction: `src/exoarmur/proof/hash_extractor.py`
- CLI: `src/exoarmur/cli.py` (benchmark command)
- Tests: `tests/test_benchmark.py`
