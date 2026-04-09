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
# Extract languages + translators
# -----------------------------
$languages = $config.languages
if (-not $languages -or $languages.Count -eq 0)
{
    Write-Error "No languages configured in languages.json"
    exit 1
}
Write-Host "Languages: $($languages -join ', ')"

$translators = @{ }
if ($null -ne $config.translators)
{
    foreach ($prop in $config.translators.PSObject.Properties)
    {
        $name = $prop.Name
        $cfg = $prop.Value
        if ($cfg -is [string])
        {
            $baseName = $cfg
        }
        else
        {
            $baseName = $cfg.base_file_name
        }

        if ( [string]::IsNullOrWhiteSpace($baseName))
        {
            Write-Error "Translator '$name' must define base_file_name"
            exit 1
        }
        $includeRoots = @()
        if ($cfg -isnot [string] -and $null -ne $cfg.include_roots)
        {
            $includeRoots = @($cfg.include_roots)
        }

        $translators[$name] = [PSCustomObject]@{
            BaseName = $baseName
            IncludeRoots = $includeRoots
        }
    }
}
elseif ($null -ne $config.base_file_name)
{
    # Backward compatibility
    $translators["app"] = [PSCustomObject]@{
        BaseName = $config.base_file_name
        IncludeRoots = @()
    }
}
else
{
    Write-Error "No translators configured in languages.json"
    exit 1
}

Write-Host "Translators: $( $translators.Keys -join ', ' )"

# -----------------------------
# Virtual environment
# -----------------------------
function Find-VenvActivateUpward {
    param(
        [Parameter(Mandatory = $true)]
        [string]$startDir
    )

    $currentDir = Resolve-Path $startDir
    while ($null -ne $currentDir) {
        $candidatePaths = @(
            (Join-Path $currentDir ".venv\Scripts\Activate.ps1"),
            (Join-Path $currentDir "venv\Scripts\Activate.ps1")
        )

        foreach ($candidate in $candidatePaths) {
            if (Test-Path $candidate) {
                return $candidate
            }
        }

        $parentDir = Split-Path $currentDir -Parent
        if ($parentDir -eq $currentDir -or [string]::IsNullOrWhiteSpace($parentDir)) {
            break
        }
        $currentDir = $parentDir
    }

    return $null
}

$venvActivate = Find-VenvActivateUpward -startDir $scriptDir
if ($venvActivate) {
    Write-Host "Activating virtual environment: $venvActivate"
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
    foreach ($translator in $translators.Values)
    {
        $validFiles += (Split-Path ($translator.BaseName + $lang + ".ts") -Leaf)
        $validFiles += (Split-Path ($translator.BaseName + $lang + ".qm") -Leaf)
    }
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
$allPyFiles = Get-ChildItem -Path (Join-Path $projectRoot "Control_Optimizer\src") -Recurse -Include *.py |
        Where-Object { $_.FullName -notmatch "\\__pycache__\\" } |
    ForEach-Object { $_.FullName }

$allPyFiles += Join-Path $projectRoot "Control_Optimizer\src\main.py"

Write-Host "Found $( $allPyFiles.Count ) Python files to scan for translation"

# -----------------------------
# Assign files to translators
# -----------------------------
$translatorFiles = @{ }
$nonAppFiles = [System.Collections.Generic.HashSet[string]]::new()
$fileOwners = @{ }

foreach ($translatorKey in $translators.Keys)
{
    if ($translatorKey -eq "app")
    {
        continue
    }

    $includeRoots = $translators[$translatorKey].IncludeRoots
    if (-not $includeRoots -or $includeRoots.Count -eq 0)
    {
        Write-Warning "Translator '$translatorKey' has no include_roots configured"
        $translatorFiles[$translatorKey] = @()
        continue
    }

    $resolvedRoots = @()
    foreach ($root in $includeRoots)
    {
        if ( [string]::IsNullOrWhiteSpace($root))
        {
            continue
        }
        if ( [System.IO.Path]::IsPathRooted($root))
        {
            $resolvedRoots += (Resolve-Path $root).Path
        }
        else
        {
            $resolvedRoots += (Resolve-Path (Join-Path $projectRoot $root)).Path
        }
    }

    $matched = @()
    foreach ($file in $allPyFiles)
    {
        foreach ($rootPath in $resolvedRoots)
        {
            if ( $file.ToLowerInvariant().StartsWith($rootPath.ToLowerInvariant()))
            {
                $matched += $file
                $nonAppFiles.Add($file) | Out-Null
                if (-not $fileOwners.ContainsKey($file))
                {
                    $fileOwners[$file] = @()
                }
                $fileOwners[$file] += $translatorKey
                break
            }
        }
    }

    $translatorFiles[$translatorKey] = $matched
}

foreach ($file in $fileOwners.Keys)
{
    $owners = $fileOwners[$file]
    if ($owners.Count -gt 1)
    {
        Write-Warning "Python file belongs to multiple translators: $file -> $( $owners -join ', ' )"
    }
}

$appFiles = @()
foreach ($file in $allPyFiles)
{
    if (-not $nonAppFiles.Contains($file))
    {
        $appFiles += $file
    }
}
$translatorFiles["app"] = $appFiles

# -----------------------------
# Process active languages
# -----------------------------
foreach ($lang in $languages) {
    foreach ($translatorKey in $translators.Keys)
    {
        $baseName = $translators[$translatorKey].BaseName
        $sourceFiles = $translatorFiles[$translatorKey]
        if (-not $sourceFiles -or $sourceFiles.Count -eq 0)
        {
            Write-Warning "No source files assigned to translator '$translatorKey' (skipping)"
            continue
        }

        $tsFile = Join-Path $i18nDir ($baseName + $lang + ".ts")
        $qmFile = Join-Path $i18nDir ($baseName + $lang + ".qm")

        Write-Host "Processing translator: $translatorKey | language: $lang"
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
        if ($hasNewStrings)
        {
            Write-Host "New strings detected -> opening Qt Linguist"
            pyside6-linguist $tsFile
        }

        # -------------------------
        # Build qm file
        # -------------------------
        Write-Host "Building qm file"
        pyside6-lrelease $tsFile -qm $qmFile
    }
}

Write-Host "i18n build finished"
