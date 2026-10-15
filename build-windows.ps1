$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m pip install -e . pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
python -m PyInstaller --noconfirm --clean --onefile --windowed --name AION2-Global-Translator --paths src --collect-all blake3 --collect-all lz4 --hidden-import aion2_global_translator.codec --hidden-import aion2_global_translator.providers --hidden-import aion2_global_translator.protection app_entry.py
if ($LASTEXITCODE -ne 0) { throw 'Application build failed' }
