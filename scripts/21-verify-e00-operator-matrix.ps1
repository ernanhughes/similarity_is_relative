param(
    [string]$SourceDirectory = "runs/e00/canonical-seed-17",
    [string]$OperatorDirectory = "runs/e00/operator-matrix-seed-17"
)

$ErrorActionPreference = "Stop"

python -m relate.verification.e00_operator_matrix `
    --source $SourceDirectory `
    --operators $OperatorDirectory `
    --output "$OperatorDirectory/verification.json"
