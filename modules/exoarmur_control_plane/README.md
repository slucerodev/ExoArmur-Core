# Control Plane (ExoArmur Control Plane)

Control Plane defines the Stage 1 contract surface for **Signed Operator Intent**
(SOI), arbitration records, and emergency kill authority semantics.

- **Stage**: V2 Stage 1 (contracts only, inert).
- **Runtime**: No executable code or tests in this module.
- **Boundary**: Core remains independent; Control Plane is exportable and optional.

Contracts are defined in `contracts/soi_v1.md`, `contracts/arbitration_v1.md`, and
`contracts/kill_authority_v1.md` with supporting context in
`docs/SOI_OVERVIEW.md`.
