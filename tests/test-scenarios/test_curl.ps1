# test_curl.ps1 — Test all 6 personas against the FastAPI server
#
# Prerequisites:
#   1. FastAPI server running:  uvicorn src.referral_engine.main:app --host 0.0.0.0 --port 8000
#   2. OPENAI_API_KEY set in .env
#
# Usage:  .\tests\test-scenarios\test_curl.ps1

$ErrorActionPreference = "Continue"
$BaseUrl = "http://localhost:8000"
$DataDir = "$PSScriptRoot\data"

# Check server
Write-Host "Checking server health..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -ErrorAction Stop
    Write-Host "  Health: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: Server not running at $BaseUrl" -ForegroundColor Red
    Write-Host "  Start with: uvicorn src.referral_engine.main:app --host 0.0.0.0 --port 8000" -ForegroundColor Yellow
    exit 1
}

$personas = @(
    @{name="Power User"; file="power_user.json"},
    @{name="New User"; file="new_user.json"},
    @{name="Builder"; file="builder_user.json"},
    @{name="Amplifier"; file="amplifier_user.json"},
    @{name="Declining"; file="declining_user.json"},
    @{name="Sharer"; file="sharer_user.json"}
)

foreach ($p in $personas) {
    Write-Host "`n$('─'*60)" -ForegroundColor Cyan
    Write-Host "  Persona: $($p.name)" -ForegroundColor Cyan
    Write-Host "$('─'*60)" -ForegroundColor Cyan

    $payload = Get-Content "$DataDir\$($p.file)" -Raw

    # POST /analyze
    try {
        Write-Host "  POST /v1/referral/analyze..."
        $response = Invoke-RestMethod `
            -Uri "$BaseUrl/v1/referral/analyze" `
            -Method Post `
            -ContentType "application/json" `
            -Body $payload `
            -ErrorAction Stop
        $jobId = $response.job_id
        Write-Host "    job_id: $jobId" -ForegroundColor Green
        Write-Host "    status: $($response.status)" -ForegroundColor Green
        Write-Host "    estimated: $($response.estimated_time)"
    } catch {
        Write-Host "    FAILED: $_" -ForegroundColor Red
        continue
    }

    # Poll GET /results (wait up to 60s)
    $maxRetries = 12
    $retry = 0
    do {
        Start-Sleep -Seconds 5
        try {
            $result = Invoke-RestMethod `
                -Uri "$BaseUrl/v1/referral/results/$jobId" `
                -Method Get `
                -ErrorAction Stop

            $doneStatuses = @("completed", "held", "failed")
            if ($result.status -in $doneStatuses) {
                Write-Host "    Result: status=$($result.status) | reach=$($result.reach_score) | advocacy=$($result.advocacy_score) | tier=$($result.tier) | should_ask=$($result.should_ask) | urgency=$($result.urgency)"
                if ($result.error) {
                    Write-Host "    Error: $($result.error)" -ForegroundColor Red
                }
                break
            }
            Write-Host "    Poll #$retry: status=$($result.status)..."
        } catch {
            Write-Host "    Poll #$retry: no result yet..."
        }
        $retry++
    } while ($retry -lt $maxRetries)

    if ($retry -ge $maxRetries) {
        Write-Host "    TIMEOUT: Job did not complete in 60s" -ForegroundColor Yellow
    }
}

Write-Host "`n$('─'*60)" -ForegroundColor Cyan
Write-Host "  All personas tested." -ForegroundColor Green
Write-Host "$('─'*60)" -ForegroundColor Cyan
