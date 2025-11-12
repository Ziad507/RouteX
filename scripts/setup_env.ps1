# PowerShell script to create .env file from env.example
# Usage: .\scripts\setup_env.ps1

$BaseDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$EnvExample = Join-Path $BaseDir "env.example"
$EnvFile = Join-Path $BaseDir ".env"

# Check if .env already exists
if (Test-Path $EnvFile) {
    $response = Read-Host "⚠️  .env file already exists. Overwrite? (y/N)"
    if ($response -ne "y") {
        Write-Host "❌ Cancelled. .env file not modified." -ForegroundColor Red
        exit
    }
}

# Check if env.example exists
if (-not (Test-Path $EnvExample)) {
    Write-Host "❌ Error: env.example not found!" -ForegroundColor Red
    exit 1
}

# Read env.example
$Content = Get-Content $EnvExample -Raw

# Generate SECRET_KEY using Python
$SecretKey = python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error generating SECRET_KEY. Make sure Django is installed." -ForegroundColor Red
    exit 1
}

# Replace SECRET_KEY placeholder
$Content = $Content -replace "DJANGO_SECRET_KEY=your-secret-key-here", "DJANGO_SECRET_KEY=$SecretKey"

# Add development-friendly defaults
$Content = $Content -replace "EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend", "EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend"

# Write .env file
$Content | Out-File -FilePath $EnvFile -Encoding utf8 -NoNewline

Write-Host "✅ .env file created successfully!" -ForegroundColor Green
Write-Host "📁 Location: $EnvFile" -ForegroundColor Cyan
Write-Host "🔑 SECRET_KEY generated: $($SecretKey.Substring(0, 20))..." -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠️  IMPORTANT:" -ForegroundColor Yellow
Write-Host "   - Never commit .env to version control"
Write-Host "   - Keep SECRET_KEY secret"
Write-Host "   - Review and update settings as needed"

