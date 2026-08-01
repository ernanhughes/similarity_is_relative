$ErrorActionPreference = "Stop"

python -m relate.verification.e01_relational_conjunction `
  --result runs/e01/relational-conjunction-seed-307/relational-conjunction-result-with-hash.json `
  --output runs/e01/relational-conjunction-seed-307/verification.json
