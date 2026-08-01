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

Freeze the verified baseline checkpoint into compact public records:

```powershell
.\scripts\12-finalize-e00.ps1
```

The finalizer refuses to continue unless verification passes. It writes:

```text
docs/results/e00-baseline-checkpoint-v1.json
docs/results/e00-baseline-checkpoint-v1.md
artifacts/canonical/e00/e00-baseline-checkpoint-v1.json
```

It also updates the generated E00 checkpoint block in `README.md`. Review the Git diff before committing.

The canonical local payload is written under:

```text
runs/e00/canonical-seed-17/
```

`runs/` is intentionally excluded from Git. Large local arrays remain local; the public checkpoint records their hashes, the run configuration, verification identity, selected metrics, publication boundary and next-stage decision.

This checkpoint is not a scientific release. The optional annotated Git tag name after the checkpoint commit is merged is:

```text
e00-baseline-checkpoint-v1
```

Do not use an `e00-complete` or scientific-result tag until the registered operator suite, nulls, confidence intervals and certification decision are finished.
