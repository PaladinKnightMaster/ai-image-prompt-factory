# EXP-019 v1.2 G3 operator hardening tools

**Spec:** `EXP019-V12-G3-HARDENING-SPEC-2026-10-26.r0`  
**Policies:** `UNLOCK-AFTER-STOP=FORBID`, `CAPTURE_BLOCKED_POLICY=ABORT_ONLY`

Copy this folder into a **new** private pilot run’s `tools/` directory (do not mutate closed runs).

Core logic: `aipf.exp019_v1_2_g3_hardening` (Python).

Guided entry: `g3_operator.ps1 -WorkRoot <run> -Stage PREPARE ...`

Local tooling does **not** control ChatGPT Images.
