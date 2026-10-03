if (-not $env:FUMIN_API_KEY) {
  throw "请先设置 `$env:FUMIN_API_KEY"
}
if (-not $env:FUMIN_MODEL) {
  throw "请先设置 `$env:FUMIN_MODEL"
}

$headers = @{
  Authorization = "Bearer $env:FUMIN_API_KEY"
  "Content-Type" = "application/json"
}

$body = @{
  model = $env:FUMIN_MODEL
  messages = @(
    @{ role = "user"; content = "只回复 OK" }
  )
  stream = $false
} | ConvertTo-Json -Depth 10

$response = Invoke-RestMethod `
  -Method Post `
  -Uri "https://fumin.ai/v1/chat/completions" `
  -Headers $headers `
  -Body $body

Write-Host "HTTP 调用成功"
Write-Host "model:" $response.model
Write-Host "reply:" $response.choices[0].message.content
