# build-i18n.ps1
# -------------------------------------------------
# i18n build script for PySide6
# - loads languages from languages.json
# - activates virtual environment if it exists
# - removes i18n files for languages not in config
# - updates .ts files for active languages
# - opens Qt Linguist only if new strings are found
# - builds .qm files
# -------------------------------------------------

# -----------------------------
# Script directory
# -----------------------------
$scriptDir = $PSScriptRoot

# Projekt-Root
$projectRoot = Resolve-Path (Join-Path $scriptDir "..\..\..")

# -----------------------------
# Load languages.json
# -----------------------------
$configFile = Join-Path $projectRoot "Control_Optimizer\src\config\languages.json"

if (!(Test-Path $configFile)) {
    Write-Error "languages.json not found: $configFile"
    exit 1
}

try {
    $config = Get-Content $configFile -Raw | ConvertFrom-Json
}
catch {
    Write-Error "Failed to parse languages.json"
    exit 1
}

# -----------------------------
# Extract languages
# -----------------------------
$languages = $config.languages.PSObject.Properties.Name
Write-Host "Languages: $($languages -join ', ')"

# -----------------------------
# Virtual environment
# -----------------------------
$venvActivate = Join-Path $projectRoot ".venv\Scripts\Activate.ps1"

if (Test-Path $venvActivate) {
    Write-Host "Activating virtual environment..."
    . $venvActivate
} else {
    Write-Host "No virtual environment found, continuing without venv"
}

# -----------------------------
# Remove obsolete .ts/.qm files
# -----------------------------
Write-Host "Checking for obsolete i18n files..."
$validFiles = @()
foreach ($lang in $languages) {
    $validFiles += (Split-Path $config.languages.$lang.ts -Leaf)
    $validFiles += (Split-Path $config.languages.$lang.qm -Leaf)
}

$i18nDir = Join-Path $projectRoot "Control_Optimizer\src\i18n"

Get-ChildItem -Path $i18nDir -File |
Where-Object { $_.Extension -in ".ts", ".qm" } |
ForEach-Object {
    if ($validFiles -notcontains $_.Name) {
        Write-Host "Removing obsolete file: $($_.Name)"
        Remove-Item $_.FullName -Force
    }
}

# -----------------------------
# Gather all relevant Python files
# -----------------------------
$includeDirs = @("app_engine", "models", "resources", "services", "utils", "viewmodels", "views")
$sourceFiles = Get-ChildItem -Path (Join-Path $projectRoot "Control_Optimizer\src") -Recurse -Include *.py |
    Where-Object { $includeDirs -contains $_.Directory.Name } |
    ForEach-Object { $_.FullName }

$sourceFiles += Join-Path $projectRoot "Control_Optimizer\src\main.py"

Write-Host "Found $($sourceFiles.Count) Python files to scan for translation"

# -----------------------------
# Process active languages
# -----------------------------
foreach ($lang in $languages) {

    $langCfg = $config.languages.$lang
    $tsFile = Join-Path $i18nDir $langCfg.ts
    $qmFile = Join-Path $i18nDir $langCfg.qm

    Write-Host "Processing language: $lang"
    Write-Host " TS: $tsFile"
    Write-Host " QM: $qmFile"

    # -------------------------
    # Run lupdate on all files
    # -------------------------
    $output = pyside6-lupdate @($sourceFiles) -ts $tsFile 2>&1
    $output | Write-Host

    # Detect new strings
    $hasNewStrings = !($output -match "\(0 new")

    # -------------------------
    # Open Qt Linguist if needed
    # -------------------------
    if ($hasNewStrings) {
        Write-Host "New strings detected → opening Qt Linguist"
        pyside6-linguist $tsFile
    }

    # -------------------------
    # Build qm file
    # -------------------------
    Write-Host "Building qm file"
    pyside6-lrelease $tsFile -qm $qmFile
}

Write-Host "i18n build finished"
