$ErrorActionPreference = "Stop"

python -m relate.verification.e00_multiseed `
  --result runs/e00/multiseed/aggregate/multiseed-result.json `
  --output runs/e00/multiseed/aggregate/verification.json
