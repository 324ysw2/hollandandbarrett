$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

docker compose -f docker-compose.elasticsearch.yml up -d

Write-Host "Waiting for Elasticsearch http://localhost:9200 ..."
for ($i = 0; $i -lt 60; $i++) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:9200" -TimeoutSec 2
        if ($response.cluster_name) {
            Write-Host "Elasticsearch is ready: $($response.cluster_name)"
            exit 0
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}

throw "Elasticsearch did not become ready in time."
