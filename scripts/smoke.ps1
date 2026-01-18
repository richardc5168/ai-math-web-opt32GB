param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [int]$TopicKey = 2
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Stop"

Write-Host "== Smoke: bootstrap ==" -ForegroundColor Cyan
$boot = Invoke-RestMethod -Method Post "$BaseUrl/admin/bootstrap?name=Smoke" 
$apiKey = $boot.api_key

$headers = @{ "X-API-Key" = $apiKey }

Write-Host "== Smoke: health ==" -ForegroundColor Cyan
$health = Invoke-RestMethod -Headers $headers "$BaseUrl/health"
Write-Host ("ok=" + $health.ok + " ts=" + $health.ts)

Write-Host "== Smoke: students ==" -ForegroundColor Cyan
$students = Invoke-RestMethod -Headers $headers "$BaseUrl/v1/students"
$studentId = $students.students[0].id
Write-Host ("student_id=" + $studentId)

Write-Host "== Smoke: next question ==" -ForegroundColor Cyan
$next = Invoke-RestMethod -Method Post -Headers $headers "$BaseUrl/v1/questions/next?student_id=$studentId&topic_key=$TopicKey"
$questionId = $next.question_id
Write-Host ("question_id=" + $questionId + " topic=" + $next.topic)

Write-Host "== Smoke: hint level1 ==" -ForegroundColor Cyan
$hintBody = @{ question_id = $questionId; level = 1 } | ConvertTo-Json
$hint = Invoke-RestMethod -Method Post -Headers $headers -ContentType "application/json" -Body $hintBody "$BaseUrl/v1/questions/hint"
Write-Host ("hint=" + $hint.hint)

Write-Host "== Smoke: submit wrong answer ==" -ForegroundColor Cyan
$submitBody = @{ student_id = $studentId; question_id = $questionId; user_answer = "1 1 1"; time_spent_sec = 15; hint_level_used = 1 } | ConvertTo-Json
$submit = Invoke-RestMethod -Method Post -Headers $headers -ContentType "application/json" -Body $submitBody "$BaseUrl/v1/answers/submit"
Write-Host ("is_correct=" + $submit.is_correct + " error_tag=" + $submit.error_tag)

Write-Host "== Smoke: parent weekly ==" -ForegroundColor Cyan
$weekly = Invoke-RestMethod -Headers $headers "$BaseUrl/v1/reports/parent_weekly?student_id=$studentId&days=7"

Write-Host "\nKPI:" -ForegroundColor Yellow
$weekly.kpis | ConvertTo-Json -Depth 5
Write-Host "\nweakness_top3:" -ForegroundColor Yellow
$weekly.weakness_top3 | ConvertTo-Json -Depth 5
Write-Host "\nnext_week_plan:" -ForegroundColor Yellow
$weekly.next_week_plan | ConvertTo-Json -Depth 5

Write-Host "\nSMOKE OK" -ForegroundColor Green
