# Federation Identity Handshake Envelope (Schema-First)

Purpose: define a deterministic envelope for establishing trust between a joining cell and a federation controller.

## Fields
- `schema`: identifier for versioning (string)
- `federation_id`: unique federation identifier (string)
- `cell_id`: unique cell identifier (string)
- `nonce`: cryptographic nonce provided by controller (string)
- `timestamp`: ISO-8601 UTC timestamp of message creation (string)
- `capabilities`: list of capability codes requested/advertised by the cell (array[string])
- `signatures`: list of detached signatures (array[object])
  - `issuer`: signer identity (string)
  - `algo`: signature algorithm (string)
  - `signature`: base64 signature (string)

## JSON Example
```json
{
  "schema": "exoarmur.v2.federation_handshake.v1",
  "federation_id": "fed-phase2-alpha",
  "cell_id": "cell-nyc-001",
  "nonce": "3f8ad4ac-5e8a-4b8c-8f9a-52a0f6f9c123",
  "timestamp": "2026-02-25T10:00:00Z",
  "capabilities": ["pod", "bft", "counterfactual"],
  "signatures": [
    {
      "issuer": "cell-nyc-001",
      "algo": "ed25519",
      "signature": "MEYCIQDOExampleSigBase64=="
    },
    {
      "issuer": "federation-controller",
      "algo": "ed25519",
      "signature": "MEQCIEControllerSigBase64=="
    }
  ]
}
```
