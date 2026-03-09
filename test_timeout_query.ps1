# Test the query that previously timed out
Write-Host "Testing query that previously timed out..." -ForegroundColor Cyan
Write-Host ""

$queries = @(
    "a gritty crime drama based in nyc",
    "romantic comedy with happy ending",
    "psychological thriller with plot twists",
    "family friendly animated movie",
    "documentary about nature and wildlife"
)

foreach ($query in $queries) {
    Write-Host "Query: '$query'" -ForegroundColor Yellow
    
    $body = @{
        query = $query
        top_k = 5
    } | ConvertTo-Json
    
    try {
        $start = Get-Date
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/recommend" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 15
        $elapsed = (Get-Date) - $start
        
        Write-Host "  Response time: $($elapsed.TotalMilliseconds)ms" -ForegroundColor Green
        Write-Host "  Results: $($response.results.Count)" -ForegroundColor Green
        
        if ($response.results.Count -gt 0) {
            Write-Host "  Top result: $($response.results[0].title) (score: $([math]::Round($response.results[0].similarity_score, 3)))" -ForegroundColor White
        }
    }
    catch {
        Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "All tests completed!" -ForegroundColor Green
