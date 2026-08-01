# PowerShell Workflow

The scripts expose the research chain as numbered, independently runnable stages.

## Setup

```powershell
.\scripts\00-setup.ps1
```

## E00 synthetic recoverability

Generate the canonical local artifact:

```powershell
.\scripts\10-run-e00.ps1
```

Verify it independently:

```powershell
.\scripts\11-verify-e00.ps1
```

The canonical local payload is written under:

```text
runs/e00/canonical-seed-17/
```

`runs/` is intentionally excluded from Git. After the complete E00 operator suite and confirmatory seed contract are implemented, a compact verified record will be copied to `docs/results/` and the canonical identities to `artifacts/canonical/e00/`.
