$ErrorActionPreference = "Stop"

python -m relate.verification.e00_certification `
  --source runs/e00/canonical-seed-17 `
  --operators runs/e00/operator-matrix-seed-17 `
  --certification runs/e00/certification-seed-17 `
  --output runs/e00/certification-seed-17/verification.json
