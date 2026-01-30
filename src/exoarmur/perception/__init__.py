"""
Perception Module - Telemetry Validation and Normalization

Validates TelemetryEventV1 inputs and normalizes them for downstream processing.
"""

from .validator import TelemetryValidator

__all__ = ['TelemetryValidator']
