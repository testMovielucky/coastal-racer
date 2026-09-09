$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
$toolDir = Join-Path $projectRoot '.tools/npm'
New-Item -ItemType Directory -Force -Path $toolDir | Out-Null
$archive = Join-Path $toolDir 'npm.tgz'
Invoke-WebRequest -Uri 'https://registry.npmjs.org/npm/-/npm-11.6.2.tgz' -OutFile $archive
tar -xzf $archive -C $toolDir
if ($LASTEXITCODE -ne 0) { throw 'npm archive extraction failed' }
Write-Output 'Local npm ready. Run: .\tools\npm.ps1 install'
