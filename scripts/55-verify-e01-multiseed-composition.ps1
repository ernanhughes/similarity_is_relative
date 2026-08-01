$ErrorActionPreference = "Stop"

python -m relate.verification.e01_multiseed_composition `
  --result runs/e01/multiseed-composition/multiseed-composition-result-with-hash.json `
  --output runs/e01/multiseed-composition/verification.json
