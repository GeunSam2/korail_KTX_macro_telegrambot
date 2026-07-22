$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

if (-not (Test-Path ".venv-gui\Scripts\python.exe")) {
    py -3.12 -m venv .venv-gui
}

& .venv-gui\Scripts\python.exe -m pip install --upgrade pip
& .venv-gui\Scripts\python.exe -m pip install -r requirements-gui.txt
$env:PYTHONPATH = Join-Path $RepoRoot "src"
& .venv-gui\Scripts\python.exe -m pytest tests/unit tests/gui -q --confcutdir=tests/gui
& .venv-gui\Scripts\pyinstaller.exe --noconfirm --clean --workpath build-gui --distpath dist KorailKTXDesktop.spec

Write-Host "Build complete: $RepoRoot\dist\KTX 자동예약\KTX 자동예약.exe"
