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

For additional principals that must NOT get their own policy rule
(e.g. a separate approver), add --credentials-only and omit the
policy/workspace/trust arguments — only the api_keys row is created and
any existing policy file is left untouched.
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
    ap.add_argument("--workspace")
    ap.add_argument("--policy-out")
    ap.add_argument("--principal-id", required=True)
    ap.add_argument("--tenant-id", required=True)
    ap.add_argument("--operation", action="append")
    ap.add_argument("--action-class", action="append", default=[])
    ap.add_argument("--default-action-class", default=None)
    ap.add_argument("--approval", default="human",
                    choices=["none", "quorum", "human"])
    ap.add_argument("--trust-score", type=float)
    ap.add_argument("--permission", action="append", default=[])
    ap.add_argument("--key-id", default=None)
    ap.add_argument("--credentials-only", action="store_true",
                    help="Only create the api_keys row; do not write a "
                         "policy file or require policy arguments. Use this "
                         "for additional principals (e.g. approvers) so an "
                         "existing operator policy is preserved.")
    args = ap.parse_args()

    digest = None
    policy_path = None
    if not args.credentials_only:
        missing = [n for n in ("workspace", "policy_out", "trust_score")
                   if getattr(args, n) is None]
        missing += ["--operation"] if not args.operation else []
        if missing:
            ap.error("policy bootstrap requires: " + ", ".join(missing)
                     + " (or pass --credentials-only for key-only bootstrap)")

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
        if policy_path.exists() and policy_path.read_bytes() != raw:
            raise SystemExit(
                f"Refusing to overwrite existing policy file {policy_path}. "
                "Choose a different --policy-out or remove it deliberately."
            )
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

    print("Principal:        ", args.principal_id)
    print("Tenant:           ", args.tenant_id)
    print()
    print("API key (shown once — store it securely):")
    print(" ", raw_key)
    print()
    if args.credentials_only:
        print("Credential-only bootstrap: no policy file written.")
        print("Keep using the EXISTING policy file/digest for the service.")
    else:
        print("Workspace:        ", ws)
        print("Policy file:      ", policy_path)
        print("Policy SHA-256:   ", digest)
        print()
        print("Configure the service with:")
        print(f"  EXOARMUR_DATABASE_URL={args.database_url}")
        print(f"  EXOARMUR_WORKSPACE_ROOT={ws}")
        print(f"  EXOARMUR_POLICY_FILE={policy_path}")
        print(f"  EXOARMUR_POLICY_SHA256={digest}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
