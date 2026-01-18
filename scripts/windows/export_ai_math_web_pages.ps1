param(
  [string]$OutDir = "dist_ai_math_web_pages"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $root "..\..")
$out = Join-Path $repoRoot $OutDir

if (Test-Path $out) {
  Remove-Item -Recurse -Force $out
}
New-Item -ItemType Directory -Force -Path $out | Out-Null

Copy-Item -Recurse -Force (Join-Path $repoRoot "docs") (Join-Path $out "docs")
Copy-Item -Force (Join-Path $repoRoot "PUBLISH_GITHUB_PAGES.md") (Join-Path $out "PUBLISH_GITHUB_PAGES.md")

"Exported to: $out"