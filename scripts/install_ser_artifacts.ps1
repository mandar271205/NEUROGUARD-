param(
    [string]$ProjectRoot = (Resolve-Path ".").Path,
    [string]$SourceModels = (Join-Path (Resolve-Path ".").Path "saved_models"),
    [string]$SourceConfigs = (Join-Path (Resolve-Path ".").Path "saved_modelconfigs")
)

$ErrorActionPreference = "Stop"

$stressRepo = Join-Path $ProjectRoot "third_party\Stress-Detection-Through-Speech-Emotion-Recognition"
$targets = @(
    (Join-Path $stressRepo "backbone\base_store"),
    (Join-Path $stressRepo "backbone_independent\base_store")
)

$datasets = @("ravdess", "cremad", "emodb", "shemo")
$genders = @("female", "male")

foreach ($baseStore in $targets) {
    New-Item -ItemType Directory -Force -Path `
        (Join-Path $baseStore "saved_models"), `
        (Join-Path $baseStore "saved_modelconfigs") | Out-Null
}

foreach ($dataset in $datasets) {
    foreach ($gender in $genders) {
        $srcModelDir = Join-Path $SourceModels "$dataset\$gender"
        $srcConfigDir = Join-Path $SourceConfigs "$dataset\$gender"

        if (-not (Test-Path $srcModelDir) -or -not (Test-Path $srcConfigDir)) {
            Write-Host "Skipping missing artifacts: $dataset/$gender"
            continue
        }

        foreach ($baseStore in $targets) {
            $dstModelDir = Join-Path $baseStore "saved_models\$dataset\$gender"
            $dstConfigDir = Join-Path $baseStore "saved_modelconfigs\$dataset\$gender"
            New-Item -ItemType Directory -Force -Path $dstModelDir, $dstConfigDir | Out-Null

            $srcH5 = Join-Path $srcModelDir "model.h5"
            $srcTflite = Join-Path $srcModelDir "model.tflite"
            $srcConfig = Join-Path $srcConfigDir "config.pkl"

            if (Test-Path $srcH5) {
                Copy-Item -LiteralPath $srcH5 -Destination (Join-Path $dstModelDir "model.h5") -Force
                Copy-Item -LiteralPath $srcH5 -Destination (Join-Path $dstModelDir "convolutional.h5") -Force
            }

            if (Test-Path $srcTflite) {
                Copy-Item -LiteralPath $srcTflite -Destination (Join-Path $dstModelDir "model.tflite") -Force
                Copy-Item -LiteralPath $srcTflite -Destination (Join-Path $dstModelDir "convolutional.tflite") -Force
            }

            if (Test-Path $srcConfig) {
                Copy-Item -LiteralPath $srcConfig -Destination (Join-Path $dstConfigDir "config.pkl") -Force
                Copy-Item -LiteralPath $srcConfig -Destination (Join-Path $dstConfigDir "convolutional") -Force
            }
        }

        Write-Host "Installed artifacts: $dataset/$gender"
    }
}

Write-Host "Done installing SER artifacts into backbone and backbone_independent base_store folders."
