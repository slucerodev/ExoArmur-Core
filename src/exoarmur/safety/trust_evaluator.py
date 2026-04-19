"""
Trust Evaluator for Safety Gate
Deterministic trust scoring based on source kind, known vendor reputation,
and per-tenant override env vars.

Trust score bands:
  0.90-1.00  Verified EDR/XDR sources (CrowdStrike, SentinelOne, Carbon Black)
  0.80-0.89  Known SIEM/observability sources (Splunk, Elastic, Datadog, QRadar)
  0.70-0.79  Network/infra sensors (Zeek, Suricata, Cisco, Palo Alto)
  0.60-0.69  Generic/unknown sensors with sensor_id present
  0.40-0.59  Anonymous or missing source info  -> triggers human review

Per-tenant override env var:
  EXOARMUR_TRUST_OVERRIDE_<TENANT>=<float>  (e.g. EXOARMUR_TRUST_OVERRIDE_DEMO_TENANT=0.95)
"""

import logging
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Known-vendor trust scores (exact match on source.name, lowercased)
_VENDOR_TRUST: Dict[str, float] = {
    # EDR / XDR — highest trust
    "crowdstrike":    0.95,
    "sentinelone":    0.93,
    "carbonblack":    0.92,
    "carbon_black":   0.92,
    "defender":       0.91,
    "cylance":        0.90,
    # SIEM / observability
    "splunk":         0.88,
    "elastic":        0.86,
    "elasticsearch":  0.86,
    "datadog":        0.85,
    "qradar":         0.84,
    "sentinel":       0.85,   # Microsoft Sentinel
    "chronicle":      0.84,
    # Network / infra
    "zeek":           0.78,
    "suricata":       0.77,
    "cisco":          0.76,
    "paloalto":       0.75,
    "palo_alto":      0.75,
    "fortinet":       0.74,
}

# Source kind baseline (source.kind field)
_KIND_BASELINE: Dict[str, float] = {
    "edr":            0.87,
    "xdr":            0.87,
    "siem":           0.82,
    "ndr":            0.75,
    "network":        0.73,
    "infra":          0.72,
    "sensor":         0.65,
    "generic":        0.62,
}

_FALLBACK_TRUST = 0.62      # sensor_id present but unknown vendor/kind
_ANONYMOUS_TRUST = 0.45     # no sensor_id, no vendor — triggers human review


@dataclass
class TrustEvaluationContext:
    """Context for trust evaluation"""
    event_source: Dict[str, Any]
    emitter_id: Optional[str]
    tenant_id: str
    cell_id: str
    correlation_id: str
    trace_id: str


class TrustEvaluator:
    """Deterministic trust evaluator — vendor-aware source scoring"""

    def __init__(self):
        logger.info("TrustEvaluator initialized with vendor-aware scoring")

    def evaluate_trust(
        self,
        event_source: Dict[str, Any],
        emitter_id: Optional[str],
        tenant_id: str
    ) -> float:
        """
        Evaluate trust score deterministically from source metadata.

        Args:
            event_source: Event source dict (kind, name, sensor_id, host, ...)
            emitter_id: Emitter identifier (sensor_id)
            tenant_id: Tenant identifier

        Returns:
            Trust score float in [0.0, 1.0]
        """
        context = TrustEvaluationContext(
            event_source=event_source,
            emitter_id=emitter_id,
            tenant_id=tenant_id,
            cell_id="",
            correlation_id="",
            trace_id=""
        )
        try:
            score = self._evaluate_trust_internal(context)
            logger.info(
                f"Trust score={score:.2f} "
                f"vendor={event_source.get('name', '?')} "
                f"kind={event_source.get('kind', '?')} "
                f"tenant={tenant_id}"
            )
            return score
        except Exception as e:
            logger.warning(f"Trust evaluation error, using fallback: {e}")
            return _FALLBACK_TRUST

    def _evaluate_trust_internal(self, context: TrustEvaluationContext) -> float:
        """Deterministic trust scoring — vendor → kind → emitter_id → anonymous."""
        src = context.event_source

        # --- Per-tenant override (highest precedence) ---
        env_key = "EXOARMUR_TRUST_OVERRIDE_" + context.tenant_id.upper().replace("-", "_")
        override = os.getenv(env_key)
        if override:
            try:
                score = float(override)
                logger.info(f"Tenant trust override applied: {context.tenant_id}={score}")
                return max(0.0, min(1.0, score))
            except ValueError:
                logger.warning(f"Invalid trust override value for {env_key}: {override!r}")

        # --- Vendor name match ---
        vendor = str(src.get("name", "")).lower().replace(" ", "_").replace("-", "_")
        if vendor and vendor in _VENDOR_TRUST:
            return _VENDOR_TRUST[vendor]

        # --- Source kind baseline ---
        kind = str(src.get("kind", "")).lower()
        if kind and kind in _KIND_BASELINE:
            # Bump slightly if sensor_id is present (registered sensor)
            base = _KIND_BASELINE[kind]
            return base + 0.03 if context.emitter_id else base

        # --- Has sensor_id but unknown kind/vendor ---
        if context.emitter_id:
            return _FALLBACK_TRUST

        # --- Anonymous source ---
        return _ANONYMOUS_TRUST
