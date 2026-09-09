$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot
$cli = Join-Path $projectRoot '.tools/npm/package/bin/npm-cli.js'
if (!(Test-Path -LiteralPath $cli)) { throw 'Run .\tools\bootstrap-npm.ps1 first, or use your installed npm.' }
$env:npm_config_cache = Join-Path $projectRoot '.cache/npm'
& node $cli @args
exit $LASTEXITCODE
