#!/usr/bin/env python3
"""
Bootstrap an operator API key for ExoArmur governed endpoints.

Generates a random API key, stores ONLY its SHA-256 hash in the key store
file referenced by EXOARMUR_API_KEY_STORE, and prints the raw key exactly
once. The raw key is never written to the store file or logs — store it in
your secret manager and share it with the principal out-of-band.

Usage:
    python examples/bootstrap_api_key.py \
        --key-id pilot-key-1 \
        --principal-id agent-001 \
        --tenant-id tenant-1 \
        --permission execute:A0 --permission execute:A1 \
        --permission approval:request --permission approval:grant \
        --permission approval:deny --permission status:view

The store file defaults to $EXOARMUR_API_KEY_STORE or ./api_keys.json.
Existing records are preserved; re-running adds another key.
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from exoarmur.auth.auth_service import (
        APIKeyStore,
        Permission,
        import_key_store_records,
        export_key_store_records,
    )
except ImportError:  # pragma: no cover - local repo checkout
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.append(str(repo_root / "src"))
    sys.path.append(str(repo_root))
    from exoarmur.auth.auth_service import (  # type: ignore
        APIKeyStore,
        Permission,
        import_key_store_records,
        export_key_store_records,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-id", required=True, help="Stable identifier for this key")
    parser.add_argument("--principal-id", required=True, help="Principal this key authenticates as")
    parser.add_argument("--tenant-id", action="append", required=True,
                        help="Tenant the key may access (repeatable)")
    parser.add_argument("--permission", action="append", required=True,
                        help=f"Permission to grant (repeatable); one of: "
                             f"{', '.join(p.value for p in Permission)}")
    parser.add_argument("--expires-at", default=None,
                        help="Optional ISO-8601 expiry timestamp")
    parser.add_argument("--description", default=None)
    parser.add_argument("--store", default=None,
                        help="Key store path (default: $EXOARMUR_API_KEY_STORE or ./api_keys.json)")
    args = parser.parse_args()

    store_path = Path(args.store or os.environ.get("EXOARMUR_API_KEY_STORE") or "api_keys.json")

    permissions = []
    for raw in args.permission:
        try:
            permissions.append(Permission(raw))
        except ValueError:
            parser.error(f"Unknown permission {raw!r}")

    expires_at = None
    if args.expires_at:
        from datetime import datetime
        try:
            expires_at = datetime.fromisoformat(args.expires_at)
        except ValueError:
            parser.error(f"Invalid --expires-at {args.expires_at!r}")

    store = APIKeyStore()
    if store_path.exists():
        try:
            records = json.loads(store_path.read_text(encoding="utf-8"))
            import_key_store_records(store, records)
        except (OSError, ValueError) as exc:
            print(f"error: cannot load existing key store {store_path}: {exc}", file=sys.stderr)
            return 1

    if args.key_id in store.keys:
        print(f"error: key_id {args.key_id!r} already exists; choose another or revoke it first",
              file=sys.stderr)
        return 1

    actual_key = store.create_key(
        key_id=args.key_id,
        tenant_ids=args.tenant_id,
        permissions=permissions,
        principal_id=args.principal_id,
        expires_at=expires_at,
        description=args.description,
    )

    store_path.write_text(
        json.dumps(export_key_store_records(store), indent=2) + "\n",
        encoding="utf-8",
    )

    print("=" * 72)
    print("API key created. This is the ONLY time the raw key is shown.")
    print("=" * 72)
    print(f"key_id:       {args.key_id}")
    print(f"principal_id: {args.principal_id}")
    print(f"tenants:      {', '.join(args.tenant_id)}")
    print(f"permissions:  {', '.join(sorted(p.value for p in permissions))}")
    print(f"store file:   {store_path}")
    print()
    print("RAW API KEY (store in your secret manager, never commit):")
    print(actual_key)
    print()
    print("Send it as the 'X-API-Key' header on governed endpoints.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
