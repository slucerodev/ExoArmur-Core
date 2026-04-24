#!/bin/bash
# Demo Benchmark Script - Terminal-Ready
# Runs determinism load test with minimal clean output for screen recording

set -e

python -m exoarmur.cli benchmark --determinism-load --runs 100 --concurrency 500 --minimal
