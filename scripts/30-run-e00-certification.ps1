$ErrorActionPreference = "Stop"

relate-e00-certify `
  --source runs/e00/canonical-seed-17 `
  --operators runs/e00/operator-matrix-seed-17 `
  --output runs/e00/certification-seed-17
