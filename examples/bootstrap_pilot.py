#!/usr/bin/env python3
"""
Bootstrap the ExoArmur pilot: workspace, operator policy, API key.

Generates (never stores) a raw API key, persists only its SHA-256 verifier,
writes a versioned operator policy file, and prints the pinned digest the
operator must configure as EXOARMUR_POLICY_SHA256.

Usage:
    python examples/bootstrap_pilot.py \
        --database-url postgresql://user:pass@host:5432/exoarmur_pilot \
        --workspace /srv/exoarmur/workspace \
        --policy-out /etc/exoarmur/policy.json \
        --principal-id operator-1 --tenant-id tenant-1 \
        --operation fs.create_file --operation fs.modify_file \
        --action-class fs.create_file=A1_soft_containment \
        --action-class fs.modify_file=A2_hard_containment \
        --approval human --trust-score 0.9 \
        --permission action:submit --permission action:read \
        --permission action:resume --permission approval:grant \
        --permission approval:deny --permission pause:control \
        --permission evidence:read
"""

import argparse
import asyncio
import hashlib
import json
import secrets
import sys
from pathlib import Path

import asyncpg


def parse_action_class(pairs):
    out = {}
    for p in pairs or []:
        k, _, v = p.partition("=")
        out[k.strip()] = v.strip()
    return out


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--policy-out", required=True)
    ap.add_argument("--principal-id", required=True)
    ap.add_argument("--tenant-id", required=True)
    ap.add_argument("--operation", action="append", required=True)
    ap.add_argument("--action-class", action="append", default=[])
    ap.add_argument("--default-action-class", default=None)
    ap.add_argument("--approval", default="human",
                    choices=["none", "quorum", "human"])
    ap.add_argument("--trust-score", type=float, required=True)
    ap.add_argument("--permission", action="append", default=[])
    ap.add_argument("--key-id", default=None)
    args = ap.parse_args()

    ws = Path(args.workspace)
    ws.mkdir(parents=True, exist_ok=True)

    policy = {
        "version": 1,
        "rules": [
            {
                "tenant_id": args.tenant_id,
                "principal_id": args.principal_id,
                "operations": args.operation,
                "action_classes": parse_action_class(args.action_class),
                "default_action_class": args.default_action_class,
                "required_approval": args.approval,
                "trust_score": args.trust_score,
            }
        ],
    }
    policy_path = Path(args.policy_out)
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(policy, indent=2, sort_keys=True).encode()
    policy_path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()

    raw_key = "exk_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    conn = await asyncpg.connect(args.database_url)
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                key_hash TEXT PRIMARY KEY,
                principal_id TEXT NOT NULL,
                tenant_ids TEXT[] NOT NULL DEFAULT '{}',
                permissions TEXT[] NOT NULL DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ,
                revoked BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
        await conn.execute(
            """
            INSERT INTO api_keys (key_hash, principal_id, tenant_ids, permissions)
            VALUES ($1,$2,$3,$4)
            ON CONFLICT (key_hash) DO NOTHING
            """,
            key_hash, args.principal_id, [args.tenant_id], args.permission,
        )
    finally:
        await conn.close()

    print("Workspace:        ", ws)
    print("Policy file:      ", policy_path)
    print("Policy SHA-256:   ", digest)
    print("Principal:        ", args.principal_id)
    print("Tenant:           ", args.tenant_id)
    print()
    print("API key (shown once — store it securely):")
    print(" ", raw_key)
    print()
    print("Configure the service with:")
    print(f"  EXOARMUR_DATABASE_URL={args.database_url}")
    print(f"  EXOARMUR_WORKSPACE_ROOT={ws}")
    print(f"  EXOARMUR_POLICY_FILE={policy_path}")
    print(f"  EXOARMUR_POLICY_SHA256={digest}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
