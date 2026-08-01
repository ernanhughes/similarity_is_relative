param(
    [string]$RunDirectory = "runs/e00/canonical-seed-17",
    [switch]$NoReadmeUpdate
)

$ErrorActionPreference = "Stop"

$arguments = @(
    "-m", "relate.publication.e00",
    "--run-directory", $RunDirectory,
    "--repository-root", "."
)

if ($NoReadmeUpdate) {
    $arguments += "--no-readme-update"
}

python @arguments

Write-Host ""
Write-Host "E00 baseline checkpoint generated. Review the Git diff before committing:"
Write-Host "  git diff"
Write-Host "  git status --short"
Write-Host ""
Write-Host "Do not create a scientific release tag yet. After merge, an optional annotated"
Write-Host "checkpoint tag may be created as: e00-baseline-checkpoint-v1"
