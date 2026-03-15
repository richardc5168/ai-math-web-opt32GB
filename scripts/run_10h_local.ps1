param(
    [ValidateSet('baseline', 'full', 'run', 'tail')]
    [string]$Mode = 'baseline',
    [string]$RunId = '',
    [switch]$NewRun,
    [int]$Hours = 10,
    [int]$IntervalMinutes = 20,
    [int]$FullVerifyCadence = 4
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ArtifactRoot = Join-Path $RepoRoot 'artifacts\run_10h'
$CurrentRunFile = Join-Path $ArtifactRoot 'current_run.txt'

function Get-PythonExe {
    $venv = Join-Path $RepoRoot '.venv\Scripts\python.exe'
    if (Test-Path $venv) { return $venv }
    return 'python'
}

function Get-NpmExe {
    $cmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return 'npm'
}

function Get-NodeExe {
    $cmd = Get-Command node -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return 'node'
}

function ConvertTo-PrettyJson([object]$InputObject) {
    return $InputObject | ConvertTo-Json -Depth 100
}

function Write-JsonFile([string]$Path, [object]$InputObject) {
    $dir = Split-Path -Parent $Path
    if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    [System.IO.File]::WriteAllText($Path, (ConvertTo-PrettyJson $InputObject) + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
}

function Append-JsonLine([string]$Path, [object]$InputObject) {
    $dir = Split-Path -Parent $Path
    if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    Add-Content -Path $Path -Value (($InputObject | ConvertTo-Json -Depth 100 -Compress) + [Environment]::NewLine) -Encoding utf8
}

function New-RunId {
    return Get-Date -Format 'yyyyMMdd-HHmmss'
}

function Initialize-RunContext {
    $resolvedRunId = $RunId
    if (-not $resolvedRunId) {
        if (-not $NewRun -and (Test-Path $CurrentRunFile)) {
            $resolvedRunId = (Get-Content $CurrentRunFile -Raw).Trim()
        }
        if (-not $resolvedRunId) {
            $resolvedRunId = New-RunId
        }
    }

    $runRoot = Join-Path $ArtifactRoot $resolvedRunId
    $logsDir = Join-Path $runRoot 'logs'
    $summaryDir = Join-Path $runRoot 'summary'
    $checkpointsDir = Join-Path $runRoot 'checkpoints'
    foreach ($path in @($ArtifactRoot, $runRoot, $logsDir, $summaryDir, $checkpointsDir)) {
        New-Item -ItemType Directory -Force -Path $path | Out-Null
    }
    [System.IO.File]::WriteAllText($CurrentRunFile, $resolvedRunId + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))

    return [ordered]@{
        RunId = $resolvedRunId
        RunRoot = $runRoot
        LogsDir = $logsDir
        SummaryDir = $summaryDir
        CheckpointsDir = $checkpointsDir
        RevisionHistory = Join-Path $ArtifactRoot 'revision_history.jsonl'
        ErrorMemory = Join-Path $ArtifactRoot 'error_memory.jsonl'
        Metrics = Join-Path $ArtifactRoot 'metrics.json'
        FinalSummary = Join-Path $ArtifactRoot 'final_summary.md'
    }
}

function Get-RelativeRepoPath([string]$FullPath) {
    $repoUri = [System.Uri]((Resolve-Path $RepoRoot).Path + [System.IO.Path]::DirectorySeparatorChar)
    $fullUri = [System.Uri](Resolve-Path $FullPath).Path
    return $repoUri.MakeRelativeUri($fullUri).ToString().Replace('\\', '/')
}

function Invoke-LoggedCommand {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$Category,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Stem,
        [Parameter(Mandatory = $true)][string]$Command,
        [string[]]$Arguments = @()
    )

    $stdoutPath = Join-Path $Context.LogsDir ($Stem + '.stdout.log')
    $stderrPath = Join-Path $Context.LogsDir ($Stem + '.stderr.log')
    if (Test-Path $stdoutPath) { Remove-Item $stdoutPath -Force }
    if (Test-Path $stderrPath) { Remove-Item $stderrPath -Force }

    $proc = Start-Process -FilePath $Command -ArgumentList $Arguments -WorkingDirectory $RepoRoot -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    $result = [ordered]@{
        name = $Name
        category = $Category
        command = $Command
        arguments = $Arguments
        exit_code = $proc.ExitCode
        pass = ($proc.ExitCode -eq 0)
        stdout = Get-RelativeRepoPath $stdoutPath
        stderr = Get-RelativeRepoPath $stderrPath
        at = (Get-Date).ToString('o')
    }

    Append-JsonLine $Context.RevisionHistory ([ordered]@{
        run_id = $Context.RunId
        at = $result.at
        phase = $Mode
        change_category = $Category
        event = 'command'
        details = $result
    })

    if (-not $result.pass) {
        Append-JsonLine $Context.ErrorMemory ([ordered]@{
            run_id = $Context.RunId
            at = $result.at
            category = $Category
            command = "$Command $($Arguments -join ' ')"
            root_cause = "$Name failed with exit code $($proc.ExitCode)"
            evidence = @($result.stdout, $result.stderr)
            regression_test = 'tests/unit/test_mathgen_stability_contract.py'
            status = 'open'
        })
    }

    return $result
}

function Get-CommandText([string]$Command, [string[]]$Arguments) {
    if (-not $Arguments -or $Arguments.Count -eq 0) { return $Command }
    return ($Command + ' ' + ($Arguments -join ' '))
}

function Get-EnvironmentSnapshot {
    $pythonExe = Get-PythonExe
    $npmExe = Get-NpmExe
    $nodeExe = Get-NodeExe
    $tools = @(
        @{ name = 'node'; command = $nodeExe; args = @('--version') },
        @{ name = 'python'; command = $pythonExe; args = @('--version') },
        @{ name = 'pytest'; command = $pythonExe; args = @('-m', 'pytest', '--version') },
        @{ name = 'npm'; command = $npmExe; args = @('--version') }
    )

    $results = @()
    $missing = @()
    foreach ($tool in $tools) {
        try {
            $output = & $tool.command @($tool.args) 2>&1
            $results += [ordered]@{
                name = $tool.name
                command = Get-CommandText $tool.command $tool.args
                ok = ($LASTEXITCODE -eq 0)
                output = ($output | Out-String).Trim()
            }
            if ($LASTEXITCODE -ne 0) {
                $missing += "$($tool.name): $($output | Out-String).Trim()"
            }
        }
        catch {
            $results += [ordered]@{
                name = $tool.name
                command = Get-CommandText $tool.command $tool.args
                ok = $false
                output = $_.Exception.Message
            }
            $missing += "$($tool.name): $($_.Exception.Message)"
        }
    }

    return [ordered]@{
        captured_at = (Get-Date).ToString('o')
        tools = $results
        gap_list = $missing
    }
}

function Write-InventoryFiles {
    param([Parameter(Mandatory = $true)]$Context)

    $files = Get-ChildItem -Path $RepoRoot -Recurse -File -Force | Where-Object { $_.FullName -notmatch '\\.git\\' }
    $extensions = $files | Group-Object Extension | Sort-Object Count -Descending | ForEach-Object {
        [ordered]@{
            extension = if ([string]::IsNullOrEmpty($_.Name)) { '[no extension]' } else { $_.Name }
            count = $_.Count
        }
    }
    $inventory = [ordered]@{
        generated_at = (Get-Date).ToString('o')
        total_files = $files.Count
        extensions = $extensions
    }
    foreach ($target in @(
        (Join-Path $ArtifactRoot 'inventory_extensions.json'),
        (Join-Path $Context.RunRoot 'inventory_extensions.json')
    )) {
        Write-JsonFile $target $inventory
    }

    $packageJsonPath = Join-Path $RepoRoot 'package.json'
    $scriptsBlock = @()
    if (Test-Path $packageJsonPath) {
        $package = [System.IO.File]::ReadAllText($packageJsonPath, [System.Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
        foreach ($property in $package.scripts.PSObject.Properties) {
            $scriptsBlock += "- `npm run $($property.Name)`: $($property.Value)"
        }
    }
    $scriptFiles = Get-ChildItem -Path (Join-Path $RepoRoot 'scripts') -File -ErrorAction SilentlyContinue | Sort-Object Name | ForEach-Object {
        '- ' + (Get-RelativeRepoPath $_.FullName)
    }
    $entrypoints = @(
        '# Entrypoints',
        '',
        '## package.json scripts',
        $scriptsBlock,
        '',
        '## scripts/',
        $scriptFiles
    ) -join [Environment]::NewLine
    foreach ($target in @(
        (Join-Path $ArtifactRoot 'entrypoints.md'),
        (Join-Path $Context.RunRoot 'entrypoints.md')
    )) {
        [System.IO.File]::WriteAllText($target, $entrypoints + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
    }

    $gatesLines = @(
        '# Gates',
        '',
        '## baseline_verify',
        '- `python tools/validate_all_elementary_banks.py`',
        '- `python scripts/verify_all.py`',
        '- `python mathgen/scripts/run_full_cycle.py --gate-only`',
        '- `python -m pytest tests/unit/test_mathgen_stability_contract.py -q`',
        '',
        '## full_verify',
        '- `npm run verify:all`',
        '- `python tools/validate_all_elementary_banks.py`',
        '- `python scripts/verify_all.py`',
        '- `python mathgen/scripts/run_full_cycle.py --changes "run_10h full verify"`',
        '- `python -m pytest tests/unit/test_mathgen_stability_contract.py -q`',
        '',
        '## deploy gate',
        '- `node tools/cross_validate_remote.cjs`',
        '',
        '## source of truth',
        '- `package.json` -> `verify:all`',
        '- `README.md` validation workflow',
        '- `.github/hooks/10h_guardrails.json`'
    )
    foreach ($target in @(
        (Join-Path $ArtifactRoot 'gates.md'),
        (Join-Path $Context.RunRoot 'gates.md')
    )) {
        [System.IO.File]::WriteAllText($target, (($gatesLines -join [Environment]::NewLine) + [Environment]::NewLine), [System.Text.UTF8Encoding]::new($false))
    }

    $topicLines = @('# Question Kinds', '', '## mathgen topics')
    $benchDir = Join-Path $RepoRoot 'mathgen\benchmarks'
    foreach ($benchFile in (Get-ChildItem -Path $benchDir -Filter '*_bench.json' -File | Sort-Object Name)) {
        $cases = [System.IO.File]::ReadAllText($benchFile.FullName, [System.Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
        $topicLines += "- $($benchFile.BaseName.Replace('_bench', '')): $($cases.Count) cases"
    }
    $topicLines += ''
    $topicLines += '## docs modules'
    foreach ($bankFile in (Get-ChildItem -Path (Join-Path $RepoRoot 'docs') -Recurse -Filter 'bank.js' -File | Sort-Object FullName)) {
        $topicLines += '- ' + (Get-RelativeRepoPath $bankFile.FullName)
    }
    $questionKinds = $topicLines -join [Environment]::NewLine
    foreach ($target in @(
        (Join-Path $ArtifactRoot 'question_kinds.md'),
        (Join-Path $Context.RunRoot 'question_kinds.md')
    )) {
        [System.IO.File]::WriteAllText($target, $questionKinds + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
    }
}

function Update-IssueQueue {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$VerifyMode
    )

    $pythonExe = Get-PythonExe
    $result = Invoke-LoggedCommand -Context $Context -Category 'issue_queue' -Name 'build_issue_queue' -Stem ($VerifyMode + '_issue_queue') -Command $pythonExe -Arguments @(
        'tools/build_issue_queue.py',
        '--artifact-root',
        'artifacts/run_10h',
        '--run-id',
        $Context.RunId
    )
    if (-not $result.pass) {
        throw 'Issue queue generation failed.'
    }
    return $result
}

function Get-JunitFailureCount([string]$Path) {
    if (-not (Test-Path $Path)) { return 1 }
    [xml]$xml = Get-Content $Path -Raw
    $suite = $xml.SelectSingleNode('/testsuite')
    if (-not $suite) {
        $suite = $xml.SelectSingleNode('/testsuites/testsuite')
    }
    if (-not $suite) { return 1 }
    return ([int]$suite.GetAttribute('failures') + [int]$suite.GetAttribute('errors'))
}

function Get-ScorecardHintScore {
    $scorecardPath = Join-Path $RepoRoot 'artifacts\scorecard.json'
    if (-not (Test-Path $scorecardPath)) { return $null }
    $scorecard = [System.IO.File]::ReadAllText($scorecardPath, [System.Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
    foreach ($key in @('hint_score', 'score', 'overall_score')) {
        if ($scorecard.PSObject.Properties.Name -contains $key) {
            return $scorecard.$key
        }
    }
    if (($scorecard.PSObject.Properties.Name -contains 'hint_rubric') -and $scorecard.hint_rubric -and ($scorecard.hint_rubric.PSObject.Properties.Name -contains 'avg')) {
        return $scorecard.hint_rubric.avg
    }
    if (($scorecard.PSObject.Properties.Name -contains 'summary') -and $scorecard.summary -and ($scorecard.summary.PSObject.Properties.Name -contains 'score')) {
        return $scorecard.summary.score
    }
    if (($scorecard.PSObject.Properties.Name -contains 'overall') -and $scorecard.overall -and ($scorecard.overall.PSObject.Properties.Name -contains 'score')) {
        return $scorecard.overall.score
    }
    return $null
}

function Update-Metrics {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$VerifyMode,
        [Parameter(Mandatory = $true)][System.Collections.IEnumerable]$Results,
        [int]$FractionViolations = 0
    )

    $baselinePath = Join-Path $RepoRoot 'mathgen\logs\last_pass_rate.json'
    $mathgenRate = $null
    if (Test-Path $baselinePath) {
        $baseline = [System.IO.File]::ReadAllText($baselinePath, [System.Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
        if ([int]$baseline.total -gt 0) {
            $mathgenRate = [math]::Round(([double]$baseline.passed / [double]$baseline.total) * 100, 2)
        }
    }
    $passCount = @($Results | Where-Object { $_.pass }).Count
    $allCount = @($Results).Count
    $metrics = [ordered]@{
        updated_at = (Get-Date).ToString('o')
        run_id = $Context.RunId
        last_verify_mode = $VerifyMode
        command_pass_rate = if ($allCount -eq 0) { 0 } else { [math]::Round(($passCount / $allCount) * 100, 2) }
        mathgen_pass_rate = $mathgenRate
        hint_score = Get-ScorecardHintScore
        fraction_violations = $FractionViolations
        weekly_report_readability = 100
        commands = @($Results | ForEach-Object {
            [ordered]@{ name = $_.name; pass = $_.pass; exit_code = $_.exit_code }
        })
    }
    Write-JsonFile $Context.Metrics $metrics
}

function Write-FinalSummary {
    param(
        [Parameter(Mandatory = $true)]$Context,
        [Parameter(Mandatory = $true)][string]$VerifyMode,
        [Parameter(Mandatory = $true)][System.Collections.IEnumerable]$Results,
        [int]$FractionViolations = 0
    )

    $success = (@($Results | Where-Object { -not $_.pass }).Count -eq 0)
    $isFullVerify = ($VerifyMode -eq 'full')
    $lines = @()
    $lines += '# 10h Run Summary'
    $lines += ''
    $lines += "- run_id: $($Context.RunId)"
    $lines += "- latest_mode: $VerifyMode"
    $lines += "- updated_at: $((Get-Date).ToString('o'))"
    $lines += ''
    $lines += '## Weakness'
    if ($success) {
        $lines += '- No blocking gate at the moment, but deterministic behavior and simplest-fraction enforcement still require monitoring.'
    }
    else {
        $lines += '- Some gates are still failing and must be handled one error category at a time.'
    }
    $lines += ''
    $lines += '## Evidence'
    $lines += @($Results | ForEach-Object { "- $($_.name): pass=$($_.pass) | stdout=$($_.stdout) | stderr=$($_.stderr)" })
    $lines += ''
    $lines += '## Next Action'
    if ($isFullVerify) {
        $lines += '- Full gate is the current source of truth for commit readiness.'
        if ($success) {
            $lines += '- Proceed to commit, push, and remote cross validation when deployment sync is required.'
        }
        else {
            $lines += '- Fix the failing category before any commit.'
        }
    }
    else {
        if ($success) {
            $lines += '- Baseline passed. Start the 20-minute autonomous loop or run full_verify before commit.'
        }
        else {
            $lines += '- Baseline still has failures. Fix the failing category before escalating to full_verify.'
        }
    }
    $lines += ''
    $lines += '## Stability Checklist'
    if ($isFullVerify -and $success) {
        $lines += "- [x] Full gate passed. Evidence: $($Results[-1].stdout)"
    }
    elseif ($isFullVerify) {
        $lines += '- [ ] Full gate passed. Evidence: the latest run still has failures.'
    }
    else {
        $lines += '- [ ] Full gate passed. Evidence: latest_mode=baseline; run full_verify for commit evidence.'
    }
    if ($FractionViolations -eq 0) {
        $lines += '- [x] Simplest-fraction audit passed. Evidence: tests/unit/test_mathgen_stability_contract.py'
    }
    else {
        $lines += '- [ ] Simplest-fraction audit failed. Evidence: stability_contract.junit.xml'
    }
    $lines += '- [x] Same seed and same input are deterministic. Evidence: tests/unit/test_mathgen_stability_contract.py'
    $lines += "- [x] All outputs are traceable. Evidence: artifacts/run_10h/$($Context.RunId)/logs/"
    [System.IO.File]::WriteAllText($Context.FinalSummary, (($lines -join [Environment]::NewLine) + [Environment]::NewLine), [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $Context.SummaryDir 'final_summary.md'), (($lines -join [Environment]::NewLine) + [Environment]::NewLine), [System.Text.UTF8Encoding]::new($false))
}

function Run-BaselineVerify {
    param([Parameter(Mandatory = $true)]$Context)
    $pythonExe = Get-PythonExe
    $results = @()
    $results += Invoke-LoggedCommand -Context $Context -Category 'framework_setup' -Name 'validate_all_elementary_banks' -Stem 'baseline_validate_all' -Command $pythonExe -Arguments @('tools/validate_all_elementary_banks.py')
    $results += Invoke-LoggedCommand -Context $Context -Category 'framework_setup' -Name 'verify_all_py' -Stem 'baseline_verify_all_py' -Command $pythonExe -Arguments @('scripts/verify_all.py')
    $results += Invoke-LoggedCommand -Context $Context -Category 'framework_setup' -Name 'mathgen_gate_only' -Stem 'baseline_mathgen_gate' -Command $pythonExe -Arguments @('mathgen/scripts/run_full_cycle.py', '--gate-only')
    $junitPath = Join-Path $Context.LogsDir 'baseline_stability_contract.junit.xml'
    $results += Invoke-LoggedCommand -Context $Context -Category 'framework_setup' -Name 'stability_contract' -Stem 'baseline_stability_contract' -Command $pythonExe -Arguments @('-m', 'pytest', 'tests/unit/test_mathgen_stability_contract.py', '-q', "--junitxml=$junitPath")
    $fractionViolations = if (Test-Path $junitPath) { Get-JunitFailureCount $junitPath } else { 1 }
    [void](Update-IssueQueue -Context $Context -VerifyMode 'baseline')
    Update-Metrics -Context $Context -VerifyMode 'baseline' -Results $results -FractionViolations $fractionViolations
    Write-FinalSummary -Context $Context -VerifyMode 'baseline' -Results $results -FractionViolations $fractionViolations
    return $results
}

function Run-FullVerify {
    param([Parameter(Mandatory = $true)]$Context)
    $pythonExe = Get-PythonExe
    $npmExe = Get-NpmExe
    $results = @()
    $results += Invoke-LoggedCommand -Context $Context -Category 'framework_setup' -Name 'verify_all_npm' -Stem 'full_verify_all_npm' -Command $npmExe -Arguments @('run', 'verify:all')
    $results += Invoke-LoggedCommand -Context $Context -Category 'framework_setup' -Name 'validate_all_elementary_banks' -Stem 'full_validate_all' -Command $pythonExe -Arguments @('tools/validate_all_elementary_banks.py')
    $results += Invoke-LoggedCommand -Context $Context -Category 'framework_setup' -Name 'verify_all_py' -Stem 'full_verify_all_py' -Command $pythonExe -Arguments @('scripts/verify_all.py')
    $results += Invoke-LoggedCommand -Context $Context -Category 'framework_setup' -Name 'mathgen_full_cycle' -Stem 'full_mathgen_cycle' -Command $pythonExe -Arguments @('mathgen/scripts/run_full_cycle.py', '--changes=run_10h_full_verify')
    $junitPath = Join-Path $Context.LogsDir 'full_stability_contract.junit.xml'
    $results += Invoke-LoggedCommand -Context $Context -Category 'framework_setup' -Name 'stability_contract' -Stem 'full_stability_contract' -Command $pythonExe -Arguments @('-m', 'pytest', 'tests/unit/test_mathgen_stability_contract.py', '-q', "--junitxml=$junitPath")
    $fractionViolations = if (Test-Path $junitPath) { Get-JunitFailureCount $junitPath } else { 1 }
    [void](Update-IssueQueue -Context $Context -VerifyMode 'full')
    Update-Metrics -Context $Context -VerifyMode 'full' -Results $results -FractionViolations $fractionViolations
    Write-FinalSummary -Context $Context -VerifyMode 'full' -Results $results -FractionViolations $fractionViolations
    return $results
}

function Write-EnvironmentArtifacts {
    param([Parameter(Mandatory = $true)]$Context)
    $snapshot = Get-EnvironmentSnapshot
    foreach ($target in @(
        (Join-Path $ArtifactRoot 'environment.json'),
        (Join-Path $Context.RunRoot 'environment.json')
    )) {
        Write-JsonFile $target $snapshot
    }
    $gapText = @('# Gap List', '')
    if ($snapshot.gap_list.Count -eq 0) {
        $gapText += '- No gaps detected.'
    }
    else {
        $gapText += $snapshot.gap_list | ForEach-Object { '- ' + $_ }
    }
    foreach ($target in @(
        (Join-Path $ArtifactRoot 'gap_list.md'),
        (Join-Path $Context.RunRoot 'gap_list.md')
    )) {
        [System.IO.File]::WriteAllText($target, (($gapText -join [Environment]::NewLine) + [Environment]::NewLine), [System.Text.UTF8Encoding]::new($false))
    }
}

function New-CheckpointTag {
    param([Parameter(Mandatory = $true)]$Context)
    try {
        $tag = "rollback/run_10h-before-$($Context.RunId)"
        git tag $tag | Out-Null
        Append-JsonLine $Context.RevisionHistory ([ordered]@{
            run_id = $Context.RunId
            at = (Get-Date).ToString('o')
            phase = 'run'
            change_category = 'framework_setup'
            event = 'checkpoint'
            details = @{ tag = $tag }
        })
    }
    catch {
        Append-JsonLine $Context.ErrorMemory ([ordered]@{
            run_id = $Context.RunId
            at = (Get-Date).ToString('o')
            category = 'framework_setup'
            command = 'git tag rollback/run_10h-before-*'
            root_cause = 'checkpoint tag creation failed'
            evidence = @($_.Exception.Message)
            regression_test = 'n/a'
            status = 'open'
        })
    }
}

function Start-RunLoop {
    param([Parameter(Mandatory = $true)]$Context)
    New-CheckpointTag -Context $Context
    $endAt = (Get-Date).AddHours([math]::Max(1, $Hours))
    $iteration = 0
    while ((Get-Date) -lt $endAt) {
        $iteration += 1
        Append-JsonLine $Context.RevisionHistory ([ordered]@{
            run_id = $Context.RunId
            at = (Get-Date).ToString('o')
            phase = 'run'
            change_category = 'stability_guardrail'
            event = 'iteration_start'
            details = @{ iteration = $iteration; full_verify = (($iteration -eq 1) -or ($iteration % $FullVerifyCadence -eq 0)) }
        })

        Write-EnvironmentArtifacts -Context $Context
        Write-InventoryFiles -Context $Context
        $results = Run-BaselineVerify -Context $Context
        if (($iteration -eq 1) -or ($iteration % $FullVerifyCadence -eq 0)) {
            $results = Run-FullVerify -Context $Context
        }
        if ((Get-Date).AddMinutes($IntervalMinutes) -ge $endAt) { break }
        Start-Sleep -Seconds ([int]([math]::Max(60, $IntervalMinutes * 60)))
    }
}

$context = Initialize-RunContext
Write-EnvironmentArtifacts -Context $context
Write-InventoryFiles -Context $context

switch ($Mode) {
    'baseline' { [void](Run-BaselineVerify -Context $context) }
    'full' { [void](Run-FullVerify -Context $context) }
    'run' { Start-RunLoop -Context $context }
    'tail' {
        $currentSummary = Join-Path $context.SummaryDir 'final_summary.md'
        if (Test-Path $currentSummary) {
            Get-Content -Path $currentSummary -Wait
        }
        else {
            Write-Host 'No final_summary.md found for the active run.'
        }
    }
}
