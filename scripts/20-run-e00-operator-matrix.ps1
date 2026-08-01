param(
    [string]$SourceDirectory = "runs/e00/canonical-seed-17",
    [string]$OutputDirectory = "runs/e00/operator-matrix-seed-17"
)

$ErrorActionPreference = "Stop"

python -m relate.experiments.e00_operator_matrix `
    --source $SourceDirectory `
    --output $OutputDirectory
