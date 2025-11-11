Param(
    [string]$OutDir = "docs",
    [string]$BaseName = "openapi"
)

# Ensure output directory exists
if (-not (Test-Path -Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
}

# Generate JSON and YAML using drf-spectacular management command
Write-Host "Exporting OpenAPI JSON..."
python manage.py spectacular --file "$OutDir\$BaseName.json" --format openapi-json

Write-Host "Exporting OpenAPI YAML..."
python manage.py spectacular --file "$OutDir\$BaseName.yaml" --format openapi-yaml

Write-Host "Done. Files generated:"
Get-ChildItem -Path $OutDir -Filter "$BaseName.*" | ForEach-Object { Write-Host " - $($_.FullName)" }


