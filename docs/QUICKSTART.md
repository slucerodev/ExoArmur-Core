# ExoArmur 60-Second Replay Quickstart

This quickstart shows deterministic replay using real AuditRecordV1 schema.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install .
```

## Run the replay example

```bash
python examples/quickstart_replay.py
```

Expected output (result may vary if you change the record):

```
Replay result: success
Failures: none
Warnings: none
```

## What this proves
- ReplayEngine reads canonical AuditRecordV1 entries and deterministically reconstructs outcomes.
- No external services are contacted; all data is local and canonicalized.

## What’s next
- Additional modules (federation, control plane, threat classification) exist but are phase/feature gated.
- Keep using ReplayEngine for offline verification until gates are opened.
