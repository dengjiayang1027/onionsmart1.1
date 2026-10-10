$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONPATH = Join-Path $PSScriptRoot '.runtime'
$projectPython = 'C:\Users\rense\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $projectPython -m streamlit run app.py
