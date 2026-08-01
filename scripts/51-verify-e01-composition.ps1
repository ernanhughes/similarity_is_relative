$ErrorActionPreference = "Stop"

python -m relate.verification.e01_composition `
  --result runs/e01/composition-seed-211/composition-result-with-hash.json `
  --output runs/e01/composition-seed-211/verification.json
