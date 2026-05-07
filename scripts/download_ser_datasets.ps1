param(
    [string]$ProjectRoot = (Resolve-Path ".").Path
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$stressRepo = Join-Path $ProjectRoot "third_party\Stress-Detection-Through-Speech-Emotion-Recognition"
$resources = Join-Path $ProjectRoot "third_party\Resources\Databases"
$downloads = Join-Path $ProjectRoot "third_party\downloads\ser_datasets"
$cleanAudio = Join-Path $stressRepo "backbone\base_store\clean_audio"

New-Item -ItemType Directory -Force -Path $resources, $downloads, $cleanAudio | Out-Null

function Download-IfMissing {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$OutFile
    )

    if (Test-Path $OutFile) {
        Write-Host "Already downloaded: $OutFile"
        return
    }

    Write-Host "Downloading: $Uri"
    Invoke-WebRequest -Uri $Uri -OutFile $OutFile -MaximumRedirection 10
}

function Expand-IfNeeded {
    param(
        [Parameter(Mandatory = $true)][string]$Archive,
        [Parameter(Mandatory = $true)][string]$Destination,
        [string]$Marker
    )

    if ($Marker -and (Test-Path (Join-Path $Destination $Marker))) {
        Write-Host "Already extracted: $Destination"
        return
    }

    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Write-Host "Extracting: $Archive"
    Expand-Archive -Path $Archive -DestinationPath $Destination -Force
}

# 1. RAVDESS speech audio
$ravdessZip = Join-Path $downloads "ravdess_audio_speech.zip"
$ravdessDest = Join-Path $resources "RAVDESS_Audio"
Download-IfMissing "https://zenodo.org/records/1188976/files/Audio_Speech_Actors_01-24.zip" $ravdessZip
Expand-IfNeeded $ravdessZip $ravdessDest "Actor_01"

# 2. EmoDB
$emodbZip = Join-Path $downloads "emodb_download.zip"
$emodbDest = Join-Path $resources "EmoDB"
Download-IfMissing "http://emodb.bilderbar.info/download/download.zip" $emodbZip
Expand-IfNeeded $emodbZip $emodbDest "wav"

# 3. CREMA-D audio + demographics via sparse checkout
$cremadDest = Join-Path $resources "CREMA-D"
if (-not (Test-Path (Join-Path $cremadDest ".git"))) {
    if (Test-Path $cremadDest) {
        $existing = Get-ChildItem -Force $cremadDest
        if ($existing.Count -gt 0) {
            throw "CREMA-D destination exists but is not a git checkout: $cremadDest"
        }
    }
    Write-Host "Cloning CREMA-D audio/demographics with sparse checkout..."
    git clone --depth 1 --filter=blob:none --sparse https://github.com/CheyneyComputerScience/CREMA-D.git $cremadDest
    Push-Location $cremadDest
    git sparse-checkout set --no-cone "/AudioMP3/*" "/VideoDemographics.csv"
    Pop-Location
} else {
    Write-Host "CREMA-D already present: $cremadDest"
    Push-Location $cremadDest
    git sparse-checkout set --no-cone "/AudioMP3/*" "/VideoDemographics.csv"
    Pop-Location
}

# 4. ShEMO
$shemoDest = Join-Path $resources "ShEMO"
if (-not (Test-Path (Join-Path $shemoDest ".git"))) {
    if (Test-Path $shemoDest) {
        $existing = Get-ChildItem -Force $shemoDest
        if ($existing.Count -gt 0) {
            throw "ShEMO destination exists but is not a git checkout: $shemoDest"
        }
    }
    Write-Host "Cloning ShEMO..."
    git clone --depth 1 https://github.com/mansourehk/ShEMO.git $shemoDest
} else {
    Write-Host "ShEMO already present: $shemoDest"
}

python (Join-Path $ProjectRoot "scripts\organize_ser_datasets.py") `
    --resources $resources `
    --clean-audio $cleanAudio

$rootBaseStore = Join-Path $stressRepo "base_store"
$backboneBaseStore = Join-Path $stressRepo "backbone\base_store"
if (-not (Test-Path $rootBaseStore)) {
    New-Item -ItemType Junction -Path $rootBaseStore -Target $backboneBaseStore | Out-Null
    Write-Host "Created compatibility junction: $rootBaseStore -> $backboneBaseStore"
}

Write-Host "Done. Raw datasets: $resources"
Write-Host "Clean/gender split audio: $cleanAudio"
