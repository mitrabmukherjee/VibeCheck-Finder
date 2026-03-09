# Test Sentence-BERT semantic search with various query types

$queries = @(
    "a little girl",
    "romantic comedy",
    "scary horror movie",
    "space adventure",
    "something funny to watch",
    "high school drama",
    "true crime documentary",
    "finding yourself",
    "young child",
    "frightening film"
)

Write-Host "`n🎬 SENTENCE-BERT SEMANTIC SEARCH TEST" -ForegroundColor Cyan
Write-Host "=" * 80
Write-Host "Testing various query types to evaluate semantic understanding...`n"

foreach ($query in $queries) {
    Write-Host "`n$('='*80)" -ForegroundColor Yellow
    Write-Host "QUERY: '$query'" -ForegroundColor Yellow
    Write-Host "$('='*80)" -ForegroundColor Yellow
    
    $body = @{
        query = $query
        top_k = 5
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/recommend" -Method POST -Body $body -ContentType "application/json"
        
        Write-Host "✅ Found $($response.results.Count) results in $([math]::Round($response.query_time_ms, 2))ms`n" -ForegroundColor Green
        
        $i = 1
        foreach ($result in $response.results) {
            $score = [math]::Round($result.similarity_score, 3)
            $title = $result.title
            $type = $result.media_type
            $desc = if ($result.description.Length -gt 100) { $result.description.Substring(0, 100) + "..." } else { $result.description }
            
            Write-Host "$i. [$score] $title ($type)" -ForegroundColor White
            Write-Host "   $desc`n" -ForegroundColor Gray
            $i++
        }
    }
    catch {
        Write-Host "❌ ERROR: $_" -ForegroundColor Red
    }
    
    Start-Sleep -Milliseconds 200
}

Write-Host "`n$('='*80)" -ForegroundColor Cyan
Write-Host "✅ TEST COMPLETE" -ForegroundColor Green
Write-Host "$('='*80)" -ForegroundColor Cyan
